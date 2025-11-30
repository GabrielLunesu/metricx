"""Shopify webhook subscription service.

WHAT: Manages webhook subscriptions for Shopify stores
WHY: Webhooks must be registered via GraphQL API after OAuth
REFERENCES:
    - https://shopify.dev/docs/api/admin-graphql/2024-07/mutations/webhookSubscriptionCreate
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-07")


async def subscribe_to_webhooks(
    shop_domain: str,
    access_token: str,
) -> dict:
    """Subscribe to required webhooks for a Shopify store.

    WHAT: Register webhook subscriptions via GraphQL API
    WHY: Attribution engine needs orders/paid webhook to trigger

    Args:
        shop_domain: The shop's domain (e.g., "mystore.myshopify.com")
        access_token: The shop's access token from OAuth

    Returns:
        Dict with subscription results for each webhook topic
    """
    # Get the backend URL for webhook callbacks
    # Priority: NGROK_URL (local dev) > BACKEND_URL (production)
    backend_url = os.getenv("NGROK_URL", "").rstrip("/")
    if not backend_url:
        backend_url = os.getenv("BACKEND_URL", "").rstrip("/")

    if not backend_url:
        logger.error("[WEBHOOK_SUB] No NGROK_URL or BACKEND_URL configured")
        return {"error": "No webhook callback URL configured"}

    # Ensure HTTPS (Shopify requires it)
    if backend_url.startswith("http://"):
        backend_url = backend_url.replace("http://", "https://")
        logger.info(f"[WEBHOOK_SUB] Upgraded to HTTPS: {backend_url}")

    # Webhooks to subscribe
    webhooks = [
        {
            "topic": "ORDERS_PAID",
            "path": "/webhooks/shopify/orders/paid",
        },
        # Add more webhooks here as needed:
        # {"topic": "ORDERS_CANCELLED", "path": "/webhooks/shopify/orders/cancelled"},
    ]

    results = {}

    for webhook in webhooks:
        topic = webhook["topic"]
        callback_url = f"{backend_url}{webhook['path']}"

        try:
            result = await _create_webhook_subscription(
                shop_domain=shop_domain,
                access_token=access_token,
                topic=topic,
                callback_url=callback_url,
            )
            results[topic] = result
        except Exception as e:
            logger.error(f"[WEBHOOK_SUB] Failed to subscribe to {topic}: {e}")
            results[topic] = {"error": str(e)}

    return results


async def _create_webhook_subscription(
    shop_domain: str,
    access_token: str,
    topic: str,
    callback_url: str,
) -> dict:
    """Create a single webhook subscription via GraphQL.

    WHAT: Call webhookSubscriptionCreate mutation
    WHY: Register a specific webhook topic for callbacks

    Args:
        shop_domain: The shop's domain
        access_token: The shop's access token
        topic: Webhook topic (e.g., "ORDERS_PAID")
        callback_url: Full URL for webhook callbacks

    Returns:
        Dict with subscription ID or error
    """
    mutation = """
    mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
        webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
            webhookSubscription {
                id
                topic
                endpoint {
                    ... on WebhookHttpEndpoint {
                        callbackUrl
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """

    variables = {
        "topic": topic,
        "webhookSubscription": {
            "callbackUrl": callback_url,
            "format": "JSON",
        }
    }

    graphql_url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            graphql_url,
            headers={
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            },
            json={"query": mutation, "variables": variables},
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.error(
                f"[WEBHOOK_SUB] GraphQL request failed: {response.status_code}",
                extra={"response": response.text}
            )
            return {"error": f"HTTP {response.status_code}"}

        data = response.json()

        # Log full response for debugging
        logger.debug(f"[WEBHOOK_SUB] GraphQL response: {data}")

        # Check for GraphQL errors
        if data.get("errors"):
            errors = data["errors"]
            # Check if already registered (not a real error)
            error_msg = str(errors)
            if "has already been taken" in error_msg.lower():
                logger.info(f"[WEBHOOK_SUB] Webhook {topic} already registered")
                return {"status": "already_registered", "topic": topic}

            logger.error(f"[WEBHOOK_SUB] GraphQL errors: {errors}")
            return {"error": errors}

        # Check for user errors
        result = data.get("data", {}).get("webhookSubscriptionCreate", {})
        user_errors = result.get("userErrors", [])

        if user_errors:
            # Check for "already taken" error
            for err in user_errors:
                if "already been taken" in err.get("message", "").lower():
                    logger.info(f"[WEBHOOK_SUB] Webhook {topic} already registered")
                    return {"status": "already_registered", "topic": topic}

            logger.error(f"[WEBHOOK_SUB] User errors: {user_errors}")
            return {"error": user_errors}

        # Success
        subscription = result.get("webhookSubscription")
        if subscription:
            subscription_id = subscription.get("id")
            logger.info(
                f"[WEBHOOK_SUB] Successfully subscribed to {topic}",
                extra={
                    "subscription_id": subscription_id,
                    "callback_url": callback_url,
                }
            )
            return {
                "status": "created",
                "subscription_id": subscription_id,
                "topic": topic,
                "callback_url": callback_url,
            }

        return {"error": "No subscription returned"}


async def list_webhook_subscriptions(
    shop_domain: str,
    access_token: str,
) -> list:
    """List all webhook subscriptions for a shop.

    WHAT: Query existing webhook subscriptions
    WHY: Debug and verify webhook configuration

    Args:
        shop_domain: The shop's domain
        access_token: The shop's access token

    Returns:
        List of webhook subscriptions
    """
    query = """
    query {
        webhookSubscriptions(first: 25) {
            edges {
                node {
                    id
                    topic
                    endpoint {
                        ... on WebhookHttpEndpoint {
                            callbackUrl
                        }
                    }
                }
            }
        }
    }
    """

    graphql_url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            graphql_url,
            headers={
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.error(f"[WEBHOOK_SUB] Failed to list webhooks: {response.status_code}")
            return []

        data = response.json()
        edges = data.get("data", {}).get("webhookSubscriptions", {}).get("edges", [])

        return [
            {
                "id": edge["node"]["id"],
                "topic": edge["node"]["topic"],
                "callback_url": edge["node"]["endpoint"].get("callbackUrl"),
            }
            for edge in edges
        ]
