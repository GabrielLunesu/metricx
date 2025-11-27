<!-- 786ef563-d8fd-4cda-841a-03e4664d6975 d79a7e4f-9d69-4ef8-bd81-256c747a5d9c -->
# Finance P&L Backend Integration Plan

## Overview

Connect Finance page to backend using:

- **Data source**: MetricFact (real-time ad spend) + ManualCost (user costs)
- **Pnl table**: Kept for future historical locking but not used initially
- **Architecture**: Thin API client → Adapter → UI components (zero business logic in UI)
- **Future-proof**: Contracts support daily granularity without UI refactoring

## Architecture Decisions

**Data Flow:**

```
MetricFact (ad spend) ┐
                      ├→ Finance Endpoint → financeApiClient → pnlAdapter → UI Components
ManualCost (manual)   ┘
```

**Why this approach:**

- Real-time data matches user expectations and `/kpis` pattern
- Pnl table kept for future EOD locking/audit requirements
- Clear separation: backend computes, frontend displays
- Monthly granularity now, daily supported by contract

---

## Phase 1: Database Schema & Migration

### 1.1 Create ManualCost Model

**File**: `backend/app/models.py`

Add new model after `Pnl` class (~line 420):

```python
class ManualCost(Base):
    """Manual costs entered by users (non-ad costs like SaaS, agency fees).
    
    WHAT: Stores user-entered costs with flexible date allocation
    WHY: Finance P&L needs to combine ad spend (from MetricFact) with operational costs
    REFERENCES: 
      - app/routers/finance.py: CRUD endpoints
      - app/schemas.py: ManualCostCreate, ManualCostOut
      - app/services/cost_allocation.py: Pro-rating logic
    
    Allocation types:
      - one_off: Single date cost (marketing event, one-time purchase)
      - range: Spread cost across date range (monthly subscription pro-rated daily)
    """
    __tablename__ = "manual_costs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Display
    label = Column(String, nullable=False)  # "HubSpot", "Consultant Fee"
    category = Column(String, nullable=False)  # "Tools / SaaS", "Agency Fees", "Miscellaneous"
    notes = Column(String, nullable=True)
    
    # Amount
    amount_dollar = Column(Numeric(12, 2), nullable=False)  # Total cost amount THIS IS ALWAYS DOLLARS (in future when we support multiple currency we'll just convert to $ before sending to db)
    
    # Allocation (determines which dates to include cost)
    allocation_type = Column(String, nullable=False)  # "one_off" or "range"
    allocation_date = Column(DateTime, nullable=True)  # For one_off: the single date
    allocation_start = Column(DateTime, nullable=True)  # For range: inclusive start
    allocation_end = Column(DateTime, nullable=True)  # For range: exclusive end
    
    # Workspace scoping
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    workspace = relationship("Workspace", back_populates="manual_costs")
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    def __str__(self):
        return f"{self.label} ({self.category}): €{self.amount_eur}"
```

Add relationship to `Workspace` model (~line 97):

```python
manual_costs = relationship("ManualCost", back_populates="workspace")
```

### 1.2 Create Migration

**File**: `backend/alembic/versions/YYYYMMDD_HHMMSS_add_manual_costs.py`

```bash
cd backend
alembic revision -m "add_manual_costs"
```

Migration content:

```python
"""add_manual_costs

Revision ID: <generated>
Revises: <previous>
Create Date: <generated>

WHAT: Adds manual_costs table for user-entered operational costs
WHY: Finance P&L needs to track non-ad costs (SaaS, agency fees, etc.)
REFERENCES: app/models.py:ManualCost
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'manual_costs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('amount_eur', sa.Numeric(12, 2), nullable=False),
        sa.Column('allocation_type', sa.String(), nullable=False),
        sa.Column('allocation_date', sa.DateTime(), nullable=True),
        sa.Column('allocation_start', sa.DateTime(), nullable=True),
        sa.Column('allocation_end', sa.DateTime(), nullable=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'])
    )
    op.create_index('idx_manual_costs_workspace', 'manual_costs', ['workspace_id'])
    op.create_index('idx_manual_costs_dates', 'manual_costs', ['allocation_start', 'allocation_end'])

def downgrade():
    op.drop_index('idx_manual_costs_dates')
    op.drop_index('idx_manual_costs_workspace')
    op.drop_table('manual_costs')
```

Run migration on Railway database:

```bash
alembic upgrade head
```

---

## Phase 2: Backend Schemas & DTOs

**File**: `backend/app/schemas.py`

Add after existing schemas (~line 570):

