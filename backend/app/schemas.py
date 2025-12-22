"""Pydantic schemas for request/response payloads."""

from datetime import datetime, date
from enum import Enum
from uuid import UUID
from typing import Optional, List, Literal, Union, Any
from decimal import Decimal
from pydantic import BaseModel, EmailStr, constr, Field, field_serializer, field_validator
from .models import RoleEnum, ProviderEnum, LevelEnum, KindEnum, ComputeRunTypeEnum, GoalEnum, BillingStatusEnum, BillingPlanEnum


class UserCreate(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(
        description="User email address",
        example="user@company.com"
    )
    name: str = Field(
        description="User full name",
        example="John Doe"
    )
    password: constr(min_length=8) = Field(
        description="Password (minimum 8 characters)",
        example="securePassword123"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@company.com",
                "name": "John Doe",
                "password": "securePassword123"
            }
        }
    }


class UserLogin(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(
        description="User email address",
        example="user@company.com"
    )
    password: str = Field(
        description="User password",
        example="securePassword123"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@company.com",
                "password": "securePassword123"
            }
        }
    }


class UserOut(BaseModel):
    """Public representation of a user."""

    id: UUID = Field(
        description="Unique user identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: EmailStr = Field(
        description="User email address",
        example="john.doe@company.com"
    )
    name: str = Field(
        description="User display name",
        example="John Doe"
    )
    role: RoleEnum = Field(
        description="User role within the active workspace",
        example="Admin"
    )
    workspace_id: UUID = Field(
        description="Active workspace ID (legacy field; mirrors active_workspace_id)",
        example="456e7890-e89b-12d3-a456-426614174001"
    )
    active_workspace_id: UUID | None = Field(
        default=None,
        description="Active workspace ID",
        example="456e7890-e89b-12d3-a456-426614174001"
    )
    memberships: list["WorkspaceMemberOutLite"] = Field(
        default_factory=list,
        description="All workspace memberships for this user"
    )
    pending_invites: list["WorkspaceInviteOut"] = Field(
        default_factory=list,
        description="Pending workspace invites for this user"
    )
    avatar_url: Optional[str] = Field(
        None,
        description="URL to user avatar image",
        example="https://example.com/avatar.png"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@company.com",
                "name": "John Doe",
                "role": "Admin",
                "workspace_id": "456e7890-e89b-12d3-a456-426614174001",
                "avatar_url": "https://example.com/avatar.png"
            }
        }
    }


class UserUpdate(BaseModel):
    """Payload for updating user profile."""
    name: Optional[str] = Field(None, description="User display name")
    email: Optional[EmailStr] = Field(None, description="User email address")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")


class PasswordChange(BaseModel):
    """Payload for changing password."""
    old_password: str = Field(..., description="Current password")
    new_password: constr(min_length=8) = Field(..., description="New password (min 8 chars)")


