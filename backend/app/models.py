"""SQLAlchemy ORM models and enums.

This module defines the domain schema using UUID primary keys and explicit
relationships. Authentication secrets are stored in a separate
`auth_credentials` table to keep the domain `users` table clean.
"""

import uuid
from datetime import datetime
import enum

from sqlalchemy import Column, String, DateTime, Enum, Integer, ForeignKey, Numeric, JSON, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base


# Single Base used by the entire application
Base = declarative_base()


# Enums ---------------------------------------------------------

class RoleEnum(str, enum.Enum):
    owner = "Owner"
    admin = "Admin"
    viewer = "Viewer"

class InviteStatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class ProviderEnum(str, enum.Enum):
    google = "google"
    meta = "meta"
    tiktok = "tiktok"
    other = "other"


class LevelEnum(str, enum.Enum):
    account = "account"
    campaign = "campaign"
    adset = "adset"
    ad = "ad"
    creative = "creative"
    unknown = "unknown"


class KindEnum(str, enum.Enum):
    snapshot = "snapshot"
    eod = "eod"


class ComputeRunTypeEnum(str, enum.Enum):
    snapshot = "snapshot"
    eod = "eod"
    backfill = "backfill"


class GoalEnum(str, enum.Enum):
    """Campaign/entity objective type.
    
    Used to determine which derived metrics are most relevant:
    - awareness: Focus on CPM, impressions, reach
    - traffic: Focus on CPC, CTR, clicks
    - leads: Focus on CPL, lead volume
    - app_installs: Focus on CPI, install volume
    - purchases: Focus on CPP, AOV, purchase volume
    - conversions: Focus on CPA, CVR, ROAS (generic conversions)
    - other: No specific objective
    """
    awareness = "awareness"
    traffic = "traffic"
    leads = "leads"
    app_installs = "app_installs"
    purchases = "purchases"
    conversions = "conversions"
    other = "other"


# Core models ----------------------------------------------------

class Workspace(Base):
    """Workspace represents a company/organization account.
    
    A workspace is the top-level container that groups all resources
    for a specific company. All data (connections, entities, metrics)
    belongs to a workspace.
    
    Current relationship: One workspace can have many users (ONE-to-MANY)
    TODO: Should be MANY-to-MANY (users can belong to multiple workspaces)
    """
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships - these create reverse lookups
    users = relationship("User", back_populates="workspace")  # Active workspace for the user (legacy single workspace)
    memberships = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    invites = relationship("WorkspaceInvite", back_populates="workspace", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="workspace")  # All ad platform connections
    entities = relationship("Entity", back_populates="workspace")  # All entities (campaigns, ads, etc)
    compute_runs = relationship("ComputeRun", back_populates="workspace")  # All compute runs
    queries = relationship("QaQueryLog", back_populates="workspace")  # All queries made in workspace
    manual_costs = relationship("ManualCost", back_populates="workspace")  # All manual costs (non-ad costs)
    
    # This is used to display the model in the admin interface.
    def __str__(self):
        return self.name


