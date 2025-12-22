"""Google Ads client service abstraction.

WHAT:
    Encapsulates Google Ads API usage behind a small, testable service layer.
    Provides GAQL helpers, entity listing, basic metrics retrieval, retries,
    and rate limiting. Designed to mirror Meta's service structure while
    honoring Google Ads specifics (GAQL/search, account timezone/currency).

WHY:
    - Separation of concerns: keep provider SDK logic out of routers.
    - Single responsibility: this module only talks to Google Ads.
    - Testability: allow dependency injection and mocking in unit tests.

REFERENCES:
    docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD
    docs/living-docs/META_INTEGRATION_STATUS.md (service patterns)
    backend/app/models.py (ProviderEnum, GoalEnum)
"""

from __future__ import annotations

import logging
import os
import re
import time
import random
from datetime import date
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

from app.models import GoalEnum

logger = logging.getLogger(__name__)

try:
    # Import lazily to keep tests fast when the SDK isn't installed.
    from google.ads.googleads.client import GoogleAdsClient as _SdkClient
    from google.ads.googleads.errors import GoogleAdsException
except Exception:  # pragma: no cover - tests will mock without importing SDK
    _SdkClient = None  # type: ignore


# =============================================================================
# EXCEPTIONS
# =============================================================================

class QuotaExhaustedError(Exception):
    """Raised when Google Ads API quota is exhausted.

    WHAT:
        Custom exception for quota exhaustion (429 errors) that includes
        the retry delay hint from Google.

    WHY:
        Allows callers to implement circuit breaker pattern - when this is
        raised, the connection should be marked as rate-limited and skipped
        until the cooldown expires.

    REFERENCES:
        docs/living-docs/plans/fancy-launching-lake.md (quota fix plan)
    """

    def __init__(self, message: str, retry_seconds: int = 600):
        """Initialize QuotaExhaustedError.

        Args:
            message: Error message
            retry_seconds: Number of seconds Google suggests to wait (default 10 min)
        """
        super().__init__(message)
        self.retry_seconds = retry_seconds


def _extract_retry_seconds(error_str: str) -> Optional[int]:
    """Extract retry delay from Google Ads API error message.

    WHAT:
        Parses error messages like "Retry in 723 seconds" to extract the delay.

    WHY:
        Google Ads API embeds retry hints in error messages for quota exhaustion.
        We must respect these to avoid hammering the API.

    Args:
        error_str: String representation of the error

    Returns:
        Number of seconds to wait, or None if not found.
    """
    # Match patterns like "Retry in 723 seconds" or "retry in 60 seconds"
    match = re.search(r'[Rr]etry in (\d+) seconds', error_str)
    if match:
        return int(match.group(1))
    return None


class GoogleAdsRateLimiter:
    """Simple token bucket rate limiter.

    WHAT:
        Guard outgoing requests to honor QPS/quota. Defaults are conservative.
    WHY:
        Avoid RESOURCE_EXHAUSTED errors and smooth out bursts.
    """

    def __init__(self, capacity: int = 15, refill_per_sec: float = 5.0) -> None:
        self.capacity = capacity
        self.tokens = capacity
        self.refill_per_sec = refill_per_sec
        self.last = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        # Refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
        if self.tokens < 1:
            # Sleep until we have at least 1 token
            missing = 1 - self.tokens
            sleep_s = missing / self.refill_per_sec
            time.sleep(max(0.0, sleep_s))
            self.tokens = 0
        # Consume one token
        self.tokens = max(0.0, self.tokens - 1)


