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
    shopify = "shopify"  # Shopify e-commerce platform for orders, products, customers
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

    # Attribution engine: Web Pixel ID for Shopify connections
    # WHAT: Stores the Shopify web pixel ID after activation
    # WHY: Need to track which pixel is activated for this store
    # REFERENCES: docs/living-docs/ATTRIBUTION_ENGINE.md
    web_pixel_id = Column(String, nullable=True)

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


class MediaTypeEnum(str, enum.Enum):
    """Type of creative media asset."""
    image = "image"
    video = "video"
    carousel = "carousel"
    unknown = "unknown"


class Entity(Base):
    """Entity represents a marketing entity (campaign, ad set, ad, etc.).

    Derived Metrics v1 addition:
    - goal: Campaign objective (awareness, traffic, leads, app_installs, purchases, conversions, other)

    Creative Support (v2.5):
    - thumbnail_url: URL to creative thumbnail image (for ad-level entities)
    - image_url: URL to full creative image (for ad-level entities)
    - media_type: Type of creative (image, video, carousel)

    Note: Creative images currently only supported for Meta ads.

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

    # Creative Support v2.5: Image URLs for ad creatives (Meta only for now)
    thumbnail_url = Column(String, nullable=True)  # Small preview image
    image_url = Column(String, nullable=True)  # Full-size creative image
    media_type = Column(Enum(MediaTypeEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=True)

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


# =============================================================================
# SHOPIFY E-COMMERCE MODELS
# =============================================================================
# WHAT: Dedicated tables for Shopify store data (shops, products, customers, orders)
# WHY: Shopify data structure differs from ad platforms - needs separate schema
#      for LTV calculations, profit tracking (COGS), and revenue analytics
# REFERENCES:
#   - Shopify GraphQL Admin API: https://shopify.dev/docs/api/admin-graphql
#   - Implementation plan: docs/living-docs/SHOPIFY_INTEGRATION_PLAN.md


class ShopifyFinancialStatusEnum(str, enum.Enum):
    """Shopify order financial status.

    WHAT: Represents payment state of an order
    WHY: Track payment lifecycle for accurate revenue reporting
    REFERENCES: https://shopify.dev/docs/api/admin-graphql/2024-07/enums/OrderDisplayFinancialStatus
    """
    pending = "pending"
    authorized = "authorized"
    partially_paid = "partially_paid"
    paid = "paid"
    partially_refunded = "partially_refunded"
    refunded = "refunded"
    voided = "voided"


class ShopifyFulfillmentStatusEnum(str, enum.Enum):
    """Shopify order fulfillment status.

    WHAT: Represents shipping/delivery state of an order
    WHY: Track order lifecycle for operational reporting
    REFERENCES: https://shopify.dev/docs/api/admin-graphql/2024-07/enums/OrderDisplayFulfillmentStatus
    """
    unfulfilled = "unfulfilled"
    partial = "partial"
    fulfilled = "fulfilled"
    restocked = "restocked"
    pending_fulfillment = "pending_fulfillment"
    open = "open"
    in_progress = "in_progress"
    on_hold = "on_hold"
    scheduled = "scheduled"


class ShopifyShop(Base):
    """Shopify store metadata - one per Connection.

    WHAT: Stores Shopify shop configuration and metadata
    WHY: Each Connection links to exactly one Shopify shop; we need shop-level
         settings like timezone and currency for accurate metric calculations
    REFERENCES:
        - Shopify Shop API: https://shopify.dev/docs/api/admin-graphql/2024-07/objects/Shop
        - Similar pattern: Connection model stores external_account_id
    """
    __tablename__ = "shopify_shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Workspace scoping (required for data isolation)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Link to Connection (one shop per connection)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("connections.id"), nullable=False, unique=True)

    # Shopify identifiers
    external_shop_id = Column(String, nullable=False)  # Shopify's internal shop ID (gid://shopify/Shop/xxx)
    shop_domain = Column(String, nullable=False)  # e.g., "mystore.myshopify.com"
    shop_name = Column(String, nullable=False)  # Display name from Shopify

    # Shop settings (for metric calculations)
    currency = Column(String, nullable=False, default="USD")  # ISO currency code
    timezone = Column(String, nullable=True)  # IANA timezone (e.g., "America/New_York")
    country_code = Column(String, nullable=True)  # ISO country code

    # Shop metadata
    plan_name = Column(String, nullable=True)  # Shopify plan (Basic, Shopify, Advanced, Plus)
    email = Column(String, nullable=True)  # Shop contact email

    # Sync tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)

    # Relationships
    connection = relationship("Connection", backref="shopify_shop")
    products = relationship("ShopifyProduct", back_populates="shop", cascade="all, delete-orphan")
    customers = relationship("ShopifyCustomer", back_populates="shop", cascade="all, delete-orphan")
    orders = relationship("ShopifyOrder", back_populates="shop", cascade="all, delete-orphan")

    def __str__(self):
        return f"{self.shop_name} ({self.shop_domain})"


class ShopifyProduct(Base):
    """Product catalog with COGS from metafields.

    WHAT: Stores Shopify product data including cost information for profit calculations
    WHY: Need product-level cost (COGS) to calculate true profit per order
         Cost comes from: 1) inventoryItem.unitCost 2) custom metafield 3) None (user warned)
    REFERENCES:
        - Shopify Product API: https://shopify.dev/docs/api/admin-graphql/2024-07/objects/Product
        - Cost metafield: https://shopify.dev/docs/apps/selling-strategies/pricing/cost-per-item
    """
    __tablename__ = "shopify_products"
    __table_args__ = (
        UniqueConstraint("shop_id", "external_product_id", name="uq_shopify_product"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Workspace scoping
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Link to shop
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shopify_shops.id"), nullable=False)

    # Shopify identifiers
    external_product_id = Column(String, nullable=False)  # gid://shopify/Product/xxx
    handle = Column(String, nullable=True)  # URL-friendly handle

    # Product info
    title = Column(String, nullable=False)
    product_type = Column(String, nullable=True)  # e.g., "T-Shirt", "Electronics"
    vendor = Column(String, nullable=True)  # Brand/manufacturer
    status = Column(String, nullable=False, default="active")  # active, archived, draft

    # Pricing (representative price - variants may differ)
    price = Column(Numeric(18, 4), nullable=True)  # Primary variant price
    compare_at_price = Column(Numeric(18, 4), nullable=True)  # Original price (for sales)

    # COGS - Cost of Goods Sold (critical for profit calculation)
    # WHAT: Product cost used to calculate profit = revenue - COGS
    # WHY: Without COGS, we can only report revenue, not actual profit
    # PRIORITY: 1) variant.inventoryItem.unitCost 2) metafield 3) None (QA warns user)
    cost_per_item = Column(Numeric(18, 4), nullable=True)  # From metafield or inventory item
    cost_source = Column(String, nullable=True)  # "inventory_item", "metafield", "manual", None

    # Inventory (for future use)
    total_inventory = Column(Integer, nullable=True)  # Sum across all variants

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shopify_created_at = Column(DateTime, nullable=True)  # When created in Shopify
    shopify_updated_at = Column(DateTime, nullable=True)  # When updated in Shopify

    # Relationships
    shop = relationship("ShopifyShop", back_populates="products")
    line_items = relationship("ShopifyOrderLineItem", back_populates="product")

    def __str__(self):
        return f"{self.title} (${self.price})"


class ShopifyCustomer(Base):
    """Customer master for LTV calculations.

    WHAT: Stores Shopify customer data with aggregated order stats
    WHY: Customer-level metrics enable LTV (Lifetime Value) calculations
         LTV = total_spent / customer_count (average lifetime value)
    REFERENCES:
        - Shopify Customer API: https://shopify.dev/docs/api/admin-graphql/2024-07/objects/Customer
        - LTV calculation: revenue per customer over their entire history
    """
    __tablename__ = "shopify_customers"
    __table_args__ = (
        UniqueConstraint("shop_id", "external_customer_id", name="uq_shopify_customer"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Workspace scoping
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Link to shop
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shopify_shops.id"), nullable=False)

    # Shopify identifiers
    external_customer_id = Column(String, nullable=False)  # gid://shopify/Customer/xxx

    # Customer info (PII - handle with care)
    email = Column(String, nullable=True)  # May be null for guest checkouts
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    # Customer state
    state = Column(String, nullable=True)  # enabled, disabled, invited, declined
    verified_email = Column(Boolean, default=False)
    accepts_marketing = Column(Boolean, default=False)

    # LTV metrics (aggregated from orders)
    # WHAT: Pre-computed customer lifetime stats
    # WHY: Avoid expensive aggregation queries; update on each order sync
    total_spent = Column(Numeric(18, 4), default=0)  # Sum of all order totals
    order_count = Column(Integer, default=0)  # Number of orders
    average_order_value = Column(Numeric(18, 4), nullable=True)  # total_spent / order_count

    # Temporal metrics (for cohort analysis)
    first_order_at = Column(DateTime, nullable=True)  # Date of first purchase
    last_order_at = Column(DateTime, nullable=True)  # Date of most recent purchase

    # Tags and segments
    tags = Column(JSON, nullable=True)  # Shopify customer tags

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shopify_created_at = Column(DateTime, nullable=True)

    # Relationships
    shop = relationship("ShopifyShop", back_populates="customers")
    orders = relationship("ShopifyOrder", back_populates="customer")

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip() or "Guest"
        return f"{name} ({self.email or 'No email'}) - ${self.total_spent}"


class ShopifyOrder(Base):
    """Order facts with attribution and line items.

    WHAT: Stores Shopify order data including totals, status, and attribution
    WHY: Orders are the source of truth for revenue and profit metrics
         Attribution fields (utm_*, source_name) enable channel tracking
    REFERENCES:
        - Shopify Order API: https://shopify.dev/docs/api/admin-graphql/2024-07/objects/Order
        - Only last 60 days accessible by default; need read_all_orders scope for historical
    """
    __tablename__ = "shopify_orders"
    __table_args__ = (
        UniqueConstraint("shop_id", "external_order_id", name="uq_shopify_order"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Workspace scoping
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Link to shop
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shopify_shops.id"), nullable=False)

    # Link to customer (nullable for guest checkouts)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("shopify_customers.id"), nullable=True)

    # Shopify identifiers
    external_order_id = Column(String, nullable=False)  # gid://shopify/Order/xxx
    order_number = Column(Integer, nullable=True)  # Human-readable order number (#1001)
    name = Column(String, nullable=True)  # Display name (e.g., "#1001")

    # Order totals (in shop currency)
    total_price = Column(Numeric(18, 4), nullable=False)  # Final total including tax/shipping
    subtotal_price = Column(Numeric(18, 4), nullable=True)  # Before tax/shipping
    total_tax = Column(Numeric(18, 4), nullable=True)
    total_shipping = Column(Numeric(18, 4), nullable=True)
    total_discounts = Column(Numeric(18, 4), nullable=True)
    currency = Column(String, nullable=False, default="USD")

    # Profit calculation (computed from line items)
    # WHAT: Pre-computed profit for fast queries
    # WHY: Avoid joins to line_items for aggregate profit queries
    total_cost = Column(Numeric(18, 4), nullable=True)  # Sum of line item costs
    total_profit = Column(Numeric(18, 4), nullable=True)  # subtotal - total_cost
    has_missing_costs = Column(Boolean, default=False)  # True if any line item missing COGS

    # Order status
    financial_status = Column(
        Enum(ShopifyFinancialStatusEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True
    )
    fulfillment_status = Column(
        Enum(ShopifyFulfillmentStatusEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True
    )
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String, nullable=True)

    # Attribution (Phase 1: basic UTM tracking)
    # WHAT: Where did this order come from?
    # WHY: Connect revenue to marketing channels (even without full attribution engine)
    # NOTE: Full attribution engine planned for Phase 2
    source_name = Column(String, nullable=True)  # e.g., "web", "pos", "mobile"
    landing_site = Column(String, nullable=True)  # Full landing page URL with UTMs
    referring_site = Column(String, nullable=True)  # Referrer URL

    # Extracted UTM params (parsed from landing_site for easy querying)
    utm_source = Column(String, nullable=True)  # e.g., "facebook", "google", "email"
    utm_medium = Column(String, nullable=True)  # e.g., "cpc", "social", "newsletter"
    utm_campaign = Column(String, nullable=True)  # Campaign name
    utm_content = Column(String, nullable=True)  # Ad content identifier
    utm_term = Column(String, nullable=True)  # Search term (for PPC)

    # Additional metadata
    app_name = Column(String, nullable=True)  # App that created the order
    tags = Column(JSON, nullable=True)  # Order tags
    note = Column(Text, nullable=True)  # Order notes

    # Attribution engine: checkout_token for journey linking
    # WHAT: Token from Shopify checkout, used to link pixel journey to order
    # WHY: Pixel sends checkout_token on checkout_completed; webhook has same token
    checkout_token = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)  # When synced to our DB
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    order_created_at = Column(DateTime, nullable=False)  # When order was placed in Shopify
    order_processed_at = Column(DateTime, nullable=True)  # When order was processed
    order_closed_at = Column(DateTime, nullable=True)  # When order was closed

    # Relationships
    shop = relationship("ShopifyShop", back_populates="orders")
    customer = relationship("ShopifyCustomer", back_populates="orders")
    line_items = relationship("ShopifyOrderLineItem", back_populates="order", cascade="all, delete-orphan")

    def __str__(self):
        return f"Order {self.name or self.external_order_id} - ${self.total_price}"


class ShopifyOrderLineItem(Base):
    """Line items linking orders to products with cost tracking.

    WHAT: Individual items within an order with quantity, price, and cost
    WHY: Line-item level cost tracking enables accurate profit calculation
         profit = (price * quantity) - (cost_per_item * quantity) - total_discount
    REFERENCES:
        - Shopify LineItem API: https://shopify.dev/docs/api/admin-graphql/2024-07/objects/LineItem
        - Cost from variant.inventoryItem.unitCost or product metafield
    """
    __tablename__ = "shopify_order_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to order (required)
    order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=False)

    # Link to product (nullable - product may be deleted)
    product_id = Column(UUID(as_uuid=True), ForeignKey("shopify_products.id"), nullable=True)

    # Shopify identifiers
    external_line_item_id = Column(String, nullable=False)  # gid://shopify/LineItem/xxx
    external_product_id = Column(String, nullable=True)  # Store even if product deleted
    external_variant_id = Column(String, nullable=True)

    # Item details
    title = Column(String, nullable=False)  # Product title at time of order
    variant_title = Column(String, nullable=True)  # Variant name (e.g., "Large / Blue")
    sku = Column(String, nullable=True)

    # Quantity and pricing
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(18, 4), nullable=False)  # Unit price
    total_discount = Column(Numeric(18, 4), default=0)  # Discount on this line

    # COGS tracking (critical for profit)
    # WHAT: Cost per item at time of order
    # WHY: Product cost may change; we snapshot cost at order time for accurate profit
    cost_per_item = Column(Numeric(18, 4), nullable=True)  # From inventory or metafield
    cost_source = Column(String, nullable=True)  # "inventory_item", "metafield", "product", None

    # Computed profit for this line (price * qty - cost * qty - discount)
    line_profit = Column(Numeric(18, 4), nullable=True)

    # Fulfillment tracking
    fulfillable_quantity = Column(Integer, nullable=True)
    fulfillment_status = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("ShopifyOrder", back_populates="line_items")
    product = relationship("ShopifyProduct", back_populates="line_items")

    def __str__(self):
        return f"{self.title} x{self.quantity} @ ${self.price}"


# =============================================================================
# ATTRIBUTION ENGINE MODELS
# =============================================================================
# WHAT: Models for tracking customer journeys and attributing orders to campaigns
# WHY: Bridges the gap between ad spend and revenue by tracking customer journeys
#      from first ad click through purchase
# REFERENCES:
#   - docs/living-docs/ATTRIBUTION_ENGINE.md
#   - Shopify Web Pixels API: https://shopify.dev/docs/api/web-pixels-api


class PixelEvent(Base):
    """Immutable raw event log from web pixel (event sourcing).

    WHAT: Stores every event from the Shopify Web Pixel Extension
    WHY: Never lose data; can recompute journeys if attribution logic changes
    REFERENCES:
        - Shopify Web Pixels API: https://shopify.dev/docs/api/web-pixels-api
        - docs/living-docs/ATTRIBUTION_ENGINE.md
    """
    __tablename__ = "pixel_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    visitor_id = Column(String, nullable=False)

    # Client-generated UUID for deduplication
    event_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, default={})

    # Attribution fields (denormalized for fast queries)
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    utm_content = Column(String, nullable=True)
    utm_term = Column(String, nullable=True)
    fbclid = Column(String, nullable=True)
    gclid = Column(String, nullable=True)
    ttclid = Column(String, nullable=True)
    landing_page = Column(String, nullable=True)

    # Context
    url = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    ip_hash = Column(String, nullable=True)  # Hashed for privacy

    created_at = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"{self.event_type} - {self.visitor_id} - {self.created_at}"


class CustomerJourney(Base):
    """Tracks visitors across sessions for attribution.

    WHAT: Aggregates visitor activity across sessions
    WHY: One visitor can make multiple purchases over time (journey 1:N orders)
         Links pixel events to orders via checkout_token or email
    REFERENCES:
        - docs/living-docs/ATTRIBUTION_ENGINE.md
    """
    __tablename__ = "customer_journeys"
    __table_args__ = (
        UniqueConstraint("workspace_id", "visitor_id", name="uq_journey_visitor"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Identity
    visitor_id = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    shopify_customer_id = Column(Integer, nullable=True)

    # For linking to orders (most recent checkout)
    checkout_token = Column(String, nullable=True)

    # First touch attribution (captured on first visit)
    first_touch_source = Column(String, nullable=True)
    first_touch_medium = Column(String, nullable=True)
    first_touch_campaign = Column(String, nullable=True)
    first_touch_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)

    # Last touch (updated on each touchpoint)
    last_touch_source = Column(String, nullable=True)
    last_touch_medium = Column(String, nullable=True)
    last_touch_campaign = Column(String, nullable=True)
    last_touch_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)

    # Journey state
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    touchpoint_count = Column(Integer, default=0)

    # Conversion tracking
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Numeric(12, 2), default=0)
    first_order_at = Column(DateTime, nullable=True)
    last_order_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    touchpoints = relationship("JourneyTouchpoint", back_populates="journey", cascade="all, delete-orphan")
    attributions = relationship("Attribution", back_populates="journey")

    def __str__(self):
        return f"Journey {self.visitor_id} - {self.touchpoint_count} touchpoints"


class JourneyTouchpoint(Base):
    """Each marketing interaction (UTMs, click IDs).

    WHAT: Records each marketing touchpoint in a customer journey
    WHY: Attribution models need all touchpoints to determine credit
    REFERENCES:
        - docs/living-docs/ATTRIBUTION_ENGINE.md
    """
    __tablename__ = "journey_touchpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journey_id = Column(UUID(as_uuid=True), ForeignKey("customer_journeys.id", ondelete="CASCADE"), nullable=False)

    # Event info
    event_type = Column(String, nullable=False)

    # Attribution params
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    utm_content = Column(String, nullable=True)
    utm_term = Column(String, nullable=True)
    fbclid = Column(String, nullable=True)
    gclid = Column(String, nullable=True)
    ttclid = Column(String, nullable=True)

    # Resolved entity (if matched)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    provider = Column(String, nullable=True)

    # Context
    landing_page = Column(String, nullable=True)
    referrer = Column(String, nullable=True)

    touched_at = Column(DateTime, nullable=False)

    # Relationships
    journey = relationship("CustomerJourney", back_populates="touchpoints")
    entity = relationship("Entity")

    def __str__(self):
        source = self.utm_source or self.provider or "unknown"
        return f"{self.event_type} from {source} at {self.touched_at}"


class AttributionModelEnum(str, enum.Enum):
    """Attribution model types."""
    first_click = "first_click"
    last_click = "last_click"
    linear = "linear"


class AttributionConfidenceEnum(str, enum.Enum):
    """Attribution confidence levels."""
    high = "high"      # gclid resolved, exact UTM match
    medium = "medium"  # fbclid, partial UTM match
    low = "low"        # utm_source only, referrer inference
    none = "none"      # No attribution data


class Attribution(Base):
    """Final attribution records linking orders to entities.

    WHAT: Stores the result of attribution processing
    WHY: Fast dashboard queries for attributed revenue by campaign/ad
    REFERENCES:
        - docs/living-docs/ATTRIBUTION_ENGINE.md
    """
    __tablename__ = "attributions"
    __table_args__ = (
        # One attribution per order per model
        UniqueConstraint("shopify_order_id", "attribution_model", name="uq_attribution_order_model"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    # Links
    journey_id = Column(UUID(as_uuid=True), ForeignKey("customer_journeys.id"), nullable=True)
    shopify_order_id = Column(UUID(as_uuid=True), ForeignKey("shopify_orders.id"), nullable=True)

    # Attribution result
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    # Provider: meta, google, tiktok, direct, organic, unknown
    provider = Column(String, nullable=False)
    # Entity level: campaign, adset, ad (NULL if no entity match)
    entity_level = Column(String, nullable=True)

    # Match info
    # match_type: gclid, utm_campaign, utm_content, fbclid, utm_source, referrer, none
    match_type = Column(String, nullable=False)
    # confidence: high, medium, low, none
    confidence = Column(String, nullable=False)
    attribution_model = Column(String, nullable=False, default="last_click")
    attribution_window_days = Column(Integer, default=30)

    # Revenue (stored in order's original currency)
    attributed_revenue = Column(Numeric(12, 2), nullable=True)
    # For multi-touch (0.0-1.0)
    attribution_credit = Column(Numeric(5, 4), default=1.0)
    currency = Column(String, nullable=False, default="USD")

    # Timestamps
    order_created_at = Column(DateTime, nullable=True)
    attributed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    journey = relationship("CustomerJourney", back_populates="attributions")
    shopify_order = relationship("ShopifyOrder", backref="attributions")
    entity = relationship("Entity")

    def __str__(self):
        entity_name = self.entity.name if self.entity else self.provider
        return f"Attribution to {entity_name} ({self.match_type}, {self.confidence})"


# Local auth credential (password hash stored separately) ----------

class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credential")
    
    def __str__(self):
        return f"Credential for {self.user.email if self.user else 'Unknown'}"