class PasswordResetRequest(BaseModel):
    """Payload for requesting password reset."""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Payload for confirming password reset."""
    token: str = Field(..., description="Reset token")
    new_password: constr(min_length=8) = Field(..., description="New password (min 8 chars)")


class EmailVerification(BaseModel):
    """Payload for verifying email."""
    token: str = Field(..., description="Verification token")


class TokenPayload(BaseModel):
    """JWT token contents."""

    sub: str = Field(
        description="Subject (user email)",
        example="user@company.com"
    )
    exp: int = Field(
        description="Token expiration timestamp",
        example=1640995200
    )


class LoginResponse(BaseModel):
    """Response from successful login."""
    
    user: UserOut = Field(
        description="Authenticated user information"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john.doe@company.com",
                    "name": "John Doe",
                    "role": "Admin",
                    "workspace_id": "456e7890-e89b-12d3-a456-426614174001"
                }
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str = Field(
        description="Error message",
        example="Invalid credentials"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Invalid credentials"
            }
        }
    }


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    status: str = Field(default="ok", description="Status message")
    detail: str | None = Field(
        default=None,
        description="Success message",
        example="Operation completed successfully"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "logged out"
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        description="Service status",
        example="ok"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok"
            }
        }
    }


# Workspace Schemas
class WorkspaceCreate(BaseModel):
    """Schema for creating a new workspace."""
    
    name: str = Field(
        description="Workspace name",
        example="ACME Corp Marketing",
        min_length=1,
        max_length=100
    )


class WorkspaceUpdate(BaseModel):
    """Schema for updating workspace."""
    
    name: Optional[str] = Field(
        None,
        description="Updated workspace name",
        example="ACME Corp Marketing - Updated",
        min_length=1,
        max_length=100
    )


class WorkspaceOut(BaseModel):
    """Public representation of a workspace."""
    
    id: UUID = Field(description="Unique workspace identifier")
    name: str = Field(description="Workspace name")
    created_at: datetime = Field(description="Creation timestamp")
    
    model_config = {"from_attributes": True}


class WorkspaceWithRole(BaseModel):
    """Workspace summary with membership role/status.

    Attributes:
        is_active: True if this is the user's currently active workspace.
                   Used by frontend to highlight the active workspace in switcher.
    """

    id: UUID
    name: str
    created_at: datetime
    role: RoleEnum
    status: str = "active"
    is_active: bool = False

    model_config = {"from_attributes": True}


class WorkspaceInfo(BaseModel):
    """
    Summary info for sidebar display.
    Includes workspace name and last sync timestamp.
    last_sync is taken from Fetch (raw data sync) because:
    - It tells us the freshest point we ingested data from an ad platform.
    - ComputeRun may happen later, but Fetch = ground truth of availability.
    """
    id: str = Field(description="Workspace ID")
    name: str = Field(description="Workspace name")
    last_sync: Optional[datetime] = Field(description="Last successful sync timestamp")

    model_config = {"from_attributes": True}


class WorkspaceStatus(BaseModel):
    """
    Connection status for conditional UI rendering.

    WHAT: Returns flags indicating which platforms are connected and ready
    WHY: Frontend needs to know whether to show attribution UI components

    Fields:
        has_shopify: True if an active Shopify connection exists
        has_ad_platform: True if any ad platform (Meta/Google/TikTok) is connected
        connected_platforms: List of connected platform names
        attribution_ready: True if Shopify + pixel is receiving events

    REFERENCES:
        - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
        - Frontend uses this to conditionally render attribution components
    """
    has_shopify: bool = Field(
        description="Whether Shopify is connected and active"
    )
    has_ad_platform: bool = Field(
        description="Whether any ad platform (Meta, Google, TikTok) is connected"
    )
    connected_platforms: List[str] = Field(
        description="List of connected platform provider names (e.g., ['meta', 'google', 'shopify'])"
    )
    attribution_ready: bool = Field(
        description="Whether attribution is fully set up (Shopify + pixel receiving events)"
    )

    model_config = {"from_attributes": True}


class WorkspaceMemberOutLite(BaseModel):
    workspace_id: UUID
    workspace_name: str | None = None
    role: RoleEnum
    status: str = "active"

    model_config = {"from_attributes": True}


class WorkspaceMemberOut(WorkspaceMemberOutLite):
    user_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    user_email: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class WorkspaceMemberCreate(BaseModel):
    user_id: UUID
    role: RoleEnum


class WorkspaceMemberUpdate(BaseModel):
    role: RoleEnum


class WorkspaceInviteCreate(BaseModel):
    email: EmailStr
    role: RoleEnum


class WorkspaceInviteOut(BaseModel):
    id: UUID
    workspace_id: UUID
    workspace_name: str | None = None
    email: EmailStr
    role: RoleEnum
    status: str
    invited_by: UUID
    created_at: datetime
    responded_at: datetime | None = None

    model_config = {"from_attributes": True}


# Connection Schemas
class ConnectionCreate(BaseModel):
    """Schema for creating a new ad platform connection."""
    
    provider: ProviderEnum = Field(
        description="Ad platform provider",
        example="google"
    )
    external_account_id: str = Field(
        description="Account ID in the external platform",
        example="123-456-7890"
    )
    name: str = Field(
        description="Friendly name for this connection",
        example="ACME Google Ads"
    )
    status: str = Field(
        description="Connection status",
        example="active"
    )


class ConnectionUpdate(BaseModel):
    """Schema for updating connection."""
    
    name: Optional[str] = Field(None, description="Updated connection name")
    status: Optional[str] = Field(None, description="Updated connection status")


class ConnectionOut(BaseModel):
    """Public representation of a connection."""

    id: UUID = Field(description="Unique connection identifier")
    provider: ProviderEnum = Field(description="Ad platform provider")
    external_account_id: str = Field(description="External account ID")
    name: str = Field(description="Connection name")
    status: str = Field(description="Connection status")
    connected_at: datetime = Field(description="Connection timestamp")
    workspace_id: UUID = Field(description="Associated workspace ID")
    sync_frequency: str = Field(description="Sync cadence", default="15min")
    sync_status: str = Field(description="Sync state", default="idle")
    last_sync_attempted_at: Optional[datetime] = None
    last_sync_completed_at: Optional[datetime] = None
    last_metrics_changed_at: Optional[datetime] = None
    total_syncs_attempted: int = 0
    total_syncs_with_changes: int = 0
    last_sync_error: Optional[str] = None
    meta_pixel_id: Optional[str] = Field(None, description="Meta Pixel ID for CAPI (Meta connections only)")

    model_config = {"from_attributes": True}


class SyncFrequencyUpdate(BaseModel):
    """Request body for updating sync frequency."""

    sync_frequency: str = Field(
        description="Desired frequency: manual, 5min, 10min, 30min, hourly, daily (realtime reserved for special access)",
        examples=["manual", "5min", "10min", "30min", "hourly", "daily"],
    )


class ConnectionSyncStatus(BaseModel):
    """Current sync state for a connection."""

    sync_frequency: str
    sync_status: str
    last_sync_attempted_at: Optional[datetime] = None
    last_sync_completed_at: Optional[datetime] = None
    last_metrics_changed_at: Optional[datetime] = None
    total_syncs_attempted: int
    total_syncs_with_changes: int
    last_sync_error: Optional[str] = None

    model_config = {"from_attributes": True}


class SyncJobResponse(BaseModel):
    """Response when enqueuing a sync job."""

    job_id: str = Field(description="RQ job identifier")
    status: str = Field(description="State after enqueue (queued)")


class QAJobResponse(BaseModel):
    """Response when enqueuing a QA job."""

    job_id: str = Field(description="RQ job identifier")
    status: str = Field(description="Job status: queued, processing, completed, failed")


class QAJobStatusResponse(BaseModel):
    """Status response for a QA job."""

    job_id: str = Field(description="RQ job identifier")
    status: str = Field(description="Job status: queued, processing, completed, failed")
    answer: Optional[str] = Field(None, description="Answer (when completed)")
    executed_dsl: Optional[dict] = Field(None, description="Executed DSL (when completed)")
    data: Optional[dict] = Field(None, description="Result data (when completed)")
    context_used: Optional[List[dict]] = Field(None, description="Context used (when completed)")
    visuals: Optional[dict] = Field(
        default=None,
        description="Optional rich payload containing cards, charts, and tables"
    )
    error: Optional[str] = Field(None, description="Error message (when failed)")


# Entity Schemas
class EntityCreate(BaseModel):
    """Schema for creating a new entity (campaign, ad set, ad, etc.)."""
    
    level: LevelEnum = Field(
        description="Entity level in hierarchy",
        example="campaign"
    )
    external_id: str = Field(
        description="ID in the external ad platform",
        example="camp_123456"
    )
    name: str = Field(
        description="Entity name",
        example="Summer Sale Campaign"
    )
    status: str = Field(
        description="Entity status",
        example="active"
    )
    connection_id: Optional[UUID] = Field(
        None,
        description="Associated connection ID"
    )
    parent_id: Optional[UUID] = Field(
        None,
        description="Parent entity ID (for hierarchy)"
    )


class EntityUpdate(BaseModel):
    """Schema for updating entity."""
    
    name: Optional[str] = Field(None, description="Updated entity name")
    status: Optional[str] = Field(None, description="Updated entity status")


class EntityOut(BaseModel):
    """Public representation of an entity."""
    
    id: UUID = Field(description="Unique entity identifier")
    level: LevelEnum = Field(description="Entity level")
    external_id: str = Field(description="External platform ID")
    name: str = Field(description="Entity name")
    status: str = Field(description="Entity status")
    workspace_id: UUID = Field(description="Associated workspace ID")
    connection_id: Optional[UUID] = Field(description="Associated connection ID")
    parent_id: Optional[UUID] = Field(description="Parent entity ID")
    goal: Optional[GoalEnum] = Field(description="Campaign objective (for campaigns)")
    
    model_config = {"from_attributes": True}


# MetricFact Schemas
class MetricFactOut(BaseModel):
    """Public representation of performance metrics."""
    
    id: UUID = Field(description="Unique metric identifier")
    provider: ProviderEnum = Field(description="Data provider")
    level: LevelEnum = Field(description="Entity level")
    event_date: datetime = Field(description="Event date")
    spend: float = Field(description="Ad spend amount")
    impressions: int = Field(description="Number of impressions")
    clicks: int = Field(description="Number of clicks")
    conversions: Optional[float] = Field(description="Number of conversions")
    revenue: Optional[float] = Field(description="Revenue amount")
    currency: str = Field(description="Currency code")
    entity_id: Optional[UUID] = Field(description="Associated entity ID")
    
    model_config = {"from_attributes": True}


# P&L Schemas
class PnlOut(BaseModel):
    """Public representation of P&L data."""
    
    id: UUID = Field(description="Unique P&L identifier")
    provider: ProviderEnum = Field(description="Data provider")
    level: LevelEnum = Field(description="Entity level")
    kind: KindEnum = Field(description="P&L calculation type")
    event_date: Optional[datetime] = Field(description="Event date")
    spend: float = Field(description="Total spend")
    revenue: Optional[float] = Field(description="Total revenue")
    conversions: Optional[float] = Field(description="Total conversions")
    clicks: int = Field(description="Total clicks")
    impressions: int = Field(description="Total impressions")
    cpa: Optional[float] = Field(description="Cost per acquisition")
    roas: Optional[float] = Field(description="Return on ad spend")
    entity_id: Optional[UUID] = Field(description="Associated entity ID")
    
    model_config = {"from_attributes": True}


# List Response Schemas
class WorkspaceListResponse(BaseModel):
    """Response schema for workspace list."""

    workspaces: List[WorkspaceWithRole] = Field(description="List of workspaces with roles")
    total: int = Field(description="Total number of workspaces")


class ActiveWorkspaceResponse(BaseModel):
    """Response schema for GET /workspaces/active.

    WHAT: Returns current user's active workspace context with role and memberships
    WHY: Frontend needs this after Clerk login to hydrate workspace state and
         determine user permissions (e.g., can manage team members, invite users)

    REFERENCES:
        - ui/lib/workspace.js (getActiveWorkspace, currentUser)
        - ui/app/(dashboard)/settings/components/UsersTab.jsx (checks memberships for canManage)
        - backend/app/routers/workspaces.py (get_active_workspace)
    """

    workspace_id: str = Field(description="Active workspace UUID")
    workspace_name: str = Field(description="Workspace display name")
    user_id: str = Field(description="Current user UUID")
    user_name: str = Field(description="User's display name")
    user_email: str = Field(description="User's email address")
    role: str = Field(description="User's role in the active workspace (Owner, Admin, Viewer)")
    memberships: List[WorkspaceMemberOutLite] = Field(
        description="All workspace memberships for this user (for permission checks)"
    )


class ConnectionListResponse(BaseModel):
    """Response schema for connection list."""
    
    connections: List[ConnectionOut] = Field(description="List of connections")
    total: int = Field(description="Total number of connections")


class EntityListResponse(BaseModel):
    """Response schema for entity list."""
    
    entities: List[EntityOut] = Field(description="List of entities")
    total: int = Field(description="Total number of entities")


class MetricListResponse(BaseModel):
    """Response schema for metrics list."""
    
    metrics: List[MetricFactOut] = Field(description="List of metrics")
    total: int = Field(description="Total number of metrics")


class PnlListResponse(BaseModel):
    """Response schema for P&L list."""
    
    pnl_data: List[PnlOut] = Field(description="List of P&L records")
    total: int = Field(description="Total number of P&L records")


# --- KPI request/response schemas ---
# We keep this small & stable so both UI and (later) AI can rely on it.

MetricKey = Literal[
    # Base measures
    "spend","revenue","clicks","impressions","conversions","leads","installs","purchases","visitors","profit",
    # Derived metrics - Cost/Efficiency
    "cpc","cpm","cpa","cpl","cpi","cpp",
    # Derived metrics - Value
    "roas","poas","arpv","aov",
    # Derived metrics - Engagement
    "ctr","cvr"
]

class TimeRange(BaseModel):
    """
    TimeRange supports either:
    - last_n_days (easiest for UI quick filters)
    - explicit start/end (YYYY-MM-DD)
    Exactly one style is sufficient; last_n_days has priority if set.
    """
    last_n_days: Optional[int] = 7
    start: Optional[date] = None
    end: Optional[date] = None

class KpiRequest(BaseModel):
    """
    The UI tells us which metrics it wants to render as cards.
    We also support:
    - compare_to_previous: return previous-period totals for delta%
    - sparkline: daily series for small inline charts
    """
    metrics: List[MetricKey] = Field(default_factory=lambda: ["spend","revenue","conversions","roas"])
    time_range: TimeRange = TimeRange()
    compare_to_previous: bool = True
    sparkline: bool = True

# Sparkline = that tiny mini-chart under each KPI card (like you see on your dashboard design).
# A sparkline needs a series of points over time, not just one number.
# Each point in that series is a SparkPoint:
# - date: the day (string, e.g. "2025-09-01")
# - value: the metric's value for that day (or None if missing)

class SparkPoint(BaseModel):
    date: str
    value: Optional[float] = None

class KpiValue(BaseModel):
    """
    Single card payload.
    value: current-period aggregated value
    prev: previous-period aggregated value (optional)
    delta_pct: percentage change vs previous (optional)
    sparkline: daily values over the selected range (optional)
    """
    key: MetricKey
    value: Optional[float] = None
    prev: Optional[float] = None
    delta_pct: Optional[float] = None
    sparkline: Optional[List[SparkPoint]] = None



# --- AI / QA schemas ---
# We introduce a small, explicit DSL to keep AI-generated queries safe and
# backend-controlled. The AI only proposes JSON matching this schema; the
# backend validates with Pydantic and executes using our own metric logic.

MetricLiteral = Literal[
    "spend",
    "revenue",
    "clicks",
    "impressions",
    "conversions",
    "roas",
    "cpa",
    "cvr",
]


class MetricQuery(BaseModel):
    """
    DSL (Domain Specific Language) for metrics queries.

    WHY DSL?
    - Keeps AI output constrained and safe.
    - Prevents LLM from inventing SQL or breaking the DB.
    - Ensures backend is the single source of truth for metrics math.

    Fields
    - metric: which metric to aggregate
    - time_range: either {"last_n_days": int} or {"start": YYYY-MM-DD, "end": YYYY-MM-DD}
    - compare_to_previous: include previous-period comparison
    - group_by: optional breakdown (none|campaign|adset|ad)
    - filters: reserved for future provider/entity filters
    """

    metric: MetricLiteral
    time_range: dict = Field(
        ...,
        description="Either {last_n_days:int} or {start:YYYY-MM-DD, end:YYYY-MM-DD}",
        json_schema_extra={
            "examples": [
                {"last_n_days": 7},
                {"start": "2025-09-01", "end": "2025-09-30"},
            ]
        },
    )
    compare_to_previous: bool = False
    group_by: Optional[Literal["none", "campaign", "adset", "ad"]] = "none"
    filters: dict = Field(default_factory=dict)


class QARequest(BaseModel):
    """Natural language question from the user."""

    question: str


class QAResult(BaseModel):
    """
    Response returned by /qa.
    Contains both a human-readable answer and the machine-executed DSL.
    
    DSL v1.2 note:
    - executed_dsl is a dict (not MetricQuery model) to support all query types
    - For providers/entities queries, some fields like metric/time_range may be null
    
    Context note:
    - context_used: Shows previous queries that were available for this request
    - Helps debug follow-up question behavior in Swagger UI
    - Empty list means no prior context (first question in conversation)
    """

    answer: str = Field(
        description="Human-readable answer to the question",
        example="Your REVENUE for the selected period is $58,300.90."
    )
    executed_dsl: dict = Field(
        description="The validated DSL query that was executed",
        example={"metric": "revenue", "time_range": {"last_n_days": 7}}
    )
    data: dict = Field(
        description="Query execution results (summary, timeseries, breakdown)",
        example={"summary": 58300.9}
    )
    context_used: Optional[List[dict]] = Field(
        default=None,
        description="Previous queries used for context (for debugging follow-ups)",
        example=[{"question": "how much revenue this week?", "metric": "revenue"}]
    )
    visuals: Optional[dict] = Field(
        default=None,
        description="Optional rich payload with cards, viz specs (Recharts/Vega-Lite), and tables"
    )


# --- QA query log schemas ---
# We purposely avoid changing DB models right now (no migration) and keep
# the response contract simple. If we later add a dedicated `answer_text`
# column, these schemas already match the intended API.

class QaLogEntry(BaseModel):
    id: str
    question_text: str
    answer_text: str | None
    dsl_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QaLogCreate(BaseModel):
    question_text: str
    answer_text: str
    dsl_json: dict | None = None


# ==========================================================================
# QA FEEDBACK SCHEMAS (Self-Learning System)
# ==========================================================================


class FeedbackType(str, Enum):
    """Type of feedback provided on a QA answer."""
    accuracy = "accuracy"
    relevance = "relevance"
    visualization = "visualization"
    completeness = "completeness"
    other = "other"


class QaFeedbackCreate(BaseModel):
    """
    WHAT: Request body for submitting feedback on a QA answer.
    WHY: Enables self-learning by collecting user feedback on answer quality.
    """
    query_log_id: str = Field(description="ID of the QaQueryLog being rated")
    rating: int = Field(ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")
    feedback_type: Optional[FeedbackType] = Field(default=None, description="What aspect the feedback is about")
    comment: Optional[str] = Field(default=None, description="Optional free-text comment")
    corrected_answer: Optional[str] = Field(default=None, description="What the answer should have been")


class QaFeedbackResponse(BaseModel):
    """
    WHAT: Response body for feedback operations.
    WHY: Returns feedback details including self-learning flags.
    """
    id: str
    query_log_id: str
    user_id: str
    rating: int
    feedback_type: Optional[str] = None
    comment: Optional[str] = None
    corrected_answer: Optional[str] = None
    is_few_shot_example: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class QaFeedbackStats(BaseModel):
    """
    WHAT: Aggregated feedback statistics for a workspace.
    WHY: Provides overview of QA system performance for monitoring.
    """
    total_feedback: int
    average_rating: float
    rating_distribution: dict[int, int]  # {1: count, 2: count, ...}
    feedback_by_type: dict[str, int]
    few_shot_examples_count: int


# ==========================================================================
# CAMPAIGN / ENTITY PERFORMANCE SCHEMAS
# ==========================================================================


class EntityTrendPoint(BaseModel):
    """
    WHAT: Single sparkline datapoint for an entity row.
    WHY: Allows UI to render campaign/ad set trend charts without recomputing values.
    REFERENCES: Generated by backend/app/routers/entity_performance.py when building trends.
    """

    date: str = Field(description="ISO date (YYYY-MM-DD)")
    value: Optional[float] = Field(default=None, description="Metric value for the date")


class EntityPerformanceRow(BaseModel):
    """
    WHAT: Contract for campaign/ad set table rows returned by entity performance API.
    WHY: Keeps UI components dumb – adapter reads this schema and formats values only.
    REFERENCES: Used by ui/lib/campaignsAdapter.js (view model) and TrendSparkline component.
    """

    id: str
    name: str
    platform: Optional[str] = None
    revenue: float
    spend: float
    roas: Optional[float] = None
    conversions: Optional[float] = None
    cpc: Optional[float] = None
    ctr_pct: Optional[float] = None
    status: str
    last_updated_at: Optional[datetime] = None
    trend: List[EntityTrendPoint] = Field(default_factory=list)
    trend_metric: Literal["revenue", "roas"] = "revenue"
    # Optional descriptive label for campaign type (e.g., "PMax")
    kind_label: Optional[str] = None


class EntityPerformanceMeta(BaseModel):
    """
    WHAT: Metadata for the current entity context (campaign list or specific campaign).
    WHY: Adapter turns this into header title/subtitle strings without hitting the database again.
    REFERENCES: ui/lib/campaignsAdapter.js (builds EntityMeta view model).
    """

    title: str
    level: Literal["campaign", "adset", "ad", "creative"]
    last_updated_at: Optional[datetime] = None


class PageMeta(BaseModel):
    """
    WHAT: Pagination payload describing total items and current window.
    WHY: Shared contract so UI can reuse existing pagination controls.
    REFERENCES: entity_performance router + ui campaigns list page.
    """

    total: int
    page: int
    page_size: int


class EntityPerformanceResponse(BaseModel):
    """
    WHAT: Full response for entity performance listings.
    WHY: Encapsulates table rows, pagination, and contextual metadata in one payload.
    REFERENCES: backend/app/routers/entity_performance.py endpoint; consumed by campaigns API client.
    """

    meta: EntityPerformanceMeta
    pagination: PageMeta
    rows: List[EntityPerformanceRow]


# ============================================================================
# FINANCE & P&L SCHEMAS
# ============================================================================

# Simple schemas
class CompositionSlice(BaseModel):
    """Pie chart slice."""
    label: str
    value: float

class FinancialInsightRequest(BaseModel):
    """Request for AI financial insight."""
    month: str
    year: int

class FinancialInsightResponse(BaseModel):
    """AI-generated financial insight."""
    message: str

# Test 2: Add PnL summary schemas
class PnLComparison(BaseModel):
    """Comparison metrics vs previous period."""
    revenue_delta_pct: Optional[float] = None
    spend_delta_pct: Optional[float] = None
    profit_delta_pct: Optional[float] = None
    roas_delta: Optional[float] = None

class PnLSummary(BaseModel):
    """Top-level P&L summary."""
    total_revenue: float
    total_spend: float
    gross_profit: float
    net_roas: float
    compare: Optional[PnLComparison] = None

# Test 3: Add PnLRow
class PnLRow(BaseModel):
    """Single row in P&L statement."""
    id: str
    category: str
    actual_dollar: float
    planned_dollar: Optional[float] = None
    variance_pct: Optional[float] = None
    notes: Optional[str] = None
    source: Literal["ads", "manual"]

# Test 4: Add PnLStatementResponse
class PnLStatementResponse(BaseModel):
    """Complete P&L statement response."""
    summary: PnLSummary
    rows: List[PnLRow]
    composition: List[CompositionSlice]
    timeseries: Optional[List[dict]] = None

# Manual Cost schemas
class ManualCostAllocation(BaseModel):
    """Allocation strategy for manual costs."""
    type: Literal["one_off", "range"]
    date: Any = None
    start_date: Any = None
    end_date: Any = None

class ManualCostCreate(BaseModel):
    """Create a manual cost entry."""
    label: str
    category: str
    amount_dollar: float
    allocation: ManualCostAllocation
    notes: Optional[str] = None

class ManualCostUpdate(BaseModel):
    """Update a manual cost entry."""
    label: Optional[str] = None
    category: Optional[str] = None
    amount_dollar: Optional[float] = None
    allocation: Optional[ManualCostAllocation] = None
    notes: Optional[str] = None

# Test 7: Add ManualCostOut (likely culprit)
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



# ============================================================================
# Meta Ads Ingestion Schemas (Phase 1.2)
# ============================================================================

class MetricFactCreate(BaseModel):
    """
    Schema for ingesting metric facts from ad platforms (Meta, Google, TikTok).
    
    WHY:
    - Unified schema for ingestion from any ad platform
    - Can infer entity_id from external_entity_id + provider if entity already exists
    - Supports UPSERT pattern via natural_key
    
    WHAT:
    - External identifiers from ad platform (campaign_id, ad_id, etc.)
    - Base measures only (no computed metrics)
    - Timezone-aware event_at timestamp
    
    WHERE:
    - Used by POST /workspaces/{workspace_id}/metrics/ingest
    - Called by Phase 3 MetaMetricsFetcher service
    
    REFERENCES:
    - app/models.py:MetricFact (target table)
    - backend/docs/roadmap/meta-ads-roadmap.md Phase 1.2
    """
    
    # Entity identification (one of these patterns):
    # Pattern 1: Existing entity
    entity_id: Optional[UUID] = Field(
        None,
        description="metricx entity UUID (if entity already synced)"
    )
    
    # Pattern 2: New entity (will be looked up or created)
    external_entity_id: Optional[str] = Field(
        None,
        description="Platform's entity ID (e.g., Meta campaign_id)",
        example="123456789"
    )
    
    # Required metadata
    provider: ProviderEnum = Field(
        description="Ad platform provider",
        example="meta"
    )
    
    level: LevelEnum = Field(
        description="Entity hierarchy level",
        example="campaign"
    )
    
    # Timestamp (timezone-aware)
    event_at: datetime = Field(
        description="When this metric occurred (with timezone)",
        example="2025-10-30T14:00:00+00:00"
    )
    
    # Base measures (Meta Insights API fields)
    spend: Decimal = Field(
        description="Ad spend in currency units",
        example=150.50,
        ge=0
    )
    
    impressions: int = Field(
        description="Number of ad impressions",
        example=5420,
        ge=0
    )
    
    clicks: int = Field(
        description="Number of clicks",
        example=234,
        ge=0
    )
    
    # Optional base measures
    conversions: Optional[Decimal] = Field(
        None,
        description="Conversion events count",
        example=12.0,
        ge=0
    )
    
    revenue: Optional[Decimal] = Field(
        None,
        description="Revenue attributed to ads",
        example=1250.00,
        ge=0
    )
    
    leads: Optional[Decimal] = Field(
        None,
        description="Lead form submissions",
        example=8.0,
        ge=0
    )
    
    installs: Optional[int] = Field(
        None,
        description="App installs",
        example=15,
        ge=0
    )
    
    purchases: Optional[int] = Field(
        None,
        description="Purchase events",
        example=5,
        ge=0
    )
    
    visitors: Optional[int] = Field(
        None,
        description="Landing page visitors",
        example=180,
        ge=0
    )
    
    profit: Optional[Decimal] = Field(
        None,
        description="Net profit (revenue - costs)",
        example=1100.00
    )
    
    # Currency
    currency: str = Field(
        description="Currency code",
        example="USD",
        min_length=3,
        max_length=3
    )
    
    # Natural key (for deduplication)
    natural_key: Optional[str] = Field(
        None,
        description="Unique key for this fact (prevents duplicates)",
        example="123456789-2025-10-30T14:00:00+00:00"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "external_entity_id": "123456789",
                "provider": "meta",
                "level": "campaign",
                "event_at": "2025-10-30T14:00:00+00:00",
                "spend": 150.50,
                "impressions": 5420,
                "clicks": 234,
                "conversions": 12.0,
                "revenue": 1250.00,
                "currency": "USD"
            }
        }
    }


class MetricFactIngestResponse(BaseModel):
    """Response from metric fact ingestion."""
    
    success: bool = Field(
        description="Whether ingestion succeeded"
    )
    
    ingested: int = Field(
        description="Number of facts ingested",
        example=24
    )
    
    skipped: int = Field(
        description="Number of facts skipped (duplicates)",
        example=0
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "ingested": 24,
                "skipped": 0,
                "errors": []
            }
        }
    }


# Meta Ads Sync Schemas
# ---------------------------------------------------------------------

class EntitySyncStats(BaseModel):
    """Statistics from entity synchronization.
    
    WHAT: Tracks created/updated counts for campaigns, adsets, ads
    WHY: Provides visibility into what changed during sync
    """
    
    campaigns_created: int = Field(
        default=0,
        description="Number of campaigns created"
    )
    campaigns_updated: int = Field(
        default=0,
        description="Number of campaigns updated"
    )
    adsets_created: int = Field(
        default=0,
        description="Number of adsets created"
    )
    adsets_updated: int = Field(
        default=0,
        description="Number of adsets updated"
    )
    ads_created: int = Field(
        default=0,
        description="Number of ads created"
    )
    ads_updated: int = Field(
        default=0,
        description="Number of ads updated"
    )
    duration_seconds: float = Field(
        description="Total duration in seconds"
    )


class EntitySyncResponse(BaseModel):
    """Response from entity synchronization endpoint.
    
    WHAT: Returns success status, stats, and any errors
    WHY: Provides complete feedback for sync operation
    """
    
    success: bool = Field(
        description="Whether sync succeeded overall (partial success possible)"
    )
    synced: EntitySyncStats = Field(
        description="Statistics about what was synced"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages (if any)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "synced": {
                    "campaigns_created": 5,
                    "campaigns_updated": 2,
                    "adsets_created": 12,
                    "adsets_updated": 3,
                    "ads_created": 24,
                    "ads_updated": 8,
                    "duration_seconds": 15.3
                },
                "errors": []
            }
        }
    }


class DateRange(BaseModel):
    """Date range for metrics sync.
    
    WHAT: Start and end dates for metrics fetching
    WHY: Provides visibility into what period was synced
    """
    
    start: date = Field(
        description="Start date (inclusive)"
    )
    end: date = Field(
        description="End date (inclusive)"
    )


class MetricsSyncRequest(BaseModel):
    """Request for metrics synchronization.
    
    WHAT: Optional parameters to control metrics sync
    WHY: Allows manual date range and force refresh
    """
    
    start_date: Optional[date] = Field(
        default=None,
        description="Start date (default: 90 days ago or last synced date)"
    )
    end_date: Optional[date] = Field(
        default=None,
        description="End date (default: yesterday)"
    )
    force_refresh: bool = Field(
        default=False,
        description="Re-fetch data even if it already exists"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "force_refresh": False
            }
        }
    }


class MetricsSyncStats(BaseModel):
    """Statistics from metrics synchronization.
    
    WHAT: Tracks facts ingested, skipped, date range, and ads processed
    WHY: Provides visibility into sync operation results
    """
    
    facts_ingested: int = Field(
        description="Number of metric facts ingested"
    )
    facts_skipped: int = Field(
        description="Number of facts skipped (already existed)"
    )
    date_range: DateRange = Field(
        description="Date range that was synced"
    )
    ads_processed: int = Field(
        description="Number of ads processed"
    )
    duration_seconds: float = Field(
        description="Total duration in seconds"
    )


class MetricsSyncResponse(BaseModel):
    """Response from metrics synchronization endpoint.
    
    WHAT: Returns success status, stats, and any errors
    WHY: Provides complete feedback for sync operation
    """
    
    success: bool = Field(
        description="Whether sync succeeded overall"
    )
    synced: MetricsSyncStats = Field(
        description="Statistics about what was synced"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages (if any)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "synced": {
                    "facts_ingested": 450,
                    "facts_skipped": 0,
                    "date_range": {
                        "start": "2024-10-01",
                        "end": "2024-10-31"
                    },
                    "ads_processed": 15,
                    "duration_seconds": 245.7
                },
                "errors": []
            }
        }
    }


# ==========================================================================
# ONBOARDING SCHEMAS
# ==========================================================================
# WHAT: Request/response schemas for onboarding flow
# WHY: Collect business profile for AI personalization
# REFERENCES: backend/app/routers/onboarding.py


class DomainAnalyzeRequest(BaseModel):
    """Request to analyze a domain for business information extraction."""

    domain: str = Field(
        description="Domain to analyze (e.g., 'acme.com')",
        example="acme.com",
        min_length=3
    )


class DomainSuggestions(BaseModel):
    """AI-extracted business suggestions from domain analysis."""

    business_name: Optional[str] = Field(
        None,
        description="Suggested business name"
    )
    description: Optional[str] = Field(
        None,
        description="AI-extracted business description"
    )
    niche: Optional[str] = Field(
        None,
        description="Suggested niche/industry"
    )
    brand_voice: Optional[str] = Field(
        None,
        description="Suggested brand voice"
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score (0-1)"
    )


class DomainAnalyzeResponse(BaseModel):
    """Response from domain analysis endpoint."""

    success: bool = Field(description="Whether analysis succeeded")
    suggestions: Optional[DomainSuggestions] = Field(
        None,
        description="AI-extracted suggestions"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if analysis failed"
    )


class OnboardingCompleteRequest(BaseModel):
    """Request to complete onboarding and save business profile."""

    workspace_name: str = Field(
        description="Workspace/business name (required)",
        min_length=1,
        max_length=100
    )
    domain: Optional[str] = Field(
        None,
        description="Business domain"
    )
    domain_description: Optional[str] = Field(
        None,
        description="Business description (AI-generated or user-edited)"
    )
    niche: Optional[str] = Field(
        None,
        description="Business niche/industry"
    )
    target_markets: Optional[List[str]] = Field(
        None,
        description="Target markets (countries, continents, or 'Worldwide')"
    )
    brand_voice: Optional[str] = Field(
        None,
        description="Brand voice style"
    )
    business_size: Optional[str] = Field(
        None,
        description="Business size (startup, smb, enterprise)"
    )
    intended_ad_providers: Optional[List[str]] = Field(
        None,
        description="Ad platforms user intends to connect"
    )


class OnboardingCompleteResponse(BaseModel):
    """Response from onboarding completion."""

    success: bool = Field(description="Whether onboarding completed successfully")
    redirect_to: str = Field(
        default="/dashboard",
        description="Where to redirect after completion"
    )


class OnboardingStatusResponse(BaseModel):
    """Response from onboarding status check."""

    completed: bool = Field(description="Whether onboarding is completed")
    workspace_id: str = Field(description="Current workspace ID")
    workspace_name: str = Field(description="Current workspace name")
    profile: Optional[dict] = Field(
        None,
        description="Current business profile data (if any)"
    )


class BusinessProfileUpdate(BaseModel):
    """Request to update business profile (from Settings page)."""

    domain: Optional[str] = Field(None, description="Business domain")
    domain_description: Optional[str] = Field(None, description="Business description")
    niche: Optional[str] = Field(None, description="Business niche")
    target_markets: Optional[List[str]] = Field(None, description="Target markets")
    brand_voice: Optional[str] = Field(None, description="Brand voice")
    business_size: Optional[str] = Field(None, description="Business size")


class BusinessProfileResponse(BaseModel):
    """Response with business profile data."""

    workspace_id: str
    workspace_name: str
    domain: Optional[str] = None
    domain_description: Optional[str] = None
    niche: Optional[str] = None
    target_markets: Optional[List[str]] = None
    brand_voice: Optional[str] = None
    business_size: Optional[str] = None
    onboarding_completed: bool
    onboarding_completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==========================================================================
# BILLING SCHEMAS (Polar Integration)
# ==========================================================================
# WHAT: Request/response schemas for workspace billing operations
# WHY: Per-workspace subscription state for access gating
# REFERENCES:
#   - openspec/changes/add-polar-workspace-billing/proposal.md
#   - backend/app/routers/polar.py


class BillingInfo(BaseModel):
    """Billing information for a workspace.

    WHAT: Summary of workspace subscription state and feature tier
    WHY: Frontend needs this to show billing status, manage subscriptions,
         and gate features based on tier (free vs starter)
    """

    billing_status: BillingStatusEnum = Field(description="Current subscription status")
    billing_tier: BillingPlanEnum = Field(description="Feature tier: free (limited) or starter (full)")
    billing_plan: Optional[str] = Field(None, description="Plan type: monthly | annual")
    trial_end: Optional[datetime] = Field(None, description="When trial expires")
    current_period_start: Optional[datetime] = Field(None, description="Current billing period start")
    current_period_end: Optional[datetime] = Field(None, description="Current billing period end")
    is_access_allowed: bool = Field(description="Whether user can access subscription-gated routes")
    can_manage_billing: bool = Field(description="Whether user can manage billing (Owner/Admin)")
    portal_url: Optional[str] = Field(None, description="Polar customer portal URL (Owner/Admin only)")

    model_config = {"from_attributes": True}


class WorkspaceBillingStatusResponse(BaseModel):
    """Response from GET /billing/status endpoint.

    WHAT: Full billing status for the active workspace
    WHY: Frontend dashboard shell needs this to gate routes
    """

    workspace_id: str = Field(description="Workspace UUID")
    workspace_name: str = Field(description="Workspace display name")
    billing: BillingInfo = Field(description="Billing information")


class CheckoutCreateRequest(BaseModel):
    """Request to create a Polar checkout session.

    WHAT: User initiates subscription checkout
    WHY: Starts the Polar payment flow for a workspace
    """

    workspace_id: str = Field(description="Workspace UUID to subscribe")
    plan: Literal["monthly", "annual"] = Field(description="Subscription plan to purchase")
    success_url: Optional[str] = Field(None, description="Redirect URL after successful checkout")
    cancel_url: Optional[str] = Field(None, description="Redirect URL if checkout is canceled")


class CheckoutCreateResponse(BaseModel):
    """Response with Polar checkout URL.

    WHAT: Returns the URL to redirect user to Polar checkout
    WHY: Frontend redirects to this URL to complete payment
    """

    checkout_url: str = Field(description="Polar checkout page URL")
    checkout_id: str = Field(description="Polar checkout ID for tracking")


class BillingPortalRequest(BaseModel):
    """Request to get Polar customer portal URL.

    WHAT: Owner/Admin requests portal link to manage subscription
    WHY: Users need to update payment method, cancel, etc.
    """

    workspace_id: str = Field(description="Workspace UUID")


class BillingPortalResponse(BaseModel):
    """Response with Polar customer portal URL.

    WHAT: Portal URL for self-service billing management
    WHY: Polar handles subscription changes, invoices, cancellation
    """

    portal_url: str = Field(description="Polar customer portal URL")


class WebhookResponse(BaseModel):
    """Standard webhook response.

    WHAT: Acknowledges webhook receipt
    WHY: Polar expects 200 OK; this provides structured response
    """

    received: bool = Field(default=True, description="Webhook received successfully")
    event_type: Optional[str] = Field(None, description="Event type processed")
    action: Optional[str] = Field(None, description="Action taken (processed, skipped, error)")


class WorkspaceBillingUpdate(BaseModel):
    """Internal schema for updating workspace billing.

    WHAT: Fields updated by webhook handlers
    WHY: Used internally to apply subscription changes
    """

    billing_status: Optional[BillingStatusEnum] = None
    billing_plan: Optional[str] = None
    polar_subscription_id: Optional[str] = None
    polar_customer_id: Optional[str] = None
    trial_end: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None


# Resolve forward references for nested models
WorkspaceMemberOutLite.model_rebuild()
WorkspaceMemberOut.model_rebuild()
WorkspaceInviteOut.model_rebuild()
UserOut.model_rebuild()
