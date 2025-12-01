"""Google Ads Offline Conversions Service.

WHAT:
    Uploads offline conversion data to Google Ads for attribution and optimization.
    This enables Google to optimize campaigns based on actual purchase data,
    similar to Meta CAPI but for Google Ads.

WHY:
    - Improves Google Ads campaign optimization with real revenue data
    - Enables offline conversion tracking (purchases that happen after ad click)
    - Better ROAS measurement and bidding optimization
    - Closes the attribution loop: ad click -> purchase -> report back to Google

HOW:
    Uses Google Ads API ConversionUploadService to upload click conversions
    with gclid (Google Click ID) for attribution.

PREREQUISITES:
    1. Conversion Action must exist in Google Ads account
    2. gclid must be captured within 90 days
    3. Valid Google Ads API credentials

REFERENCES:
    - https://developers.google.com/google-ads/api/docs/conversions/upload-offline
    - https://developers.google.com/google-ads/api/samples/upload-offline-conversion
    - docs/living-docs/ATTRIBUTION_ENGINE.md
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GoogleConversionsError(Exception):
    """Base exception for Google Conversions errors."""
    pass


class GoogleConversionsService:
    """Service for uploading offline conversions to Google Ads.

    WHAT: Sends purchase/conversion events to Google Ads for optimization
    WHY: Improves ad targeting and ROAS measurement

    Usage:
        ```python
        service = GoogleConversionsService(
            customer_id="1234567890",
            refresh_token="token",
            login_customer_id="9876543210"  # If using MCC
        )
        result = await service.upload_conversion(
            gclid="CjwKCAjw...",
            conversion_action_id="123456789",
            conversion_time=datetime.now(),
            conversion_value=99.99,
            currency="USD",
            order_id="ORD-001",
        )
        ```
    """

    def __init__(
        self,
        customer_id: str,
        refresh_token: str,
        login_customer_id: Optional[str] = None,
    ):
        """Initialize Google Conversions service.

        Args:
            customer_id: Google Ads customer ID (10 digits, no dashes)
            refresh_token: OAuth refresh token for API access
            login_customer_id: MCC customer ID if accessing via manager account
        """
        self.customer_id = self._normalize_customer_id(customer_id)
        self.refresh_token = refresh_token
        self.login_customer_id = self._normalize_customer_id(login_customer_id) if login_customer_id else None
        self._client = None

    @staticmethod
    def _normalize_customer_id(customer_id: str) -> str:
        """Remove dashes from customer ID.

        WHAT: Normalize customer ID to digits only
        WHY: Google Ads API expects 10-digit ID without dashes
        """
        if not customer_id:
            return ""
        return "".join(ch for ch in customer_id if ch.isdigit())

    def _get_client(self):
        """Get or create Google Ads API client.

        WHAT: Lazy-load the Google Ads client
        WHY: Avoid creating client until needed
        """
        if self._client is None:
            from google.ads.googleads.client import GoogleAdsClient

            config = {
                "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "refresh_token": self.refresh_token,
                "use_proto_plus": True,
            }

            if self.login_customer_id:
                config["login_customer_id"] = self.login_customer_id

            self._client = GoogleAdsClient.load_from_dict(config)

        return self._client

    async def upload_conversion(
        self,
        gclid: str,
        conversion_action_id: str,
        conversion_time: datetime,
        conversion_value: Decimal,
        currency: str = "USD",
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a single click conversion to Google Ads.

        WHAT: Reports a purchase/conversion back to Google Ads
        WHY: Enables conversion optimization and accurate ROAS tracking

        Args:
            gclid: Google Click ID from the ad click
            conversion_action_id: ID of the conversion action in Google Ads
            conversion_time: When the conversion occurred
            conversion_value: Monetary value of the conversion
            currency: ISO currency code (default: USD)
            order_id: Order ID for deduplication (recommended)

        Returns:
            Dict with upload results including any partial failures

        Raises:
            GoogleConversionsError: If the upload fails completely
        """
        if not gclid:
            raise GoogleConversionsError("gclid is required for conversion upload")

        if not conversion_action_id:
            raise GoogleConversionsError("conversion_action_id is required")

        try:
            client = self._get_client()
            conversion_upload_service = client.get_service("ConversionUploadService")

            # Build the click conversion
            click_conversion = client.get_type("ClickConversion")

            # Set conversion action resource name
            click_conversion.conversion_action = (
                f"customers/{self.customer_id}/conversionActions/{conversion_action_id}"
            )

            # Set gclid for attribution
            click_conversion.gclid = gclid

            # Format datetime: 'yyyy-mm-dd hh:mm:ss+|-hh:mm'
            # Google requires timezone-aware datetime
            if conversion_time.tzinfo is None:
                conversion_time = conversion_time.replace(tzinfo=timezone.utc)

            click_conversion.conversion_date_time = conversion_time.strftime(
                "%Y-%m-%d %H:%M:%S%z"
            )
            # Fix timezone format: +0000 -> +00:00
            dt_str = click_conversion.conversion_date_time
            if len(dt_str) > 5 and dt_str[-5] in "+-" and ":" not in dt_str[-5:]:
                click_conversion.conversion_date_time = dt_str[:-2] + ":" + dt_str[-2:]

            # Set conversion value
            click_conversion.conversion_value = float(conversion_value)
            click_conversion.currency_code = currency

            # Set order_id for deduplication (highly recommended)
            if order_id:
                click_conversion.order_id = order_id

            # Upload the conversion
            request = client.get_type("UploadClickConversionsRequest")
            request.customer_id = self.customer_id
            request.conversions = [click_conversion]
            request.partial_failure = True  # Continue on partial failures

            response = conversion_upload_service.upload_click_conversions(
                request=request
            )

            # Check for partial failures
            if response.partial_failure_error:
                error_msg = response.partial_failure_error.message
                logger.warning(
                    f"[GOOGLE_CONV] Partial failure uploading conversion: {error_msg}",
                    extra={"gclid": gclid[:20], "order_id": order_id}
                )
                return {
                    "success": False,
                    "partial_failure": True,
                    "error": error_msg,
                    "gclid": gclid,
                    "order_id": order_id,
                }

            # Success
            uploaded = response.results[0] if response.results else None
            logger.info(
                f"[GOOGLE_CONV] Successfully uploaded conversion",
                extra={
                    "gclid": gclid[:20] + "...",
                    "order_id": order_id,
                    "value": float(conversion_value),
                    "currency": currency,
                }
            )

            return {
                "success": True,
                "gclid": gclid,
                "order_id": order_id,
                "conversion_action": uploaded.conversion_action if uploaded else None,
                "conversion_date_time": uploaded.conversion_date_time if uploaded else None,
            }

        except Exception as e:
            logger.error(
                f"[GOOGLE_CONV] Failed to upload conversion: {e}",
                extra={"gclid": gclid[:20] if gclid else None, "order_id": order_id}
            )
            raise GoogleConversionsError(f"Failed to upload conversion: {e}")