def _with_retries(func):
    """Retry decorator with exponential backoff and jitter.

    WHAT:
        Retries on transient errors (UNAVAILABLE, INTERNAL, RST_STREAM) with
        exponential backoff. For quota exhaustion (RESOURCE_EXHAUSTED), raises
        QuotaExhaustedError with the retry hint to trigger circuit breaker.

    WHY:
        - Transient errors (network, server) benefit from retries
        - Quota exhaustion needs circuit breaker, not retries (wastes resources)
        - Google's "Retry in X seconds" hints can be 700+ seconds - we respect them

    REFERENCES:
        docs/living-docs/plans/fancy-launching-lake.md (quota fix plan)
    """

    def wrapper(self, *args, **kwargs):  # type: ignore
        max_attempts = 3  # Reduced from 5 - faster failure for quota errors
        base = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                error_str = str(e)

                # Check for quota exhaustion (429) - needs circuit breaker, not retries
                is_quota_exhausted = (
                    'RESOURCE_EXHAUSTED' in error_str or
                    '429' in error_str or
                    'Too many requests' in error_str or
                    'quota' in error_str.lower()
                )

                if is_quota_exhausted:
                    # Extract retry hint from error message
                    retry_seconds = _extract_retry_seconds(error_str)
                    if retry_seconds and retry_seconds > 120:
                        # Long cooldown (> 2 min) - raise QuotaExhaustedError for circuit breaker
                        logger.warning(
                            "[GOOGLE_ADS] Quota exhausted, Google suggests retry in %ds. "
                            "Raising QuotaExhaustedError for circuit breaker.",
                            retry_seconds
                        )
                        raise QuotaExhaustedError(
                            f"Google Ads quota exhausted. Retry in {retry_seconds} seconds.",
                            retry_seconds=retry_seconds
                        )
                    elif retry_seconds:
                        # Short cooldown (< 2 min) - wait and retry
                        logger.info(
                            "[GOOGLE_ADS] Quota warning (attempt %d/%d), waiting %ds",
                            attempt, max_attempts, retry_seconds
                        )
                        if attempt < max_attempts:
                            time.sleep(retry_seconds)
                            continue
                    # No hint or last attempt - raise QuotaExhaustedError with default
                    raise QuotaExhaustedError(
                        f"Google Ads quota exhausted: {error_str[:200]}",
                        retry_seconds=600  # Default 10 min cooldown
                    )

                # Try to detect GoogleAdsException for other transient errors
                code = None
                retry_after = None
                if 'GoogleAdsException' in e.__class__.__name__ or e.__class__.__module__.startswith('google'):
                    code = getattr(getattr(e, 'error', None), 'code', None)
                    retry_after = getattr(e, 'retry_after', None)

                # Transient errors → retry
                transient = False
                if code:
                    code_str = str(code)
                    transient = 'UNAVAILABLE' in code_str or 'INTERNAL' in code_str
                else:
                    transient = any(k in error_str for k in ('UNAVAILABLE', 'RST_STREAM', 'deadline exceeded'))

                if not transient or attempt == max_attempts:
                    raise

                # Backoff with jitter for transient errors
                if retry_after:
                    sleep_s = float(retry_after)
                else:
                    sleep_s = base * (2 ** (attempt - 1)) * (1 + random.random())
                sleep_s = min(sleep_s, 30.0)  # Cap at 30s for transient errors

                logger.info(
                    "[GOOGLE_ADS] Transient error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt, max_attempts, sleep_s, error_str[:100]
                )
                time.sleep(sleep_s)
        # Unreachable
    return wrapper


