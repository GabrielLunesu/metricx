"""Meta Ads API Client Service.

WHAT:
    Wrapper for Facebook Business SDK providing rate-limited access to Meta Marketing API.
    Handles campaigns, adsets, ads, and insights fetching with automatic pagination.

WHY:
    - Centralized Meta API interaction (single source of truth)
    - Rate limiting enforcement (200 calls/hour per account)
    - Pagination handling (Meta returns max 100 records per call)
    - Graceful error handling (400/401/403 responses)

WHERE USED:
    - app/routers/meta_sync.py (sync endpoints call this service)
    - app/services/meta_metrics_fetcher.py (Phase 3, automated sync)

DEPENDENCIES:
    - facebook_business SDK
    - app/deps.py (META_ACCESS_TOKEN from .env)
    
RATE LIMITS:
    - 200 API calls per hour per ad account
    - Implements decorator: @rate_limit(calls_per_hour=200)

REFERENCES:
    - backend/test_meta_api.py (test patterns)
    - backend/app/models.py (Connection, Entity)
    - https://developers.facebook.com/docs/marketing-api
"""

import logging
from functools import wraps
from time import time, sleep
from collections import deque
from typing import List, Dict, Any, Optional
from datetime import datetime

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)


def rate_limit(calls_per_hour: int):
    """Decorator to enforce rate limiting using sliding window algorithm.
    
    WHAT:
        Tracks API call timestamps in a deque and enforces maximum calls per hour.
        Sleeps if rate limit would be exceeded.
    
    WHY:
        Meta enforces 200 calls/hour per ad account. Exceeding this causes 429 errors.
        Proactive rate limiting prevents API throttling and ensures reliable syncs.
    
    Args:
        calls_per_hour: Maximum number of calls allowed per hour
        
    Returns:
        Decorated function that enforces rate limiting
    """
    call_times = deque(maxlen=calls_per_hour)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            
            # Remove calls older than 1 hour (3600 seconds)
            while call_times and call_times[0] < now - 3600:
                call_times.popleft()
            
            # If at limit, sleep until oldest call expires
            if len(call_times) >= calls_per_hour:
                sleep_time = 3600 - (now - call_times[0]) + 1
                logger.warning(
                    f"[META_CLIENT] Rate limit reached ({calls_per_hour} calls/hour). "
                    f"Sleeping for {sleep_time:.1f}s"
                )
                sleep(sleep_time)
            
            call_times.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class MetaAdsClientError(Exception):
    """Base exception for Meta Ads Client errors."""
    pass


class MetaAdsAuthenticationError(MetaAdsClientError):
    """Raised when authentication fails (401)."""
    pass


class MetaAdsPermissionError(MetaAdsClientError):
    """Raised when permissions are insufficient (403)."""
    pass


class MetaAdsValidationError(MetaAdsClientError):
    """Raised when request is malformed (400)."""
    pass


