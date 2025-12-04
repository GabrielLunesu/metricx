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

import os
import time
import random
from datetime import date
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

from app.models import GoalEnum

try:
    # Import lazily to keep tests fast when the SDK isn't installed.
    from google.ads.googleads.client import GoogleAdsClient as _SdkClient
    from google.ads.googleads.errors import GoogleAdsException
except Exception:  # pragma: no cover - tests will mock without importing SDK
    _SdkClient = None  # type: ignore


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

    Retries on transient errors (RESOURCE_EXHAUSTED/UNAVAILABLE) and SDK
    transport errors, respecting any retry delay hints when present.
    """

    def wrapper(self, *args, **kwargs):  # type: ignore
        max_attempts = 5
        base = 0.5
        for attempt in range(1, max_attempts + 1):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                # Try to detect GoogleAdsException without importing it in tests
                code = None
                retry_after = None
                if 'GoogleAdsException' in e.__class__.__name__ or e.__class__.__module__.startswith('google'):
                    # best-effort extraction
                    code = getattr(getattr(e, 'error', None), 'code', None)
                    retry_after = getattr(e, 'retry_after', None)
                # Transient errors → retry
                transient = False
                if code:
                    code_str = str(code)
                    transient = 'RESOURCE_EXHAUSTED' in code_str or 'UNAVAILABLE' in code_str or 'INTERNAL' in code_str
                else:
                    # Transport-level/transient
                    transient = any(k in str(e) for k in ('RESOURCE_EXHAUSTED', 'UNAVAILABLE', 'RST_STREAM', 'deadline exceeded'))

                if not transient or attempt == max_attempts:
                    raise
                # Backoff with jitter, prefer server hint if present
                if retry_after:
                    sleep_s = float(retry_after)
                else:
                    sleep_s = base * (2 ** (attempt - 1)) * (1 + random.random())
                time.sleep(min(sleep_s, 10.0))
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
    def list_campaigns(self, customer_id: str) -> List[Dict[str, Any]]:
        """Return campaigns with delivery/status fields and channel type."""
        q = (
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.serving_status, campaign.primary_status, "
            "campaign.primary_status_reasons, campaign.advertising_channel_type "
            "FROM campaign ORDER BY campaign.name"
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

    # --- Metrics --------------------------------------------------------
    def fetch_daily_metrics(self, customer_id: str, start: date, end: date, level: str = "campaign") -> List[Dict[str, Any]]:
        """Fetch daily metrics for a given level (campaign/ad_group/ad).

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
        q = (
            f"SELECT {select_id}, "
            "metrics.impressions, metrics.clicks, metrics.cost_micros, "
            "metrics.conversions, metrics.conversions_value, segments.date "
            f"FROM {resource} "
            f"WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"
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
                "conversions": float(m.conversions or 0.0),
                "revenue": float(m.conversions_value or 0.0),
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