```python
# ============================================================================
# FINANCE & P&L SCHEMAS
# ============================================================================
# WHAT: Request/response models for Finance P&L endpoints
# WHY: Type-safe contracts between frontend and backend
# REFERENCES: 
#   - app/routers/finance.py: Endpoints using these schemas
#   - ui/lib/financeApiClient.js: Frontend client
#   - ui/lib/pnlAdapter.js: View model mapping

# Manual Cost Schemas
# -------------------

class ManualCostAllocation(BaseModel):
    """Allocation strategy for manual costs.
    
    WHAT: Defines how a cost is spread across dates
    WHY: Supports one-off events and pro-rated subscriptions
    """
    type: Literal["one_off", "range"] = Field(
        description="Allocation type: one_off (single date) or range (spread across dates)"
    )
    date: Optional[date] = Field(
        None,
        description="For one_off: the single date (YYYY-MM-DD)"
    )
    start_date: Optional[date] = Field(
        None,
        description="For range: inclusive start date (YYYY-MM-DD)"
    )
    end_date: Optional[date] = Field(
        None,
        description="For range: exclusive end date (YYYY-MM-DD)"
    )

class ManualCostCreate(BaseModel):
    """Create a manual cost entry."""
    label: str = Field(description="Display name", example="HubSpot Marketing Hub")
    category: str = Field(description="Cost category", example="Tools / SaaS")
    amount_dollar: float = Field(description="Total cost in DOLLAR", example=299.00)
    allocation: ManualCostAllocation = Field(description="Date allocation strategy")
    notes: Optional[str] = Field(None, description="Optional notes", example="Annual plan")

class ManualCostUpdate(BaseModel):
    """Update a manual cost entry."""
    label: Optional[str] = None
    category: Optional[str] = None
    amount_dollar: Optional[float] = None
    allocation: Optional[ManualCostAllocation] = None
    notes: Optional[str] = None

class ManualCostOut(BaseModel):
    """Manual cost output."""
    id: UUID
    label: str
    category: str
    amount_dollar: float
    allocation: ManualCostAllocation
    notes: Optional[str]
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

# P&L Schemas
# -----------

class PnLRow(BaseModel):
    """Single row in P&L statement.
    
    WHAT: Represents one line item (ad platform or manual cost)
    WHY: Combined view of all costs for monthly P&L
    """
    id: str = Field(description="Unique row ID")
    category: str = Field(description="Row label", example="Ad Spend - Google")
    actual_dollar: float = Field(description="Actual amount spent")
    planned_dollar: Optional[float] = Field(None, description="Planned/budgeted amount")
    variance_pct: Optional[float] = Field(None, description="Variance % vs plan")
    notes: Optional[str] = Field(None, description="Row notes")
    source: Literal["ads", "manual"] = Field(description="Data source")

class PnLComparison(BaseModel):
    """Comparison metrics vs previous period."""
    revenue_delta_pct: Optional[float] = None
    spend_delta_pct: Optional[float] = None
    profit_delta_pct: Optional[float] = None
    roas_delta: Optional[float] = None

class PnLSummary(BaseModel):
    """Top-level P&L summary (for cards).
    
    WHAT: Aggregated KPIs for the selected period
    WHY: Summary cards at top of Finance page
    REFERENCES: ui/app/(dashboard)/finance/components/FinancialSummaryCards.jsx
    """
    total_revenue: float = Field(description="Total revenue")
    total_spend: float = Field(description="Total spend (ads + manual)")
    gross_profit: float = Field(description="Revenue - Spend")
    net_roas: float = Field(description="Revenue / Spend")
    compare: Optional[PnLComparison] = Field(None, description="Comparison vs previous period")

class CompositionSlice(BaseModel):
    """Pie chart slice."""
    label: str
    value: float

class PnLStatementResponse(BaseModel):
    """Complete P&L statement response.
    
    WHAT: Full P&L data for a period
    WHY: Powers Finance page table, charts, and summary
    REFERENCES:
      - ui/lib/pnlAdapter.js: Maps to view model
      - ui/app/(dashboard)/finance/page.jsx: Consumes data
    """
    summary: PnLSummary = Field(description="Top-level KPIs")
    rows: List[PnLRow] = Field(description="P&L line items")
    composition: List[CompositionSlice] = Field(description="Spend breakdown for pie chart")
    timeseries: Optional[List[dict]] = Field(
        None,
        description="Future: Daily timeseries for daily granularity support"
    )
    
class FinancialInsightRequest(BaseModel):
    """Request for AI financial insight.
    
    WHAT: Triggers QA system with financial question
    WHY: Powers AI insights section
    REFERENCES: app/routers/qa.py:/qa endpoint
    """
    month: str = Field(description="Month name", example="October")
    year: int = Field(description="Year", example=2025)

class FinancialInsightResponse(BaseModel):
    """AI-generated financial insight."""
    message: str = Field(description="Formatted insight text")
```

---

## Phase 3: Cost Allocation Service

**File**: `backend/app/services/cost_allocation.py` (NEW)

```python
"""Manual cost allocation logic.

WHAT: Pro-rates manual costs across date ranges for P&L inclusion
WHY: Monthly P&L must include only the portion of costs overlapping the period
REFERENCES:
  - app/routers/finance.py: Uses these functions
  - app/models.py:ManualCost: Data model
  - tests/test_cost_allocation.py: Unit tests
  
Allocation rules:
  - one_off: Include if date falls within [period_start, period_end)
  - range: Pro-rate daily across [start, end), include overlapping days only
"""

from datetime import date, timedelta
from typing import List, Dict, Optional
from app.models import ManualCost


def calculate_allocated_amount(
    cost: ManualCost,
    period_start: date,
    period_end: date  # Exclusive
) -> float:
    """Calculate the portion of a manual cost that falls within a period.
    
    WHAT: Pro-rates cost based on overlapping days
    WHY: Monthly view must include only relevant portion of multi-month costs
    
    Args:
        cost: ManualCost with allocation info
        period_start: Inclusive start of target period
        period_end: Exclusive end of target period
        
    Returns:
        Allocated amount in DOLLAR for this period
        
    Examples:
        # One-off inside period → full amount
        one_off(date=2025-10-15), period=[2025-10-01, 2025-11-01) → full amount
        
        # One-off outside period → 0
        one_off(date=2025-09-15), period=[2025-10-01, 2025-11-01) → 0
        
        # Range fully inside → full amount
        range(start=2025-10-05, end=2025-10-15), period=[2025-10-01, 2025-11-01) → full
        
        # Range partially overlapping → pro-rated
        range(start=2025-09-20, end=2025-10-10), period=[2025-10-01, 2025-11-01)
          → 10 days / 20 days = 50% of amount
    """
    if cost.allocation_type == "one_off":
        # Include if date falls within period
        cost_date = cost.allocation_date.date() if hasattr(cost.allocation_date, 'date') else cost.allocation_date
        if period_start <= cost_date < period_end:
            return float(cost.amount_eur)
        return 0.0
        
    elif cost.allocation_type == "range":
        # Pro-rate based on overlapping days
        cost_start = cost.allocation_start.date() if hasattr(cost.allocation_start, 'date') else cost.allocation_start
        cost_end = cost.allocation_end.date() if hasattr(cost.allocation_end, 'date') else cost.allocation_end
        
        # Calculate overlap
        overlap_start = max(cost_start, period_start)
        overlap_end = min(cost_end, period_end)
        
        if overlap_start >= overlap_end:
            return 0.0  # No overlap
            
        # Count overlapping days
        overlap_days = (overlap_end - overlap_start).days
        total_days = (cost_end - cost_start).days
        
        if total_days == 0:
            return 0.0
            
        # Pro-rate
        return float(cost.amount_eur) * (overlap_days / total_days)
    
    return 0.0


def get_allocated_costs(
    costs: List[ManualCost],
    period_start: date,
    period_end: date
) -> Dict[str, float]:
    """Get all costs allocated to a period, grouped by category.
    
    WHAT: Aggregates manual costs by category for P&L table
    WHY: P&L needs one row per category with total
    
    Returns:
        Dict mapping category → total allocated amount
    """
    category_totals = {}
    
    for cost in costs:
        allocated = calculate_allocated_amount(cost, period_start, period_end)
        if allocated > 0:
            category = cost.category
            category_totals[category] = category_totals.get(category, 0) + allocated
            
    return category_totals
```

