"""Pydantic schemas for request/response payloads."""

from datetime import datetime, date
from enum import Enum
from uuid import UUID
from typing import Optional, List, Literal, Union, Any, Dict
from decimal import Decimal
from pydantic import (
    BaseModel,
    EmailStr,
    constr,
    Field,
    field_serializer,
    field_validator,
)
from .models import (
    RoleEnum,
    ProviderEnum,
    LevelEnum,
    KindEnum,
    ComputeRunTypeEnum,
    GoalEnum,
    BillingStatusEnum,
    BillingPlanEnum,
    # Agent system enums
    AgentStatusEnum,
    AgentScopeTypeEnum,
    AgentStateEnum,
    TriggerModeEnum,
    AccumulationUnitEnum,
    AccumulationModeEnum,
    AgentResultTypeEnum,
    ActionTypeEnum,
)


class UserCreate(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(
        description="User email address", example="user@company.com"
    )
    name: str = Field(description="User full name", example="John Doe")
    password: constr(min_length=8) = Field(
        description="Password (minimum 8 characters)", example="securePassword123"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@company.com",
                "name": "John Doe",
                "password": "securePassword123",
            }
        }
    }


class UserLogin(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(
        description="User email address", example="user@company.com"
    )
    password: str = Field(description="User password", example="securePassword123")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@company.com",
                "password": "securePassword123",
            }
        }
    }


class UserOut(BaseModel):
    """Public representation of a user."""

    id: UUID = Field(
        description="Unique user identifier",
        example="123e4567-e89b-12d3-a456-426614174000",
    )
    email: EmailStr = Field(
        description="User email address", example="john.doe@company.com"
    )
    name: str = Field(description="User display name", example="John Doe")
    role: RoleEnum = Field(
        description="User role within the active workspace", example="Admin"
    )
    workspace_id: UUID = Field(
        description="Active workspace ID (legacy field; mirrors active_workspace_id)",
        example="456e7890-e89b-12d3-a456-426614174001",
    )
    active_workspace_id: UUID | None = Field(
        default=None,
        description="Active workspace ID",
        example="456e7890-e89b-12d3-a456-426614174001",
    )
    memberships: list["WorkspaceMemberOutLite"] = Field(
        default_factory=list, description="All workspace memberships for this user"
    )
    pending_invites: list["WorkspaceInviteOut"] = Field(
        default_factory=list, description="Pending workspace invites for this user"
    )
    avatar_url: Optional[str] = Field(
        None,
        description="URL to user avatar image",
        example="https://example.com/avatar.png",
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
                "avatar_url": "https://example.com/avatar.png",
            }
        },
    }


class UserUpdate(BaseModel):
    """Payload for updating user profile."""

    name: Optional[str] = Field(None, description="User display name")
    email: Optional[EmailStr] = Field(None, description="User email address")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")


class PasswordChange(BaseModel):
    """Payload for changing password."""

    old_password: str = Field(..., description="Current password")
    new_password: constr(min_length=8) = Field(
        ..., description="New password (min 8 chars)"
    )


class PasswordResetRequest(BaseModel):
    """Payload for requesting password reset."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Payload for confirming password reset."""

    token: str = Field(..., description="Reset token")
    new_password: constr(min_length=8) = Field(
        ..., description="New password (min 8 chars)"
    )


class EmailVerification(BaseModel):
    """Payload for verifying email."""

    token: str = Field(..., description="Verification token")


class TokenPayload(BaseModel):
    """JWT token contents."""

    sub: str = Field(description="Subject (user email)", example="user@company.com")
    exp: int = Field(description="Token expiration timestamp", example=1640995200)


class LoginResponse(BaseModel):
    """Response from successful login."""

    user: UserOut = Field(description="Authenticated user information")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john.doe@company.com",
                    "name": "John Doe",
                    "role": "Admin",
                    "workspace_id": "456e7890-e89b-12d3-a456-426614174001",
                }
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(description="Error message", example="Invalid credentials")

    model_config = {"json_schema_extra": {"example": {"detail": "Invalid credentials"}}}


class SuccessResponse(BaseModel):
    """Standard success response."""

    status: str = Field(default="ok", description="Status message")
    detail: str | None = Field(
        default=None,
        description="Success message",
        example="Operation completed successfully",
    )

    model_config = {"json_schema_extra": {"example": {"detail": "logged out"}}}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status", example="ok")

    model_config = {"json_schema_extra": {"example": {"status": "ok"}}}


# Workspace Schemas
class WorkspaceCreate(BaseModel):
    """Schema for creating a new workspace."""

    name: str = Field(
        description="Workspace name",
        example="ACME Corp Marketing",
        min_length=1,
        max_length=100,
    )


