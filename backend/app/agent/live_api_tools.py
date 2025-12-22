"""
Live API Tools
==============

**Version**: 1.0.0
**Created**: 2025-12-17

Live API query tools for the AI Copilot.

WHY THIS FILE EXISTS
--------------------
The semantic layer queries pre-aggregated snapshot data. However, some
questions require real-time data:
- "What's my spend TODAY right now?"
- "What's my current budget?"
- "Show me campaigns I just created"

This module provides tools to query Google/Meta Ads APIs directly when:
1. User explicitly requests "live" or "real-time" data
2. Snapshot data is stale (>24h) or missing

SECURITY GUARDRAILS
-------------------
- READ-ONLY operations only - no modifications to campaigns/ads
- Workspace scoped - can only query connections in user's workspace
- Rate limited - per-workspace limits prevent abuse
- Audit logged - all calls tracked for security

RELATED FILES
-------------
- app/agent/tools.py: SemanticTools (snapshot-based queries)
- app/agent/connection_resolver.py: Token decryption and client instantiation
- app/agent/rate_limiter.py: Per-workspace rate limiting
- app/agent/exceptions.py: Custom error types
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session
from redis import Redis

from app.models import Connection, MetricSnapshot, Entity, ProviderEnum
from app.agent.connection_resolver import ConnectionResolver
from app.agent.rate_limiter import WorkspaceRateLimiter
from app.agent.exceptions import (
    LiveApiError,
    QuotaExhaustedError,
    TokenExpiredError,
    WorkspaceRateLimitError,
    ProviderNotConnectedError,
    LiveApiTimeoutError,
)
from app.services.google_ads_client import GAdsClient, QuotaExhaustedError as GoogleQuotaError
from app.services.meta_ads_client import MetaAdsClient, MetaAdsClientError

logger = logging.getLogger(__name__)

# Staleness threshold in hours (24 hours = stale)
STALENESS_THRESHOLD_HOURS = 24


class LiveApiTools:
    """
    Live API query tools for the AI Copilot.

    WHAT:
        Provides real-time data fetching from Google Ads and Meta Ads APIs.
        Complements SemanticTools which queries snapshot data.

    WHY:
        - Some questions need real-time data (current budget, today's spend)
        - New entities may not be in snapshots yet
        - Auto-fallback when snapshots are stale

    SECURITY:
        - READ-ONLY operations only
        - Workspace scoped via ConnectionResolver
        - Rate limited via WorkspaceRateLimiter
        - All calls logged for audit

    USAGE:
        tools = LiveApiTools(db, workspace_id, user_id, redis_client)

        # Check if snapshots are stale
        freshness = tools.check_data_freshness()

        # Get live metrics
        metrics = tools.get_live_metrics(
            provider="meta",
            entity_type="campaign",
            metrics=["spend", "impressions", "clicks"],
            date_range="today"
        )

        # Get entity details
        details = tools.get_live_entity_details(
            provider="google",
            entity_type="campaign",
            entity_id="123456789",
            fields=["budget", "status", "objective"]
        )
    """

    def __init__(
        self,
        db: Session,
        workspace_id: str,
        user_id: str,
        redis_client: Optional[Redis] = None,
    ):
        """
        Initialize live API tools.

        PARAMETERS:
            db: SQLAlchemy session
            workspace_id: UUID of the workspace
            user_id: UUID of the user making the request
            redis_client: Optional Redis client for rate limiting
        """
        self.db = db
        self.workspace_id = str(workspace_id)
        self.user_id = str(user_id)

        # Initialize helpers
        self.resolver = ConnectionResolver(db, workspace_id)
        self.rate_limiter = WorkspaceRateLimiter(redis_client, workspace_id)

        # Track API calls for logging
        self.api_calls: List[Dict[str, Any]] = []

    def _log_api_call(
        self,
        provider: str,
        endpoint: str,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """
        Log an API call for audit trail.

        WHAT:
            Records API call metadata for debugging and observability.
        """
        call = {
            "provider": provider,
            "endpoint": endpoint,
            "success": success,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
        }
        if error:
            call["error"] = error

        self.api_calls.append(call)

        log_fn = logger.info if success else logger.warning
        log_fn(
            f"[LIVE_API] {provider}.{endpoint} "
            f"{'OK' if success else 'FAIL'} "
            f"({latency_ms}ms) workspace={self.workspace_id}"
        )

    def check_data_freshness(
        self,
        provider: Optional[Literal["google", "meta"]] = None,
    ) -> Dict[str, Any]:
        """
        Check if snapshot data is stale and live fallback might be needed.

        WHAT:
            Queries MetricSnapshot to find the most recent data timestamp.
            Returns freshness status per provider.

        WHY:
            Determines if auto-fallback to live API is needed.
            Data older than STALENESS_THRESHOLD_HOURS is considered stale.

        PARAMETERS:
            provider: Optional filter to check specific provider only

        RETURNS:
            {
                "google": {
                    "last_sync": "2024-01-01T12:00:00Z",
                    "is_stale": False,
                    "hours_old": 2.5
                },
                "meta": {
                    "last_sync": "2024-01-01T10:00:00Z",
                    "is_stale": True,
                    "hours_old": 26.0
                }
            }
        """
        result = {}
        providers_to_check = [provider] if provider else ["google", "meta"]

        for prov in providers_to_check:
            # Find most recent snapshot for this provider in workspace
            latest = (
                self.db.query(MetricSnapshot.captured_at)
                .join(Entity)
                .filter(
                    Entity.workspace_id == self.workspace_id,
                    Entity.provider == (ProviderEnum.google if prov == "google" else ProviderEnum.meta),
                )
                .order_by(MetricSnapshot.captured_at.desc())
                .first()
            )

            if not latest or not latest[0]:
                result[prov] = {
                    "last_sync": None,
                    "is_stale": True,
                    "hours_old": None,
                    "reason": "no_data",
                }
            else:
                last_sync = latest[0]
                now = datetime.now(timezone.utc)

                # Handle timezone-naive datetimes
                if last_sync.tzinfo is None:
                    last_sync = last_sync.replace(tzinfo=timezone.utc)

                hours_old = (now - last_sync).total_seconds() / 3600
                is_stale = hours_old > STALENESS_THRESHOLD_HOURS

                result[prov] = {
                    "last_sync": last_sync.isoformat(),
                    "is_stale": is_stale,
                    "hours_old": round(hours_old, 1),
                }

        return result

    def get_live_metrics(
        self,
        provider: Literal["google", "meta"],
        entity_type: Literal["account", "campaign", "adset", "ad"] = "account",
        entity_ids: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        date_range: Literal["today", "yesterday", "last_7d", "last_30d"] = "today",
    ) -> Dict[str, Any]:
        """
        Fetch live metrics from provider API.

        WHAT:
            Queries Google Ads or Meta Ads API for real-time performance metrics.

        WHY:
            Provides up-to-the-minute data when snapshots are stale or user
            explicitly requests live data.

        PARAMETERS:
            provider: Which ad platform to query ("google" or "meta")
            entity_type: Granularity level (account/campaign/adset/ad)
            entity_ids: Optional filter to specific entity IDs
            metrics: Which metrics to fetch (defaults to common metrics)
            date_range: Time period to query

        RETURNS:
            {
                "success": True,
                "data": {
                    "summary": {"spend": 1234.56, "impressions": 50000, ...},
                    "breakdown": [...] // if entity_type != "account"
                },
                "provider": "meta",
                "fetched_at": "2024-01-01T12:00:00Z",
                "is_live": True
            }

        RAISES:
            ProviderNotConnectedError: No connection for provider
            WorkspaceRateLimitError: Rate limit exceeded
            QuotaExhaustedError: API quota exceeded
            TokenExpiredError: OAuth token expired
        """
        start_time = datetime.now()

        # Default metrics if not specified
        if metrics is None:
            metrics = ["spend", "impressions", "clicks", "conversions", "revenue"]

        # Check rate limit BEFORE making the call
        if not self.rate_limiter.can_make_call(provider):
            retry_after = self.rate_limiter.get_retry_after(provider)
            raise WorkspaceRateLimitError(
                retry_after=retry_after,
                workspace_id=self.workspace_id,
                provider=provider,
            )

        try:
            # Calculate date range
            today = date.today()
            if date_range == "today":
                start_date = today
                end_date = today
            elif date_range == "yesterday":
                start_date = today - timedelta(days=1)
                end_date = today - timedelta(days=1)
            elif date_range == "last_7d":
                start_date = today - timedelta(days=6)
                end_date = today
            else:  # last_30d
                start_date = today - timedelta(days=29)
                end_date = today

            # Fetch from appropriate provider
            if provider == "google":
                data = self._fetch_google_metrics(
                    entity_type, entity_ids, start_date, end_date
                )
            else:
                data = self._fetch_meta_metrics(
                    entity_type, entity_ids, start_date, end_date
                )

            # Record the API call
            self.rate_limiter.record_call(provider)

            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, "get_metrics", True, latency_ms)

            return {
                "success": True,
                "data": data,
                "provider": provider,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "is_live": True,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

        except (ProviderNotConnectedError, TokenExpiredError, WorkspaceRateLimitError):
            # Re-raise these as-is
            raise

        except GoogleQuotaError as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, "get_metrics", False, latency_ms, str(e))
            raise QuotaExhaustedError(
                provider="google",
                retry_after=getattr(e, "retry_seconds", None),
            )

        except MetaAdsClientError as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, "get_metrics", False, latency_ms, str(e))

            # Check if it's a rate limit error
            if "rate limit" in str(e).lower() or "too many" in str(e).lower():
                raise QuotaExhaustedError(provider="meta")
            raise LiveApiError(str(e), provider=provider)

        except Exception as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, "get_metrics", False, latency_ms, str(e))
            logger.exception(f"[LIVE_API] Unexpected error fetching {provider} metrics")
            raise LiveApiError(f"Failed to fetch metrics: {str(e)}", provider=provider)

    def _fetch_google_metrics(
        self,
        entity_type: str,
        entity_ids: Optional[List[str]],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Fetch metrics from Google Ads API.

        INTERNAL: Called by get_live_metrics().
        """
        client = self.resolver.get_google_client()
        account_id = self.resolver.get_account_id("google")

        # Normalize customer ID (remove dashes)
        customer_id = account_id.replace("-", "")

        # Map entity_type to Google Ads level
        level_map = {
            "account": "campaign",  # Account-level = sum of all campaigns
            "campaign": "campaign",
            "adset": "ad_group",  # Google calls it ad_group
            "ad": "ad",
        }
        level = level_map.get(entity_type, "campaign")

        # Fetch daily metrics
        raw_metrics = client.fetch_daily_metrics(
            customer_id=customer_id,
            start=start_date,
            end=end_date,
            level=level,
            active_only=False,
        )

        # Aggregate results
        summary = {
            "spend": 0.0,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
        }
        breakdown = []

        for row in raw_metrics:
            # Filter by entity_ids if specified
            if entity_ids and str(row.get("id")) not in entity_ids:
                continue

            # Aggregate to summary
            # Note: Google Ads client returns "revenue" field (from conversions_value_by_conversion_date)
            summary["spend"] += row.get("spend", 0) or 0
            summary["impressions"] += row.get("impressions", 0) or 0
            summary["clicks"] += row.get("clicks", 0) or 0
            summary["conversions"] += row.get("conversions", 0) or 0
            summary["revenue"] += row.get("revenue", 0) or 0

            # Add to breakdown if not account-level
            if entity_type != "account":
                breakdown.append({
                    "id": str(row.get("id")),
                    "name": row.get("name"),
                    "spend": row.get("spend", 0),
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "conversions": row.get("conversions", 0),
                    "revenue": row.get("revenue", 0),
                })

        # Calculate derived metrics (ROAS, CPC, CTR)
        if summary["spend"] > 0:
            summary["roas"] = round(summary["revenue"] / summary["spend"], 2)
            summary["cpc"] = round(summary["spend"] / summary["clicks"], 2) if summary["clicks"] > 0 else 0
        else:
            summary["roas"] = 0
            summary["cpc"] = 0

        if summary["impressions"] > 0:
            summary["ctr"] = round((summary["clicks"] / summary["impressions"]) * 100, 2)
        else:
            summary["ctr"] = 0

        result = {"summary": summary}
        if breakdown:
            result["breakdown"] = breakdown

        return result

    def _fetch_meta_metrics(
        self,
        entity_type: str,
        entity_ids: Optional[List[str]],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Fetch metrics from Meta Ads API.

        INTERNAL: Called by get_live_metrics().
        """
        client = self.resolver.get_meta_client()
        account_id = self.resolver.get_account_id("meta")

        # Ensure account_id has act_ prefix
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        # Map entity_type to Meta level
        level_map = {
            "account": "account",
            "campaign": "campaign",
            "adset": "adset",
            "ad": "ad",
        }
        level = level_map.get(entity_type, "ad")

        # Fetch insights at account level with breakdown
        raw_insights = client.get_account_insights(
            ad_account_id=account_id,
            level=level,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            time_increment=0,  # Aggregate, not daily
        )

        # Aggregate results
        summary = {
            "spend": 0.0,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
        }
        breakdown = []

        for row in raw_insights:
            # Filter by entity_ids if specified
            row_id = row.get("ad_id") or row.get("adset_id") or row.get("campaign_id")
            if entity_ids and str(row_id) not in entity_ids:
                continue

            # Parse values
            spend = float(row.get("spend", 0) or 0)
            impressions = int(row.get("impressions", 0) or 0)
            clicks = int(row.get("clicks", 0) or 0)
            conversions = int(row.get("conversions", 0) or 0)
            revenue = float(row.get("revenue", 0) or 0)

            # Aggregate to summary
            summary["spend"] += spend
            summary["impressions"] += impressions
            summary["clicks"] += clicks
            summary["conversions"] += conversions
            summary["revenue"] += revenue

            # Add to breakdown if not account-level
            if entity_type != "account":
                breakdown.append({
                    "id": str(row_id),
                    "name": row.get("ad_name") or row.get("adset_name") or row.get("campaign_name"),
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "revenue": revenue,
                })

        result = {"summary": summary}
        if breakdown:
            result["breakdown"] = breakdown

        return result

    def get_live_entity_details(
        self,
        provider: Literal["google", "meta"],
        entity_type: Literal["campaign", "adset", "ad"],
        entity_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch live entity configuration details.

        WHAT:
            Gets current settings for a campaign/adset/ad from the API.

        WHY:
            Budget changes, status updates, etc. may not be in snapshots yet.

        PARAMETERS:
            provider: Which ad platform
            entity_type: Type of entity
            entity_id: ID of the entity
            fields: Which fields to fetch (defaults to common fields)

        RETURNS:
            {
                "success": True,
                "data": {
                    "id": "123",
                    "name": "My Campaign",
                    "status": "ACTIVE",
                    "budget": 100.00,
                    "objective": "CONVERSIONS"
                },
                "provider": "meta",
                "fetched_at": "2024-01-01T12:00:00Z",
                "is_live": True
            }
        """
        start_time = datetime.now()

        # Default fields
        if fields is None:
            fields = ["budget", "status", "objective", "name"]

        # Check rate limit
        if not self.rate_limiter.can_make_call(provider):
            retry_after = self.rate_limiter.get_retry_after(provider)
            raise WorkspaceRateLimitError(
                retry_after=retry_after,
                workspace_id=self.workspace_id,
                provider=provider,
            )

        try:
            if provider == "google":
                data = self._fetch_google_entity(entity_type, entity_id)
            else:
                data = self._fetch_meta_entity(entity_type, entity_id)

            # Record the API call
            self.rate_limiter.record_call(provider)

            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, f"get_{entity_type}", True, latency_ms)

            return {
                "success": True,
                "data": data,
                "provider": provider,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "is_live": True,
            }

        except (ProviderNotConnectedError, TokenExpiredError, WorkspaceRateLimitError):
            raise

        except Exception as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, f"get_{entity_type}", False, latency_ms, str(e))
            logger.exception(f"[LIVE_API] Failed to fetch {entity_type} details")
            raise LiveApiError(f"Failed to fetch entity details: {str(e)}", provider=provider)

    def _fetch_google_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        """Fetch single entity details from Google Ads."""
        client = self.resolver.get_google_client()
        customer_id = self.resolver.get_account_id("google").replace("-", "")

        if entity_type == "campaign":
            campaigns = client.list_campaigns(customer_id)
            for c in campaigns:
                if str(c.get("id")) == entity_id:
                    return {
                        "id": str(c.get("id")),
                        "name": c.get("name"),
                        "status": c.get("status"),
                        "channel_type": c.get("channel_type"),
                    }
        elif entity_type == "adset":
            # Google calls it ad_group
            ad_groups = client.list_all_ad_groups(customer_id)
            for ag in ad_groups:
                if str(ag.get("id")) == entity_id:
                    return {
                        "id": str(ag.get("id")),
                        "name": ag.get("name"),
                        "status": ag.get("status"),
                    }
        elif entity_type == "ad":
            ads = client.list_all_ads(customer_id)
            for ad in ads:
                if str(ad.get("id")) == entity_id:
                    return {
                        "id": str(ad.get("id")),
                        "name": ad.get("name"),
                        "status": ad.get("status"),
                        "tracking_url_template": ad.get("tracking_url_template"),
                    }

        raise LiveApiError(f"{entity_type} {entity_id} not found", provider="google")

    def _fetch_meta_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        """Fetch single entity details from Meta Ads."""
        client = self.resolver.get_meta_client()
        account_id = self.resolver.get_account_id("meta")

        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        if entity_type == "campaign":
            campaigns = client.get_campaigns(account_id)
            for c in campaigns:
                if str(c.get("id")) == entity_id:
                    return {
                        "id": str(c.get("id")),
                        "name": c.get("name"),
                        "status": c.get("status"),
                        "objective": c.get("objective"),
                        "daily_budget": c.get("daily_budget"),
                        "lifetime_budget": c.get("lifetime_budget"),
                    }
        elif entity_type == "adset":
            # Need to iterate through campaigns to find adsets
            campaigns = client.get_campaigns(account_id)
            for camp in campaigns:
                adsets = client.get_adsets(camp.get("id"))
                for a in adsets:
                    if str(a.get("id")) == entity_id:
                        return {
                            "id": str(a.get("id")),
                            "name": a.get("name"),
                            "status": a.get("status"),
                            "daily_budget": a.get("daily_budget"),
                            "lifetime_budget": a.get("lifetime_budget"),
                            "bid_amount": a.get("bid_amount"),
                        }
        elif entity_type == "ad":
            # This could be expensive - consider caching
            campaigns = client.get_campaigns(account_id)
            for camp in campaigns:
                adsets = client.get_adsets(camp.get("id"))
                for adset in adsets:
                    ads = client.get_ads(adset.get("id"))
                    for ad in ads:
                        if str(ad.get("id")) == entity_id:
                            return {
                                "id": str(ad.get("id")),
                                "name": ad.get("name"),
                                "status": ad.get("status"),
                            }

        raise LiveApiError(f"{entity_type} {entity_id} not found", provider="meta")

    def list_live_entities(
        self,
        provider: Literal["google", "meta"],
        entity_type: Literal["campaign", "adset", "ad"],
        status_filter: Optional[Literal["active", "paused", "all"]] = "all",
        name_contains: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        List entities from the live API.

        WHAT:
            Gets current list of campaigns/adsets/ads from provider.

        WHY:
            New entities may not have been synced to snapshots yet.

        PARAMETERS:
            provider: Which ad platform
            entity_type: Type of entities to list
            status_filter: Filter by status
            name_contains: Filter by name substring
            limit: Max entities to return

        RETURNS:
            {
                "success": True,
                "data": {
                    "entities": [...],
                    "total": 15
                },
                "provider": "google",
                "fetched_at": "...",
                "is_live": True
            }
        """
        start_time = datetime.now()

        # Check rate limit
        if not self.rate_limiter.can_make_call(provider):
            retry_after = self.rate_limiter.get_retry_after(provider)
            raise WorkspaceRateLimitError(
                retry_after=retry_after,
                workspace_id=self.workspace_id,
                provider=provider,
            )

        try:
            if provider == "google":
                entities = self._list_google_entities(entity_type, status_filter)
            else:
                entities = self._list_meta_entities(entity_type, status_filter)

            # Apply name filter
            if name_contains:
                name_lower = name_contains.lower()
                entities = [
                    e for e in entities
                    if name_lower in (e.get("name") or "").lower()
                ]

            # Record the API call
            self.rate_limiter.record_call(provider)

            total = len(entities)
            entities = entities[:limit]

            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, f"list_{entity_type}s", True, latency_ms)

            return {
                "success": True,
                "data": {
                    "entities": entities,
                    "total": total,
                    "returned": len(entities),
                },
                "provider": provider,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "is_live": True,
            }

        except (ProviderNotConnectedError, TokenExpiredError, WorkspaceRateLimitError):
            raise

        except Exception as e:
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_api_call(provider, f"list_{entity_type}s", False, latency_ms, str(e))
            logger.exception(f"[LIVE_API] Failed to list {entity_type}s")
            raise LiveApiError(f"Failed to list entities: {str(e)}", provider=provider)

    def _list_google_entities(
        self,
        entity_type: str,
        status_filter: str,
    ) -> List[Dict[str, Any]]:
        """List entities from Google Ads."""
        client = self.resolver.get_google_client()
        customer_id = self.resolver.get_account_id("google").replace("-", "")

        active_only = status_filter == "active"

        if entity_type == "campaign":
            campaigns = client.list_campaigns(customer_id, active_only=active_only)
            return [
                {
                    "id": str(c.get("id")),
                    "name": c.get("name"),
                    "status": c.get("status"),
                    "channel_type": c.get("channel_type"),
                }
                for c in campaigns
                if status_filter == "all" or self._matches_status(c.get("status"), status_filter)
            ]
        elif entity_type == "adset":
            ad_groups = client.list_all_ad_groups(customer_id)
            return [
                {
                    "id": str(ag.get("id")),
                    "name": ag.get("name"),
                    "status": ag.get("status"),
                }
                for ag in ad_groups
                if status_filter == "all" or self._matches_status(ag.get("status"), status_filter)
            ]
        elif entity_type == "ad":
            ads = client.list_all_ads(customer_id)
            return [
                {
                    "id": str(ad.get("id")),
                    "name": ad.get("name"),
                    "status": ad.get("status"),
                }
                for ad in ads
                if status_filter == "all" or self._matches_status(ad.get("status"), status_filter)
            ]

        return []

    def _list_meta_entities(
        self,
        entity_type: str,
        status_filter: str,
    ) -> List[Dict[str, Any]]:
        """List entities from Meta Ads."""
        client = self.resolver.get_meta_client()
        account_id = self.resolver.get_account_id("meta")

        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        if entity_type == "campaign":
            campaigns = client.get_campaigns(account_id)
            return [
                {
                    "id": str(c.get("id")),
                    "name": c.get("name"),
                    "status": c.get("status"),
                    "objective": c.get("objective"),
                }
                for c in campaigns
                if status_filter == "all" or self._matches_status(c.get("status"), status_filter)
            ]
        elif entity_type == "adset":
            # Get all adsets across all campaigns
            campaigns = client.get_campaigns(account_id)
            adsets = []
            for camp in campaigns:
                camp_adsets = client.get_adsets(camp.get("id"))
                for a in camp_adsets:
                    if status_filter == "all" or self._matches_status(a.get("status"), status_filter):
                        adsets.append({
                            "id": str(a.get("id")),
                            "name": a.get("name"),
                            "status": a.get("status"),
                            "campaign_id": str(camp.get("id")),
                        })
            return adsets
        elif entity_type == "ad":
            # Get all ads (expensive operation)
            campaigns = client.get_campaigns(account_id)
            ads = []
            for camp in campaigns:
                adsets = client.get_adsets(camp.get("id"))
                for adset in adsets:
                    adset_ads = client.get_ads(adset.get("id"))
                    for ad in adset_ads:
                        if status_filter == "all" or self._matches_status(ad.get("status"), status_filter):
                            ads.append({
                                "id": str(ad.get("id")),
                                "name": ad.get("name"),
                                "status": ad.get("status"),
                                "adset_id": str(adset.get("id")),
                            })
            return ads

        return []

    def _matches_status(self, status: str, filter: str) -> bool:
        """Check if entity status matches filter."""
        if filter == "all":
            return True
        elif filter == "active":
            return status in ("ACTIVE", "ENABLED", "active", "enabled")
        elif filter == "paused":
            return status in ("PAUSED", "paused")
        return True

    def get_api_calls_summary(self) -> Dict[str, Any]:
        """
        Get summary of API calls made during this session.

        WHAT:
            Returns statistics about API calls for debugging/logging.

        RETURNS:
            {
                "total_calls": 5,
                "successful": 4,
                "failed": 1,
                "by_provider": {"google": 3, "meta": 2},
                "calls": [...]
            }
        """
        total = len(self.api_calls)
        successful = len([c for c in self.api_calls if c.get("success")])
        failed = total - successful

        by_provider = {}
        for call in self.api_calls:
            prov = call.get("provider", "unknown")
            by_provider[prov] = by_provider.get(prov, 0) + 1

        return {
            "total_calls": total,
            "successful": successful,
            "failed": failed,
            "by_provider": by_provider,
            "calls": self.api_calls,
        }