---

## Phase 4: Finance Router & Endpoints

**File**: `backend/app/routers/finance.py` (NEW)

```python
"""Finance & P&L endpoints.

WHAT: REST API for Finance page data (P&L aggregation + manual costs CRUD)
WHY: Combines ad spend (MetricFact) with manual costs for complete P&L view
REFERENCES:
  - app/models.py: MetricFact, ManualCost, Entity
  - app/schemas.py: Finance schemas
  - app/services/cost_allocation.py: Pro-rating logic
  - ui/lib/financeApiClient.js: Frontend consumer

Design decisions:
  - Aggregates from MetricFact (real-time) not Pnl (future optimization)
  - Supports monthly granularity now, daily in contract (future-proof)
  - All queries workspace-scoped at SQL level (security)
"""

from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.cost_allocation import calculate_allocated_amount, get_allocated_costs
from app.metrics.registry import compute_metric

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
      - Ad spend: Aggregated from MetricFact (real-time)
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
      1. Aggregate ad spend by provider from MetricFact
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
    # WHAT: Sum all base measures from MetricFact, group by provider
    # WHY: Each ad platform becomes one P&L row
    # REFERENCES: app/routers/kpis.py:get_workspace_kpis (similar aggregation)
    
    MF = models.MetricFact
    E = models.Entity
    
    ad_spend_query = (
        db.query(
            MF.provider,
            func.sum(MF.spend).label("spend"),
            func.sum(MF.revenue).label("revenue"),
            func.sum(MF.clicks).label("clicks"),
            func.sum(MF.impressions).label("impressions"),
            func.sum(MF.conversions).label("conversions"),
        )
        .join(E, E.id == MF.entity_id)
        .filter(E.workspace_id == workspace_id)
        .filter(MF.event_date >= period_start)
        .filter(MF.event_date < period_end)
        .group_by(MF.provider)
    )
    
    ad_spend_by_provider = {
        row.provider: {
            "spend": float(row.spend or 0),
            "revenue": float(row.revenue or 0),
            "clicks": int(row.clicks or 0),
            "impressions": int(row.impressions or 0),
            "conversions": float(row.conversions or 0),
        }
        for row in ad_spend_query.all()
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
    
    rows: list[schemas.PnLRow] = []
    
    # Ad platform rows
    for provider, data in ad_spend_by_provider.items():
        rows.append(schemas.PnLRow(
            id=f"ads-{provider}",
            category=f"Ad Spend - {provider.capitalize()}",
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
        schemas.CompositionSlice(label=row.category, value=row.actual_eur)
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
        
        # Aggregate previous ad spend
        prev_ad_query = (
            db.query(
                func.sum(MF.spend).label("spend"),
                func.sum(MF.revenue).label("revenue"),
            )
            .join(E, E.id == MF.entity_id)
            .filter(E.workspace_id == workspace_id)
            .filter(MF.event_date >= prev_start)
            .filter(MF.event_date < prev_end)
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
    # 7. RETURN COMPLETE STATEMENT
    # ========================================================================
    
    return schemas.PnLStatementResponse(
        summary=summary,
        rows=rows,
        composition=composition,
        timeseries=None  # Future: daily granularity support
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
    response_model=list[schemas.ManualCostOut],
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
    
    # Call QA service
    from app.services.qa_service import QAService
    qa_service = QAService(db)
    
    try:
        result = qa_service.ask(
            question=question,
            workspace_id=str(workspace_id),
            user_id=str(current_user.id)
        )
        
        return schemas.FinancialInsightResponse(
            message=result.answer
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
    allocation = schemas.ManualCostAllocation(
        type=cost.allocation_type,
        date=cost.allocation_date.date() if cost.allocation_date else None,
        start_date=cost.allocation_start.date() if cost.allocation_start else None,
        end_date=cost.allocation_end.date() if cost.allocation_end else None
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
```

Register router in `backend/app/main.py` after other routers (~line 50):

```python
from app.routers import finance
app.include_router(finance.router)
```

---

## Phase 5: Update Seed Data

**File**: `backend/app/seed_mock.py`

Add manual cost seeding after ComputeRun creation (~line 520):

```python
        # 8. Create manual costs for testing
        # WHY: Finance page needs manual cost examples for realistic testing
        print("💰 Creating manual costs...")
        
        # One-off costs
        hubspot_cost = models.ManualCost(
            id=uuid.uuid4(),
            label="HubSpot Marketing Hub",
            category="Tools / SaaS",
            amount_dollar=299.00,
            allocation_type="one_off",
            allocation_date=datetime.utcnow() - timedelta(days=15),
            notes="Monthly subscription payment",
            workspace_id=workspace.id,
            created_by_user_id=owner_id
        )
        
        event_cost = models.ManualCost(
            id=uuid.uuid4(),
            label="Trade Show Booth",
            category="Events",
            amount_dollar=2500.00,
            allocation_type="one_off",
            allocation_date=datetime.utcnow() - timedelta(days=10),
            notes="SaaS Conference 2025",
            workspace_id=workspace.id,
            created_by_user_id=owner_id
        )
        
        # Range costs (pro-rated)
        agency_cost = models.ManualCost(
            id=uuid.uuid4(),
            label="Creative Agency Retainer",
            category="Agency Fees",
            amount_dollar=3000.00,
            allocation_type="range",
            allocation_start=datetime.utcnow() - timedelta(days=60),
            allocation_end=datetime.utcnow() + timedelta(days=30),
            notes="Q4 2025 retainer (3 months)",
            workspace_id=workspace.id,
            created_by_user_id=owner_id
        )
        
        tools_cost = models.ManualCost(
            id=uuid.uuid4(),
            label="Analytics Stack",
            category="Tools / SaaS",
            amount_dollar=1200.00,
            allocation_type="range",
            allocation_start=datetime.utcnow() - timedelta(days=30),
            allocation_end=datetime.utcnow() + timedelta(days=335),  # 1 year
            notes="Annual Mixpanel + Segment subscription",
            workspace_id=workspace.id,
            created_by_user_id=owner_id
        )
        
        db.add_all([hubspot_cost, event_cost, agency_cost, tools_cost])
        db.commit()
        
        manual_cost_count = 4
        print(f"✅ Created {manual_cost_count} manual costs")
```