class WorkspaceUpdate(BaseModel):
    """Schema for updating workspace."""

    name: Optional[str] = Field(
        None,
        description="Updated workspace name",
        example="ACME Corp Marketing - Updated",
        min_length=1,
        max_length=100,
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

    has_shopify: bool = Field(description="Whether Shopify is connected and active")
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

    provider: ProviderEnum = Field(description="Ad platform provider", example="google")
    external_account_id: str = Field(
        description="Account ID in the external platform", example="123-456-7890"
    )
    name: str = Field(
        description="Friendly name for this connection", example="ACME Google Ads"
    )
    status: str = Field(description="Connection status", example="active")


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
    meta_pixel_id: Optional[str] = Field(
        None, description="Meta Pixel ID for CAPI (Meta connections only)"
    )

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
    executed_dsl: Optional[dict] = Field(
        None, description="Executed DSL (when completed)"
    )
    data: Optional[dict] = Field(None, description="Result data (when completed)")
    context_used: Optional[List[dict]] = Field(
        None, description="Context used (when completed)"
    )
    visuals: Optional[dict] = Field(
        default=None,
        description="Optional rich payload containing cards, charts, and tables",
    )
    error: Optional[str] = Field(None, description="Error message (when failed)")


# Entity Schemas
class EntityCreate(BaseModel):
    """Schema for creating a new entity (campaign, ad set, ad, etc.)."""

    level: LevelEnum = Field(
        description="Entity level in hierarchy", example="campaign"
    )
    external_id: str = Field(
        description="ID in the external ad platform", example="camp_123456"
    )
    name: str = Field(description="Entity name", example="Summer Sale Campaign")
    status: str = Field(description="Entity status", example="active")
    connection_id: Optional[UUID] = Field(None, description="Associated connection ID")
    parent_id: Optional[UUID] = Field(
        None, description="Parent entity ID (for hierarchy)"
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

    workspaces: List[WorkspaceWithRole] = Field(
        description="List of workspaces with roles"
    )
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
    role: str = Field(
        description="User's role in the active workspace (Owner, Admin, Viewer)"
    )
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
    "spend",
    "revenue",
    "clicks",
    "impressions",
    "conversions",
    "leads",
    "installs",
    "purchases",
    "visitors",
    "profit",
    # Derived metrics - Cost/Efficiency
    "cpc",
    "cpm",
    "cpa",
    "cpl",
    "cpi",
    "cpp",
    # Derived metrics - Value
    "roas",
    "poas",
    "arpv",
    "aov",
    # Derived metrics - Engagement
    "ctr",
    "cvr",
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

    metrics: List[MetricKey] = Field(
        default_factory=lambda: ["spend", "revenue", "conversions", "roas"]
    )
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
        example="Your REVENUE for the selected period is $58,300.90.",
    )
    executed_dsl: dict = Field(
        description="The validated DSL query that was executed",
        example={"metric": "revenue", "time_range": {"last_n_days": 7}},
    )
    data: dict = Field(
        description="Query execution results (summary, timeseries, breakdown)",
        example={"summary": 58300.9},
    )
    context_used: Optional[List[dict]] = Field(
        default=None,
        description="Previous queries used for context (for debugging follow-ups)",
        example=[{"question": "how much revenue this week?", "metric": "revenue"}],
    )
    visuals: Optional[dict] = Field(
        default=None,
        description="Optional rich payload with cards, viz specs (Recharts/Vega-Lite), and tables",
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
    feedback_type: Optional[FeedbackType] = Field(
        default=None, description="What aspect the feedback is about"
    )
    comment: Optional[str] = Field(
        default=None, description="Optional free-text comment"
    )
    corrected_answer: Optional[str] = Field(
        default=None, description="What the answer should have been"
    )


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
    value: Optional[float] = Field(
        default=None, description="Metric value for the date"
    )


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
    # Raw traffic metrics (needed for CPM, CTR, Conv Rate calculations)
    clicks: Optional[float] = None
    impressions: Optional[float] = None
    # Calculated metrics
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
    # For manual costs: list of individual cost UUIDs that make up this row
    # Enables frontend to edit individual costs when aggregated by category
    cost_ids: Optional[List[str]] = None


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
        None, description="metricx entity UUID (if entity already synced)"
    )

    # Pattern 2: New entity (will be looked up or created)
    external_entity_id: Optional[str] = Field(
        None,
        description="Platform's entity ID (e.g., Meta campaign_id)",
        example="123456789",
    )

    # Required metadata
    provider: ProviderEnum = Field(description="Ad platform provider", example="meta")

    level: LevelEnum = Field(description="Entity hierarchy level", example="campaign")

    # Timestamp (timezone-aware)
    event_at: datetime = Field(
        description="When this metric occurred (with timezone)",
        example="2025-10-30T14:00:00+00:00",
    )

    # Base measures (Meta Insights API fields)
    spend: Decimal = Field(
        description="Ad spend in currency units", example=150.50, ge=0
    )

    impressions: int = Field(description="Number of ad impressions", example=5420, ge=0)

    clicks: int = Field(description="Number of clicks", example=234, ge=0)

    # Optional base measures
    conversions: Optional[Decimal] = Field(
        None, description="Conversion events count", example=12.0, ge=0
    )

    revenue: Optional[Decimal] = Field(
        None, description="Revenue attributed to ads", example=1250.00, ge=0
    )

    leads: Optional[Decimal] = Field(
        None, description="Lead form submissions", example=8.0, ge=0
    )

    installs: Optional[int] = Field(None, description="App installs", example=15, ge=0)

    purchases: Optional[int] = Field(
        None, description="Purchase events", example=5, ge=0
    )

    visitors: Optional[int] = Field(
        None, description="Landing page visitors", example=180, ge=0
    )

    profit: Optional[Decimal] = Field(
        None, description="Net profit (revenue - costs)", example=1100.00
    )

    # Currency
    currency: str = Field(
        description="Currency code", example="USD", min_length=3, max_length=3
    )

    # Natural key (for deduplication)
    natural_key: Optional[str] = Field(
        None,
        description="Unique key for this fact (prevents duplicates)",
        example="123456789-2025-10-30T14:00:00+00:00",
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
                "currency": "USD",
            }
        }
    }


class MetricFactIngestResponse(BaseModel):
    """Response from metric fact ingestion."""

    success: bool = Field(description="Whether ingestion succeeded")

    ingested: int = Field(description="Number of facts ingested", example=24)

    skipped: int = Field(description="Number of facts skipped (duplicates)", example=0)

    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )

    model_config = {
        "json_schema_extra": {
            "example": {"success": True, "ingested": 24, "skipped": 0, "errors": []}
        }
    }


# Meta Ads Sync Schemas
# ---------------------------------------------------------------------


class EntitySyncStats(BaseModel):
    """Statistics from entity synchronization.

    WHAT: Tracks created/updated counts for campaigns, adsets, ads
    WHY: Provides visibility into what changed during sync
    """

    campaigns_created: int = Field(default=0, description="Number of campaigns created")
    campaigns_updated: int = Field(default=0, description="Number of campaigns updated")
    adsets_created: int = Field(default=0, description="Number of adsets created")
    adsets_updated: int = Field(default=0, description="Number of adsets updated")
    ads_created: int = Field(default=0, description="Number of ads created")
    ads_updated: int = Field(default=0, description="Number of ads updated")
    duration_seconds: float = Field(description="Total duration in seconds")