class MetaAdsClient:
    """Client for interacting with Meta Marketing API.
    
    WHAT:
        Provides methods to fetch campaigns, adsets, ads, and insights from Meta.
        Handles rate limiting, pagination, and error responses automatically.
    
    WHY:
        Centralizes all Meta API interactions in one place.
        Ensures consistent error handling and rate limiting across all sync operations.
    
    Usage:
        ```python
        client = MetaAdsClient(access_token="YOUR_TOKEN")
        campaigns = client.get_campaigns("act_123456789")
        insights = client.get_insights("123456", "2024-01-01", "2024-01-07", level="ad")
        ```
    """
    
    def __init__(self, access_token: str, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """Initialize Meta Ads client with access token.
        
        WHAT:
            Initializes FacebookAdsApi with provided credentials.
            For system user tokens, app_id and app_secret are optional.
        
        WHY:
            System user tokens (used in Phase 2) don't require app credentials.
            OAuth tokens (Phase 7) will need app_id and app_secret.
        
        Args:
            access_token: Meta access token (system user or OAuth)
            app_id: Optional Meta app ID
            app_secret: Optional Meta app secret
        """
        self.access_token = access_token
        
        # Initialize Facebook Ads API
        FacebookAdsApi.init(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token
        )
        
        logger.info("[META_CLIENT] Initialized with access token")
    
    @rate_limit(calls_per_hour=200)
    def get_campaigns(self, account_id: str) -> List[Dict[str, Any]]:
        """Fetch all campaigns for an ad account.
        
        WHAT:
            Retrieves all campaigns from Meta, handles pagination automatically.
            Returns campaign metadata (id, name, status, objective, etc.)
        
        WHY:
            First step in entity sync - campaigns are the top level of hierarchy.
        
        Args:
            account_id: Meta ad account ID (format: "act_123456789")
            
        Returns:
            List of campaign dictionaries with fields:
                - id: Campaign ID
                - name: Campaign name
                - status: ACTIVE, PAUSED, DELETED, ARCHIVED
                - objective: Campaign objective (e.g., OUTCOME_SALES)
                - daily_budget: Daily budget in cents (optional)
                - lifetime_budget: Lifetime budget in cents (optional)
                - created_time: Creation timestamp
                
        Raises:
            MetaAdsAuthenticationError: Invalid or expired token
            MetaAdsPermissionError: Insufficient permissions for account
            MetaAdsValidationError: Invalid account ID format
            MetaAdsClientError: Other API errors
        """
        try:
            logger.info(f"[META_CLIENT] Fetching campaigns for account: {account_id}")
            
            account = AdAccount(account_id)
            campaigns = account.get_campaigns(fields=[
                Campaign.Field.id,
                Campaign.Field.name,
                Campaign.Field.status,
                Campaign.Field.objective,
                Campaign.Field.daily_budget,
                Campaign.Field.lifetime_budget,
                Campaign.Field.created_time,
            ])
            
            # SDK iterator handles pagination automatically
            result = []
            for campaign in campaigns:
                result.append(dict(campaign))
            
            logger.info(f"[META_CLIENT] Fetched {len(result)} campaigns")
            return result
            
        except FacebookRequestError as e:
            return self._handle_api_error(e, f"fetching campaigns for {account_id}")
    
    @rate_limit(calls_per_hour=200)
    def get_adsets(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Fetch all adsets for a campaign.
        
        WHAT:
            Retrieves all adsets belonging to a campaign.
            Returns adset metadata (id, name, status, targeting, etc.)
        
        WHY:
            Second level of entity hierarchy - adsets belong to campaigns.
        
        Args:
            campaign_id: Meta campaign ID
            
        Returns:
            List of adset dictionaries with fields:
                - id: AdSet ID
                - name: AdSet name
                - status: ACTIVE, PAUSED, DELETED, ARCHIVED
                - campaign_id: Parent campaign ID
                - daily_budget: Daily budget in cents (optional)
                - lifetime_budget: Lifetime budget in cents (optional)
                - targeting: Targeting configuration
                
        Raises:
            MetaAdsAuthenticationError: Invalid or expired token
            MetaAdsPermissionError: Insufficient permissions
            MetaAdsValidationError: Invalid campaign ID
            MetaAdsClientError: Other API errors
        """
        try:
            logger.info(f"[META_CLIENT] Fetching adsets for campaign: {campaign_id}")
            
            campaign = Campaign(campaign_id)
            adsets = campaign.get_ad_sets(fields=[
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.status,
                AdSet.Field.campaign_id,
                AdSet.Field.daily_budget,
                AdSet.Field.lifetime_budget,
                AdSet.Field.targeting,
            ])
            
            result = []
            for adset in adsets:
                result.append(dict(adset))
            
            logger.info(f"[META_CLIENT] Fetched {len(result)} adsets")
            return result
            
        except FacebookRequestError as e:
            return self._handle_api_error(e, f"fetching adsets for campaign {campaign_id}")
    
    @rate_limit(calls_per_hour=200)
    def get_ads(self, adset_id: str) -> List[Dict[str, Any]]:
        """Fetch all ads for an adset.

        WHAT:
            Retrieves all ads belonging to an adset.
            Returns ad metadata (id, name, status, creative, etc.)

        WHY:
            Third level of entity hierarchy - ads belong to adsets.
            Ad-level metrics are most granular and avoid double-counting.

        Args:
            adset_id: Meta adset ID

        Returns:
            List of ad dictionaries with fields:
                - id: Ad ID
                - name: Ad name
                - status: ACTIVE, PAUSED, DELETED, ARCHIVED
                - adset_id: Parent adset ID
                - creative: Creative configuration

        Raises:
            MetaAdsAuthenticationError: Invalid or expired token
            MetaAdsPermissionError: Insufficient permissions
            MetaAdsValidationError: Invalid adset ID
            MetaAdsClientError: Other API errors
        """
        try:
            logger.info(f"[META_CLIENT] Fetching ads for adset: {adset_id}")

            adset = AdSet(adset_id)
            ads = adset.get_ads(fields=[
                Ad.Field.id,
                Ad.Field.name,
                Ad.Field.status,
                Ad.Field.adset_id,
                Ad.Field.creative,
                # Note: url_tags is on AdCreative, not Ad. We fetch it via get_creative_details
            ])

            result = []
            for ad in ads:
                ad_dict = dict(ad)
                result.append(ad_dict)

            logger.info(f"[META_CLIENT] Fetched {len(result)} ads")
            return result

        except FacebookRequestError as e:
            return self._handle_api_error(e, f"fetching ads for adset {adset_id}")

    @rate_limit(calls_per_hour=200)
    def get_creative_details(self, creative_id: str) -> Optional[Dict[str, Any]]:
        """Fetch creative details including thumbnail URL and url_tags.

        WHAT:
            Retrieves creative asset details from Meta for displaying ad previews.
            Returns thumbnail URL, image URL, media type, and url_tags for UTM tracking.

        WHY:
            Enables showing actual creative images in the QA system when users
            ask "show me my best creatives" or similar queries.
            Also fetches url_tags for proactive UTM detection.

        REFERENCES:
            - docs/living-docs/FRONTEND_REFACTOR_PLAN.md (UTM detection)

        Args:
            creative_id: Meta creative ID (from Ad.creative.id)

        Returns:
            Dictionary with creative details:
                - id: Creative ID
                - thumbnail_url: URL to thumbnail image
                - image_url: URL to full-size image (if available)
                - media_type: "image", "video", or "carousel"
                - url_tags: URL tracking parameters (for UTM detection)
            Returns None if creative cannot be fetched.

        Raises:
            MetaAdsAuthenticationError: Invalid or expired token
            MetaAdsPermissionError: Insufficient permissions
            MetaAdsClientError: Other API errors
        """
        try:
            logger.info(f"[META_CLIENT] Fetching creative details for: {creative_id}")

            creative = AdCreative(creative_id)
            creative_data = creative.api_get(fields=[
                AdCreative.Field.id,
                AdCreative.Field.thumbnail_url,
                AdCreative.Field.image_url,
                AdCreative.Field.object_type,
                AdCreative.Field.object_story_spec,
                AdCreative.Field.url_tags,  # For UTM tracking detection
            ])

            result = {
                "id": creative_data.get("id"),
                "thumbnail_url": creative_data.get("thumbnail_url"),
                "image_url": creative_data.get("image_url"),
                "media_type": self._determine_media_type(creative_data),
                "url_tags": creative_data.get("url_tags"),  # UTM tracking params
            }

            # Try to extract image from object_story_spec if not directly available
            if not result["image_url"]:
                object_story_spec = creative_data.get("object_story_spec", {})
                # Check for link_data image
                link_data = object_story_spec.get("link_data", {})
                if link_data.get("image_hash") or link_data.get("picture"):
                    result["image_url"] = link_data.get("picture")
                # Check for video_data thumbnail
                video_data = object_story_spec.get("video_data", {})
                if video_data.get("image_url"):
                    result["image_url"] = video_data.get("image_url")

            logger.info(
                f"[META_CLIENT] Creative {creative_id}: "
                f"thumbnail={bool(result['thumbnail_url'])}, "
                f"image={bool(result['image_url'])}, "
                f"type={result['media_type']}"
            )
            return result

        except FacebookRequestError as e:
            # Don't fail the whole sync for creative fetch errors
            logger.warning(
                f"[META_CLIENT] Could not fetch creative {creative_id}: {e}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"[META_CLIENT] Unexpected error fetching creative {creative_id}: {e}"
            )
            return None

    def _determine_media_type(self, creative_data: Dict[str, Any]) -> str:
        """Determine media type from creative data.

        Args:
            creative_data: Creative response from Meta API

        Returns:
            One of: "image", "video", "carousel", "unknown"
        """
        object_type = creative_data.get("object_type", "").upper()

        if "VIDEO" in object_type:
            return "video"
        elif "CAROUSEL" in object_type:
            return "carousel"
        elif object_type in ["SHARE", "PHOTO", "STATUS"]:
            return "image"

        # Check object_story_spec for more clues
        object_story_spec = creative_data.get("object_story_spec", {})
        if object_story_spec.get("video_data"):
            return "video"
        if object_story_spec.get("link_data", {}).get("child_attachments"):
            return "carousel"
        if object_story_spec.get("link_data") or object_story_spec.get("photo_data"):
            return "image"

        return "unknown"

    def _extract_tracking_params(self, ad_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract UTM tracking parameters from Meta ad data.

        WHAT:
            Parses url_tags field to detect UTM parameter configuration.
            Returns structured data about which UTM params are present.

        WHY:
            Enables proactive attribution warnings. If ads don't have UTM params,
            we can warn users before they spend money without proper tracking.

        REFERENCES:
            - docs/living-docs/FRONTEND_REFACTOR_PLAN.md (UTM detection feature)

        Args:
            ad_dict: Ad data dictionary from Meta API

        Returns:
            Dictionary with tracking info:
                - url_tags: Raw URL tags string
                - has_utm_source: Whether utm_source is present
                - has_utm_medium: Whether utm_medium is present
                - has_utm_campaign: Whether utm_campaign is present
                - detected_params: List of detected UTM param names
            Returns None if no url_tags present.

        Example:
            >>> ad = {"url_tags": "utm_source=facebook&utm_campaign={{campaign.name}}"}
            >>> client._extract_tracking_params(ad)
            {
                "url_tags": "utm_source=facebook&utm_campaign={{campaign.name}}",
                "has_utm_source": True,
                "has_utm_medium": False,
                "has_utm_campaign": True,
                "detected_params": ["utm_source", "utm_campaign"]
            }
        """
        url_tags = ad_dict.get("url_tags")

        if not url_tags:
            return None

        # Normalize to lowercase for matching
        url_tags_lower = url_tags.lower()

        # Check for standard UTM parameters
        detected_params = []
        utm_params = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]

        for param in utm_params:
            if param in url_tags_lower:
                detected_params.append(param)

        # Also check for fbclid (Meta's click ID) and gclid passthrough
        if "fbclid" in url_tags_lower:
            detected_params.append("fbclid")

        result = {
            "url_tags": url_tags,
            "has_utm_source": "utm_source" in url_tags_lower,
            "has_utm_medium": "utm_medium" in url_tags_lower,
            "has_utm_campaign": "utm_campaign" in url_tags_lower,
            "detected_params": detected_params,
        }

        logger.debug(
            f"[META_CLIENT] Ad tracking params: has_source={result['has_utm_source']}, "
            f"has_campaign={result['has_utm_campaign']}, params={detected_params}"
        )

        return result

    @rate_limit(calls_per_hour=200)
    def get_insights(
        self,
        entity_id: str,
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
        level: str = "ad",  # account/campaign/adset/ad
        time_increment: int = 1  # 1=daily
    ) -> List[Dict[str, Any]]:
        """Fetch insights (metrics) for entity and date range.
        
        WHAT:
            Retrieves performance metrics for a specific entity over a date range.
            Returns daily breakdown with spend, impressions, clicks, conversions, etc.
        
        WHY:
            This is where we get the actual metrics data for ingestion.
            Meta's Insights API provides aggregated performance data.
        
        CRITICAL NOTES:
            - Maximum 93 days per request (Meta API limit)
            - Hourly breakdowns ONLY available for last 3 days
            - For metricx Phase 2: Use daily breakdowns, chunk in 7-day windows
            - Actions array contains conversions/leads/purchases (complex parsing needed)
        
        Args:
            entity_id: Meta entity ID (account/campaign/adset/ad ID)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            level: Aggregation level (account/campaign/adset/ad)
            time_increment: 1=daily, hourly=not used in Phase 2
            
        Returns:
            List of insight dictionaries with fields:
                - date_start: Period start date
                - date_stop: Period end date
                - spend: Ad spend (string, needs conversion)
                - impressions: Number of impressions (string)
                - clicks: Number of clicks (string)
                - actions: Array of conversion actions (complex structure)
                - action_values: Array of conversion values (revenue)
                
        Raises:
            MetaAdsAuthenticationError: Invalid or expired token
            MetaAdsPermissionError: Insufficient permissions
            MetaAdsValidationError: Invalid date range or entity ID
            MetaAdsClientError: Other API errors
        """
        try:
            logger.info(
                f"[META_CLIENT] Fetching insights for {entity_id}: "
                f"{start_date} to {end_date}, level={level}"
            )
            
            # Determine entity type and create appropriate object
            if level == "account":
                entity = AdAccount(entity_id)
            elif level == "campaign":
                entity = Campaign(entity_id)
            elif level == "adset":
                entity = AdSet(entity_id)
            else:  # ad
                entity = Ad(entity_id)
            
            # Fetch insights
            params = {
                'level': level,
                'time_range': {
                    'since': start_date,
                    'until': end_date
                },
                'time_increment': time_increment,
            }
            
            insights = entity.get_insights(
                fields=[
                    AdsInsights.Field.date_start,
                    AdsInsights.Field.date_stop,
                    AdsInsights.Field.spend,
                    AdsInsights.Field.impressions,
                    AdsInsights.Field.clicks,
                    AdsInsights.Field.actions,
                    AdsInsights.Field.action_values,
                ],
                params=params
            )
            
            result = []
            for insight in insights:
                result.append(dict(insight))
            
            logger.info(f"[META_CLIENT] Fetched {len(result)} insight records")
            return result
            
        except FacebookRequestError as e:
            return self._handle_api_error(e, f"fetching insights for {entity_id}")

    @rate_limit(calls_per_hour=200)
    def get_account_insights(
        self,
        ad_account_id: str,
        level: str = "ad",
        start_date: str = None,
        end_date: str = None,
        time_increment: int = 1,
        fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch insights at ACCOUNT level with breakdown by ad/adset/campaign.

        WHAT:
            Retrieves performance metrics for ALL ads in an account in a SINGLE API call.
            Much more efficient than calling get_insights per entity.

        WHY:
            - Reduces API calls from N (one per entity) to 1 (one per account)
            - Avoids rate limit issues (200 calls/hour per account)
            - Faster sync times for accounts with many ads

        Args:
            ad_account_id: Meta ad account ID (format: "act_123456789")
            level: Breakdown level - "ad", "adset", or "campaign"
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            time_increment: 1=daily breakdown
            fields: List of fields to fetch (defaults to standard metrics)

        Returns:
            List of insight dictionaries, one per ad per day, with fields:
                - ad_id: Ad ID (when level="ad")
                - date_start/date_stop: Date range
                - spend, impressions, clicks, actions, action_values

        Raises:
            MetaAdsClientError: On API errors
        """
        try:
            logger.info(
                f"[META_CLIENT] Fetching ACCOUNT-LEVEL insights: {ad_account_id}, "
                f"level={level}, {start_date} to {end_date}"
            )

            account = AdAccount(ad_account_id)

            # Default fields if not specified
            if fields is None:
                fields = [
                    AdsInsights.Field.date_start,
                    AdsInsights.Field.date_stop,
                    AdsInsights.Field.spend,
                    AdsInsights.Field.impressions,
                    AdsInsights.Field.clicks,
                    AdsInsights.Field.actions,
                    AdsInsights.Field.action_values,
                    AdsInsights.Field.account_currency,
                ]

            # Add level-specific ID field
            if level == "ad":
                fields.append(AdsInsights.Field.ad_id)
                fields.append(AdsInsights.Field.ad_name)
            elif level == "adset":
                fields.append(AdsInsights.Field.adset_id)
                fields.append(AdsInsights.Field.adset_name)
            elif level == "campaign":
                fields.append(AdsInsights.Field.campaign_id)
                fields.append(AdsInsights.Field.campaign_name)

            params = {
                'level': level,
                'time_increment': time_increment,
            }

            if start_date and end_date:
                params['time_range'] = {
                    'since': start_date,
                    'until': end_date
                }

            insights = account.get_insights(fields=fields, params=params)

            result = []
            for insight in insights:
                result.append(dict(insight))

            logger.info(f"[META_CLIENT] Fetched {len(result)} insights (account-level)")
            return result

        except FacebookRequestError as e:
            return self._handle_api_error(e, f"fetching account insights for {ad_account_id}")

    def _handle_api_error(self, error: FacebookRequestError, context: str) -> None:
        """Handle Facebook API errors with specific exceptions.
        
        WHAT:
            Translates FacebookRequestError into specific exception types.
            Logs error details for debugging.
        
        WHY:
            Allows calling code to handle different error types appropriately.
            Centralizes error logging and handling logic.
        
        Args:
            error: The Facebook API error
            context: Description of what operation failed
            
        Raises:
            MetaAdsAuthenticationError: For 401 errors
            MetaAdsPermissionError: For 403 errors
            MetaAdsValidationError: For 400 errors
            MetaAdsClientError: For other errors (429, 500, etc.)
        """
        error_code = error.api_error_code()
        error_message = error.api_error_message()
        http_status = error.http_status()
        
        logger.error(
            f"[META_CLIENT] API error while {context}: "
            f"HTTP {http_status}, Code {error_code}, Message: {error_message}"
        )
        
        # Map HTTP status to specific exceptions
        if http_status == 401:
            raise MetaAdsAuthenticationError(
                f"Authentication failed while {context}. Token may be expired or invalid."
            )
        elif http_status == 403:
            raise MetaAdsPermissionError(
                f"Permission denied while {context}. Check token permissions."
            )
        elif http_status == 400:
            raise MetaAdsValidationError(
                f"Invalid request while {context}: {error_message}"
            )
        elif http_status == 429:
            # Rate limit hit (should be prevented by decorator, but handle gracefully)
            raise MetaAdsClientError(
                f"Rate limit exceeded while {context}. This should not happen with rate limiting."
            )
        else:
            # 500, 503, or other server errors
            raise MetaAdsClientError(
                f"API error while {context}: HTTP {http_status}, {error_message}"
            )