async def send_purchase_to_google(
    workspace_id: str,
    gclid: str,
    order_id: str,
    value: Decimal,
    currency: str,
    conversion_time: datetime,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """Convenience function to send purchase conversion for a workspace.

    WHAT: Looks up Google credentials and sends conversion
    WHY: Simplifies integration from attribution flow

    Args:
        workspace_id: Workspace UUID
        gclid: Google Click ID
        order_id: Order ID for deduplication
        value: Purchase value
        currency: Currency code
        conversion_time: When the purchase occurred
        db: Database session

    Returns:
        Upload result dict or None if no Google connection

    Configuration:
        The connection must have:
        1. Valid refresh token (from OAuth)
        2. google_conversion_action_id set (from settings or env)

    Environment Variables:
        GOOGLE_CONVERSION_ACTION_ID: Fallback conversion action ID
        GOOGLE_DEVELOPER_TOKEN: Required for API access
    """
    if not gclid:
        logger.debug("[GOOGLE_CONV] No gclid provided, skipping upload")
        return None

    # Import here to avoid circular imports
    from app.models import Connection, ProviderEnum
    from app.services.token_service import get_decrypted_token

    # Find Google connection for workspace
    google_connection = db.query(Connection).filter(
        Connection.workspace_id == workspace_id,
        Connection.provider == ProviderEnum.google,
        Connection.status == "active",
    ).first()

    if not google_connection:
        logger.debug(f"[GOOGLE_CONV] No active Google connection for workspace {workspace_id}")
        return None

    # Get refresh token
    refresh_token = get_decrypted_token(db, google_connection.id, "refresh")
    if not refresh_token:
        logger.warning(f"[GOOGLE_CONV] No refresh token for connection {google_connection.id}")
        return None

    # Get customer ID
    customer_id = google_connection.external_account_id
    if not customer_id:
        logger.warning(f"[GOOGLE_CONV] No customer ID for connection {google_connection.id}")
        return None

    # Get conversion action ID - prefer connection setting, fallback to env
    conversion_action_id = getattr(google_connection, 'google_conversion_action_id', None)
    if not conversion_action_id:
        conversion_action_id = os.getenv("GOOGLE_CONVERSION_ACTION_ID")

    if not conversion_action_id:
        logger.debug(
            "[GOOGLE_CONV] No conversion_action_id configured "
            "(set via API or GOOGLE_CONVERSION_ACTION_ID env)"
        )
        return None

    # Get login_customer_id (MCC) if available from token metadata
    from app.models import ConnectionToken
    token_record = db.query(ConnectionToken).filter(
        ConnectionToken.connection_id == google_connection.id,
        ConnectionToken.token_type == "refresh",
    ).first()

    login_customer_id = None
    if token_record and token_record.metadata_:
        login_customer_id = token_record.metadata_.get("parent_mcc_id")

    # Send conversion
    try:
        service = GoogleConversionsService(
            customer_id=customer_id,
            refresh_token=refresh_token,
            login_customer_id=login_customer_id,
        )

        result = await service.upload_conversion(
            gclid=gclid,
            conversion_action_id=conversion_action_id,
            conversion_time=conversion_time,
            conversion_value=value,
            currency=currency,
            order_id=order_id,
        )

        return result

    except GoogleConversionsError as e:
        logger.error(f"[GOOGLE_CONV] Failed to send purchase: {e}")
        return None