class User(Base):
    """User represents a person who can access the system.
    
    Users authenticate via email/password and belong to workspaces.
    Each user has a role (Owner, Admin, Viewer) within their workspace.
    
    CURRENT ISSUE: User can only belong to ONE workspace (via workspace_id)
    This should be changed to MANY-to-MANY relationship.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(Enum(RoleEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)

    # Profile fields
    avatar_url = Column(String, nullable=True)

    # Security / Verification fields
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    
    # Password Reset
    reset_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    # Active workspace context (legacy single-workspace field; now treated as "active workspace")
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    workspace = relationship("Workspace", back_populates="users")
    memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")

    # 1:1 credential for local password-based auth
    credential = relationship("AuthCredential", back_populates="user", uselist=False)

    # All queries made by this user
    queries = relationship("QaQueryLog", back_populates="user")

    # All feedback provided by this user
    qa_feedback = relationship("QaFeedback", back_populates="user")

    # This is used to display the model in the admin interface.
    def __str__(self):
        return f"{self.name} ({self.email})"


class WorkspaceMember(Base):
    """Join table mapping users to workspaces with a role.
    
    NOTE: We retain the `users.workspace_id` field as the active workspace pointer for compatibility.
    """
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(Enum(RoleEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(String, default="active")  # active, removed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class WorkspaceInvite(Base):
    """Pending invites for existing users (email-based)."""
    __tablename__ = "workspace_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False)
    role = Column(Enum(RoleEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(Enum(InviteStatusEnum, values_callable=lambda obj: [e.value for e in obj]), default=InviteStatusEnum.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="invites")


class Connection(Base):
    """Connection represents a link to an advertising platform account.
    
    Each connection belongs to ONE workspace. When you create a connection
    in the admin panel, you MUST select which workspace it belongs to.
    
    Examples: Google Ads account, Facebook Ads account, TikTok Ads account
    """
    __tablename__ = "connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(ProviderEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    external_account_id = Column(String, nullable=False)  # The account ID in the external platform
    name = Column(String, nullable=False)  # Friendly name for this connection
    status = Column(String, nullable=False)  # active, paused, disconnected, etc.
    connected_at = Column(DateTime, default=datetime.utcnow)

    # Google-specific connection metadata (also useful across providers)
    # WHAT: Persist account timezone and currency for accurate windowing/formatting
    # WHY: Google Ads stats and segments are in account timezone; currency is set per account
    # REFERENCES: docs/living-docs/GOOGLE_INTEGRATION_STATUS.MD (Date & timezone, Currency model)
    timezone = Column(String, nullable=True)
    currency_code = Column(String, nullable=True)

    # Sync automation tracking
    # WHAT: Fields for managing near-realtime sync jobs and tracking sync health
    # WHY: Users need control over sync frequency and visibility into sync status
    # REFERENCES: docs/living-docs/REALTIME_SYNC_STATUS.md
    sync_frequency = Column(
        String,
        default="manual",
    )  # manual, 5min, 10min, 30min, hourly, daily (realtime reserved via docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md)
    last_sync_attempted_at = Column(DateTime, nullable=True)  # Last sync start (success or failure)
    last_sync_completed_at = Column(DateTime, nullable=True)  # Last successful completion
    last_metrics_changed_at = Column(DateTime, nullable=True)  # Last actual data change (freshness)
    total_syncs_attempted = Column(Integer, default=0)  # Counter: all attempts
    total_syncs_with_changes = Column(Integer, default=0)  # Counter: syncs with DB writes
    sync_status = Column(String, default="idle")  # idle, syncing, error
    last_sync_error = Column(Text, nullable=True)  # Error message from last failure

    # Foreign key - EVERY connection belongs to exactly ONE workspace
    # This ensures data isolation between different companies
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    workspace = relationship("Workspace", back_populates="connections")

    # Optional link to authentication token
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"))
    token = relationship("Token", back_populates="connections")

    # Reverse relationships
    entities = relationship("Entity", back_populates="connection")  # All campaigns/ads from this connection
    fetches = relationship("Fetch", back_populates="connection")  # All data fetch operations
    
    def __str__(self):
        return f"{self.name} ({self.provider.value})"


class Token(Base):
    """Encrypted provider credential bundle.
    
    WHAT:
        Stores Meta tokens (Phase 2.1) with symmetric encryption applied.
    WHY:
        Prevents leaking access/refresh tokens while preserving metadata for future OAuth work.
    REFERENCES:
        - backend/app/security.py (encrypt_secret / decrypt_secret)
        - docs/living-docs/META_INTEGRATION_STATUS.md (Phase 2.1)
    """
    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(ProviderEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    access_token_enc = Column(String, nullable=True)
    refresh_token_enc = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scope = Column(String, nullable=True)
    ad_account_ids = Column(JSON, nullable=True)

    connections = relationship("Connection", back_populates="token")
    
    def __str__(self):
        expires = self.expires_at.strftime('%Y-%m-%d %H:%M') if self.expires_at else 'no-expiry'
        return f"{self.provider.value} token (expires: {expires})"


class Fetch(Base):
    __tablename__ = "fetches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    range_start = Column(DateTime, nullable=True)
    range_end = Column(DateTime, nullable=True)

    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=False)
    connection = relationship("Connection", back_populates="fetches")

    imports = relationship("Import", back_populates="fetch")
    
    def __str__(self):
        return f"{self.kind} ({self.status}) - {self.started_at.strftime('%Y-%m-%d %H:%M')}"


class Import(Base):
    __tablename__ = "imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    as_of = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String, nullable=True)

    fetch_id = Column(UUID(as_uuid=True), ForeignKey("fetches.id"), nullable=False)
    fetch = relationship("Fetch", back_populates="imports")

    facts = relationship("MetricFact", back_populates="import_")
    
    def __str__(self):
        return f"Import as of {self.as_of.strftime('%Y-%m-%d')}{' - ' + self.note if self.note else ''}"


class Entity(Base):
    """Entity represents a marketing entity (campaign, ad set, ad, etc.).
    
    Derived Metrics v1 addition:
    - goal: Campaign objective (awareness, traffic, leads, app_installs, purchases, conversions, other)
    
    WHY goal matters:
    - Helps determine which metrics are most relevant to the user
    - CPL makes sense for leads campaigns, CPI for app_installs, CPP for purchases
    - QA system can recommend metrics based on goal
    - Seed data generates appropriate base measures based on goal
    """
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(Enum(LevelEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    external_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    
    # Derived Metrics v1: Campaign objective
    goal = Column(Enum(GoalEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=True)

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    workspace = relationship("Workspace", back_populates="entities")

    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=True)
    connection = relationship("Connection", back_populates="entities")
    
    # Timestamps for tracking entity lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children = relationship("Entity", backref="parent", remote_side=[id])
    facts = relationship("MetricFact", back_populates="entity")
    pnls = relationship("Pnl", back_populates="entity")
    
    def __str__(self):
        return f"{self.name} ({self.level.value})"


class MetricFact(Base):
    """MetricFact stores RAW BASE MEASURES from ad platforms.
    
    Derived Metrics v1 philosophy:
    - Store ONLY base measures (raw facts from platforms)
    - Compute derived metrics on-demand (executor) or during snapshots (Pnl)
    - Never store computed values here → avoids formula drift over time
    
    Base measures (original):
    - spend, impressions, clicks, conversions, revenue
    
    Base measures (added in Derived Metrics v1):
    - leads: Lead form submissions (Meta Lead Ads, Google Lead Form Extensions)
    - installs: App installations (App Install campaigns)
    - purchases: Purchase events (Conversions API, pixel tracking)
    - visitors: Landing page visitors (from analytics platforms)
    - profit: Net profit (revenue - COGS/costs)
    
    WHY these additions:
    - Enables computing CPL, CPI, CPP, ARPV, POAS, AOV
    - Maintains fact table as wide "base" table (no joins needed)
    - Platform APIs provide these metrics → we store them raw
    
    Related:
    - app/metrics/registry.py: Lists all base measures
    - app/dsl/executor.py: Aggregates these for ad-hoc queries
    - app/services/compute_service.py: Aggregates these for Pnl snapshots
    """
    __tablename__ = "metric_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    provider = Column(Enum(ProviderEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    level = Column(Enum(LevelEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    event_at = Column(DateTime, nullable=False)
    event_date = Column(DateTime, nullable=False)
    
    # Original base measures
    spend = Column(Numeric(18, 4), nullable=False)
    impressions = Column(Integer, nullable=False)
    clicks = Column(Integer, nullable=False)
    conversions = Column(Numeric(18, 4), nullable=True)
    revenue = Column(Numeric(18, 4), nullable=True)
    
    # Derived Metrics v1: New base measures
    leads = Column(Numeric(18, 4), nullable=True)  # Lead form submissions
    installs = Column(Integer, nullable=True)  # App installs
    purchases = Column(Integer, nullable=True)  # Purchase events
    visitors = Column(Integer, nullable=True)  # Landing page visitors
    profit = Column(Numeric(18, 4), nullable=True)  # Net profit (revenue - costs)
    
    currency = Column(String, nullable=False)
    natural_key = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    import_id = Column(UUID(as_uuid=True), ForeignKey("imports.id"), nullable=False)
    import_ = relationship("Import", back_populates="facts")

    entity = relationship("Entity", back_populates="facts")
    
    def __str__(self):
        return f"{self.event_date.strftime('%Y-%m-%d')} - {self.provider.value} - ${self.spend}"


class ComputeRun(Base):
    __tablename__ = "compute_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    as_of = Column(DateTime, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False)
    type = Column(Enum(ComputeRunTypeEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    workspace = relationship("Workspace", back_populates="compute_runs")

    pnls = relationship("Pnl", back_populates="compute_run")
    
    def __str__(self):
        return f"{self.type.value} - {self.as_of.strftime('%Y-%m-%d')} ({self.status})"


class Pnl(Base):
    """Pnl (Profit & Loss) stores SNAPSHOT/EOD aggregations with BOTH base and derived metrics.
    
    Derived Metrics v1 philosophy:
    - Store base measures + derived metrics for FAST dashboard queries
    - Materialize expensive computations (no real-time calculation overhead)
    - "Locked" historical reports → snapshots don't change
    - Can recompute if formulas change (track formula_version if needed)
    
    WHY store derived in Pnl but not MetricFact?
    - Pnl: Snapshot/EOD → performance matters, data is historical
    - MetricFact: Source of truth → keep raw, avoid formula drift
    
    Original columns:
    - Base: spend, revenue, conversions, clicks, impressions
    - Derived: cpa, roas
    
    Derived Metrics v1 additions:
    - Base: leads, installs, purchases, visitors, profit
    - Derived: cpc, cpm, cpl, cpi, cpp, poas, arpv, aov, ctr, cvr
    
    Related:
    - app/services/compute_service.py: Computes these snapshots using app/metrics/registry
    - app/metrics/formulas.py: Pure functions for computing derived metrics
    """
    __tablename__ = "pnls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("compute_runs.id"), nullable=False)
    provider = Column(Enum(ProviderEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    level = Column(Enum(LevelEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    kind = Column(Enum(KindEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    as_of = Column(DateTime, nullable=True)
    event_date = Column(DateTime, nullable=True)
    
    # Original base measures
    spend = Column(Numeric(18, 4), nullable=False)
    revenue = Column(Numeric(18, 4), nullable=True)
    conversions = Column(Numeric(18, 4), nullable=True)
    clicks = Column(Integer, nullable=False)
    impressions = Column(Integer, nullable=False)
    
    # Derived Metrics v1: New base measures
    leads = Column(Numeric(18, 4), nullable=True)
    installs = Column(Integer, nullable=True)
    purchases = Column(Integer, nullable=True)
    visitors = Column(Integer, nullable=True)
    profit = Column(Numeric(18, 4), nullable=True)
    
    # Original derived metrics
    cpa = Column(Numeric(18, 4), nullable=True)
    roas = Column(Numeric(18, 4), nullable=True)
    
    # Derived Metrics v1: New derived metrics (Cost/Efficiency)
    cpc = Column(Numeric(18, 4), nullable=True)  # spend / clicks
    cpm = Column(Numeric(18, 4), nullable=True)  # (spend / impressions) * 1000
    cpl = Column(Numeric(18, 4), nullable=True)  # spend / leads
    cpi = Column(Numeric(18, 4), nullable=True)  # spend / installs
    cpp = Column(Numeric(18, 4), nullable=True)  # spend / purchases
    
    # Derived Metrics v1: New derived metrics (Revenue/Value)
    poas = Column(Numeric(18, 4), nullable=True)  # profit / spend
    arpv = Column(Numeric(18, 4), nullable=True)  # revenue / visitors
    aov = Column(Numeric(18, 4), nullable=True)  # revenue / conversions
    
    # Derived Metrics v1: New derived metrics (Performance/Engagement)
    ctr = Column(Numeric(18, 6), nullable=True)  # clicks / impressions (higher precision)
    cvr = Column(Numeric(18, 6), nullable=True)  # conversions / clicks (higher precision)
    
    computed_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="pnls")
    compute_run = relationship("ComputeRun", back_populates="pnls")
    
    def __str__(self):
        date_str = self.event_date.strftime('%Y-%m-%d') if self.event_date else 'N/A'
        return f"{self.kind.value} P&L - {date_str} - ${self.spend}"


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
    
    # Amount (always in USD - in future when we support multiple currencies, convert to USD before saving)
    amount_dollar = Column(Numeric(12, 2), nullable=False)  # Total cost amount in USD
    
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
        return f"{self.label} ({self.category}): ${self.amount_dollar}"


class QaQueryLog(Base):
    """QaQueryLog tracks all natural language queries made by users.

    When creating a query log in the admin panel:
    1. You MUST select a workspace_id - which workspace was this query made in?
    2. You MUST select a user_id - which user made this query?

    This creates an audit trail of who asked what questions and when.
    """
    __tablename__ = "qa_query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys - BOTH are required to track query context
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    question_text = Column(String, nullable=False)  # The natural language question
    dsl_json = Column(JSON, nullable=False)  # The parsed query structure
    answer_text = Column(Text, nullable=True)  # The generated answer (for feedback tracking)
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)  # How long the query took to execute

    # Relationships for easy access to related objects
    workspace = relationship("Workspace", back_populates="queries")
    user = relationship("User", back_populates="queries")
    feedback = relationship("QaFeedback", back_populates="query_log", uselist=False)

    def __str__(self):
        return f"{self.question_text[:50]}... - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class FeedbackTypeEnum(str, enum.Enum):
    """Type of feedback provided on a QA answer."""
    accuracy = "accuracy"        # Was the data/answer correct?
    relevance = "relevance"      # Did it answer the question asked?
    visualization = "visualization"  # Was the chart/table appropriate?
    completeness = "completeness"    # Was the answer complete enough?
    other = "other"


class QaFeedback(Base):
    """QaFeedback stores user feedback on QA answers for self-learning.

    This enables:
    1. Tracking answer quality over time
    2. Identifying common failure patterns
    3. Building few-shot examples from highly-rated answers
    4. Continuous improvement of the QA system
    """
    __tablename__ = "qa_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the original query
    query_log_id = Column(UUID(as_uuid=True), ForeignKey("qa_query_logs.id"), nullable=False)

    # Who provided the feedback
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Feedback data
    rating = Column(Integer, nullable=False)  # 1-5 scale (1=bad, 5=excellent)
    feedback_type = Column(Enum(FeedbackTypeEnum), nullable=True)  # What aspect is feedback about
    comment = Column(Text, nullable=True)  # Optional free-text comment
    corrected_answer = Column(Text, nullable=True)  # What should the answer have been

    # Self-learning flags
    is_few_shot_example = Column(Boolean, default=False)  # Mark as training example
    reviewed_at = Column(DateTime, nullable=True)  # When admin reviewed this feedback

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    query_log = relationship("QaQueryLog", back_populates="feedback")
    user = relationship("User", back_populates="qa_feedback")

    def __str__(self):
        return f"Feedback {self.rating}/5 for query {self.query_log_id}"


# Local auth credential (password hash stored separately) ----------

class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credential")
    
    def __str__(self):
        return f"Credential for {self.user.email if self.user else 'Unknown'}"