class EntitySyncResponse(BaseModel):
    """Response from entity synchronization endpoint.

    WHAT: Returns success status, stats, and any errors
    WHY: Provides complete feedback for sync operation
    """

    success: bool = Field(
        description="Whether sync succeeded overall (partial success possible)"
    )
    synced: EntitySyncStats = Field(description="Statistics about what was synced")
    errors: List[str] = Field(
        default_factory=list, description="List of error messages (if any)"
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
                    "duration_seconds": 15.3,
                },
                "errors": [],
            }
        }
    }


class DateRange(BaseModel):
    """Date range for metrics sync.

    WHAT: Start and end dates for metrics fetching
    WHY: Provides visibility into what period was synced
    """

    start: date = Field(description="Start date (inclusive)")
    end: date = Field(description="End date (inclusive)")


class MetricsSyncRequest(BaseModel):
    """Request for metrics synchronization.

    WHAT: Optional parameters to control metrics sync
    WHY: Allows manual date range and force refresh
    """

    start_date: Optional[date] = Field(
        default=None,
        description="Start date (default: 90 days ago or last synced date)",
    )
    end_date: Optional[date] = Field(
        default=None, description="End date (default: yesterday)"
    )
    force_refresh: bool = Field(
        default=False, description="Re-fetch data even if it already exists"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "force_refresh": False,
            }
        }
    }


class MetricsSyncStats(BaseModel):
    """Statistics from metrics synchronization.

    WHAT: Tracks facts ingested, skipped, date range, and ads processed
    WHY: Provides visibility into sync operation results
    """

    facts_ingested: int = Field(description="Number of metric facts ingested")
    facts_skipped: int = Field(description="Number of facts skipped (already existed)")
    date_range: DateRange = Field(description="Date range that was synced")
    ads_processed: int = Field(description="Number of ads processed")
    duration_seconds: float = Field(description="Total duration in seconds")


class MetricsSyncResponse(BaseModel):
    """Response from metrics synchronization endpoint.

    WHAT: Returns success status, stats, and any errors
    WHY: Provides complete feedback for sync operation
    """

    success: bool = Field(description="Whether sync succeeded overall")
    synced: MetricsSyncStats = Field(description="Statistics about what was synced")
    errors: List[str] = Field(
        default_factory=list, description="List of error messages (if any)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "synced": {
                    "facts_ingested": 450,
                    "facts_skipped": 0,
                    "date_range": {"start": "2024-10-01", "end": "2024-10-31"},
                    "ads_processed": 15,
                    "duration_seconds": 245.7,
                },
                "errors": [],
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
        min_length=3,
    )


class DomainSuggestions(BaseModel):
    """AI-extracted business suggestions from domain analysis."""

    business_name: Optional[str] = Field(None, description="Suggested business name")
    description: Optional[str] = Field(
        None, description="AI-extracted business description"
    )
    niche: Optional[str] = Field(None, description="Suggested niche/industry")
    brand_voice: Optional[str] = Field(None, description="Suggested brand voice")
    confidence: float = Field(default=0.0, description="Confidence score (0-1)")


class DomainAnalyzeResponse(BaseModel):
    """Response from domain analysis endpoint."""

    success: bool = Field(description="Whether analysis succeeded")
    suggestions: Optional[DomainSuggestions] = Field(
        None, description="AI-extracted suggestions"
    )
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class OnboardingCompleteRequest(BaseModel):
    """Request to complete onboarding and save business profile."""

    workspace_name: str = Field(
        description="Workspace/business name (required)", min_length=1, max_length=100
    )
    domain: Optional[str] = Field(None, description="Business domain")
    domain_description: Optional[str] = Field(
        None, description="Business description (AI-generated or user-edited)"
    )
    niche: Optional[str] = Field(None, description="Business niche/industry")
    target_markets: Optional[List[str]] = Field(
        None, description="Target markets (countries, continents, or 'Worldwide')"
    )
    brand_voice: Optional[str] = Field(None, description="Brand voice style")
    business_size: Optional[str] = Field(
        None, description="Business size (startup, smb, enterprise)"
    )
    intended_ad_providers: Optional[List[str]] = Field(
        None, description="Ad platforms user intends to connect"
    )


class OnboardingCompleteResponse(BaseModel):
    """Response from onboarding completion."""

    success: bool = Field(description="Whether onboarding completed successfully")
    redirect_to: str = Field(
        default="/dashboard", description="Where to redirect after completion"
    )