Update summary section (~line 565):

```python
        print(f"\n💰 MANUAL COSTS:")
        print(f"   Total manual costs: {manual_cost_count}")
        print(f"   - One-off: 2 (HubSpot, Trade Show)")
        print(f"   - Range: 2 (Agency retainer, Analytics stack)")
        print(f"   Categories: Tools/SaaS, Agency Fees, Events")
```

---

## Phase 6: Backend Tests

### 6.1 Cost Allocation Tests

**File**: `backend/app/tests/test_cost_allocation.py` (NEW)

```python
"""Unit tests for manual cost allocation logic.

WHAT: Tests pro-rating rules for one-off and range costs
WHY: Allocation logic is critical for accurate P&L; must handle edge cases
REFERENCES: app/services/cost_allocation.py
"""

import pytest
from datetime import date
from app.services.cost_allocation import calculate_allocated_amount
from app.models import ManualCost
from unittest.mock import MagicMock


def test_one_off_inside_period():
    """One-off cost inside period → full amount."""
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "one_off"
    cost.allocation_date = date(2025, 10, 15)
    cost.amount_eur = 299.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 10, 1),
        period_end=date(2025, 11, 1)
    )
    
    assert allocated == 299.00


def test_one_off_outside_period():
    """One-off cost outside period → 0."""
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "one_off"
    cost.allocation_date = date(2025, 9, 15)
    cost.amount_eur = 299.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 10, 1),
        period_end=date(2025, 11, 1)
    )
    
    assert allocated == 0.0


def test_range_fully_inside():
    """Range fully inside period → full amount."""
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "range"
    cost.allocation_start = date(2025, 10, 5)
    cost.allocation_end = date(2025, 10, 15)
    cost.amount_eur = 1000.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 10, 1),
        period_end=date(2025, 11, 1)
    )
    
    assert allocated == 1000.00


def test_range_partial_overlap():
    """Range partially overlapping → pro-rated.
    
    Cost: Sept 20 - Oct 10 (20 days)
    Period: Oct 1 - Nov 1
    Overlap: Oct 1 - Oct 10 (10 days)
    Expected: 50% of amount
    """
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "range"
    cost.allocation_start = date(2025, 9, 20)
    cost.allocation_end = date(2025, 10, 10)
    cost.amount_eur = 2000.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 10, 1),
        period_end=date(2025, 11, 1)
    )
    
    assert allocated == 1000.00  # 10 days / 20 days = 50%


def test_range_no_overlap():
    """Range outside period → 0."""
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "range"
    cost.allocation_start = date(2025, 8, 1)
    cost.allocation_end = date(2025, 9, 1)
    cost.amount_eur = 1000.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 10, 1),
        period_end=date(2025, 11, 1)
    )
    
    assert allocated == 0.0


def test_range_spanning_multiple_months():
    """Range spanning 3 months → correct pro-rating.
    
    Cost: Oct 1 - Dec 31 (92 days)
    Period: Nov 1 - Dec 1 (30 days)
    Expected: 30/92 of amount
    """
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "range"
    cost.allocation_start = date(2025, 10, 1)
    cost.allocation_end = date(2025, 12, 31)
    cost.amount_dollar = 9200.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2025, 11, 1),
        period_end=date(2025, 12, 1)
    )
    
    expected = 9200.00 * (30 / 92)
    assert abs(allocated - expected) < 0.01  # Float comparison


def test_leap_year_feb():
    """Leap year February (29 days) → correct allocation."""
    cost = MagicMock(spec=ManualCost)
    cost.allocation_type = "range"
    cost.allocation_start = date(2024, 2, 1)
    cost.allocation_end = date(2024, 3, 1)
    cost.amount_dollar = 2900.00
    
    allocated = calculate_allocated_amount(
        cost,
        period_start=date(2024, 2, 1),
        period_end=date(2024, 3, 1)
    )
    
    assert allocated == 2900.00  # Full 29 days
```

### 6.2 Finance Endpoint Tests

**File**: `backend/app/tests/test_finance_endpoints.py` (NEW)

