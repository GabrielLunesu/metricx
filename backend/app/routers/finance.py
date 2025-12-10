"""Finance & P&L endpoints.

WHAT: REST API for Finance page data (P&L aggregation + manual costs CRUD)
WHY: Combines ad spend (MetricSnapshot) with manual costs for complete P&L view

DATA SOURCE:
  Uses MetricSnapshot table (15-min granularity) instead of deprecated MetricFact.

REFERENCES:
  - app/models.py: MetricSnapshot, ManualCost, Entity
  - app/schemas.py: Finance schemas
  - app/services/cost_allocation.py: Pro-rating logic
  - ui/lib/financeApiClient.js: Frontend consumer

Design decisions:
  - Aggregates from MetricSnapshot (real-time) not Pnl (future optimization)
  - Supports monthly granularity now, daily in contract (future-proof)
  - All queries workspace-scoped at SQL level (security)
"""

from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.cost_allocation import calculate_allocated_amount, get_allocated_costs

router = APIRouter(
    prefix="/workspaces",
    tags=["Finance"],
)


# ============================================================================
# P&L ENDPOINTS
# ============================================================================

@router.get(
    "/{workspace_id}/finance/pnl",
    response_model=schemas.PnLStatementResponse,
    summary="Get P&L statement",
    description="""
    Get complete P&L statement combining ad spend and manual costs.

    Data sources:
      - Ad spend: Aggregated from MetricSnapshot (real-time, 15-min granularity)
      - Manual costs: From manual_costs table with date allocation

    Future support: Can switch to daily granularity without breaking contract.
    """
)
def get_pnl_statement(
    workspace_id: UUID,
    granularity: str = Query("month", description="Granularity: month (now) or day (future)"),
    period_start: date = Query(..., description="Period start (YYYY-MM-DD, inclusive)"),
    period_end: date = Query(..., description="Period end (YYYY-MM-DD, exclusive)"),
    compare: bool = Query(False, description="Include previous period comparison"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get P&L statement for a period.

    WHAT: Aggregates ad spend + manual costs into P&L rows
    WHY: Finance page needs complete cost picture

    Process:
      1. Aggregate ad spend by provider from MetricSnapshot
      2. Aggregate manual costs by category (pro-rated)
      3. Compute summary KPIs (revenue, spend, profit, ROAS)
      4. Build P&L rows (one per provider + one per manual category)
      5. Optionally compare to previous period
    """
    # Verify workspace access
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    # ========================================================================
    # 1. AGGREGATE AD SPEND BY PROVIDER
    # ========================================================================
    # WHAT: Sum all base measures from MetricSnapshot, group by provider
    # WHY: Each ad platform becomes one P&L row
    # REFACTORED: Now uses UnifiedMetricService for consistent calculations
    
    # Import UnifiedMetricService
    from app.services.unified_metric_service import UnifiedMetricService, MetricFilters
    from app.dsl.schema import TimeRange as DSLTimeRange
    
    # Initialize service
    service = UnifiedMetricService(db)
    
    # Convert period to service inputs
    time_range = DSLTimeRange(start=period_start, end=period_end)
    filters = MetricFilters(
        provider=None,  # Get all providers
        level=None,
        status=None,  # Include ALL entities (active + inactive) as per comment
        entity_ids=None,
        entity_name=None,
        metric_filters=None
    )
    
    # Get breakdown by provider
    breakdown_items = service.get_breakdown(
        workspace_id=str(workspace_id),
        metric="revenue",  # Use revenue as the primary metric for breakdown
        time_range=time_range,
        filters=filters,
        breakdown_dimension="provider",
        top_n=100,  # Get all providers
        sort_order="desc"
    )
    
    # Convert to expected format
    ad_spend_by_provider = {}
    for item in breakdown_items:
        provider = item.label  # Provider name from breakdown
        ad_spend_by_provider[provider] = {
            "spend": float(item.spend or 0),
            "revenue": float(item.revenue or 0),
            "clicks": int(item.clicks or 0),
            "impressions": int(item.impressions or 0),
            "conversions": float(item.conversions or 0),
        }
    
    # ========================================================================
    # 2. AGGREGATE MANUAL COSTS BY CATEGORY
    # ========================================================================
    # WHAT: Get all manual costs for workspace, pro-rate to period
    # WHY: Manual costs must be included in total spend
    # REFERENCES: app/services/cost_allocation.py:get_allocated_costs
    
    manual_costs = db.query(models.ManualCost).filter(
        models.ManualCost.workspace_id == workspace_id
    ).all()
    
    manual_by_category = get_allocated_costs(manual_costs, period_start, period_end)
    
    # ========================================================================
    # 3. COMPUTE SUMMARY KPIS
    # ========================================================================
    # WHAT: Total revenue, spend, profit, ROAS
    # WHY: Powers summary cards at top of page
    
    total_ad_spend = sum(p["spend"] for p in ad_spend_by_provider.values())
    total_manual_spend = sum(manual_by_category.values())
    total_spend = total_ad_spend + total_manual_spend
    
    total_revenue = sum(p["revenue"] for p in ad_spend_by_provider.values())
    gross_profit = total_revenue - total_spend
    net_roas = total_revenue / total_spend if total_spend > 0 else 0
    
    summary = schemas.PnLSummary(
        total_revenue=total_revenue,
        total_spend=total_spend,
        gross_profit=gross_profit,
        net_roas=net_roas,
    )
    
    # ========================================================================
    # 4. BUILD P&L ROWS
    # ========================================================================
    # WHAT: One row per provider + one row per manual cost category
    # WHY: Finance table displays all cost sources
    
    rows: List[schemas.PnLRow] = []
    
    # Ad platform rows
    for provider, data in ad_spend_by_provider.items():
        # Convert enum string to readable name
        provider_name = provider.replace("ProviderEnum.", "").capitalize()
        rows.append(schemas.PnLRow(
            id=f"ads-{provider}",
            category=f"Ad Spend - {provider_name}",
            actual_dollar=data["spend"],
            planned_dollar=None,  # TODO: Budget feature
            variance_pct=None,
            notes=None,
            source="ads"
        ))
    
    # Manual cost rows
    for category, amount in manual_by_category.items():
        rows.append(schemas.PnLRow(
            id=f"manual-{category}",
            category=category,
            actual_dollar=amount,
            planned_dollar=None,
            variance_pct=None,
            notes=None,
            source="manual"
        ))
    
    # ========================================================================
    # 5. BUILD COMPOSITION (PIE CHART)
    # ========================================================================
    # WHAT: Spend breakdown for visualization
    # WHY: ChartsSection shows spend composition
    
    composition = [
        schemas.CompositionSlice(label=row.category, value=row.actual_dollar)
        for row in rows
    ]
    
    # ========================================================================
    # 6. PREVIOUS PERIOD COMPARISON (OPTIONAL)
    # ========================================================================
    # WHAT: Same aggregation for previous period, compute deltas
    # WHY: Compare toggle shows period-over-period changes
    # REFERENCES: app/routers/kpis.py:get_workspace_kpis (similar logic)
    
    if compare:
        # Calculate previous period (same length)
        period_length = (period_end - period_start).days
        prev_start = period_start - timedelta(days=period_length)
        prev_end = period_start

        # Use MetricSnapshot instead of deprecated MetricFact
        MS = models.MetricSnapshot

        # Aggregate previous ad spend
        prev_ad_query = (
            db.query(
                func.sum(MS.spend).label("spend"),
                func.sum(MS.revenue).label("revenue"),
            )
            .join(models.Entity, models.Entity.id == MS.entity_id)
            .filter(models.Entity.workspace_id == workspace_id)
            .filter(func.date(MS.captured_at) >= prev_start)
            .filter(func.date(MS.captured_at) < prev_end)
        ).one()
        
        prev_ad_spend = float(prev_ad_query.spend or 0)
        prev_ad_revenue = float(prev_ad_query.revenue or 0)
        
        # Pro-rate previous manual costs
        prev_manual_by_category = get_allocated_costs(manual_costs, prev_start, prev_end)
        prev_manual_spend = sum(prev_manual_by_category.values())
        
        prev_total_spend = prev_ad_spend + prev_manual_spend
        prev_total_revenue = prev_ad_revenue
        prev_profit = prev_total_revenue - prev_total_spend
        prev_roas = prev_total_revenue / prev_total_spend if prev_total_spend > 0 else 0
        
        # Compute deltas
        summary.compare = schemas.PnLComparison(
            revenue_delta_pct=(total_revenue - prev_total_revenue) / prev_total_revenue if prev_total_revenue > 0 else None,
            spend_delta_pct=(total_spend - prev_total_spend) / prev_total_spend if prev_total_spend > 0 else None,
            profit_delta_pct=(gross_profit - prev_profit) / abs(prev_profit) if prev_profit != 0 else None,
            roas_delta=net_roas - prev_roas
        )
    
    # ========================================================================
    # 7. BUILD TIMESERIES (REVENUE CHART)
    # ========================================================================
    # WHAT: Daily revenue data for the period
    # WHY: Frontend needs this for the Revenue bar chart
    
    # Query daily revenue data from MetricSnapshot
    MS = models.MetricSnapshot
    daily_data = (
        db.query(
            func.date(MS.captured_at).label("date"),
            func.sum(MS.revenue).label("revenue"),
            func.sum(MS.spend).label("spend")
        )
        .join(models.Entity, MS.entity_id == models.Entity.id)
        .filter(models.Entity.workspace_id == workspace_id)
        # Note: Finance includes ALL entities (active + inactive) because inactive campaigns still generated revenue
        .filter(func.date(MS.captured_at) >= period_start)
        .filter(func.date(MS.captured_at) < period_end)
        .group_by(func.date(MS.captured_at))
        .order_by(func.date(MS.captured_at))
        .all()
    )
    
    # Convert to timeseries format
    timeseries = [
        {
            "date": str(row.date),
            "revenue": float(row.revenue or 0),
            "spend": float(row.spend or 0)
        }
        for row in daily_data
    ]
    
    # ========================================================================
    # 8. RETURN COMPLETE STATEMENT
    # ========================================================================
    
    return schemas.PnLStatementResponse(
        summary=summary,
        rows=rows,
        composition=composition,
        timeseries=timeseries
    )


# ============================================================================
# MANUAL COSTS CRUD
# ============================================================================

@router.post(
    "/{workspace_id}/finance/costs",
    response_model=schemas.ManualCostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual cost",
)
def create_manual_cost(
    workspace_id: UUID,
    cost: schemas.ManualCostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a manual cost entry."""
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    # Convert allocation to DB fields
    allocation_type = cost.allocation.type
    allocation_date = cost.allocation.date if cost.allocation.type == "one_off" else None
    allocation_start = cost.allocation.start_date if cost.allocation.type == "range" else None
    allocation_end = cost.allocation.end_date if cost.allocation.type == "range" else None
    
    db_cost = models.ManualCost(
        label=cost.label,
        category=cost.category,
        amount_dollar=cost.amount_dollar,
        allocation_type=allocation_type,
        allocation_date=allocation_date,
        allocation_start=allocation_start,
        allocation_end=allocation_end,
        notes=cost.notes,
        workspace_id=workspace_id,
        created_by_user_id=current_user.id
    )
    
    db.add(db_cost)
    db.commit()
    db.refresh(db_cost)
    
    # Convert back to schema
    return _cost_to_schema(db_cost)


@router.get(
    "/{workspace_id}/finance/costs",
    response_model=List[schemas.ManualCostOut],
    summary="List manual costs",
)
def list_manual_costs(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all manual costs for workspace."""
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    costs = db.query(models.ManualCost).filter(
        models.ManualCost.workspace_id == workspace_id
    ).order_by(models.ManualCost.created_at.desc()).all()
    
    return [_cost_to_schema(c) for c in costs]


@router.put(
    "/{workspace_id}/finance/costs/{cost_id}",
    response_model=schemas.ManualCostOut,
    summary="Update manual cost",
)
def update_manual_cost(
    workspace_id: UUID,
    cost_id: UUID,
    updates: schemas.ManualCostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a manual cost entry."""
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    db_cost = db.query(models.ManualCost).filter(
        models.ManualCost.id == cost_id,
        models.ManualCost.workspace_id == workspace_id
    ).first()
    
    if not db_cost:
        raise HTTPException(status_code=404, detail="Cost not found")
    
    # Apply updates
    if updates.label is not None:
        db_cost.label = updates.label
    if updates.category is not None:
        db_cost.category = updates.category
    if updates.amount_dollar is not None:
        db_cost.amount_dollar = updates.amount_dollar
    if updates.notes is not None:
        db_cost.notes = updates.notes
    if updates.allocation is not None:
        db_cost.allocation_type = updates.allocation.type
        db_cost.allocation_date = updates.allocation.date if updates.allocation.type == "one_off" else None
        db_cost.allocation_start = updates.allocation.start_date if updates.allocation.type == "range" else None
        db_cost.allocation_end = updates.allocation.end_date if updates.allocation.type == "range" else None
    
    db_cost.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_cost)
    
    return _cost_to_schema(db_cost)


@router.delete(
    "/{workspace_id}/finance/costs/{cost_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete manual cost",
)
def delete_manual_cost(
    workspace_id: UUID,
    cost_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a manual cost entry."""
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    db_cost = db.query(models.ManualCost).filter(
        models.ManualCost.id == cost_id,
        models.ManualCost.workspace_id == workspace_id
    ).first()
    
    if not db_cost:
        raise HTTPException(status_code=404, detail="Cost not found")
    
    db.delete(db_cost)
    db.commit()
    
    return None


# ============================================================================
# FINANCIAL INSIGHT (QA INTEGRATION)
# ============================================================================

@router.post(
    "/{workspace_id}/finance/insight",
    response_model=schemas.FinancialInsightResponse,
    summary="Get AI financial insight",
)
def get_financial_insight(
    workspace_id: UUID,
    req: schemas.FinancialInsightRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get AI-generated financial insight via QA system.
    
    WHAT: Constructs QA question and returns formatted answer
    WHY: Powers AI insights section on Finance page
    REFERENCES: app/routers/qa.py:ask_question
    """
    if str(current_user.workspace_id) != str(workspace_id):
        raise HTTPException(status_code=403, detail="Workspace access denied")
    
    # Construct QA question
    question = f"Give me a financial breakdown of {req.month} {req.year}"

    # Call Semantic QA service (v3.0+ - replaced legacy QAService)
    from app.services.semantic_qa_service import SemanticQAService
    qa_service = SemanticQAService(db)

    try:
        result = qa_service.answer(
            question=question,
            workspace_id=str(workspace_id),
            user_id=str(current_user.id)
        )

        return schemas.FinancialInsightResponse(
            message=result.get("answer", "No insight available.")
        )
    except Exception as e:
        # Fallback message
        return schemas.FinancialInsightResponse(
            message=f"Unable to generate insight for {req.month} {req.year}. Please try again."
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _cost_to_schema(cost: models.ManualCost) -> schemas.ManualCostOut:
    """Convert DB model to schema."""
    # Extract dates properly - if they're datetime objects, get the date part; if already date, use as-is
    def extract_date(dt):
        if dt is None:
            return None
        if hasattr(dt, 'date'):
            return dt.date()
        return dt
    
    allocation = schemas.ManualCostAllocation(
        type=cost.allocation_type,
        date=extract_date(cost.allocation_date),
        start_date=extract_date(cost.allocation_start),
        end_date=extract_date(cost.allocation_end)
    )
    
    return schemas.ManualCostOut(
        id=cost.id,
        label=cost.label,
        category=cost.category,
        amount_dollar=float(cost.amount_dollar),
        allocation=allocation,
        notes=cost.notes,
        workspace_id=cost.workspace_id,
        created_at=cost.created_at,
        updated_at=cost.updated_at
    )