class GAdsClient:
    """Testable wrapper around Google Ads Python SDK.

    WHAT:
        - Builds an SDK client from environment configuration.
        - Provides GAQL search and convenience methods for common listings.
    WHY:
        - Keep routers/services free from SDK-specific details.
    """

    def __init__(self, client: Optional[Any] = None, rate_limiter: Optional[GoogleAdsRateLimiter] = None) -> None:
        self._client = client or self._build_client_from_env()
        self._ga_service = None
        self._rate = rate_limiter or GoogleAdsRateLimiter()

    # --- Client factory -------------------------------------------------
    @staticmethod
    def _build_client_from_env() -> Any:
        """Build GoogleAdsClient from environment variables.

        Env vars:
            GOOGLE_DEVELOPER_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
            GOOGLE_REFRESH_TOKEN, GOOGLE_LOGIN_CUSTOMER_ID, GOOGLE_ADS_ENVIRONMENT
        """
        if _SdkClient is None:  # pragma: no cover
            raise RuntimeError("google-ads SDK not installed")

        # Normalize optional login customer id (digits only)
        login_cid_env = os.getenv("GOOGLE_LOGIN_CUSTOMER_ID")
        if login_cid_env:
            login_cid_env = "".join(ch for ch in login_cid_env if ch.isdigit())
            # Only use if valid 10-digit ID; otherwise omit to avoid client error
            if len(login_cid_env) != 10:
                login_cid_env = None

        config = {
            "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
            # Important: google-ads >= 21 requires explicit use_proto_plus
            "use_proto_plus": True,
        }
        if login_cid_env:
            config["login_customer_id"] = login_cid_env
        # Validate minimal required fields
        missing = [k for k, v in config.items() if k in ("developer_token", "client_id", "client_secret", "refresh_token") and not v]
        if missing:
            raise ValueError(f"Missing required Google Ads env vars: {', '.join(missing)}")
        return _SdkClient.load_from_dict(config)
    
    @staticmethod
    def _build_client_from_tokens(
        refresh_token: str,
        login_customer_id: Optional[str] = None
    ) -> Any:
        """Build GoogleAdsClient from OAuth tokens (for connections).
        
        WHAT:
            Creates SDK client using refresh token from connection instead of env vars.
        WHY:
            Supports OAuth connections where tokens are stored in database.
        """
        if _SdkClient is None:  # pragma: no cover
            raise RuntimeError("google-ads SDK not installed")
        
        developer_token = os.getenv("GOOGLE_DEVELOPER_TOKEN")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not developer_token or not client_id or not client_secret:
            raise ValueError("Missing required Google Ads env vars: GOOGLE_DEVELOPER_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET")
        
        # Normalize optional login customer id (digits only)
        if login_customer_id:
            login_customer_id = "".join(ch for ch in login_customer_id if ch.isdigit())
            if len(login_customer_id) != 10:
                login_customer_id = None
        
        config = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        }
        if login_customer_id:
            config["login_customer_id"] = login_customer_id
        
        return _SdkClient.load_from_dict(config)

    # --- Low-level GAQL -------------------------------------------------
    def _service(self):
        if self._ga_service is None:
            self._ga_service = self._client.get_service("GoogleAdsService")
        return self._ga_service

    @_with_retries
    def search(self, customer_id: str, query: str, page_size: int = 10_000) -> Iterable[Any]:
        """GAQL search with rate limit + retries.

        Note: Some client versions don't accept page_size as a kwarg; we
        intentionally omit it and rely on server defaults.
        """
        self._rate.acquire()
        return self._service().search(customer_id=customer_id, query=query)

    @_with_retries
    def search_stream(self, customer_id: str, query: str) -> Generator[Any, None, None]:
        """Streaming GAQL results."""
        self._rate.acquire()
        stream = self._service().search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            yield from getattr(batch, 'results', [])

    # --- Convenience listings ------------------------------------------
    def list_campaigns(self, customer_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        """Return campaigns with delivery/status fields and channel type.

        Args:
            customer_id: Google Ads customer ID (digits only)
            active_only: If True, only return ENABLED campaigns.
                        Default is False to include PAUSED campaigns so metrics
                        totals match Google Ads dashboard (paused campaigns still
                        have historical data that counts toward totals).

        NOTE: REMOVED campaigns are always excluded as they have no data.
        """
        # Build query - include PAUSED by default to match Google Ads totals
        # REMOVED campaigns are excluded as they have no useful data
        if active_only:
            status_filter = "WHERE campaign.status = 'ENABLED'"
        else:
            status_filter = "WHERE campaign.status IN ('ENABLED', 'PAUSED')"
        q = (
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.serving_status, campaign.primary_status, "
            "campaign.primary_status_reasons, campaign.advertising_channel_type "
            f"FROM campaign {status_filter} ORDER BY campaign.name"
        )
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            c = r.campaign
            chan = getattr(c, "advertising_channel_type", None)
            if chan is not None and hasattr(chan, "name"):
                chan_val = str(chan.name)
            else:
                chan_val = str(chan) if chan is not None else None
            out.append({
                "id": getattr(c, "id", None),
                "name": getattr(c, "name", None),
                "status": getattr(c, "status", None),
                "serving_status": getattr(c, "serving_status", None),
                "primary_status": getattr(c, "primary_status", None),
                "primary_status_reasons": list(getattr(c, "primary_status_reasons", [])),
                "advertising_channel_type": chan_val,
            })
        return out

    def list_ad_groups(self, customer_id: str, campaign_id: str) -> List[Dict[str, Any]]:
        q = (
            "SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.campaign "
            "FROM ad_group WHERE ad_group.campaign = 'customers/{cid}/campaigns/{cmp}' "
            "ORDER BY ad_group.name"
        ).format(cid=customer_id, cmp=campaign_id)
        rows = self.search(customer_id, q)
        return [{
            "id": r.ad_group.id,
            "name": r.ad_group.name,
            "status": r.ad_group.status,
            "campaign_id": campaign_id,
        } for r in rows]

    def list_ads(self, customer_id: str, ad_group_id: str) -> List[Dict[str, Any]]:
        # UTM Tracking Detection: fetch tracking_url_template and final_url_suffix
        # WHY: Enables proactive warnings about missing UTM params
        # REFERENCES: docs/living-docs/FRONTEND_REFACTOR_PLAN.md
        q = (
            "SELECT ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.status, "
            "ad_group_ad.ad_group, ad_group_ad.ad.tracking_url_template, "
            "ad_group_ad.ad.final_url_suffix "
            "FROM ad_group_ad WHERE ad_group_ad.ad_group = 'customers/{cid}/adGroups/{ag}' "
            "ORDER BY ad_group_ad.ad.name"
        ).format(cid=customer_id, ag=ad_group_id)
        rows = self.search(customer_id, q)
        result = []
        for r in rows:
            ad = r.ad_group_ad.ad
            tracking_url_template = getattr(ad, "tracking_url_template", None)
            final_url_suffix = getattr(ad, "final_url_suffix", None)

            # Build tracking_params for UTM detection
            tracking_params = self._extract_google_tracking_params(
                tracking_url_template, final_url_suffix
            )

            result.append({
                "id": ad.id,
                "name": getattr(ad, "name", None),
                "status": r.ad_group_ad.status,
                "ad_group_id": ad_group_id,
                "tracking_params": tracking_params,
            })
        return result

    # --- Performance Max (Asset Groups) ---------------------------------
    def list_asset_groups(self, customer_id: str, campaign_id: str) -> List[Dict[str, Any]]:
        q = (
            "SELECT asset_group.id, asset_group.name, asset_group.status, asset_group.campaign "
            "FROM asset_group WHERE asset_group.campaign = 'customers/{cid}/campaigns/{cmp}' "
            "ORDER BY asset_group.name"
        ).format(cid=customer_id, cmp=campaign_id)
        rows = self.search(customer_id, q)
        return [{
            "id": r.asset_group.id,
            "name": getattr(r.asset_group, "name", None),
            "status": r.asset_group.status,
            "campaign_id": campaign_id,
        } for r in rows]

    # --- Campaign Configuration (for Copilot live queries) ----------------
    def get_campaigns_with_config(
        self,
        customer_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch campaigns with configuration data including start/end dates.

        WHAT:
            Gets campaign config that's NOT stored in our Entity snapshots:
            - start_date, end_date
            - budget amount
            - bidding strategy

        WHY:
            Answers Copilot questions like "which campaigns went live yesterday"
            that require data not in our snapshot database.

        Args:
            customer_id: Google Ads customer ID (digits only)
            filters: Optional dict with:
                - start_date: "yesterday", "today", or ISO date string
                - status: "ENABLED", "PAUSED"

        Returns:
            List of campaign dicts with config data
        """
        from datetime import datetime, timedelta

        q = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.amount_micros,
                campaign.bidding_strategy_type,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.status IN ('ENABLED', 'PAUSED')
        """

        # Add date filter if specified
        if filters:
            if filters.get("start_date"):
                start_date_filter = filters["start_date"]
                if start_date_filter == "yesterday":
                    yesterday = (date.today() - timedelta(days=1)).isoformat()
                    q += f" AND campaign.start_date = '{yesterday}'"
                elif start_date_filter == "today":
                    q += f" AND campaign.start_date = '{date.today().isoformat()}'"
                elif isinstance(start_date_filter, str) and len(start_date_filter) == 10:
                    # Assume ISO format YYYY-MM-DD
                    q += f" AND campaign.start_date = '{start_date_filter}'"

            if filters.get("status"):
                q += f" AND campaign.status = '{filters['status']}'"

        q += " ORDER BY campaign.start_date DESC, campaign.name"

        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []

        for r in rows:
            c = r.campaign
            budget = getattr(r, "campaign_budget", None)

            # Parse status enum properly (e.g., CampaignStatus.ENABLED -> "ENABLED")
            status_raw = getattr(c, "status", None)
            if status_raw is not None and hasattr(status_raw, "name"):
                status_val = str(status_raw.name)
            else:
                status_val = str(status_raw) if status_raw is not None else None

            # Parse channel type
            chan = getattr(c, "advertising_channel_type", None)
            if chan is not None and hasattr(chan, "name"):
                chan_val = str(chan.name)
            else:
                chan_val = str(chan) if chan is not None else None

            # Parse bidding strategy type
            bid_strategy = getattr(c, "bidding_strategy_type", None)
            if bid_strategy is not None and hasattr(bid_strategy, "name"):
                bid_strategy_val = str(bid_strategy.name)
            else:
                bid_strategy_val = str(bid_strategy) if bid_strategy is not None else None

            # Convert budget from micros
            budget_amount = None
            if budget:
                amount_micros = getattr(budget, "amount_micros", None)
                if amount_micros:
                    budget_amount = amount_micros / 1_000_000.0

            out.append({
                "id": getattr(c, "id", None),
                "name": getattr(c, "name", None),
                "status": status_val,
                "start_date": str(getattr(c, "start_date", None)) if getattr(c, "start_date", None) else None,
                "end_date": str(getattr(c, "end_date", None)) if getattr(c, "end_date", None) else None,
                "budget_amount": budget_amount,
                "bidding_strategy_type": bid_strategy_val,
                "advertising_channel_type": chan_val,
            })

        return out

    def list_keywords(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch keywords for Search campaigns.

        WHAT:
            Gets keyword targeting data from ad_group_criterion.
            Includes keyword text, match type, and status.

        WHY:
            Answers Copilot questions like "what keywords am I targeting?"
            This data is NOT stored in our snapshot database.

        Args:
            customer_id: Google Ads customer ID (digits only)
            campaign_id: Optional campaign ID to filter by

        Returns:
            List of keyword dicts with text, match_type, status
        """
        q = """
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group.name,
                campaign.name,
                campaign.id
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = 'KEYWORD'
        """

        if campaign_id:
            q += f" AND campaign.id = {campaign_id}"

        q += " ORDER BY campaign.name, ad_group.name, ad_group_criterion.keyword.text"

        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []

        for r in rows:
            keyword = getattr(r.ad_group_criterion, "keyword", None)
            if not keyword:
                continue

            # Parse match type
            match_type = getattr(keyword, "match_type", None)
            if match_type is not None and hasattr(match_type, "name"):
                match_type_val = str(match_type.name)
            else:
                match_type_val = str(match_type) if match_type is not None else None

            out.append({
                "keyword_text": getattr(keyword, "text", None),
                "match_type": match_type_val,
                "status": str(getattr(r.ad_group_criterion, "status", None)),
                "ad_group_name": getattr(r.ad_group, "name", None),
                "campaign_name": getattr(r.campaign, "name", None),
                "campaign_id": getattr(r.campaign, "id", None),
            })

        return out

    def list_search_terms(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch search terms report for Search campaigns.

        WHAT:
            Gets actual search queries that triggered ads.
            Includes the search term, keyword it matched, and metrics.

        WHY:
            Answers Copilot questions like "what did users search for?"
            This data is NOT stored in our snapshot database.

        Args:
            customer_id: Google Ads customer ID (digits only)
            campaign_id: Optional campaign ID to filter by
            start: Start date for report (default: last 7 days)
            end: End date for report (default: yesterday)

        Returns:
            List of search term dicts with term, keyword, metrics
        """
        from datetime import timedelta

        if not end:
            end = date.today() - timedelta(days=1)
        if not start:
            start = end - timedelta(days=6)

        q = f"""
            SELECT
                search_term_view.search_term,
                search_term_view.status,
                segments.keyword.info.text,
                campaign.name,
                campaign.id,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions_by_conversion_date
            FROM search_term_view
            WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'
        """

        if campaign_id:
            q += f" AND campaign.id = {campaign_id}"

        q += " ORDER BY metrics.impressions DESC LIMIT 100"

        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []

        for r in rows:
            search_term = getattr(r.search_term_view, "search_term", None)
            status = getattr(r.search_term_view, "status", None)

            # Get the matching keyword
            keyword_info = getattr(getattr(r.segments, "keyword", None), "info", None)
            keyword_text = getattr(keyword_info, "text", None) if keyword_info else None

            m = r.metrics
            spend = (m.cost_micros or 0) / 1_000_000.0

            out.append({
                "search_term": search_term,
                "status": str(status) if status else None,
                "matched_keyword": keyword_text,
                "campaign_name": getattr(r.campaign, "name", None),
                "campaign_id": getattr(r.campaign, "id", None),
                "impressions": int(m.impressions or 0),
                "clicks": int(m.clicks or 0),
                "spend": float(spend),
                "conversions": float(getattr(m, "conversions_by_conversion_date", 0.0) or 0.0),
            })

        return out

    # --- Batch Query Methods (Quota Optimization) -----------------------
    # WHY: Reduce API calls from O(N×M) to O(1) by fetching all entities
    # in a single GAQL query instead of per-campaign/per-ad_group calls.
    # REFERENCES: docs/living-docs/plans/fancy-launching-lake.md

    def list_all_ad_groups(self, customer_id: str) -> List[Dict[str, Any]]:
        """Fetch ALL ad groups across all campaigns in ONE API call.

        WHAT:
            Returns all ad groups for the customer, including their parent
            campaign resource name for relationship mapping.

        WHY:
            Reduces API calls from O(N campaigns) to O(1).
            Critical for avoiding Google Ads API quota exhaustion.

        Args:
            customer_id: Google Ads customer ID (digits only)

        Returns:
            List of ad group dicts with id, name, status, campaign_resource_name
        """
        q = (
            "SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.campaign "
            "FROM ad_group "
            "WHERE campaign.status IN ('ENABLED', 'PAUSED') "
            "ORDER BY ad_group.name"
        )
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            ag = r.ad_group
            # Extract campaign_id from resource name: customers/123/campaigns/456
            campaign_resource = getattr(ag, "campaign", None)
            campaign_id = None
            if campaign_resource:
                parts = str(campaign_resource).split("/")
                if len(parts) >= 4:
                    campaign_id = parts[-1]
            out.append({
                "id": getattr(ag, "id", None),
                "name": getattr(ag, "name", None),
                "status": getattr(ag, "status", None),
                "campaign_id": campaign_id,
                "campaign_resource": str(campaign_resource) if campaign_resource else None,
            })
        return out

    def list_all_ads(self, customer_id: str) -> List[Dict[str, Any]]:
        """Fetch ALL ads across all ad groups in ONE API call.

        WHAT:
            Returns all ads for the customer, including parent ad_group
            resource name and UTM tracking info.

        WHY:
            Reduces API calls from O(N×M) to O(1).
            Critical for avoiding Google Ads API quota exhaustion.

        Args:
            customer_id: Google Ads customer ID (digits only)

        Returns:
            List of ad dicts with id, name, status, ad_group_id, tracking_params
        """
        q = (
            "SELECT ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.status, "
            "ad_group_ad.ad_group, ad_group_ad.ad.tracking_url_template, "
            "ad_group_ad.ad.final_url_suffix "
            "FROM ad_group_ad "
            "WHERE campaign.status IN ('ENABLED', 'PAUSED') "
            "ORDER BY ad_group_ad.ad.name"
        )
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            ad = r.ad_group_ad.ad
            # Extract ad_group_id from resource name: customers/123/adGroups/456
            ad_group_resource = getattr(r.ad_group_ad, "ad_group", None)
            ad_group_id = None
            if ad_group_resource:
                parts = str(ad_group_resource).split("/")
                if len(parts) >= 4:
                    ad_group_id = parts[-1]

            # UTM tracking detection
            tracking_url_template = getattr(ad, "tracking_url_template", None)
            final_url_suffix = getattr(ad, "final_url_suffix", None)
            tracking_params = self._extract_google_tracking_params(
                tracking_url_template, final_url_suffix
            )

            out.append({
                "id": getattr(ad, "id", None),
                "name": getattr(ad, "name", None),
                "status": r.ad_group_ad.status,
                "ad_group_id": ad_group_id,
                "ad_group_resource": str(ad_group_resource) if ad_group_resource else None,
                "tracking_params": tracking_params,
            })
        return out

    def list_all_asset_groups(self, customer_id: str) -> List[Dict[str, Any]]:
        """Fetch ALL asset groups (PMax) across all campaigns in ONE API call.

        WHAT:
            Returns all asset groups for Performance Max campaigns,
            including parent campaign resource name.

        WHY:
            Reduces API calls from O(N PMax campaigns) to O(1).
            Critical for avoiding Google Ads API quota exhaustion.

        Args:
            customer_id: Google Ads customer ID (digits only)

        Returns:
            List of asset group dicts with id, name, status, campaign_id
        """
        q = (
            "SELECT asset_group.id, asset_group.name, asset_group.status, asset_group.campaign "
            "FROM asset_group "
            "WHERE campaign.status IN ('ENABLED', 'PAUSED') "
            "ORDER BY asset_group.name"
        )
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            ag = r.asset_group
            # Extract campaign_id from resource name: customers/123/campaigns/456
            campaign_resource = getattr(ag, "campaign", None)
            campaign_id = None
            if campaign_resource:
                parts = str(campaign_resource).split("/")
                if len(parts) >= 4:
                    campaign_id = parts[-1]
            out.append({
                "id": getattr(ag, "id", None),
                "name": getattr(ag, "name", None),
                "status": getattr(ag, "status", None),
                "campaign_id": campaign_id,
                "campaign_resource": str(campaign_resource) if campaign_resource else None,
            })
        return out

    def list_asset_group_assets(self, customer_id: str, asset_group_id: str) -> List[Dict[str, Any]]:
        q = (
            "SELECT asset_group_asset.asset, asset_group_asset.field_type, asset_group_asset.status, asset_group_asset.asset_group "
            "FROM asset_group_asset WHERE asset_group_asset.asset_group = 'customers/{cid}/assetGroups/{ag}'"
        ).format(cid=customer_id, ag=asset_group_id)
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            asset_id = getattr(r.asset_group_asset, "asset", None)
            field_type = getattr(r.asset_group_asset, "field_type", None)
            status = getattr(r.asset_group_asset, "status", None)
            # Build a simple display name from type+id tail
            tail = str(asset_id).split("/")[-1] if asset_id else ""
            type_name = field_type.name if hasattr(field_type, "name") else str(field_type)
            name = f"{type_name.title()} {tail}".strip()
            out.append({
                "id": tail or str(asset_id),
                "name": name,
                "status": status,
                "asset_group_id": asset_group_id,
            })
        return out

    def _extract_google_tracking_params(
        self,
        tracking_url_template: Optional[str],
        final_url_suffix: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Extract UTM tracking parameters from Google Ads tracking fields.

        WHAT:
            Parses tracking_url_template and final_url_suffix to detect UTM presence.
            Returns structured data about which UTM params are configured.

        WHY:
            Enables proactive attribution warnings. If ads don't have UTM params,
            we can warn users before they spend money without proper tracking.

        REFERENCES:
            - docs/living-docs/FRONTEND_REFACTOR_PLAN.md (UTM detection feature)

        Args:
            tracking_url_template: Google Ads tracking URL template
            final_url_suffix: URL suffix appended to final URLs

        Returns:
            Dictionary with tracking info or None if no tracking configured.
        """
        if not tracking_url_template and not final_url_suffix:
            return None

        # Combine both sources for checking
        combined = ""
        if tracking_url_template:
            combined += tracking_url_template.lower()
        if final_url_suffix:
            combined += " " + final_url_suffix.lower()

        # Check for standard UTM parameters
        detected_params = []
        utm_params = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]

        for param in utm_params:
            if param in combined:
                detected_params.append(param)

        # Also check for gclid (Google's click ID - auto-tagging)
        # If gclid is present, tracking is configured via auto-tagging
        has_gclid = "gclid" in combined

        result = {
            "tracking_url_template": tracking_url_template,
            "final_url_suffix": final_url_suffix,
            "has_utm_source": "utm_source" in combined,
            "has_utm_medium": "utm_medium" in combined,
            "has_utm_campaign": "utm_campaign" in combined,
            "has_gclid": has_gclid,
            "detected_params": detected_params,
        }

        return result

    # --- Account metadata ----------------------------------------------
    def get_customer_metadata(self, customer_id: str) -> Dict[str, Optional[str]]:
        """Fetch customer timezone and currency code."""
        q = (
            "SELECT customer.time_zone, customer.currency_code FROM customer LIMIT 1"
        )
        rows = list(self.search(customer_id, q))
        if not rows:
            return {"time_zone": None, "currency_code": None}
        cust = rows[0].customer
        return {"time_zone": getattr(cust, "time_zone", None), "currency_code": getattr(cust, "currency_code", None)}

    # --- Shopping / Product Performance --------------------------------
    def fetch_shopping_performance(
        self, customer_id: str, start: date, end: date
    ) -> List[Dict[str, Any]]:
        """Fetch product-level metrics from shopping_performance_view.

        WHAT:
            Retrieves daily product metrics for Shopping campaigns.
            Returns product_item_id, product_title, brand, and metrics.

        WHY:
            Shopping campaigns don't have ad_group_ad entities - they use
            product groups from Merchant Center. This is the source of truth
            for Shopping campaign performance at the product level.

        REFERENCES:
            - Google Ads API: shopping_performance_view resource
            - https://developers.google.com/google-ads/api/docs/shopping-ads/reporting

        Args:
            customer_id: Google Ads customer ID (digits only)
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of dicts with product metrics including:
            - campaign_id, ad_group_id: For hierarchy linking
            - product_item_id, product_title, product_brand: Product info
            - impressions, clicks, spend, conversions, revenue: Metrics
            - resource_id: Unique ID for entity creation
        """
        q = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                segments.product_item_id,
                segments.product_title,
                segments.product_brand,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions_by_conversion_date,
                metrics.conversions_value_by_conversion_date
            FROM shopping_performance_view
            WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'
        """
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            m = r.metrics
            d = r.segments.date
            spend = (m.cost_micros or 0) / 1_000_000.0

            # Extract IDs for hierarchy linking
            campaign_id = getattr(r.campaign, "id", None)
            ad_group_id = getattr(r.ad_group, "id", None)
            product_item_id = getattr(r.segments, "product_item_id", None) or "unknown"
            product_title = getattr(r.segments, "product_title", None)
            product_brand = getattr(r.segments, "product_brand", None)

            # Build unique external ID: product-{campaign_id}-{product_item_id}
            # This ensures uniqueness per product per campaign
            resource_id = f"product-{campaign_id}-{product_item_id}"

            out.append({
                "date": str(d),
                "campaign_id": campaign_id,
                "ad_group_id": ad_group_id,
                "product_item_id": product_item_id,
                "product_title": product_title or f"Product {product_item_id}",
                "product_brand": product_brand,
                "impressions": int(m.impressions or 0),
                "clicks": int(m.clicks or 0),
                "spend": float(spend),
                "conversions": float(getattr(m, "conversions_by_conversion_date", 0.0) or 0.0),
                "revenue": float(getattr(m, "conversions_value_by_conversion_date", 0.0) or 0.0),
                "resource_id": resource_id,
                "_raw": r,
            })
        return out

    def fetch_pmax_product_performance(
        self, customer_id: str, start: date, end: date
    ) -> List[Dict[str, Any]]:
        """Fetch product-level metrics from asset_group_product_group_view.

        WHAT:
            Retrieves product metrics for Performance Max retail campaigns.
            Returns asset_group linkage and aggregated product metrics.

        WHY:
            PMax retail campaigns have product-level performance data that
            rolls up to asset groups. This enables top product analysis
            for PMax campaigns connected to Merchant Center.

        REFERENCES:
            - Google Ads API: asset_group_product_group_view resource
            - https://developers.google.com/google-ads/api/docs/performance-max/retail

        Args:
            customer_id: Google Ads customer ID (digits only)
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of dicts with product group metrics including:
            - asset_group_id: For hierarchy linking
            - impressions, clicks, spend, conversions, revenue: Metrics
            - resource_id: Unique ID for entity creation
        """
        q = f"""
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group.campaign,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions_by_conversion_date,
                metrics.conversions_value_by_conversion_date
            FROM asset_group_product_group_view
            WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'
        """
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            m = r.metrics
            d = r.segments.date
            spend = (m.cost_micros or 0) / 1_000_000.0

            asset_group_id = getattr(r.asset_group, "id", None)
            asset_group_name = getattr(r.asset_group, "name", None)
            # Extract campaign_id from resource name: customers/123/campaigns/456
            campaign_resource = getattr(r.asset_group, "campaign", None)
            campaign_id = None
            if campaign_resource:
                parts = str(campaign_resource).split("/")
                if len(parts) >= 4:
                    campaign_id = parts[-1]

            # Unique ID for product group within asset group
            resource_id = f"pmax-product-{asset_group_id}"

            out.append({
                "date": str(d),
                "asset_group_id": asset_group_id,
                "asset_group_name": asset_group_name,
                "campaign_id": campaign_id,
                "impressions": int(m.impressions or 0),
                "clicks": int(m.clicks or 0),
                "spend": float(spend),
                "conversions": float(getattr(m, "conversions_by_conversion_date", 0.0) or 0.0),
                "revenue": float(getattr(m, "conversions_value_by_conversion_date", 0.0) or 0.0),
                "resource_id": resource_id,
                "_raw": r,
            })
        return out

    # --- Metrics --------------------------------------------------------
    def fetch_daily_metrics(
        self,
        customer_id: str,
        start: date,
        end: date,
        level: str = "campaign",
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch daily metrics for a given level (campaign/ad_group/ad).

        Args:
            customer_id: Google Ads customer ID
            start: Start date (inclusive)
            end: End date (inclusive)
            level: Entity level to fetch (campaign/ad_group/ad/asset_group)
            active_only: If True, only fetch metrics for ENABLED campaigns.
                        Default is False to include PAUSED campaigns so totals
                        match Google Ads dashboard.

        NOTE: No segmentation other than date to include zero rows.
        """
        resource = {
            "campaign": "campaign",
            "ad_group": "ad_group",
            "ad": "ad_group_ad",
            "asset_group": "asset_group",
            "asset_group_asset": "asset_group_asset",
        }[level]
        select_id = {
            "campaign": "campaign.id, campaign.name",
            "ad_group": "ad_group.id, ad_group.name, ad_group.campaign",
            "ad": "ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.ad_group",
            "asset_group": "asset_group.id, asset_group.name, asset_group.campaign",
            "asset_group_asset": "asset_group_asset.asset, asset_group_asset.field_type, asset_group_asset.asset_group",
        }[level]

        # Build WHERE clause
        where_parts = [f"segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"]
        if active_only:
            where_parts.append("campaign.status = 'ENABLED'")
        where_clause = " AND ".join(where_parts)

        q = (
            f"SELECT {select_id}, "
            "metrics.impressions, metrics.clicks, metrics.cost_micros, "
            "metrics.conversions_by_conversion_date, metrics.conversions_value_by_conversion_date, segments.date "
            f"FROM {resource} "
            f"WHERE {where_clause}"
        )
        rows = self.search(customer_id, q)
        out: List[Dict[str, Any]] = []
        for r in rows:
            m = r.metrics
            d = r.segments.date
            # Normalize spend from micros to standard units
            spend = (m.cost_micros or 0) / 1_000_000.0
            # Extract resource id by level
            if level == "campaign":
                resource_id = getattr(r.campaign, "id", None)
            elif level == "ad_group":
                resource_id = getattr(r.ad_group, "id", None)
            elif level == "ad":
                resource_id = getattr(getattr(r.ad_group_ad, "ad", None), "id", None)
            elif level == "asset_group":
                resource_id = getattr(r.asset_group, "id", None)
            else:  # asset_group_asset
                # resource id is the asset id; normalize to trailing numeric id
                asset = getattr(r.asset_group_asset, "asset", None)
                resource_id = str(asset).split("/")[-1] if asset else None
            out.append({
                "date": str(d),
                "impressions": int(m.impressions or 0),
                "clicks": int(m.clicks or 0),
                "spend": float(spend),
                "conversions": float(getattr(m, "conversions_by_conversion_date", 0.0) or 0.0),
                "revenue": float(getattr(m, "conversions_value_by_conversion_date", 0.0) or 0.0),
                "resource_id": resource_id,
                "_raw": r,
            })
        return out


# --- Campaign channel → Goal mapping -----------------------------------

def map_channel_to_goal(channel_type: Optional[object]) -> GoalEnum:
    """Map Google Ads advertising_channel_type to metricx GoalEnum.

    Extended to cover all common channel types; refined in future with
    subtypes/strategies if needed.
    """
    mapping = {
        "SEARCH": GoalEnum.conversions,
        "DISPLAY": GoalEnum.awareness,
        "VIDEO": GoalEnum.awareness,
        "PERFORMANCE_MAX": GoalEnum.purchases,
        "SHOPPING": GoalEnum.purchases,
        "HOTEL": GoalEnum.purchases,
        "LOCAL": GoalEnum.traffic,
        "SMART": GoalEnum.conversions,
        "DISCOVERY": GoalEnum.traffic,
        "AUDIO": GoalEnum.awareness,
        "APP": GoalEnum.app_installs,
    }
    # Normalize to uppercase string
    if channel_type is None:
        key = ""
    elif hasattr(channel_type, "name"):
        key = str(channel_type.name).upper()
    else:
        key = str(channel_type).upper()
    return mapping.get(key, GoalEnum.other)