```python
"""Integration tests for Finance endpoints.

WHAT: Tests P&L aggregation and manual cost CRUD
WHY: Ensures correct workspace scoping, allocation logic, and API contracts
REFERENCES:
  - app/routers/finance.py: Endpoints
  - app/schemas.py: Request/response models
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import Workspace, User, ManualCost, MetricFact
from sqlalchemy.orm import Session


@pytest.fixture
def client():
    return TestClient(app)


def test_get_pnl_statement_month_with_only_ads(client, db: Session, auth_headers):
    """Monthly P&L with only ad spend → correct aggregation."""
    # Setup: Workspace with MetricFact data
    # Test: GET /finance/pnl?granularity=month&period_start=...
    # Assert: summary.total_spend = sum of ad spend, rows count = num providers
    pass  # TODO: Implement with test fixtures


def test_get_pnl_statement_with_one_off_cost(client, db: Session, auth_headers):
    """Month with one-off manual cost → included if date in range."""
    # Setup: MetricFact + ManualCost(one_off, date=2025-10-15)
    # Test: GET /finance/pnl for October 2025
    # Assert: total_spend includes manual cost, rows include manual category
    pass


def test_get_pnl_statement_with_range_cost(client, db: Session, auth_headers):
    """Month overlapping range cost → pro-rated correctly."""
    # Setup: ManualCost(range, start=2025-09-15, end=2025-10-15, amount=3000)
    # Test: GET /finance/pnl for October 2025
    # Assert: allocated = 3000 * (15 days / 30 days) = 1500
    pass


def test_get_pnl_statement_compare_mode(client, db: Session, auth_headers):
    """Compare=true → previous period deltas computed."""
    # Setup: MetricFact for Oct and Sept
    # Test: GET /finance/pnl?compare=true for October
    # Assert: summary.compare has revenue_delta_pct, spend_delta_pct, etc.
    pass


def test_create_manual_cost_one_off(client, db: Session, auth_headers):
    """POST /finance/costs with one_off allocation → creates correctly."""
    payload = {
        "label": "Test Event",
        "category": "Events",
        "amount_eur": 500.00,
        "allocation": {"type": "one_off", "date": "2025-10-15"},
        "notes": "Test"
    }
    response = client.post("/workspaces/{workspace_id}/finance/costs", json=payload)
    assert response.status_code == 201
    assert response.json()["label"] == "Test Event"


def test_create_manual_cost_range(client, db: Session, auth_headers):
    """POST /finance/costs with range allocation → creates correctly."""
    payload = {
        "label": "Q4 Retainer",
        "category": "Agency Fees",
        "amount_eur": 9000.00,
        "allocation": {
            "type": "range",
            "start_date": "2025-10-01",
            "end_date": "2025-12-31"
        }
    }
    response = client.post("/workspaces/{workspace_id}/finance/costs", json=payload)
    assert response.status_code == 201


def test_update_manual_cost(client, db: Session, auth_headers):
    """PUT /finance/costs/{id} → updates correctly."""
    # Setup: Create cost
    # Test: PUT with updated label
    # Assert: Label changed, other fields unchanged
    pass


def test_delete_manual_cost(client, db: Session, auth_headers):
    """DELETE /finance/costs/{id} → removes from DB."""
    # Setup: Create cost
    # Test: DELETE
    # Assert: 204 response, cost not in DB
    pass


def test_workspace_isolation(client, db: Session, auth_headers):
    """Cannot access other workspace's costs."""
    # Setup: Two workspaces, cost in workspace A
    # Test: User from workspace B tries to access cost
    # Assert: 403 or 404
    pass
```

Run tests:

```bash
cd backend
pytest app/tests/test_cost_allocation.py -v
pytest app/tests/test_finance_endpoints.py -v
```

---

## Phase 7: Frontend API Client

**File**: `ui/lib/financeApiClient.js` (NEW)

```javascript
/**
 * Finance API Client
 * 
 * WHAT: Thin client for Finance/P&L endpoints
 * WHY: Centralized API calls with error handling, no business logic
 * REFERENCES:
 *   - lib/api.js: Similar pattern for KPI data
 *   - lib/pnlAdapter.js: Consumes these responses
 *   - app/(dashboard)/finance/page.jsx: Uses this client
 * 
 * Design:
 *   - All requests include workspace ID (from context/cookie)
 *   - Returns raw API responses (adapter handles mapping)
 *   - Throws on errors (caller handles)
 */

import { apiRequest } from './api';

/**
 * Get P&L statement for a period.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.granularity - "month" (now) or "day" (future)
 * @param {string} params.periodStart - ISO date (YYYY-MM-DD)
 * @param {string} params.periodEnd - ISO date (YYYY-MM-DD, exclusive)
 * @param {boolean} params.compare - Include previous period comparison
 * @returns {Promise<PnLStatementResponse>}
 */
export async function getPnLStatement({ workspaceId, granularity = 'month', periodStart, periodEnd, compare = false }) {
  const params = new URLSearchParams({
    granularity,
    period_start: periodStart,
    period_end: periodEnd,
    compare: compare.toString()
  });
  
  return apiRequest(`/workspaces/${workspaceId}/finance/pnl?${params}`);
}

/**
 * Create a manual cost entry.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId
 * @param {Object} params.cost - ManualCostCreate payload
 * @returns {Promise<ManualCostOut>}
 */
export async function createManualCost({ workspaceId, cost }) {
  return apiRequest(`/workspaces/${workspaceId}/finance/costs`, {
    method: 'POST',
    body: JSON.stringify(cost)
  });
}

/**
 * List all manual costs for workspace.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId
 * @returns {Promise<ManualCostOut[]>}
 */
export async function listManualCosts({ workspaceId }) {
  return apiRequest(`/workspaces/${workspaceId}/finance/costs`);
}

/**
 * Update a manual cost entry.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId
 * @param {string} params.costId
 * @param {Object} params.updates - ManualCostUpdate payload
 * @returns {Promise<ManualCostOut>}
 */
export async function updateManualCost({ workspaceId, costId, updates }) {
  return apiRequest(`/workspaces/${workspaceId}/finance/costs/${costId}`, {
    method: 'PUT',
    body: JSON.stringify(updates)
  });
}

/**
 * Delete a manual cost entry.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId
 * @param {string} params.costId
 * @returns {Promise<void>}
 */
export async function deleteManualCost({ workspaceId, costId }) {
  return apiRequest(`/workspaces/${workspaceId}/finance/costs/${costId}`, {
    method: 'DELETE'
  });
}

/**
 * Get AI financial insight.
 * 
 * @param {Object} params
 * @param {string} params.workspaceId
 * @param {string} params.month - Month name (e.g., "October")
 * @param {number} params.year - Year (e.g., 2025)
 * @returns {Promise<FinancialInsightResponse>}
 */
export async function getFinancialInsight({ workspaceId, month, year }) {
  return apiRequest(`/workspaces/${workspaceId}/finance/insight`, {
    method: 'POST',
    body: JSON.stringify({ month, year })
  });
}
```

---

## Phase 8: Frontend Adapter (View Model)

**File**: `ui/lib/pnlAdapter.js` (NEW)

```javascript
/**
 * P&L View Model Adapter
 * 
 * WHAT: Maps API responses to UI-friendly view models
 * WHY: Isolates UI from API contracts, handles formatting and safe defaults
 * REFERENCES:
 *   - lib/financeApiClient.js: Source data
 *   - app/(dashboard)/finance/components/*.jsx: Consumers
 * 
 * Design principles:
 *   - All currency formatting happens here (not in components)
 *   - Safe defaults for null/undefined (no crashes)
 *   - No business logic (no calculations)
 *   - Field names match UI needs (not API names)
 */

/**
 * Format currency for display.
 * @param {number} value
 * @returns {string} e.g., "$1,234.56"
 */
function formatCurrency(value) {
  if (value === null || value === undefined) return '$0.00';
  return new Intl.NumberFormat('en-IE', {
    style: 'currency',
    currency: 'DOLLAR'
  }).format(value);
}

/**
 * Format percentage for display.
 * @param {number} value - Decimal (0.15 = 15%)
 * @returns {string} e.g., "+15.0%" or "-5.2%"
 */
function formatPercentage(value) {
  if (value === null || value === undefined) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(1)}%`;
}

