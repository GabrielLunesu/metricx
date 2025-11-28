"""RQ worker entrypoint for sync jobs.

WHAT:
    Processes sync jobs for Meta/Google/Shopify connections outside HTTP request cycle.

WHY:
    - Keeps FastAPI responses fast (enqueue job instead of blocking)
    - Central place to update sync tracking fields on Connection model
    - Reuses service-layer sync functions for all providers

REFERENCES:
    - docs/living-docs/REALTIME_SYNC_STATUS.md
    - backend/app/services/meta_sync_service.py
    - backend/app/services/google_sync_service.py
    - backend/app/services/shopify_sync_service.py
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Connection, ProviderEnum
from app.schemas import MetricsSyncRequest
from app.services.meta_sync_service import (
    sync_meta_entities,
    sync_meta_metrics,
)
from app.services.google_sync_service import (
    sync_google_entities,
    sync_google_metrics,
)
from app.services.shopify_sync_service import (
    sync_shopify_all,
)

logger = logging.getLogger(__name__)


def process_sync_job(connection_id: str, workspace_id: str) -> dict:
    """RQ job handler.

    Args:
        connection_id: UUID string
        workspace_id: UUID string
    """
    db: Session = SessionLocal()
    try:
        connection = (
            db.query(Connection)
            .filter(
                Connection.id == UUID(connection_id),
                Connection.workspace_id == UUID(workspace_id),
            )
            .first()
        )

        if not connection:
            logger.error(
                "[SYNC_WORKER] Connection %s not found (workspace=%s)",
                connection_id,
                workspace_id,
            )
            return {"success": False, "error": "Connection not found"}

        logger.info(
            "[SYNC_WORKER] Processing job for connection %s (%s)",
            connection_id,
            connection.provider,
        )

        # Update attempt tracking
        connection.last_sync_attempted_at = datetime.utcnow()
        connection.sync_status = "syncing"
        connection.total_syncs_attempted += 1
        connection.last_sync_error = None
        db.commit()

        if connection.provider == ProviderEnum.meta:
            entity_resp = sync_meta_entities(
                db=db,
                workspace_id=connection.workspace_id,
                connection_id=connection.id,
            )
            metrics_resp = sync_meta_metrics(
                db=db,
                workspace_id=connection.workspace_id,
                connection_id=connection.id,
                request=MetricsSyncRequest(),
            )
        elif connection.provider == ProviderEnum.google:
            entity_resp = sync_google_entities(
                db=db,
                workspace_id=connection.workspace_id,
                connection_id=connection.id,
            )
            metrics_resp = sync_google_metrics(
                db=db,
                workspace_id=connection.workspace_id,
                connection_id=connection.id,
                request=MetricsSyncRequest(),
            )
        elif connection.provider == ProviderEnum.shopify:
            # =========================================================================
            # Shopify sync (async functions - need asyncio.run)
            # =========================================================================
            # WHAT: Run full Shopify sync (products → customers → orders)
            # WHY: sync_shopify_all is async due to GraphQL client with httpx
            #      RQ worker is synchronous, so we wrap with asyncio.run()
            shopify_result = asyncio.run(
                sync_shopify_all(
                    db=db,
                    workspace_id=connection.workspace_id,
                    connection_id=connection.id,
                    force_full_sync=False,
                )
            )

            # Convert Shopify response to match expected return format
            # WHAT: Create pseudo entity/metrics responses for consistent return
            # WHY: Maintains uniform interface across all providers
            entity_resp = type(
                "EntityResponse",
                (),
                {
                    "synced": type(
                        "Synced",
                        (),
                        {
                            "model_dump": lambda self: {
                                "products": shopify_result.stats.products_created + shopify_result.stats.products_updated,
                                "customers": shopify_result.stats.customers_created + shopify_result.stats.customers_updated,
                            }
                        },
                    )()
                },
            )()
            metrics_resp = type(
                "MetricsResponse",
                (),
                {
                    "synced": type(
                        "Synced",
                        (),
                        {
                            "facts_ingested": shopify_result.stats.orders_created + shopify_result.stats.orders_updated,
                            "model_dump": lambda self: {
                                "orders": shopify_result.stats.orders_created + shopify_result.stats.orders_updated,
                                "revenue": float(shopify_result.stats.total_revenue),
                                "profit": float(shopify_result.stats.total_profit),
                            },
                        },
                    )()
                },
            )()

            # Check for errors in Shopify sync
            if not shopify_result.success:
                raise Exception("; ".join(shopify_result.errors) or "Shopify sync failed")
        else:
            logger.error(
                "[SYNC_WORKER] Unsupported provider %s for connection %s",
                connection.provider,
                connection_id,
            )
            connection.sync_status = "error"
            connection.last_sync_error = f"Unsupported provider {connection.provider}"
            db.commit()
            return {"success": False, "error": "Unsupported provider"}

        # Update success tracking
        connection.last_sync_completed_at = datetime.utcnow()
        connection.sync_status = "idle"

        if metrics_resp.synced.facts_ingested > 0:
            connection.last_metrics_changed_at = datetime.utcnow()
            connection.total_syncs_with_changes += 1

        db.commit()

        logger.info(
            "[SYNC_WORKER] Sync complete for connection %s (ingested=%s)",
            connection_id,
            metrics_resp.synced.facts_ingested,
        )

        return {
            "success": True,
            "entity": entity_resp.synced.model_dump(),
            "metrics": metrics_resp.synced.model_dump(),
        }

    except Exception as exc:  # pragma: no cover - defensive logging
        error_msg = str(exc)
        
        # Detect rate limit errors
        is_rate_limit = (
            "rate limit" in error_msg.lower() or 
            "request limit" in error_msg.lower() or
            "user request limit reached" in error_msg.lower()
        )
        
        if is_rate_limit:
            logger.warning(
                "[SYNC_WORKER] Rate limit hit for connection %s - cooldown activated",
                connection_id
            )
            error_msg = f"⏸ Rate limit reached. Pausing syncs for 15 minutes. {error_msg}"
        else:
            logger.exception(
                "[SYNC_WORKER] Unexpected error for connection %s: %s",
                connection_id,
                exc,
            )
        
        if connection:
            connection.sync_status = "error"
            connection.last_sync_error = error_msg
            db.commit()
        
        return {"success": False, "error": error_msg, "is_rate_limit": is_rate_limit}
    finally:
        db.close()

