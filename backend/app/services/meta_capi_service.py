"""Meta Conversions API (CAPI) Service.

WHAT:
    Sends server-side conversion events to Meta for ad optimization.
    This enables better attribution and conversion tracking, especially
    for iOS 14+ users where browser tracking is limited.

WHY:
    - Server-side events are more reliable than browser pixels
    - Required for iOS 14+ optimization (ATT framework)
    - Enables offline conversion tracking
    - Deduplication with browser pixel via event_id

HOW:
    Uses Meta's Conversions API endpoint:
    POST https://graph.facebook.com/v18.0/{pixel_id}/events

REFERENCES:
    - https://developers.facebook.com/docs/marketing-api/conversions-api
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import os
import hashlib
import logging
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)

META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v18.0")
META_GRAPH_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"


class MetaCAPIError(Exception):
    """Base exception for Meta CAPI errors."""
    pass


class MetaCAPIService:
    """Service for sending server-side events to Meta Conversions API.

    WHAT: Sends purchase/lead/custom events to Meta for ad optimization
    WHY: Improves conversion tracking and ad targeting accuracy

    Usage:
        ```python
        service = MetaCAPIService(pixel_id="123456", access_token="token")
        await service.send_purchase_event(
            event_id="order_123",
            value=99.99,
            currency="USD",
            email="customer@example.com",
            order_id="ORD-001",
        )
        ```
    """

    def __init__(self, pixel_id: str, access_token: str):
        """Initialize CAPI service with pixel credentials.

        Args:
            pixel_id: Meta Pixel ID (from Meta Business Manager)
            access_token: Meta access token with ads_management permission
        """
        self.pixel_id = pixel_id
        self.access_token = access_token
        self.events_url = f"{META_GRAPH_BASE_URL}/{pixel_id}/events"

    async def send_purchase_event(
        self,
        event_id: str,
        value: Decimal,
        currency: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        order_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbclid: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
        event_source_url: Optional[str] = None,
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a Purchase conversion event to Meta.

        WHAT: Reports a completed purchase to Meta CAPI
        WHY: Enables conversion optimization and attribution

        IMPORTANT - Deduplication:
            The event_id MUST match the browser pixel's event_id to prevent
            double-counting. Our pixel uses order ID as event_id.

        Args:
            event_id: Unique ID for deduplication (use order ID)
            value: Purchase value (revenue)
            currency: ISO currency code (e.g., "USD")
            email: Customer email (will be hashed)
            phone: Customer phone (will be hashed)
            order_id: Shopify order ID for reference
            client_ip: Customer IP address
            client_user_agent: Customer browser user agent
            fbclid: Facebook click ID from URL (if available)
            fbc: Facebook browser cookie (if available)
            fbp: Facebook pixel cookie (if available)
            event_source_url: URL where conversion happened
            test_event_code: Test event code for debugging (from Events Manager)

        Returns:
            Dict with events_received count and fbtrace_id

        Raises:
            MetaCAPIError: If the API request fails
        """
        event_data = self._build_event(
            event_name="Purchase",
            event_id=event_id,
            value=value,
            currency=currency,
            email=email,
            phone=phone,
            order_id=order_id,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            fbclid=fbclid,
            fbc=fbc,
            fbp=fbp,
            event_source_url=event_source_url,
        )

        return await self._send_events([event_data], test_event_code)

    async def send_lead_event(
        self,
        event_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a Lead conversion event to Meta.

        WHAT: Reports a lead capture to Meta CAPI
        WHY: Enables lead gen campaign optimization

        Args:
            event_id: Unique ID for deduplication
            email: Lead email (will be hashed)
            phone: Lead phone (will be hashed)
            client_ip: Customer IP address
            client_user_agent: Customer browser user agent
            event_source_url: URL where lead was captured
            test_event_code: Test event code for debugging

        Returns:
            Dict with events_received count and fbtrace_id
        """
        event_data = self._build_event(
            event_name="Lead",
            event_id=event_id,
            email=email,
            phone=phone,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
        )

        return await self._send_events([event_data], test_event_code)

    async def send_custom_event(
        self,
        event_name: str,
        event_id: str,
        custom_data: Optional[Dict[str, Any]] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        event_source_url: Optional[str] = None,
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a custom conversion event to Meta.

        Args:
            event_name: Custom event name (e.g., "Subscribe")
            event_id: Unique ID for deduplication
            custom_data: Additional custom parameters
            email: Customer email (will be hashed)
            phone: Customer phone (will be hashed)
            client_ip: Customer IP address
            client_user_agent: Customer browser user agent
            event_source_url: URL where event occurred
            test_event_code: Test event code for debugging

        Returns:
            Dict with events_received count and fbtrace_id
        """
        event_data = self._build_event(
            event_name=event_name,
            event_id=event_id,
            email=email,
            phone=phone,
            client_ip=client_ip,
            client_user_agent=client_user_agent,
            event_source_url=event_source_url,
            custom_data=custom_data,
        )

        return await self._send_events([event_data], test_event_code)

    def _build_event(
        self,
        event_name: str,
        event_id: str,
        value: Optional[Decimal] = None,
        currency: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        order_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_user_agent: Optional[str] = None,
        fbclid: Optional[str] = None,
        fbc: Optional[str] = None,
        fbp: Optional[str] = None,
        event_source_url: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a single event payload.

        WHAT: Constructs the event object with user data hashing
        WHY: Meta requires specific format with SHA256-hashed PII

        Args:
            event_name: Standard or custom event name
            event_id: Unique event identifier
            value: Conversion value (for Purchase events)
            currency: Currency code
            email: Customer email (will be SHA256 hashed)
            phone: Customer phone (will be SHA256 hashed)
            order_id: Order reference
            client_ip: IP for matching
            client_user_agent: User agent for matching
            fbclid: Facebook click ID
            fbc: Facebook click cookie
            fbp: Facebook browser cookie
            event_source_url: Page URL
            custom_data: Additional parameters

        Returns:
            Event dictionary ready for API submission
        """
        # Build user_data with hashed PII
        user_data = {}

        if email:
            # Normalize and hash email
            normalized_email = email.lower().strip()
            user_data["em"] = self._sha256_hash(normalized_email)

        if phone:
            # Normalize and hash phone (remove non-digits)
            normalized_phone = "".join(filter(str.isdigit, phone))
            user_data["ph"] = self._sha256_hash(normalized_phone)

        if client_ip:
            user_data["client_ip_address"] = client_ip

        if client_user_agent:
            user_data["client_user_agent"] = client_user_agent

        if fbclid:
            # fbc format: fb.1.{timestamp}.{fbclid}
            user_data["fbc"] = fbc or f"fb.1.{int(datetime.utcnow().timestamp())}.{fbclid}"

        if fbp:
            user_data["fbp"] = fbp

        # Build custom_data
        event_custom_data = custom_data or {}

        if value is not None:
            event_custom_data["value"] = float(value)

        if currency:
            event_custom_data["currency"] = currency

        if order_id:
            event_custom_data["order_id"] = order_id

        # Build event
        event = {
            "event_name": event_name,
            "event_time": int(datetime.utcnow().timestamp()),
            "event_id": event_id,  # CRITICAL for deduplication
            "action_source": "website",
            "user_data": user_data,
        }

        if event_custom_data:
            event["custom_data"] = event_custom_data

        if event_source_url:
            event["event_source_url"] = event_source_url

        return event

    async def _send_events(
        self,
        events: List[Dict[str, Any]],
        test_event_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send events to Meta Conversions API.

        WHAT: POST events to Meta's graph API
        WHY: Actually transmit the conversion data

        Args:
            events: List of event objects
            test_event_code: If provided, events go to Test Events in Events Manager

        Returns:
            API response with events_received and fbtrace_id

        Raises:
            MetaCAPIError: If the request fails
        """
        payload = {
            "data": events,
            "access_token": self.access_token,
        }

        if test_event_code:
            payload["test_event_code"] = test_event_code

        logger.info(
            f"[META_CAPI] Sending {len(events)} event(s) to pixel {self.pixel_id}",
            extra={
                "event_names": [e["event_name"] for e in events],
                "event_ids": [e["event_id"] for e in events],
                "test_mode": bool(test_event_code),
            }
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.events_url,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get("error", {}).get("message", response.text)
                    logger.error(
                        f"[META_CAPI] API error: {response.status_code} - {error_message}",
                        extra={"response": error_data}
                    )
                    raise MetaCAPIError(f"Meta CAPI error: {error_message}")

                result = response.json()
                events_received = result.get("events_received", 0)
                fbtrace_id = result.get("fbtrace_id", "")

                logger.info(
                    f"[META_CAPI] Success: {events_received} event(s) received",
                    extra={
                        "events_received": events_received,
                        "fbtrace_id": fbtrace_id,
                    }
                )

                return result

        except httpx.RequestError as e:
            logger.error(f"[META_CAPI] Network error: {e}")
            raise MetaCAPIError(f"Network error sending to Meta CAPI: {e}")

    @staticmethod
    def _sha256_hash(value: str) -> str:
        """Hash a value using SHA256.

        WHAT: Creates SHA256 hash of input string
        WHY: Meta requires PII to be hashed for privacy

        Args:
            value: String to hash

        Returns:
            Lowercase hexadecimal hash string
        """
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def send_purchase_to_meta(
    workspace_id: str,
    order_id: str,
    value: Decimal,
    currency: str,
    email: Optional[str] = None,
    fbclid: Optional[str] = None,
    db=None,
) -> Optional[Dict[str, Any]]:
    """Convenience function to send purchase event for a workspace.

    WHAT: Looks up Meta credentials and sends purchase event
    WHY: Simplifies CAPI integration from attribution flow

    Args:
        workspace_id: Workspace UUID
        order_id: Shopify order ID (used as event_id for deduplication)
        value: Purchase value
        currency: Currency code
        email: Customer email (optional, for matching)
        fbclid: Facebook click ID (optional, for matching)
        db: Database session

    Returns:
        API response or None if no Meta connection

    Configuration Priority:
        1. Connection's meta_pixel_id (set via API)
        2. META_PIXEL_ID environment variable (fallback)

    Environment Variables:
        META_PIXEL_ID: Fallback Pixel ID if not set on connection
        META_CAPI_ACCESS_TOKEN: Optional override for access token
        META_CAPI_TEST_EVENT_CODE: Optional test event code for debugging
    """
    if not db:
        logger.warning("[META_CAPI] No database session provided")
        return None

    # Import here to avoid circular imports
    from app.models import Connection, ProviderEnum

    # Find Meta connection for workspace
    meta_connection = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.provider == ProviderEnum.meta,
        Connection.status == "active",
    ).first()

    if not meta_connection:
        logger.debug(f"[META_CAPI] No active Meta connection for workspace {workspace_id}")
        return None

    # Get Pixel ID - prefer connection setting, fallback to env
    pixel_id = meta_connection.meta_pixel_id or os.getenv("META_PIXEL_ID")
    if not pixel_id:
        logger.debug("[META_CAPI] No pixel_id configured (set via API or META_PIXEL_ID env)")
        return None

    # Get access token - prefer env override, fallback to connection token
    access_token = os.getenv("META_CAPI_ACCESS_TOKEN")

    if not access_token:
        from app.services.token_service import get_decrypted_token
        access_token = get_decrypted_token(db, meta_connection.id, "access")

    if not access_token:
        logger.warning("[META_CAPI] No access token available for CAPI")
        return None

    # Optional test event code for debugging in Meta Events Manager
    test_event_code = os.getenv("META_CAPI_TEST_EVENT_CODE")

    # Send event
    try:
        service = MetaCAPIService(pixel_id=pixel_id, access_token=access_token)
        result = await service.send_purchase_event(
            event_id=f"order_{order_id}",  # Prefix to avoid collision with browser events
            value=value,
            currency=currency,
            email=email,
            fbclid=fbclid,
            order_id=order_id,
            test_event_code=test_event_code,
        )
        return result

    except MetaCAPIError as e:
        logger.error(f"[META_CAPI] Failed to send purchase event: {e}")
        return None