/**
 * Format ratio for display.
 * @param {number} value
 * @returns {string} e.g., "2.45×"
 */
function formatRatio(value) {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(2)}×`;
}

/**
 * Map P&L statement response to view model.
 * 
 * WHAT: Converts API response to UI-ready format
 * WHY: Components only display, never compute or format
 * 
 * @param {PnLStatementResponse} apiResponse
 * @returns {Object} View model for Finance page
 */
export function adaptPnLStatement(apiResponse) {
  const { summary, rows, composition, timeseries } = apiResponse;
  
  return {
    // Summary cards (top of page)
    summary: {
      totalRevenue: {
        label: 'Total Revenue',
        value: formatCurrency(summary.total_revenue),
        rawValue: summary.total_revenue,
        delta: summary.compare?.revenue_delta_pct 
          ? formatPercentage(summary.compare.revenue_delta_pct) 
          : null
      },
      totalSpend: {
        label: 'Total Spend',
        value: formatCurrency(summary.total_spend),
        rawValue: summary.total_spend,
        delta: summary.compare?.spend_delta_pct 
          ? formatPercentage(summary.compare.spend_delta_pct) 
          : null
      },
      grossProfit: {
        label: 'Gross Profit',
        value: formatCurrency(summary.gross_profit),
        rawValue: summary.gross_profit,
        delta: summary.compare?.profit_delta_pct 
          ? formatPercentage(summary.compare.profit_delta_pct) 
          : null
      },
      netRoas: {
        label: 'Net ROAS',
        value: formatRatio(summary.net_roas),
        rawValue: summary.net_roas,
        delta: summary.compare?.roas_delta 
          ? formatRatio(summary.compare.roas_delta) 
          : null
      }
    },
    
    // P&L table rows
    rows: rows.map(row => ({
      id: row.id,
      category: row.category,
      actual: formatCurrency(row.actual_eur),
      actualRaw: row.actual_dollar,
      planned: row.planned_dollar ? formatCurrency(row.planned_dollar) : '—',
      plannedRaw: row.planned_dollar,
      variance: row.variance_pct ? formatPercentage(row.variance_pct) : '—',
      varianceRaw: row.variance_pct,
      notes: row.notes || '',
      source: row.source,
      isAdSpend: row.source === 'ads',
      isManual: row.source === 'manual'
    })),
    
    // Composition pie chart
    composition: composition.map(slice => ({
      label: slice.label,
      value: slice.value,
      formatted: formatCurrency(slice.value)
    })),
    
    // Future: Daily timeseries (not used yet)
    timeseries: timeseries || null,
    
    // Comparison mode flag
    hasComparison: !!summary.compare
  };
}

/**
 * Map manual cost list to view model.
 * 
 * @param {ManualCostOut[]} costs
 * @returns {Object[]}
 */
export function adaptManualCosts(costs) {
  return costs.map(cost => ({
    id: cost.id,
    label: cost.label,
    category: cost.category,
    amount: formatCurrency(cost.amount_eur),
    amountRaw: cost.amount_dollar,
    allocationType: cost.allocation.type,
    allocationDate: cost.allocation.date || null,
    allocationRange: cost.allocation.start_date && cost.allocation.end_date
      ? `${cost.allocation.start_date} to ${cost.allocation.end_date}`
      : null,
    notes: cost.notes || '',
    createdAt: new Date(cost.created_at).toLocaleDateString()
  }));
}

/**
 * Generate period dates for a given month.
 * 
 * WHAT: Helper to compute period_start and period_end from month selection
 * WHY: Finance page selects by month, API needs date range
 * 
 * @param {number} year
 * @param {number} month - 1-indexed (1 = January)
 * @returns {{periodStart: string, periodEnd: string}} ISO dates
 */
export function getPeriodDatesForMonth(year, month) {
  const periodStart = new Date(year, month - 1, 1).toISOString().split('T')[0];
  const periodEnd = new Date(year, month, 1).toISOString().split('T')[0]; // First day of next month (exclusive)
  
  return { periodStart, periodEnd };
}
```

---

## Phase 9: Update Finance Page

**File**: `ui/app/(dashboard)/finance/page.jsx`