class OnboardingStatusResponse(BaseModel):
    """Response from onboarding status check."""

    completed: bool = Field(description="Whether onboarding is completed")
    workspace_id: str = Field(description="Current workspace ID")
    workspace_name: str = Field(description="Current workspace name")
    profile: Optional[dict] = Field(
        None, description="Current business profile data (if any)"
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
    billing_tier: BillingPlanEnum = Field(
        description="Feature tier: free (limited) or starter (full)"
    )
    billing_plan: Optional[str] = Field(None, description="Plan type: monthly | annual")
    trial_started_at: Optional[datetime] = Field(
        None, description="When 7-day trial started (for expiry calculation)"
    )
    trial_end: Optional[datetime] = Field(None, description="When trial expires")
    current_period_start: Optional[datetime] = Field(
        None, description="Current billing period start"
    )
    current_period_end: Optional[datetime] = Field(
        None, description="Current billing period end"
    )
    is_access_allowed: bool = Field(
        description="Whether user can access subscription-gated routes"
    )
    can_manage_billing: bool = Field(
        description="Whether user can manage billing (Owner/Admin)"
    )
    portal_url: Optional[str] = Field(
        None, description="Polar customer portal URL (Owner/Admin only)"
    )

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
    plan: Literal["monthly", "annual"] = Field(
        description="Subscription plan to purchase"
    )
    success_url: Optional[str] = Field(
        None, description="Redirect URL after successful checkout"
    )
    cancel_url: Optional[str] = Field(
        None, description="Redirect URL if checkout is canceled"
    )


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
    action: Optional[str] = Field(
        None, description="Action taken (processed, skipped, error)"
    )


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


# ==========================================================================
# ADMIN DASHBOARD SCHEMAS
# ==========================================================================
# WHAT: Request/response schemas for admin dashboard operations
# WHY: Platform-level admin needs to manage users and workspaces
# REFERENCES: backend/app/routers/admin.py


class AdminWorkspaceSummary(BaseModel):
    """Summary of a workspace for admin listing.

    WHAT: Workspace info with billing status and member count
    WHY: Admin dashboard needs to see all workspaces at a glance
    """

    id: str
    name: str
    billing_status: str
    billing_tier: str
    member_count: int
    owner_email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserWorkspace(BaseModel):
    """Workspace info attached to a user in admin view.

    WHAT: Minimal workspace info for user listing
    WHY: Shows which workspaces a user belongs to
    """

    id: str
    name: str
    role: str
    billing_tier: str


class AdminUserOut(BaseModel):
    """User details for admin dashboard.

    WHAT: Full user info including superuser status and workspaces
    WHY: Admin needs to see all user details for management
    """

    id: str
    email: str
    name: str
    clerk_id: Optional[str] = None
    is_superuser: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    workspaces: List[AdminUserWorkspace] = []

    model_config = {"from_attributes": True}


class AdminUsersResponse(BaseModel):
    """Response for admin users list.

    WHAT: Paginated list of users
    WHY: Admin dashboard needs to display all users
    """

    users: List[AdminUserOut]
    total: int


class AdminWorkspacesResponse(BaseModel):
    """Response for admin workspaces list.

    WHAT: Paginated list of workspaces
    WHY: Admin dashboard needs to display all workspaces
    """

    workspaces: List[AdminWorkspaceSummary]
    total: int


class AdminSuperuserUpdate(BaseModel):
    """Request to update user superuser status.

    WHAT: Toggle superuser flag
    WHY: Admin needs to grant/revoke platform admin access
    """

    is_superuser: bool


class AdminBillingUpdate(BaseModel):
    """Request to update workspace billing tier.

    WHAT: Update billing_tier (free/starter)
    WHY: Admin needs to grant premium access or downgrade workspaces
    """

    billing_tier: Literal["free", "starter"]


class AdminDeleteUserResponse(BaseModel):
    """Response from user deletion.

    WHAT: Confirmation of user deletion with details
    WHY: Admin needs to know what was deleted
    """

    success: bool
    user_id: str
    clerk_deleted: bool
    workspaces_deleted: int
    message: str


class AdminMeResponse(BaseModel):
    """Response for admin status check.

    WHAT: Current user's superuser status
    WHY: Frontend needs to know if user can access admin dashboard
    """

    is_superuser: bool
    user_id: str
    email: str


# ==========================================================================
# AGENT SYSTEM SCHEMAS
# ==========================================================================
# WHAT: Request/response schemas for autonomous monitoring agents
# WHY: Agents watch ad metrics, evaluate conditions, and take actions
# REFERENCES:
#   - Agent System Implementation Plan
#   - backend/app/models.py (Agent, AgentEntityState, etc.)


# --- Agent Scope Configuration ---


class AgentScopeSpecific(BaseModel):
    """Scope configuration for watching specific entities.

    WHAT: Watch specific entity IDs
    WHY: User wants to monitor exact campaigns/ads
    """

    entity_ids: List[UUID] = Field(
        description="List of entity UUIDs to watch",
        min_length=1,
    )


class AgentScopeFilter(BaseModel):
    """Scope configuration for filtering entities.

    WHAT: Watch entities matching criteria
    WHY: User wants to monitor all campaigns matching conditions
    """

    level: LevelEnum = Field(description="Entity level to watch")
    provider: Optional[ProviderEnum] = Field(
        None, description="Filter by provider (meta, google, etc.)"
    )
    status: Optional[str] = Field(
        None, description="Filter by entity status (ACTIVE, PAUSED, etc.)"
    )
    name_contains: Optional[str] = Field(
        None, description="Filter by name containing substring"
    )
    aggregate: bool = Field(
        default=False,
        description="If true, sum metrics across all matched entities and evaluate ONCE (account-level monitoring)"
    )


class AgentScopeAll(BaseModel):
    """Scope configuration for watching all entities.

    WHAT: Watch all entities at a level
    WHY: User wants blanket monitoring
    """

    level: LevelEnum = Field(description="Entity level to watch (campaign, adset, ad)")
    aggregate: bool = Field(
        default=False,
        description="If true, sum metrics across all entities and evaluate ONCE (account-level monitoring)"
    )


AgentScopeConfig = Union[AgentScopeSpecific, AgentScopeFilter, AgentScopeAll]


# --- Condition Configuration ---


class ThresholdCondition(BaseModel):
    """Threshold-based condition.

    WHAT: Compare metric to a value
    WHY: "Alert when ROAS > 2" or "Pause when CPC > $3"
    """

    type: Literal["threshold"] = "threshold"
    metric: str = Field(description="Metric to evaluate (roas, cpc, spend, etc.)")
    operator: Literal["gt", "gte", "lt", "lte", "eq", "neq"] = Field(
        description="Comparison operator"
    )
    value: float = Field(description="Threshold value")


class ChangeCondition(BaseModel):
    """Change-based condition.

    WHAT: Detect metric changes over time
    WHY: "Alert when spend increases 50% vs yesterday"
    """

    type: Literal["change"] = "change"
    metric: str = Field(description="Metric to evaluate")
    direction: Literal["increase", "decrease", "any"] = Field(
        description="Direction of change"
    )
    percent: float = Field(description="Percentage change threshold", gt=0)
    reference_period: Literal["previous_day", "previous_week", "previous_period"] = (
        Field(description="What to compare against")
    )


class CompositeCondition(BaseModel):
    """Composite condition combining multiple conditions.

    WHAT: AND/OR logic for multiple conditions
    WHY: "Alert when ROAS > 2 AND spend > $100"
    """

    type: Literal["composite"] = "composite"
    operator: Literal["and", "or"] = Field(description="Logical operator")
    conditions: List["ConditionConfig"] = Field(
        description="List of conditions to combine", min_length=2
    )


class NotCondition(BaseModel):
    """Negation condition.

    WHAT: Negate another condition
    WHY: "Alert when ROAS is NOT > 2"
    """

    type: Literal["not"] = "not"
    condition: "ConditionConfig" = Field(description="Condition to negate")


ConditionConfig = Union[
    ThresholdCondition, ChangeCondition, CompositeCondition, NotCondition
]

# Forward reference resolution
CompositeCondition.model_rebuild()
NotCondition.model_rebuild()


# --- Action Configuration ---


class EmailAction(BaseModel):
    """Email notification action.

    WHAT: Send email when triggered
    WHY: Alert user about metric conditions
    """

    type: Literal["email"] = "email"
    to: Optional[List[EmailStr]] = Field(
        None, description="Recipients (default: workspace members)"
    )
    subject_template: Optional[str] = Field(
        None,
        description="Subject template with {{variables}}",
        example="Alert: {{agent_name}} triggered on {{entity_name}}",
    )
    body_template: Optional[str] = Field(
        None, description="Body template with {{variables}}"
    )


class ScaleBudgetAction(BaseModel):
    """Budget scaling action.

    WHAT: Adjust campaign budget
    WHY: Auto-scale winning campaigns
    """

    type: Literal["scale_budget"] = "scale_budget"
    scale_percent: float = Field(
        description="Percentage to scale (positive = increase, negative = decrease)",
        example=20,
    )
    max_budget: Optional[float] = Field(
        None, description="Maximum budget cap", example=1000
    )
    min_budget: Optional[float] = Field(
        None, description="Minimum budget floor", example=10
    )


class PauseCampaignAction(BaseModel):
    """Campaign pause action.

    WHAT: Pause the campaign
    WHY: Stop-loss for poor performers
    """

    type: Literal["pause_campaign"] = "pause_campaign"


class WebhookAction(BaseModel):
    """Webhook call action.

    WHAT: Call external URL
    WHY: Integration with external systems
    """

    type: Literal["webhook"] = "webhook"
    url: str = Field(description="Webhook URL to call")
    method: Literal["GET", "POST", "PUT"] = Field(
        default="POST", description="HTTP method"
    )
    headers: Optional[dict] = Field(None, description="Custom headers")
    body_template: Optional[str] = Field(
        None, description="Request body template with {{variables}}"
    )


# --- Multi-Channel Notification Configuration ---


class NotificationChannelConfig(BaseModel):
    """Configuration for a single notification channel.

    WHAT: Defines how to send notifications via a specific channel
    WHY: Allows users to configure multiple notification channels per agent

    Supported channels:
    - email: Send via Resend (existing)
    - slack: Send via Slack incoming webhook
    - webhook: Send to custom HTTP endpoint
    """

    type: Literal["email", "slack", "webhook"] = Field(
        description="Channel type: email, slack, or webhook"
    )
    enabled: bool = Field(default=True, description="Whether this channel is active")

    # Email-specific fields
    recipients: Optional[List[EmailStr]] = Field(
        None, description="Email recipients (defaults to workspace members)"
    )

    # Slack-specific fields
    webhook_url: Optional[str] = Field(
        None, description="Slack incoming webhook URL"
    )
    channel: Optional[str] = Field(
        None, description="Override default Slack channel (e.g., #alerts)"
    )

    # Webhook-specific fields
    url: Optional[str] = Field(
        None, description="Webhook URL for custom integrations"
    )
    method: Literal["GET", "POST", "PUT"] = Field(
        default="POST", description="HTTP method for webhook"
    )
    headers: Optional[dict] = Field(
        None, description="Custom headers for webhook"
    )


class NotificationEventOverride(BaseModel):
    """Optional per-event override for notify action."""

    channels: Optional[List[NotificationChannelConfig]] = Field(
        default=None,
        description="Override channels for this event",
    )
    message_template: Optional[str] = Field(
        default=None,
        description="Override message template for this event",
    )
    template_preset: Optional[str] = Field(
        default=None,
        description="Override template preset for this event",
    )
    include_metrics: Optional[List[str]] = Field(
        default=None,
        description="Override included metrics for this event",
    )


class NotifyAction(BaseModel):
    """Multi-channel notification action.

    WHAT: Send notifications to multiple channels (email, Slack, webhook)
    WHY: Users want to receive alerts via their preferred channels

    USAGE:
        {
            "type": "notify",
            "channels": [
                {"type": "email", "recipients": ["user@example.com"]},
                {"type": "slack", "webhook_url": "https://hooks.slack.com/..."}
            ],
            "template_preset": "daily_summary",
            "include_metrics": ["revenue", "spend", "roas", "profit"]
        }

    TEMPLATE VARIABLES:
        {{agent_name}} - Name of the agent
        {{entity_name}} - Name of the entity (campaign, account, etc.)
        {{headline}} - Auto-generated headline
        {{revenue}}, {{spend}}, {{roas}}, {{profit}} - Metric values
        {{date}} - Report date
        {{dashboard_url}} - Link to dashboard
    """

    type: Literal["notify"] = "notify"
    channels: List[NotificationChannelConfig] = Field(
        description="List of notification channels to send to"
    )
    message_template: Optional[str] = Field(
        None,
        description="Custom message template with {{variables}}. If not provided, uses template_preset.",
    )
    template_preset: Optional[str] = Field(
        default="alert",
        description="Preset template: 'alert', 'daily_summary', or 'digest'",
    )
    include_metrics: List[str] = Field(
        default=["spend", "revenue", "roas", "profit"],
        description="Which metrics to include in the notification",
    )
    event_overrides: Optional[Dict[str, NotificationEventOverride]] = Field(
        default=None,
        description="Optional per-event overrides (e.g., report/trigger) for channels and templates",
    )


ActionConfig = Union[EmailAction, ScaleBudgetAction, PauseCampaignAction, WebhookAction, NotifyAction]


# --- Accumulation Configuration ---


class AccumulationConfig(BaseModel):
    """Accumulation settings for agent triggers.

    WHAT: How long condition must hold before triggering
    WHY: "ROAS > 2 for 3 consecutive days" prevents noise
    """

    required: int = Field(
        default=1,
        description="Number of units required",
        ge=1,
        example=3,
    )
    unit: AccumulationUnitEnum = Field(
        default=AccumulationUnitEnum.evaluations,
        description="What to count (evaluations, hours, days)",
    )
    mode: AccumulationModeEnum = Field(
        default=AccumulationModeEnum.consecutive,
        description="consecutive or within_window",
    )
    window: Optional[int] = Field(
        None,
        description="Window size for within_window mode",
        example=7,
    )


# --- Trigger Configuration ---


class TriggerConfig(BaseModel):
    """Trigger behavior settings.

    WHAT: What happens after condition is met
    WHY: Different use cases need different patterns
    """

    mode: TriggerModeEnum = Field(
        default=TriggerModeEnum.once,
        description="once, cooldown, or continuous",
    )
    cooldown_minutes: Optional[int] = Field(
        None,
        description="Minutes to wait before can trigger again (cooldown mode)",
        example=1440,
    )
    continuous_interval_minutes: Optional[int] = Field(
        None,
        description="Minutes between triggers while condition holds (continuous mode)",
        example=60,
    )


# --- Schedule Configuration ---


class ScheduleConfig(BaseModel):
    """Schedule configuration for agent evaluation.

    WHAT: When the agent should run
    WHY: Enables scheduled reports (daily at 1am) vs realtime alerts

    SCHEDULE TYPES:
    - realtime: Evaluate every 15 minutes (existing behavior)
    - daily: Evaluate once per day at specified time
    - weekly: Evaluate once per week on specified day and time
    - monthly: Evaluate once per month on specified day and time

    EXAMPLE:
        Daily at 1am UTC:
        {"type": "daily", "hour": 1, "minute": 0, "timezone": "UTC"}

        Weekly on Monday at 9am:
        {"type": "weekly", "hour": 9, "minute": 0, "day_of_week": 0, "timezone": "America/New_York"}
    """

    type: Literal["realtime", "daily", "weekly", "monthly"] = Field(
        default="realtime",
        description="Schedule type: realtime (every 15 min), daily, weekly, or monthly",
    )
    hour: int = Field(
        default=0,
        ge=0,
        le=23,
        description="Hour of day to run (0-23)",
    )
    minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute of hour to run (0-59)",
    )
    day_of_week: Optional[int] = Field(
        None,
        ge=0,
        le=6,
        description="Day of week for weekly schedule (0=Monday, 6=Sunday)",
    )
    day_of_month: Optional[int] = Field(
        None,
        ge=1,
        le=31,
        description="Day of month for monthly schedule (1-31)",
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for schedule (e.g., 'America/New_York', 'Europe/Amsterdam')",
    )


