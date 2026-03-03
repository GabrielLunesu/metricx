"""Shopify Web Pixel activation service.

WHAT:
    Manages the lifecycle of Shopify Web Pixel extensions:
    - Creates (activates) the pixel when a shop connects
    - Deletes the pixel when disconnecting

WHY:
    The Web Pixel Extension must be activated via the Shopify Admin GraphQL API
    after OAuth. Without activation, no pixel events will be captured.

REFERENCES:
    - docs/living-docs/ATTRIBUTION_ENGINE.md
    - Shopify Web Pixel API: https://shopify.dev/docs/api/admin-graphql/2024-07/mutations/webPixelCreate
    - Shopify App ID: Required for webPixelCreate mutation
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple

import httpx

from app.models import Connection

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01")
PIXEL_ENDPOINT = os.getenv("PIXEL_ENDPOINT", "https://api.metricx.ai/v1/pixel-events")


# =============================================================================
# GRAPHQL MUTATIONS
# =============================================================================

# webPixelCreate mutation
# WHAT: Creates and activates a web pixel for a shop
# WHY: Pixel must be activated before it can capture events
# REFERENCES: https://shopify.dev/docs/api/admin-graphql/2024-07/mutations/webPixelCreate
WEB_PIXEL_CREATE_MUTATION = """
mutation webPixelCreate($webPixel: WebPixelInput!) {
    webPixelCreate(webPixel: $webPixel) {
        webPixel {
            id
        }
        userErrors {
            field
            message
        }
    }
}
"""

# webPixelDelete mutation
# WHAT: Deletes a web pixel from a shop
# WHY: Clean up when shop disconnects
WEB_PIXEL_DELETE_MUTATION = """
mutation webPixelDelete($id: ID!) {
    webPixelDelete(id: $id) {
        deletedWebPixelId
        userErrors {
            field
            message
        }
    }
}
"""

# Query to get the current app's web pixel
# WHAT: Singular webPixel query (no ID) returns this app's pixel
# WHY: Each app has at most one web pixel per store
# REFERENCES: https://shopify.dev/docs/api/admin-graphql/2024-07/queries/webPixel
WEB_PIXEL_QUERY = """
query {
    webPixel {
        id
        settings
    }
}
"""


# =============================================================================
# SERVICE CLASS
# =============================================================================

class PixelActivationService:
    """Service for managing Shopify Web Pixel activation.

    WHAT: Handles creating, querying, and deleting web pixels
    WHY: Centralizes pixel lifecycle management

    Example:
        service = PixelActivationService()
        pixel_id = await service.activate_pixel(
            shop_domain="mystore.myshopify.com",
            access_token="shpat_xxx",
            workspace_id="uuid"
        )
    """

    def __init__(self):
        """Initialize the service."""
        self.api_version = SHOPIFY_API_VERSION
        self.pixel_endpoint = PIXEL_ENDPOINT

    async def _execute_graphql(
        self,
        shop_domain: str,
        access_token: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against Shopify Admin API.

        WHAT: Sends GraphQL request to Shopify
        WHY: All pixel operations use GraphQL API

        Args:
            shop_domain: The Shopify store domain
            access_token: Shop's access token
            query: GraphQL query or mutation
            variables: Optional query variables

        Returns:
            Dict containing the response data

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        url = f"https://{shop_domain}/admin/api/{self.api_version}/graphql.json"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"query": query, "variables": variables or {}},
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def activate_pixel(
        self,
        shop_domain: str,
        access_token: str,
        workspace_id: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Create and activate web pixel for a shop.

        WHAT: Creates a web pixel via Shopify GraphQL API
        WHY: Required for the pixel extension to start capturing events

        Args:
            shop_domain: The Shopify store domain
            access_token: Shop's access token from OAuth
            workspace_id: Metricx workspace ID to pass to pixel

        Returns:
            Tuple of (pixel_id, error_message):
            - (str, None) on success
            - (None, str) on failure with descriptive error

        Note:
            The pixel settings (workspaceId, apiEndpoint) are passed to the
            extension and made available in the settings object.
        """
        logger.info(f"[PIXEL_ACTIVATION] Activating pixel for {shop_domain}")

        try:
            # First check if pixel already exists
            existing_pixel_id = await self.get_existing_pixel(shop_domain, access_token)
            if existing_pixel_id:
                logger.info(
                    f"[PIXEL_ACTIVATION] Pixel already exists for {shop_domain}: {existing_pixel_id}"
                )
                return existing_pixel_id, None

            # Create the pixel with settings
            # NOTE: The settings schema must match what's defined in shopify.extension.toml
            variables = {
                "webPixel": {
                    "settings": {
                        "workspaceId": workspace_id,
                        "apiEndpoint": self.pixel_endpoint,
                    }
                }
            }

            result = await self._execute_graphql(
                shop_domain=shop_domain,
                access_token=access_token,
                query=WEB_PIXEL_CREATE_MUTATION,
                variables=variables,
            )

            # Log full response for debugging
            logger.debug(f"[PIXEL_ACTIVATION] GraphQL response: {result}")

            # Check for GraphQL-level errors first
            if result.get("errors"):
                error_msgs = [e.get("message", "Unknown error") for e in result["errors"]]
                combined = "; ".join(error_msgs)
                logger.warning(
                    f"[PIXEL_ACTIVATION] GraphQL errors for {shop_domain}: {combined}",
                    extra={"shop_domain": shop_domain}
                )
                return None, f"GraphQL errors: {combined}"

            data = result.get("data", {}).get("webPixelCreate")
            if data is None:
                error_msg = "No webPixelCreate data in Shopify response — extension may not be deployed"
                logger.warning(f"[PIXEL_ACTIVATION] {error_msg} for {shop_domain}")
                return None, error_msg

            user_errors = data.get("userErrors", [])

            if user_errors:
                error_msgs = [
                    f"{e.get('field', 'unknown')}: {e.get('message', 'Unknown error')}"
                    for e in user_errors
                ]
                combined = "; ".join(error_msgs)

                # Handle "already set" — pixel exists but wasn't found by our query
                # WHY: Can happen if pixel was created by a previous app version or
                # if get_existing_pixel query failed silently
                if any("already been set" in (e.get("message") or "") for e in user_errors):
                    logger.info(
                        f"[PIXEL_ACTIVATION] Pixel already exists for {shop_domain}, fetching ID"
                    )
                    existing_id = await self.get_existing_pixel(shop_domain, access_token)
                    if existing_id:
                        return existing_id, None
                    # If we still can't find it, fall through to error
                    return None, f"Pixel already exists but could not retrieve ID: {combined}"

                logger.warning(
                    f"[PIXEL_ACTIVATION] userErrors creating pixel for {shop_domain}: {combined}",
                    extra={"shop_domain": shop_domain}
                )
                return None, f"Shopify userErrors: {combined}"

            pixel = data.get("webPixel", {})
            pixel_id = pixel.get("id")

            if pixel_id:
                logger.info(
                    f"[PIXEL_ACTIVATION] Successfully created pixel for {shop_domain}",
                    extra={"pixel_id": pixel_id, "workspace_id": workspace_id}
                )
                return pixel_id, None
            else:
                error_msg = "Shopify returned success but no pixel ID"
                logger.warning(f"[PIXEL_ACTIVATION] {error_msg} for {shop_domain}")
                return None, error_msg

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.warning(
                f"[PIXEL_ACTIVATION] HTTP error activating pixel for {shop_domain}: {error_msg}"
            )
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(
                f"[PIXEL_ACTIVATION] Failed to activate pixel for {shop_domain}: {e}"
            )
            return None, error_msg

    async def get_existing_pixel(
        self,
        shop_domain: str,
        access_token: str,
    ) -> Optional[str]:
        """Get existing web pixel for a shop.

        WHAT: Queries the singular webPixel for the current app
        WHY: Avoid creating duplicates; reuse existing pixel
        REFERENCES: https://shopify.dev/docs/api/admin-graphql/2024-07/queries/webPixel

        Args:
            shop_domain: The Shopify store domain
            access_token: Shop's access token

        Returns:
            str: Existing pixel ID if found
            None: If no pixel exists
        """
        try:
            result = await self._execute_graphql(
                shop_domain=shop_domain,
                access_token=access_token,
                query=WEB_PIXEL_QUERY,
            )

            logger.debug(f"[PIXEL_ACTIVATION] webPixel query response for {shop_domain}: {result}")

            pixel = result.get("data", {}).get("webPixel")
            if pixel and pixel.get("id"):
                return pixel["id"]

            return None

        except Exception as e:
            logger.warning(
                f"[PIXEL_ACTIVATION] Error checking existing pixel for {shop_domain}: {e}"
            )
            return None

    async def delete_pixel(
        self,
        shop_domain: str,
        access_token: str,
        pixel_id: str,
    ) -> bool:
        """Delete a web pixel from a shop.

        WHAT: Removes the web pixel via GraphQL
        WHY: Clean up when shop disconnects or pixel needs reset

        Args:
            shop_domain: The Shopify store domain
            access_token: Shop's access token
            pixel_id: The pixel ID to delete

        Returns:
            bool: True if deleted successfully
        """
        logger.info(
            f"[PIXEL_ACTIVATION] Deleting pixel {pixel_id} from {shop_domain}"
        )

        try:
            result = await self._execute_graphql(
                shop_domain=shop_domain,
                access_token=access_token,
                query=WEB_PIXEL_DELETE_MUTATION,
                variables={"id": pixel_id},
            )

            data = result.get("data", {}).get("webPixelDelete", {})
            user_errors = data.get("userErrors", [])

            if user_errors:
                for error in user_errors:
                    logger.error(
                        f"[PIXEL_ACTIVATION] Error deleting pixel: {error.get('message')}"
                    )
                return False

            deleted_id = data.get("deletedWebPixelId")
            if deleted_id:
                logger.info(f"[PIXEL_ACTIVATION] Successfully deleted pixel {pixel_id}")
                return True

            return False

        except Exception as e:
            logger.exception(
                f"[PIXEL_ACTIVATION] Failed to delete pixel {pixel_id}: {e}"
            )
            return False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def activate_pixel_for_connection(
    connection: Connection,
    access_token: str,
    workspace_id: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Convenience function to activate pixel for a connection.

    WHAT: Activates pixel and updates connection with pixel ID
    WHY: Single function to call after OAuth completion

    Args:
        connection: The Shopify connection
        access_token: Decrypted access token
        workspace_id: Workspace ID string

    Returns:
        Tuple of (pixel_id, error_message):
        - (str, None) on success
        - (None, str) on failure with descriptive error
    """
    service = PixelActivationService()

    shop_domain = connection.external_account_id  # shop_domain stored here

    return await service.activate_pixel(
        shop_domain=shop_domain,
        access_token=access_token,
        workspace_id=workspace_id,
    )