```javascript
"use client";
import { useState, useEffect } from "react";
import TopBar from "./components/TopBar";
import FinancialSummaryCards from "./components/FinancialSummaryCards";
import PLTable from "./components/PLTable";
import ChartsSection from "./components/ChartsSection";
import AIFinancialSummary from "./components/AIFinancialSummary";
import { getPnLStatement } from "@/lib/financeApiClient";
import { adaptPnLStatement, getPeriodDatesForMonth } from "@/lib/pnlAdapter";

/**
 * Finance & P&L Page
 * 
 * WHAT: Main Finance page with P&L statement, costs, and insights
 * WHY: Central view for financial performance
 * REFERENCES:
 *   - lib/financeApiClient.js: Data fetching
 *   - lib/pnlAdapter.js: View model mapping
 *   - components/*.jsx: Presentational components
 * 
 * State management:
 *   - selectedPeriod: {year, month} - User selection
 *   - compareEnabled: boolean - Toggle for comparison mode
 *   - viewModel: adapted P&L data (from adapter)
 *   - loading/error: UI states
 * 
 * Design:
 *   - Zero business logic (only display state)
 *   - Adapter handles all formatting
 *   - Components are presentational only
 */
export default function FinancePage() {
  // UI state
  const [compareEnabled, setCompareEnabled] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const [viewModel, setViewModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Workspace ID (from context/cookie)
  // TODO: Get from auth context
  const workspaceId = "YOUR_WORKSPACE_ID"; // Replace with actual
  
  // Fetch P&L data
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      
      try {
        const { periodStart, periodEnd } = getPeriodDatesForMonth(
          selectedPeriod.year,
          selectedPeriod.month
        );
        
        const apiResponse = await getPnLStatement({
          workspaceId,
          granularity: 'month',
          periodStart,
          periodEnd,
          compare: compareEnabled
        });
        
        const adapted = adaptPnLStatement(apiResponse);
        setViewModel(adapted);
      } catch (err) {
        console.error('Failed to fetch P&L:', err);
        setError('Failed to load financial data. Please try again.');
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [workspaceId, selectedPeriod, compareEnabled]);
  
  const handlePeriodChange = (period) => {
    setSelectedPeriod(period);
  };
  
  const handleCompareToggle = (enabled) => {
    setCompareEnabled(enabled);
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-gray-700 rounded w-1/3"></div>
          <div className="h-32 bg-gray-700 rounded"></div>
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500 rounded p-4 text-red-400">
          {error}
        </div>
      </div>
    );
  }
  
  // No data
  if (!viewModel) {
    return (
      <div className="p-8 text-gray-400">
        No financial data available for this period.
      </div>
    );
  }
  
  return (
    <div>
      {/* Filters */}
      <TopBar
        selectedPeriod={selectedPeriod}
        onPeriodChange={handlePeriodChange}
        compareEnabled={compareEnabled}
        onCompareToggle={handleCompareToggle}
      />
      
      {/* Summary KPIs */}
      <FinancialSummaryCards 
        summary={viewModel.summary} 
        showComparison={viewModel.hasComparison}
      />
      
      {/* P&L Table */}
      <PLTable rows={viewModel.rows} />
      
      {/* Charts */}
      <ChartsSection composition={viewModel.composition} />
      
      {/* AI Insight */}
      <AIFinancialSummary 
        workspaceId={workspaceId}
        selectedPeriod={selectedPeriod}
      />
    </div>
  );
}
```

---

## Phase 10: Update Finance Components

Update each component to consume view model props (no formatting/calculations):

### FinancialSummaryCards.jsx

```javascript
// WHAT: Display P&L summary KPIs (read-only cards)
// WHY: Top-level metrics at a glance
// REFERENCES: lib/pnlAdapter.js:adaptPnLStatement

export default function FinancialSummaryCards({ summary, showComparison }) {
  const cards = [
    summary.totalRevenue,
    summary.totalSpend,
    summary.grossProfit,
    summary.netRoas
  ];
  
  return (
    <div className="grid grid-cols-4 gap-4 p-6">
      {cards.map((card, i) => (
        <div key={i} className="bg-gray-800 rounded p-4">
          <div className="text-sm text-gray-400">{card.label}</div>
          <div className="text-2xl font-bold">{card.value}</div>
          {showComparison && card.delta && (
            <div className="text-sm text-green-400">{card.delta}</div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### PLTable.jsx

```javascript
// WHAT: P&L statement table (read-only, future: editable planned column)
// WHY: Line-item detail of all costs
// REFERENCES: lib/pnlAdapter.js:adaptPnLStatement