class DateRangeConfig(BaseModel):
    """Date range configuration for report data.

    WHAT: What time period to report on
    WHY: Scheduled reports need to know "yesterday's data" vs "last 7 days"

    For scheduled daily reports, "yesterday" is typically what you want.
    For realtime alerts, "rolling_24h" matches existing behavior.
    """

    type: Literal["rolling_24h", "today", "yesterday", "last_7_days", "last_30_days"] = Field(
        default="yesterday",
        description="Date range for metrics: rolling_24h, today, yesterday, last_7_days, last_30_days",
    )


# --- Safety Configuration ---


class SafetyConfig(BaseModel):
    """Safety limits and circuit breakers.

    WHAT: Hard limits to prevent runaway behavior
    WHY: Agents are autonomous - need guardrails
    """

    max_budget: Optional[float] = Field(
        None, description="Maximum budget cap for this agent's actions"
    )
    min_budget: Optional[float] = Field(
        None, description="Minimum budget floor for this agent's actions"
    )
    pause_if_roas_drops_percent: Optional[float] = Field(
        None, description="Pause if ROAS drops more than this % after action"
    )
    max_actions_per_day: Optional[int] = Field(
        None, description="Maximum actions per day per entity"
    )


# --- Agent CRUD Schemas ---


class AgentCreate(BaseModel):
    """Request to create a new agent.

    WHAT: Full agent definition
    WHY: Create monitoring agent with all configuration
    """

    name: Optional[str] = Field(
        None,
        description="Agent name (auto-generated if not provided)",
        max_length=255,
        example="High ROAS Scaler",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description",
        example="Scales budget when ROAS exceeds 2.0 for 3 days",
    )

    # Scope
    scope_type: AgentScopeTypeEnum = Field(description="How to select entities")
    scope_config: dict = Field(
        description="Scope configuration (entity_ids, filters, or level)"
    )

    # Condition
    condition: dict = Field(
        description="Condition configuration (threshold, change, composite, or not)"
    )

    # Accumulation
    accumulation: AccumulationConfig = Field(
        default_factory=AccumulationConfig,
        description="How long condition must hold",
    )

    # Trigger
    trigger: TriggerConfig = Field(
        default_factory=TriggerConfig,
        description="What happens after condition met",
    )

    # Actions
    actions: List[dict] = Field(
        description="List of actions to execute",
        min_length=1,
    )

    # Safety
    safety: Optional[SafetyConfig] = Field(
        None, description="Safety limits and circuit breakers"
    )

    # Schedule (NEW: for scheduled reports)
    schedule: Optional[ScheduleConfig] = Field(
        None,
        description="Schedule configuration for when to evaluate. Default: realtime (every 15 min)",
    )

    # Condition requirement (NEW: for always-send reports)
    condition_required: bool = Field(
        default=True,
        description="If False, agent triggers at schedule time regardless of condition (for scheduled reports)",
    )

    # Date range for metrics (NEW: for scheduled reports)
    date_range: Optional[DateRangeConfig] = Field(
        None,
        description="Date range for metrics. Default: rolling_24h for realtime, yesterday for scheduled",
    )

    # Status
    status: Literal["active", "draft"] = Field(
        default="active",
        description="Initial status (active or draft)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "High ROAS Scaler",
                "description": "Scales budget when ROAS exceeds 2.0 for 3 consecutive days",
                "scope_type": "filter",
                "scope_config": {"level": "campaign", "provider": "meta"},
                "condition": {
                    "type": "threshold",
                    "metric": "roas",
                    "operator": "gt",
                    "value": 2.0,
                },
                "accumulation": {"required": 3, "unit": "days", "mode": "consecutive"},
                "trigger": {"mode": "once"},
                "actions": [
                    {"type": "scale_budget", "scale_percent": 20, "max_budget": 1000},
                    {"type": "email"},
                ],
            }
        }
    }


