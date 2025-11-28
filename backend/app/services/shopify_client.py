"""Shopify GraphQL Admin API client.

WHAT:
    Wrapper for Shopify Admin GraphQL API with:
    - Authentication handling
    - Rate limiting (2 requests/second)
    - Cursor-based pagination
    - Error handling and retries

WHY:
    Encapsulates all Shopify API interaction for the sync service.
    GraphQL is preferred over REST for efficiency (single request for related data).

REFERENCES:
    - Shopify GraphQL Admin API: https://shopify.dev/docs/api/admin-graphql
    - Rate limits: https://shopify.dev/docs/api/usage/rate-limits
    - Pagination: https://shopify.dev/docs/api/usage/pagination-graphql
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import httpx

logger = logging.getLogger(__name__)

# Default API version
DEFAULT_API_VERSION = "2024-07"

# Rate limiting: Shopify allows 2 requests/second for regular apps
# We use a simple semaphore-based rate limiter
RATE_LIMIT_DELAY = 0.5  # seconds between requests (2 req/sec)


class ShopifyAPIError(Exception):
    """Custom exception for Shopify API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, errors: Optional[List] = None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class ShopifyClient:
    """GraphQL client for Shopify Admin API.

    WHAT: Handles all communication with Shopify's GraphQL Admin API
    WHY: Centralized API access with rate limiting, pagination, and error handling

    Usage:
        client = ShopifyClient(shop_domain="mystore.myshopify.com", access_token="shpat_xxx")
        shop = await client.get_shop()
        products, cursor = await client.get_products()
    """

    def __init__(
        self,
        shop_domain: str,
        access_token: str,
        api_version: str = DEFAULT_API_VERSION,
    ):
        """Initialize Shopify client.

        Args:
            shop_domain: Shopify store domain (e.g., "mystore.myshopify.com")
            access_token: Shopify Admin API access token
            api_version: API version to use (default: 2024-07)
        """
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"

        # Rate limiting
        self._last_request_time: float = 0

        logger.info(f"[SHOPIFY_CLIENT] Initialized for {shop_domain} (API version: {api_version})")

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        WHAT: Wait if needed to respect 2 req/sec limit
        WHY: Shopify will return 429 errors if we exceed rate limits
        """
        import time

        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - elapsed
            logger.debug(f"[SHOPIFY_CLIENT] Rate limiting: waiting {wait_time:.3f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()

    async def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against Shopify Admin API.

        WHAT: Send GraphQL request with rate limiting and retry logic
        WHY: All Shopify data fetching goes through this method

        Args:
            query: GraphQL query string
            variables: Query variables (optional)
            retries: Number of retry attempts for transient errors

        Returns:
            Response data from GraphQL query

        Raises:
            ShopifyAPIError: If query fails after all retries
        """
        await self._rate_limit()

        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error = None

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers=headers,
                    )

                    # Handle rate limiting (429)
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 2))
                        logger.warning(
                            f"[SHOPIFY_CLIENT] Rate limited, waiting {retry_after}s (attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Check for GraphQL errors
                    if "errors" in data:
                        errors = data["errors"]
                        error_messages = [e.get("message", str(e)) for e in errors]
                        logger.error(f"[SHOPIFY_CLIENT] GraphQL errors: {error_messages}")

                        # Check if it's a throttling error
                        if any("throttled" in msg.lower() for msg in error_messages):
                            logger.warning(f"[SHOPIFY_CLIENT] Throttled, waiting 2s")
                            await asyncio.sleep(2)
                            continue

                        raise ShopifyAPIError(
                            f"GraphQL errors: {', '.join(error_messages)}",
                            errors=errors,
                        )

                    return data.get("data", {})

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"[SHOPIFY_CLIENT] HTTP error {e.response.status_code} (attempt {attempt + 1}/{retries})"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"[SHOPIFY_CLIENT] Request error: {e} (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        raise ShopifyAPIError(f"Failed after {retries} attempts: {last_error}")

    # =========================================================================
    # SHOP QUERIES
    # =========================================================================

    async def get_shop(self) -> Dict[str, Any]:
        """Fetch shop information.

        WHAT: Get shop metadata (name, currency, timezone, etc.)
        WHY: Need shop settings for connection configuration

        Returns:
            Shop data dictionary
        """
        query = """
        query GetShop {
            shop {
                id
                name
                email
                currencyCode
                ianaTimezone
                primaryDomain {
                    host
                }
                plan {
                    displayName
                }
                billingAddress {
                    countryCodeV2
                }
            }
        }
        """

        data = await self.execute(query)
        shop = data.get("shop", {})

        return {
            "id": shop.get("id", "").replace("gid://shopify/Shop/", ""),
            "name": shop.get("name"),
            "email": shop.get("email"),
            "currency": shop.get("currencyCode", "USD"),
            "timezone": shop.get("ianaTimezone", "UTC"),
            "domain": shop.get("primaryDomain", {}).get("host"),
            "plan_name": shop.get("plan", {}).get("displayName"),
            "country_code": shop.get("billingAddress", {}).get("countryCodeV2"),
        }

    # =========================================================================
    # PRODUCT QUERIES
    # =========================================================================

    async def get_products(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch products with pagination.

        WHAT: Get product catalog with pricing and cost information
        WHY: Need products for profit calculation (COGS from cost metafield or inventory)

        Args:
            cursor: Pagination cursor (None for first page)
            limit: Number of products per page (max 250)

        Returns:
            Tuple of (products list, next_cursor or None if last page)
        """
        query = """
        query GetProducts($cursor: String, $limit: Int!) {
            products(first: $limit, after: $cursor) {
                edges {
                    node {
                        id
                        title
                        handle
                        status
                        vendor
                        productType
                        createdAt
                        updatedAt
                        totalInventory
                        variants(first: 10) {
                            edges {
                                node {
                                    id
                                    price
                                    compareAtPrice
                                    inventoryItem {
                                        unitCost {
                                            amount
                                            currencyCode
                                        }
                                    }
                                }
                            }
                        }
                        metafield(namespace: "custom", key: "cost_per_item") {
                            value
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        data = await self.execute(query, {"cursor": cursor, "limit": limit})
        products_data = data.get("products", {})
        edges = products_data.get("edges", [])
        page_info = products_data.get("pageInfo", {})

        products = []
        for edge in edges:
            node = edge.get("node", {})
            variants = node.get("variants", {}).get("edges", [])

            # Get price and cost from first variant
            first_variant = variants[0]["node"] if variants else {}
            price = first_variant.get("price")
            compare_at_price = first_variant.get("compareAtPrice")

            # Try to get cost from inventory item
            cost_per_item = None
            cost_source = None
            inventory_item = first_variant.get("inventoryItem", {})
            unit_cost = inventory_item.get("unitCost", {})
            if unit_cost and unit_cost.get("amount"):
                cost_per_item = Decimal(unit_cost["amount"])
                cost_source = "inventory_item"

            # Fallback to metafield cost
            if cost_per_item is None:
                metafield = node.get("metafield")
                if metafield and metafield.get("value"):
                    try:
                        cost_per_item = Decimal(metafield["value"])
                        cost_source = "metafield"
                    except (ValueError, TypeError):
                        pass

            products.append({
                "external_product_id": node.get("id"),
                "title": node.get("title"),
                "handle": node.get("handle"),
                "status": node.get("status", "active").lower(),
                "vendor": node.get("vendor"),
                "product_type": node.get("productType"),
                "price": Decimal(price) if price else None,
                "compare_at_price": Decimal(compare_at_price) if compare_at_price else None,
                "cost_per_item": cost_per_item,
                "cost_source": cost_source,
                "total_inventory": node.get("totalInventory"),
                "shopify_created_at": node.get("createdAt"),
                "shopify_updated_at": node.get("updatedAt"),
            })

        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None

        logger.info(f"[SHOPIFY_CLIENT] Fetched {len(products)} products (has_next: {page_info.get('hasNextPage')})")

        return products, next_cursor

    # =========================================================================
    # CUSTOMER QUERIES
    # =========================================================================

    async def get_customers(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch customers with pagination.

        WHAT: Get customer data with order stats
        WHY: Need customers for LTV calculations

        Args:
            cursor: Pagination cursor (None for first page)
            limit: Number of customers per page (max 250)

        Returns:
            Tuple of (customers list, next_cursor or None if last page)
        """
        # NOTE: ordersCount and totalSpent were removed in Shopify API 2024-07
        # We calculate these from orders in _update_customer_ltv after order sync
        #
        # PROTECTED CUSTOMER DATA: email, firstName, lastName, phone require
        # Protected Customer Data Access approval. We only request non-protected fields.
        # See: https://shopify.dev/docs/apps/launch/protected-customer-data
        query = """
        query GetCustomers($cursor: String, $limit: Int!) {
            customers(first: $limit, after: $cursor) {
                edges {
                    node {
                        id
                        state
                        verifiedEmail
                        createdAt
                        tags
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        data = await self.execute(query, {"cursor": cursor, "limit": limit})
        customers_data = data.get("customers", {})
        edges = customers_data.get("edges", [])
        page_info = customers_data.get("pageInfo", {})

        customers = []
        for edge in edges:
            node = edge.get("node", {})

            # NOTE: Protected fields (email, firstName, lastName, phone, emailMarketingConsent)
            # are not requested since app doesn't have Protected Customer Data access.
            # These are set to None and can be populated later if access is granted.
            #
            # NOTE: total_spent and order_count are calculated from orders
            # in _update_customer_ltv after order sync
            customers.append({
                "external_customer_id": node.get("id"),
                "email": None,  # Protected field - requires approval
                "first_name": None,  # Protected field - requires approval
                "last_name": None,  # Protected field - requires approval
                "phone": None,  # Protected field - requires approval
                "state": node.get("state"),
                "verified_email": node.get("verifiedEmail", False),
                "accepts_marketing": False,  # Requires emailMarketingConsent (protected)
                "total_spent": Decimal("0"),  # Calculated from orders
                "order_count": 0,  # Calculated from orders
                "tags": node.get("tags", []),
                "shopify_created_at": node.get("createdAt"),
            })

        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None

        logger.info(f"[SHOPIFY_CLIENT] Fetched {len(customers)} customers (has_next: {page_info.get('hasNextPage')})")

        return customers, next_cursor

    # =========================================================================
    # ORDER QUERIES
    # =========================================================================

    async def get_orders(
        self,
        since: Optional[datetime] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch orders with line items and attribution.

        WHAT: Get order data with line items for revenue and profit calculation
        WHY: Orders are the source of truth for revenue metrics

        Args:
            since: Only fetch orders created after this datetime
            cursor: Pagination cursor (None for first page)
            limit: Number of orders per page (max 250)

        Returns:
            Tuple of (orders list, next_cursor or None if last page)

        Note:
            By default, only last 60 days of orders are accessible.
            Need read_all_orders scope for historical orders.
        """
        # Build query filter
        query_filter = ""
        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            query_filter = f'created_at:>"{since_str}"'

        query = """
        query GetOrders($cursor: String, $limit: Int!, $query: String) {
            orders(first: $limit, after: $cursor, query: $query, sortKey: CREATED_AT) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        processedAt
                        closedAt
                        cancelledAt
                        cancelReason
                        displayFinancialStatus
                        displayFulfillmentStatus
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        subtotalPriceSet {
                            shopMoney {
                                amount
                            }
                        }
                        totalTaxSet {
                            shopMoney {
                                amount
                            }
                        }
                        totalShippingPriceSet {
                            shopMoney {
                                amount
                            }
                        }
                        totalDiscountsSet {
                            shopMoney {
                                amount
                            }
                        }
                        customer {
                            id
                        }
                        sourceName
                        app {
                            name
                        }
                        tags
                        note
                        lineItems(first: 100) {
                            edges {
                                node {
                                    id
                                    title
                                    variantTitle
                                    sku
                                    quantity
                                    originalUnitPriceSet {
                                        shopMoney {
                                            amount
                                        }
                                    }
                                    totalDiscountSet {
                                        shopMoney {
                                            amount
                                        }
                                    }
                                    product {
                                        id
                                    }
                                    variant {
                                        id
                                        inventoryItem {
                                            unitCost {
                                                amount
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        variables = {
            "cursor": cursor,
            "limit": limit,
            "query": query_filter if query_filter else None,
        }

        data = await self.execute(query, variables)
        orders_data = data.get("orders", {})
        edges = orders_data.get("edges", [])
        page_info = orders_data.get("pageInfo", {})

        orders = []
        for edge in edges:
            node = edge.get("node", {})

            # Parse monetary values
            def get_amount(price_set: Optional[Dict]) -> Optional[Decimal]:
                if not price_set:
                    return None
                shop_money = price_set.get("shopMoney", {})
                amount = shop_money.get("amount")
                return Decimal(amount) if amount else None

            total_price_set = node.get("totalPriceSet", {})
            currency = total_price_set.get("shopMoney", {}).get("currencyCode", "USD")

            # Parse line items
            line_items = []
            for li_edge in node.get("lineItems", {}).get("edges", []):
                li_node = li_edge.get("node", {})

                # Get cost from variant inventory item
                variant = li_node.get("variant", {})
                inventory_item = variant.get("inventoryItem", {}) if variant else {}
                unit_cost = inventory_item.get("unitCost", {})
                cost_per_item = Decimal(unit_cost["amount"]) if unit_cost and unit_cost.get("amount") else None

                line_items.append({
                    "external_line_item_id": li_node.get("id"),
                    "title": li_node.get("title"),
                    "variant_title": li_node.get("variantTitle"),
                    "sku": li_node.get("sku"),
                    "quantity": li_node.get("quantity", 1),
                    "price": get_amount(li_node.get("originalUnitPriceSet")),
                    "total_discount": get_amount(li_node.get("totalDiscountSet")) or Decimal("0"),
                    "external_product_id": li_node.get("product", {}).get("id") if li_node.get("product") else None,
                    "external_variant_id": li_node.get("variant", {}).get("id") if li_node.get("variant") else None,
                    "cost_per_item": cost_per_item,
                    "cost_source": "inventory_item" if cost_per_item else None,
                })

            # Parse order number from name (e.g., "#1001" -> 1001)
            order_name = node.get("name", "")
            order_number = None
            if order_name.startswith("#"):
                try:
                    order_number = int(order_name[1:])
                except ValueError:
                    pass

            # Parse customer
            customer = node.get("customer", {})
            customer_id = customer.get("id") if customer else None

            # NOTE: landingSite and referringSite removed in Shopify API 2024-07
            # UTM tracking would require customerJourneySummary or metafields
            landing_site = None
            utms = {}

            orders.append({
                "external_order_id": node.get("id"),
                "order_number": order_number,
                "name": order_name,
                "total_price": get_amount(node.get("totalPriceSet")),
                "subtotal_price": get_amount(node.get("subtotalPriceSet")),
                "total_tax": get_amount(node.get("totalTaxSet")),
                "total_shipping": get_amount(node.get("totalShippingPriceSet")),
                "total_discounts": get_amount(node.get("totalDiscountsSet")),
                "currency": currency,
                "financial_status": self._normalize_status(node.get("displayFinancialStatus")),
                "fulfillment_status": self._normalize_status(node.get("displayFulfillmentStatus")),
                "cancelled_at": node.get("cancelledAt"),
                "cancel_reason": node.get("cancelReason"),
                "external_customer_id": customer_id,
                "source_name": node.get("sourceName"),
                "landing_site": landing_site,
                "referring_site": None,  # Removed in Shopify API 2024-07
                "utm_source": utms.get("utm_source"),
                "utm_medium": utms.get("utm_medium"),
                "utm_campaign": utms.get("utm_campaign"),
                "utm_content": utms.get("utm_content"),
                "utm_term": utms.get("utm_term"),
                "app_name": node.get("app", {}).get("name") if node.get("app") else None,
                "tags": node.get("tags", []),
                "note": node.get("note"),
                "order_created_at": node.get("createdAt"),
                "order_processed_at": node.get("processedAt"),
                "order_closed_at": node.get("closedAt"),
                "line_items": line_items,
            })

        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None

        logger.info(f"[SHOPIFY_CLIENT] Fetched {len(orders)} orders (has_next: {page_info.get('hasNextPage')})")

        return orders, next_cursor

    def _extract_utms(self, landing_site: Optional[str]) -> Dict[str, Optional[str]]:
        """Extract UTM parameters from landing site URL.

        WHAT: Parse UTM tags from URL query string
        WHY: Enable basic attribution without full attribution engine
        """
        if not landing_site:
            return {}

        try:
            parsed = urlparse(landing_site)
            params = parse_qs(parsed.query)
            return {
                "utm_source": params.get("utm_source", [None])[0],
                "utm_medium": params.get("utm_medium", [None])[0],
                "utm_campaign": params.get("utm_campaign", [None])[0],
                "utm_content": params.get("utm_content", [None])[0],
                "utm_term": params.get("utm_term", [None])[0],
            }
        except Exception:
            return {}

    def _normalize_status(self, status: Optional[str]) -> Optional[str]:
        """Normalize Shopify status enum to lowercase.

        WHAT: Convert SCREAMING_CASE to snake_case
        WHY: Match our enum values (e.g., PARTIALLY_PAID -> partially_paid)
        """
        if not status:
            return None
        return status.lower().replace(" ", "_")

    # =========================================================================
    # PAGINATION HELPERS
    # =========================================================================

    async def get_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all products with automatic pagination.

        WHAT: Iterate through all pages of products
        WHY: Sync needs complete product catalog
        """
        all_products = []
        cursor = None

        while True:
            products, cursor = await self.get_products(cursor=cursor, limit=100)
            all_products.extend(products)

            if not cursor:
                break

        logger.info(f"[SHOPIFY_CLIENT] Fetched all {len(all_products)} products")
        return all_products

    async def get_all_customers(self) -> List[Dict[str, Any]]:
        """Fetch all customers with automatic pagination.

        WHAT: Iterate through all pages of customers
        WHY: Sync needs complete customer base for LTV
        """
        all_customers = []
        cursor = None

        while True:
            customers, cursor = await self.get_customers(cursor=cursor, limit=100)
            all_customers.extend(customers)

            if not cursor:
                break

        logger.info(f"[SHOPIFY_CLIENT] Fetched all {len(all_customers)} customers")
        return all_customers

    async def get_all_orders(
        self,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all orders with automatic pagination.

        WHAT: Iterate through all pages of orders
        WHY: Sync needs complete order history

        Args:
            since: Only fetch orders created after this datetime
        """
        all_orders = []
        cursor = None

        while True:
            orders, cursor = await self.get_orders(since=since, cursor=cursor, limit=100)
            all_orders.extend(orders)

            if not cursor:
                break

        logger.info(f"[SHOPIFY_CLIENT] Fetched all {len(all_orders)} orders")
        return all_orders