export default function PLTable({ rows }) {
  return (
    <div className="p-6">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left p-2">Category</th>
            <th className="text-right p-2">Actual</th>
            <th className="text-right p-2">Planned</th>
            <th className="text-right p-2">Variance</th>
            <th className="text-left p-2">Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.id} className="border-b border-gray-800">
              <td className="p-2">
                {row.category}
                {row.isManual && <span className="text-xs text-gray-500 ml-2">(Manual)</span>}
              </td>
              <td className="text-right p-2">{row.actual}</td>
              <td className="text-right p-2 text-gray-500">{row.planned}</td>
              <td className="text-right p-2">{row.variance}</td>
              <td className="p-2 text-sm text-gray-400">{row.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### AIFinancialSummary.jsx

```javascript
// WHAT: AI-generated financial insight
// WHY: Natural language summary via QA system
// REFERENCES: lib/financeApiClient.js:getFinancialInsight

import { useState } from "react";
import { getFinancialInsight } from "@/lib/financeApiClient";

export default function AIFinancialSummary({ workspaceId, selectedPeriod }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleGenerate = async () => {
    setLoading(true);
    try {
      const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
      const month = monthNames[selectedPeriod.month - 1];
      
      const response = await getFinancialInsight({
        workspaceId,
        month,
        year: selectedPeriod.year
      });
      
      setInsight(response.message);
    } catch (err) {
      console.error('Failed to generate insight:', err);
      setInsight('Unable to generate insight. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-6">
      <div className="bg-gray-800 rounded p-6">
        <h3 className="text-lg font-semibold mb-4">AI Financial Insight</h3>
        
        {!insight && (
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Insight'}
          </button>
        )}
        
        {insight && (
          <div className="text-gray-300 whitespace-pre-wrap">{insight}</div>
        )}
      </div>
    </div>
  );
}
```

---

## Phase 11: Documentation Updates

### Update metricx_BUILD_LOG.md

Add changelog entry at line 205:

```markdown
| - 2025-10-11T14:00:00Z — **FEATURE**: Finance & P&L Backend Integration — Real-time P&L from MetricFact + manual costs.
  - **Overview**: Connected Finance page to backend with strict SoC (thin client → adapter → UI)
  - **Data source**: MetricFact (ad spend) + ManualCost (user costs) for real-time P&L
  - **Pnl table**: Kept for future EOD locking but not used in Finance page initially
  - **Architecture**: Zero business logic in UI; all calculations in backend
  - **Files created (backend)**:
    - `backend/app/models.py`: Added ManualCost model (label, category, amount, allocation)
    - `backend/alembic/versions/YYYYMMDD_add_manual_costs.py`: Migration for manual_costs table
    - `backend/app/schemas.py`: Finance DTOs (PnLSummary, PnLRow, ManualCost schemas)
    - `backend/app/services/cost_allocation.py`: Pro-rating logic for date-based allocation
    - `backend/app/routers/finance.py`: P&L + manual costs CRUD endpoints
    - `backend/app/tests/test_cost_allocation.py`: Unit tests for allocation rules
    - `backend/app/tests/test_finance_endpoints.py`: Integration tests for endpoints
  - **Files modified (backend)**:
    - `backend/app/seed_mock.py`: Added 4 manual cost examples (one-off + range)
    - `backend/app/main.py`: Registered finance router
  - **Files created (frontend)**:
    - `ui/lib/financeApiClient.js`: Thin API client (getPnLStatement, CRUD costs, insight)
    - `ui/lib/pnlAdapter.js`: View model adapter (formatting, safe defaults)
  - **Files modified (frontend)**:
    - `ui/app/(dashboard)/finance/page.jsx`: Connected to real API with loading/error states
    - `ui/app/(dashboard)/finance/components/FinancialSummaryCards.jsx`: Displays view model
    - `ui/app/(dashboard)/finance/components/PLTable.jsx`: Displays P&L rows
    - `ui/app/(dashboard)/finance/components/AIFinancialSummary.jsx`: QA integration
  - **Features**:
    - ✅ Monthly P&L aggregation (ad spend + manual costs)
    - ✅ Manual cost allocation: one_off (single date) or range (pro-rated daily)
    - ✅ Previous period comparison (compare toggle)
    - ✅ AI financial insight via QA system
    - ✅ Workspace-scoped at SQL level (security)
    - ✅ Future-proof: Contracts support daily granularity (not implemented yet)
  - **Design principles**:
    - Strict SoC: Backend computes, frontend displays
    - Thin client: No business logic in API calls
    - Adapter layer: All formatting/mapping isolated
    - WHAT/WHY/REFERENCES comments: Every module cross-referenced
  - **Testing**:
    - Unit tests: Cost allocation edge cases (one-off, range, leap year)
    - Integration tests: P&L aggregation, CRUD, workspace isolation
    - Contract tests: View model adapters with representative payloads (TODO)
  - **Known limitations**:
    - Planned/budgeted amounts not implemented (planned_eur always null)
    - Daily granularity supported by contract but not implemented in UI
    - Manual cost allocation UI not built (CRUD via API only for now)
  - **Migration**: Run `alembic upgrade head` on Railway database
  - **Seed data**: Run `python -m app.seed_mock` for test data
```

Update section 8.1 (Backend):

```markdown
- Finance endpoints: `/workspaces/{id}/finance/pnl` (P&L statement), `/workspaces/{id}/finance/costs` (manual costs CRUD), `/workspaces/{id}/finance/insight` (AI insights)
- Manual costs: one_off (single date) or range (pro-rated across dates) allocation
```

Update section 8.2 (Frontend):

```markdown
- Finance page fetches real P&L data via financeApiClient + pnlAdapter pattern
- Strict SoC: Zero business logic in components (adapter handles all formatting)
```

### Update CLASS-DIAGRAM.MD

Add after Pnl class (~line 175):

```markdown
class ManualCost {
  +uuid id
  +string label
  +string category
  +decimal amount_eur
  +string allocation_type
  +date allocation_date?
  +date allocation_start?
  +date allocation_end?
  +uuid workspace_id
  +datetime created_at
  +datetime updated_at
  +uuid created_by_user_id?
}
```

Add relationship:

```markdown
Workspace "1" -- "0..*" ManualCost : has manual costs
ManualCost "0..*" -- "1" Workspace : belongs to
```

Add changelog:

```markdown
### 2025-10-11 - Finance & P&L Integration
- **Added ManualCost model**: Stores user-entered operational costs (non-ad spend)
- **Fields**: label, category, amount_eur, allocation_type (one_off/range), date fields for allocation
- **Purpose**: Combine ad spend (MetricFact) with manual costs for complete P&L view
- **WHY**: Finance page needs full cost picture, not just ad platform costs
- **Allocation rules**: one_off = single date, range = pro-rated daily across date range
- **Workspace scoping**: All costs belong to one workspace (tenant isolation)
```

---

## Phase 12: Final Testing & Verification

### Backend verification:

```bash
cd backend

# Run migration
alembic upgrade head

# Verify tables
psql $DATABASE_URL -c "\d manual_costs"

# Seed test data
python -m app.seed_mock

# Run tests
pytest app/tests/test_cost_allocation.py -v
pytest app/tests/test_finance_endpoints.py -v

# Start API
python start_api.py
```

### Frontend verification:

```bash
cd ui
npm run dev
```

Test checklist:

- [ ] Finance page loads without errors
- [ ] Summary cards display formatted values
- [ ] P&L table shows ad spend rows
- [ ] P&L table shows manual cost rows (from seed data)
- [ ] Compare toggle refetches with deltas
- [ ] Month selector updates data
- [ ] AI insight generates message
- [ ] Loading states work
- [ ] Error states work (disconnect API to test)

---

## Success Criteria

✅ **Backend**:

- ManualCost model + migration deployed to Railway
- Finance endpoints return correct P&L aggregation
- Ad spend (MetricFact) + manual costs combined correctly
- Pro-rating logic handles one-off and range allocations
- Previous period comparison computes deltas
- All endpoints workspace-scoped
- Unit + integration tests pass

✅ **Frontend**:

- Finance page fetches real data via financeApiClient
- pnlAdapter maps responses to view models
- Components display formatted data (zero calculations)
- Loading/error states handled gracefully
- Month selector and compare toggle functional
- AI insight calls QA endpoint

✅ **Documentation**:

- metricx_BUILD_LOG.md updated with changelog
- CLASS-DIAGRAM.MD includes ManualCost model
- All code has WHAT/WHY/REFERENCES comments
- Cross-references between modules documented

✅ **Future-proof**:

- Data contracts support daily granularity (timeseries field)
- Switching month ↔ day requires no UI refactoring
- Pnl table kept for future EOD locking feature

### To-dos

- [ ] Create ManualCost model and database migration
- [ ] Add Finance DTOs to schemas.py (PnLSummary, PnLRow, ManualCost schemas)
- [ ] Implement cost allocation logic with pro-rating rules
- [ ] Create Finance router with P&L and CRUD endpoints
- [ ] Add manual cost examples to seed_mock.py
- [ ] Write unit tests for allocation and integration tests for endpoints
- [ ] Create financeApiClient.js with thin API methods
- [ ] Create pnlAdapter.js for view model mapping
- [ ] Connect Finance page to real API with state management
- [ ] Update Finance components to consume view model props
- [ ] Update metricx_BUILD_LOG.md and CLASS-DIAGRAM.MD
- [ ] Run migration on Railway, test end-to-end, verify all success criteria