class AgentUpdate(BaseModel):
    """Request to update an agent.

    WHAT: Partial update to agent configuration
    WHY: Modify agent without recreating
    """

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    scope_type: Optional[AgentScopeTypeEnum] = None
    scope_config: Optional[dict] = None
    condition: Optional[dict] = None
    accumulation: Optional[AccumulationConfig] = None
    trigger: Optional[TriggerConfig] = None
    actions: Optional[List[dict]] = None
    safety: Optional[SafetyConfig] = None
    schedule: Optional[ScheduleConfig] = None
    condition_required: Optional[bool] = None
    date_range: Optional[DateRangeConfig] = None


class AgentEntityStateSummary(BaseModel):
    """Summary of per-entity state.

    WHAT: Current state for one entity being watched
    WHY: Show accumulation progress in UI
    """

    entity_id: UUID
    entity_name: str
    entity_provider: str
    state: AgentStateEnum
    accumulation_count: int
    accumulation_required: int
    trigger_count: int
    last_triggered_at: Optional[datetime] = None
    next_eligible_trigger_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentOut(BaseModel):
    """Agent response with full details.

    WHAT: Complete agent representation
    WHY: Return agent data to frontend
    """

    id: UUID
    name: str
    description: Optional[str] = None
    status: AgentStatusEnum
    error_message: Optional[str] = None

    # Configuration
    scope_type: AgentScopeTypeEnum
    scope_config: dict
    condition: dict
    accumulation: AccumulationConfig
    trigger: TriggerConfig
    actions: List[dict]
    safety: Optional[SafetyConfig] = None
    schedule: Optional[ScheduleConfig] = None
    condition_required: bool = True
    date_range: Optional[DateRangeConfig] = None

    # Stats
    entities_count: int = Field(
        default=0, description="Number of entities being watched"
    )
    last_evaluated_at: Optional[datetime] = None
    total_evaluations: int = 0
    total_triggers: int = 0
    last_triggered_at: Optional[datetime] = None

    # Entity states summary
    current_states: List[AgentEntityStateSummary] = Field(
        default_factory=list, description="State per watched entity"
    )

    # Metadata
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    workspace_id: UUID

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Response for agent list endpoint.

    WHAT: Paginated list of agents
    WHY: Dashboard needs to show all agents
    """

    agents: List[AgentOut]
    total: int


# --- Agent Event Schemas ---


class AgentEvaluationEventOut(BaseModel):
    """Evaluation event response.

    WHAT: Single evaluation event with full details
    WHY: Show what happened during evaluation
    """

    id: UUID
    agent_id: UUID
    entity_id: UUID
    evaluated_at: datetime

    # Result
    result_type: AgentResultTypeEnum
    headline: str

    # Entity context
    entity_name: str
    entity_provider: str
    entity_snapshot: dict

    # Observations
    observations: dict

    # Condition
    condition_definition: dict
    condition_inputs: dict
    condition_result: bool
    condition_explanation: str

    # Accumulation
    accumulation_before: dict
    accumulation_after: dict
    accumulation_explanation: str

    # State
    state_before: str
    state_after: str
    state_transition_reason: str

    # Trigger
    should_trigger: bool
    trigger_explanation: str

    # Summary
    summary: str

    # Performance
    evaluation_duration_ms: int

    model_config = {"from_attributes": True}


class AgentEvaluationEventListResponse(BaseModel):
    """Response for evaluation events list.

    WHAT: Paginated list of evaluation events
    WHY: Agent detail page shows event history
    """

    events: List[AgentEvaluationEventOut]
    total: int


class AgentActionExecutionOut(BaseModel):
    """Action execution response.

    WHAT: Record of an executed action
    WHY: Show what actions were taken and their results
    """

    id: UUID
    evaluation_event_id: UUID
    agent_id: UUID

    action_type: ActionTypeEnum
    action_config: dict

    executed_at: datetime
    success: bool
    description: str
    details: dict
    error: Optional[str] = None
    duration_ms: int

    # State tracking
    state_before: Optional[dict] = None
    state_after: Optional[dict] = None
    state_verified: bool = False

    # Rollback
    rollback_possible: bool = False
    rollback_executed_at: Optional[datetime] = None
    rollback_executed_by: Optional[UUID] = None

    model_config = {"from_attributes": True}


class AgentActionExecutionListResponse(BaseModel):
    """Response for action executions list.

    WHAT: Paginated list of action executions
    WHY: Show history of agent actions
    """

    executions: List[AgentActionExecutionOut]
    total: int


# --- Agent Status/Control Schemas ---


class AgentPauseRequest(BaseModel):
    """Request to pause an agent.

    WHAT: Optional reason for pausing
    WHY: Audit trail for agent state changes
    """

    reason: Optional[str] = Field(None, description="Reason for pausing")


class AgentResumeRequest(BaseModel):
    """Request to resume an agent.

    WHAT: Options for resuming
    WHY: May need to reset state on resume
    """

    reset_state: bool = Field(
        default=False,
        description="Reset accumulation state on resume",
    )


class AgentTestRequest(BaseModel):
    """Request to test agent evaluation.

    WHAT: Dry-run evaluation without executing actions
    WHY: Verify agent configuration before enabling
    """

    entity_ids: Optional[List[UUID]] = Field(
        None, description="Specific entities to test (default: all scoped)"
    )


class AgentTestResult(BaseModel):
    """Result from agent test evaluation.

    WHAT: What would happen if agent ran
    WHY: Preview agent behavior
    """

    entity_id: UUID
    entity_name: str
    condition_result: bool
    condition_explanation: str
    would_trigger: bool
    trigger_explanation: str
    observations: dict


class AgentTestResponse(BaseModel):
    """Response from agent test.

    WHAT: Test results for all evaluated entities
    WHY: Show what agent would do
    """

    agent_id: UUID
    results: List[AgentTestResult]
    summary: str


# --- AI/NL Parsing Schemas ---


class AgentParseNaturalRequest(BaseModel):
    """Request to parse natural language to agent config.

    WHAT: Natural language description of desired agent
    WHY: Create agents via Copilot conversationally
    """

    description: str = Field(
        description="Natural language description of agent behavior",
        example="Alert me when CPC goes above $2 on my Meta campaigns for 2 days",
    )


class AgentParseNaturalResponse(BaseModel):
    """Response with parsed agent configuration.

    WHAT: Agent config derived from natural language
    WHY: Pre-fill wizard with parsed config
    """

    success: bool
    config: Optional[AgentCreate] = None
    suggested_name: Optional[str] = None
    clarification_needed: Optional[str] = Field(
        None, description="Question if input was ambiguous"
    )
    error: Optional[str] = None


class AgentGenerateNameRequest(BaseModel):
    """Request to generate agent name from config.

    WHAT: Agent configuration to name
    WHY: Auto-generate descriptive names
    """

    condition: dict
    actions: List[dict]
    scope_type: AgentScopeTypeEnum


class AgentGenerateNameResponse(BaseModel):
    """Response with generated name.

    WHAT: Suggested name for agent
    WHY: User can accept or modify
    """

    name: str
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative name suggestions"
    )


# --- Agent Stats and Workspace Events Schemas ---


class AgentStatsResponse(BaseModel):
    """Aggregate stats for all agents in workspace.

    WHAT: Dashboard-level metrics for agent system health
    WHY: Users need quick overview of agent activity

    REFERENCES:
        - GET /v1/agents/stats endpoint
        - ui/components/agents/AgentStatsGrid.jsx
    """

    active_agents: int = Field(description="Count of ACTIVE agents")
    triggers_today: int = Field(description="Count of triggers in last 24 hours")
    evaluations_this_hour: int = Field(description="Count of evaluations in last hour")
    errors_today: int = Field(
        description="Count of ERROR status agents or failed evaluations today"
    )


class WorkspaceAgentEventOut(BaseModel):
    """Evaluation event for workspace-level notification feed.

    WHAT: Simplified event representation for notification feed
    WHY: Dashboard shows all events across all agents

    REFERENCES:
        - GET /v1/agents/events endpoint
        - ui/components/agents/NotificationFeed.jsx
    """

    id: UUID
    agent_id: UUID
    agent_name: str
    entity_id: UUID
    entity_name: str
    entity_provider: str
    result_type: AgentResultTypeEnum
    headline: str
    evaluated_at: datetime
    # Include action info for rollback capability
    actions_executed: List["WorkspaceAgentActionSummary"] = Field(
        default_factory=list, description="Actions executed for this event"
    )

    model_config = {"from_attributes": True}


class WorkspaceAgentActionSummary(BaseModel):
    """Summary of action execution for notification feed.

    WHAT: Minimal action info needed for rollback UI
    WHY: Show rollback button on events that have reversible actions
    """

    id: UUID
    action_type: str
    success: bool
    description: str
    rollback_possible: bool
    rollback_executed_at: Optional[datetime] = None
    state_before: Optional[dict] = None
    state_after: Optional[dict] = None

    model_config = {"from_attributes": True}


class WorkspaceAgentEventsResponse(BaseModel):
    """Response for workspace-level agent events.

    WHAT: Paginated events with cursor for infinite scroll
    WHY: Notification feed uses infinite scroll pattern
    """

    events: List[WorkspaceAgentEventOut]
    total: int
    next_cursor: Optional[str] = Field(
        None, description="Cursor for next page (ISO datetime of last event)"
    )


class ActionRollbackRequest(BaseModel):
    """Request to rollback an action.

    WHAT: Optional reason for rollback
    WHY: Audit trail for rollback operations
    """

    reason: Optional[str] = Field(None, description="Reason for rollback")


class ActionRollbackResponse(BaseModel):
    """Response from action rollback.

    WHAT: Confirmation of rollback with details
    WHY: User needs to know rollback succeeded
    """

    success: bool
    action_id: UUID
    action_type: str
    state_before: dict = Field(description="State that was restored")
    state_after: dict = Field(description="State that was rolled back from")
    message: str


# Resolve forward references for nested models
WorkspaceMemberOutLite.model_rebuild()
WorkspaceMemberOut.model_rebuild()
WorkspaceInviteOut.model_rebuild()
UserOut.model_rebuild()
WorkspaceAgentEventOut.model_rebuild()
