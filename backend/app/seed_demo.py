"""
Demo workspace seed script for PRODUCTION database.
Creates comprehensive test data for gabriel@lunesu.co

SAFE FOR PRODUCTION:
- No DELETE operations - only INSERTs
- Finds existing user by email (doesn't create new)
- Creates NEW workspace (doesn't touch existing)
- All data is isolated to the new workspace

Target Metrics:
- $250K/month revenue (~$8,333/day)
- ~3.0 overall ROAS
- Upward trending performance (5% week-over-week improvement)

Usage:
    cd backend
    python -m app.seed_demo
"""

import uuid
import random
import math
from datetime import datetime, date, timedelta, time, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app import models


# =============================================================================
# CONFIGURATION
# =============================================================================

TARGET_EMAIL = "gabriel@lunesu.co"
WORKSPACE_NAME = "Gabriel's Store"
CURRENCY = "USD"

# Revenue targets
MONTHLY_REVENUE = 250_000  # $250K/month
DAILY_REVENUE = MONTHLY_REVENUE / 30  # ~$8,333/day
OVERALL_ROAS = 3.0
DAILY_SPEND = DAILY_REVENUE / OVERALL_ROAS  # ~$2,778/day

# Upward trend: 5% improvement per week
WEEKLY_TREND_IMPROVEMENT = 0.05


# =============================================================================
# CAMPAIGN CONFIGURATIONS
# =============================================================================

GOOGLE_CAMPAIGNS = [
    {
        "name": "Search - Brand Terms",
        "goal": models.GoalEnum.traffic,
        "revenue_share": 0.35,
        "roas": 5.0,
        "ctr_range": (0.06, 0.14),  # High CTR for brand, wider range
        "cvr_range": (0.03, 0.10),
        "cpm_range": (12, 30),
        "ad_groups": [
            {
                "name": "Exact Match Brand",
                "ads": ["RSA Brand - Main", "RSA Brand - Sale"],
            },
            {
                "name": "Phrase Match Brand",
                "ads": ["RSA Brand Phrase 1", "RSA Brand Phrase 2"],
            },
        ],
    },
    {
        "name": "Shopping - Standard",
        "goal": models.GoalEnum.purchases,
        "revenue_share": 0.40,
        "roas": 3.5,
        "ctr_range": (0.008, 0.035),
        "cvr_range": (0.015, 0.06),
        "cpm_range": (6, 18),
        "ad_groups": [
            {
                "name": "All Products",
                "ads": ["Shopping Feed Main", "Shopping Feed Secondary"],
            },
            {
                "name": "Best Sellers",
                "ads": ["Shopping Featured", "Shopping Top Picks"],
            },
        ],
    },
    {
        "name": "Performance Max - E-commerce",
        "goal": models.GoalEnum.purchases,
        "revenue_share": 0.25,
        "roas": 3.0,
        "ctr_range": (0.01, 0.04),
        "cvr_range": (0.02, 0.07),
        "cpm_range": (8, 25),
        "is_pmax": True,
        "asset_groups": [
            {"name": "Best Sellers"},
            {"name": "New Arrivals"},
        ],
    },
]

META_CAMPAIGNS = [
    {
        "name": "Catalog Sales - DPA",
        "goal": models.GoalEnum.purchases,
        "revenue_share": 0.50,
        "roas": 4.0,
        "ctr_range": (0.008, 0.035),
        "cvr_range": (0.02, 0.07),
        "cpm_range": (6, 22),
        "ad_sets": [
            {
                "name": "DPA - All Products",
                "ads": ["DPA Dynamic 1", "DPA Dynamic 2", "DPA Dynamic 3"],
            },
            {"name": "DPA - Retargeting", "ads": ["DPA Retarget 1", "DPA Retarget 2"]},
            {"name": "DPA - Lookalikes", "ads": ["DPA Lookalike 1", "DPA Lookalike 2"]},
        ],
    },
    {
        "name": "Conversions - Prospecting",
        "goal": models.GoalEnum.conversions,
        "revenue_share": 0.30,
        "roas": 2.5,
        "ctr_range": (0.01, 0.04),
        "cvr_range": (0.02, 0.08),
        "cpm_range": (8, 25),
        "ad_sets": [
            {
                "name": "Broad Interests",
                "ads": ["Conversion Ad 1", "Conversion Ad 2", "Conversion Ad 3"],
            },
            {
                "name": "Lookalike Purchasers 1%",
                "ads": ["Lookalike Ad 1", "Lookalike Ad 2"],
            },
        ],
    },
    {
        "name": "Retargeting - Website Visitors",
        "goal": models.GoalEnum.conversions,
        "revenue_share": 0.20,
        "roas": 5.5,
        "ctr_range": (0.015, 0.05),
        "cvr_range": (0.04, 0.12),
        "cpm_range": (10, 30),
        "ad_sets": [
            {
                "name": "Cart Abandoners",
                "ads": ["Retarget Cart 1", "Retarget Cart 2"],
            },
            {
                "name": "Product Viewers",
                "ads": ["Retarget Viewer 1", "Retarget Viewer 2"],
            },
        ],
    },
    {
        "name": "Awareness - Video",
        "goal": models.GoalEnum.awareness,
        "revenue_share": 0.00,  # No direct revenue attribution
        "roas": 0.8,
        "ctr_range": (0.003, 0.015),
        "cvr_range": (0.002, 0.01),
        "cpm_range": (4, 12),
        "ad_sets": [
            {"name": "Video Views - Broad", "ads": ["Brand Video 1", "Brand Video 2"]},
        ],
    },
]

# Shopify products
SHOPIFY_PRODUCTS = [
    # Apparel (8 products)
    {
        "title": "Classic Cotton T-Shirt",
        "type": "Apparel",
        "price": 34.99,
        "cost_pct": 0.30,
        "vendor": "Essential Basics",
    },
    {
        "title": "Premium Hoodie",
        "type": "Apparel",
        "price": 79.99,
        "cost_pct": 0.32,
        "vendor": "Essential Basics",
    },
    {
        "title": "Slim Fit Jeans",
        "type": "Apparel",
        "price": 89.99,
        "cost_pct": 0.35,
        "vendor": "Denim Co",
    },
    {
        "title": "Summer Dress",
        "type": "Apparel",
        "price": 69.99,
        "cost_pct": 0.28,
        "vendor": "Style House",
    },
    {
        "title": "Winter Jacket",
        "type": "Apparel",
        "price": 149.99,
        "cost_pct": 0.38,
        "vendor": "Outerwear Plus",
    },
    {
        "title": "Athletic Shorts",
        "type": "Apparel",
        "price": 44.99,
        "cost_pct": 0.25,
        "vendor": "SportFit",
    },
    {
        "title": "Casual Blazer",
        "type": "Apparel",
        "price": 129.99,
        "cost_pct": 0.35,
        "vendor": "Style House",
    },
    {
        "title": "Yoga Pants",
        "type": "Apparel",
        "price": 59.99,
        "cost_pct": 0.28,
        "vendor": "SportFit",
    },
    # Accessories (5 products)
    {
        "title": "Leather Wallet",
        "type": "Accessories",
        "price": 49.99,
        "cost_pct": 0.25,
        "vendor": "Leather Craft",
    },
    {
        "title": "Canvas Backpack",
        "type": "Accessories",
        "price": 79.99,
        "cost_pct": 0.30,
        "vendor": "Travel Gear",
    },
    {
        "title": "Sunglasses",
        "type": "Accessories",
        "price": 39.99,
        "cost_pct": 0.22,
        "vendor": "Eye Style",
    },
    {
        "title": "Leather Belt",
        "type": "Accessories",
        "price": 44.99,
        "cost_pct": 0.25,
        "vendor": "Leather Craft",
    },
    {
        "title": "Watch",
        "type": "Accessories",
        "price": 149.99,
        "cost_pct": 0.35,
        "vendor": "TimeKeeper",
    },
    # Electronics (4 products)
    {
        "title": "Wireless Earbuds",
        "type": "Electronics",
        "price": 89.99,
        "cost_pct": 0.40,
        "vendor": "TechSound",
    },
    {
        "title": "Portable Charger",
        "type": "Electronics",
        "price": 49.99,
        "cost_pct": 0.38,
        "vendor": "PowerUp",
    },
    {
        "title": "Smart Watch",
        "type": "Electronics",
        "price": 199.99,
        "cost_pct": 0.42,
        "vendor": "TechWear",
    },
    {
        "title": "Bluetooth Speaker",
        "type": "Electronics",
        "price": 79.99,
        "cost_pct": 0.40,
        "vendor": "TechSound",
    },
    # Home (3 products)
    {
        "title": "Scented Candle Set",
        "type": "Home",
        "price": 39.99,
        "cost_pct": 0.20,
        "vendor": "Home Comfort",
    },
    {
        "title": "Throw Blanket",
        "type": "Home",
        "price": 69.99,
        "cost_pct": 0.30,
        "vendor": "Home Comfort",
    },
    {
        "title": "Decorative Pillow",
        "type": "Home",
        "price": 44.99,
        "cost_pct": 0.25,
        "vendor": "Home Comfort",
    },
]

# Customer names for Shopify
CUSTOMER_NAMES = [
    ("Emma", "Johnson"),
    ("Liam", "Williams"),
    ("Olivia", "Brown"),
    ("Noah", "Jones"),
    ("Ava", "Garcia"),
    ("Ethan", "Miller"),
    ("Sophia", "Davis"),
    ("Mason", "Rodriguez"),
    ("Isabella", "Martinez"),
    ("Lucas", "Hernandez"),
    ("Mia", "Lopez"),
    ("Alexander", "Gonzalez"),
    ("Charlotte", "Wilson"),
    ("James", "Anderson"),
    ("Amelia", "Thomas"),
    ("Benjamin", "Taylor"),
    ("Harper", "Moore"),
    ("Elijah", "Jackson"),
    ("Evelyn", "Martin"),
    ("William", "Lee"),
    ("Abigail", "Perez"),
    ("Henry", "Thompson"),
    ("Emily", "White"),
    ("Sebastian", "Harris"),
    ("Elizabeth", "Sanchez"),
    ("Jack", "Clark"),
    ("Sofia", "Ramirez"),
    ("Owen", "Lewis"),
    ("Avery", "Robinson"),
    ("Daniel", "Walker"),
    ("Scarlett", "Young"),
    ("Michael", "Allen"),
    ("Victoria", "King"),
    ("Matthew", "Wright"),
    ("Luna", "Scott"),
    ("David", "Torres"),
    ("Chloe", "Nguyen"),
    ("Joseph", "Hill"),
    ("Penelope", "Flores"),
    ("Samuel", "Green"),
    ("Layla", "Adams"),
    ("John", "Nelson"),
    ("Riley", "Baker"),
    ("Andrew", "Hall"),
    ("Zoey", "Rivera"),
    ("Christopher", "Campbell"),
    ("Nora", "Mitchell"),
    ("Joshua", "Carter"),
    ("Lily", "Roberts"),
    ("Ryan", "Phillips"),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_hourly_curve(hour: int) -> float:
    """Return activity multiplier for given hour (0-23). Peak afternoon/evening."""
    if 0 <= hour < 6:
        return 0.1 + (hour / 10)  # 0.1 to 0.7
    elif 6 <= hour < 12:
        return 0.7 + ((hour - 6) / 6)  # 0.7 to 1.7
    elif 12 <= hour < 18:
        return 1.7 + random.uniform(-0.2, 0.2)  # ~1.7 plateau
    else:  # 18-23
        return 1.7 - ((hour - 18) / 5)  # 1.7 down to 0.7


def apply_trend(day_offset: int) -> float:
    """Apply upward trend based on day offset (30 = oldest, 1 = yesterday).
    5% improvement per week with added daily fluctuations."""
    weeks_ago = day_offset / 7
    # More recent = higher multiplier
    base_trend = 1.0 + (
        WEEKLY_TREND_IMPROVEMENT * (4 - weeks_ago)
    )  # 4 weeks ago vs now

    # Add daily fluctuation (+/- 25%)
    daily_noise = random.uniform(-0.25, 0.25)

    # Add day-of-week effect (weekends slightly lower)
    day_of_week = (30 - day_offset) % 7  # 0=Mon, 6=Sun
    if day_of_week >= 5:  # Weekend
        weekend_effect = random.uniform(-0.15, 0.05)
    else:
        weekend_effect = random.uniform(-0.05, 0.10)

    return base_trend * (1 + daily_noise + weekend_effect)


def generate_campaign_metrics(
    config: dict,
    provider: str,
    day_offset: int,
    provider_daily_revenue: float,
) -> dict:
    """Generate realistic metrics for a campaign based on config with high variance."""

    # Base revenue for this campaign
    base_daily_revenue = provider_daily_revenue * config["revenue_share"]

    # Apply trend (older days have lower metrics) - now includes daily fluctuations
    trend = apply_trend(day_offset)

    # Add campaign-specific random spike/dip days (occasional big wins or losses)
    if random.random() < 0.15:  # 15% chance of a spike day
        spike = random.choice([0.5, 0.6, 1.4, 1.5, 1.8])  # Big dip or big spike
    else:
        spike = 1.0

    daily_revenue = base_daily_revenue * trend * spike

    # Calculate spend from ROAS with much higher variance (+/- 35%)
    roas = config["roas"] * (1 + random.uniform(-0.35, 0.35))

    # Occasionally have terrible or amazing ROAS days
    if random.random() < 0.10:
        roas *= random.choice([0.4, 0.5, 1.6, 2.0])

    daily_spend = daily_revenue / max(roas, 0.5)  # Prevent division issues

    # Calculate impressions from CPM with variance
    cpm = random.uniform(*config["cpm_range"]) * random.uniform(0.7, 1.4)
    impressions = int((daily_spend / max(cpm, 1)) * 1000)

    # Calculate clicks from CTR with variance
    ctr = random.uniform(*config["ctr_range"]) * random.uniform(0.6, 1.5)
    clicks = int(impressions * ctr)

    # Calculate conversions from CVR with variance
    cvr = random.uniform(*config["cvr_range"]) * random.uniform(0.5, 1.6)
    conversions = clicks * cvr

    # Goal-specific metrics
    leads = None
    purchases = None
    installs = None
    visitors = int(clicks * random.uniform(0.75, 0.98))

    goal = config["goal"]
    if goal == models.GoalEnum.leads:
        leads = conversions
    elif goal == models.GoalEnum.purchases:
        purchases = int(conversions)
        conversions = purchases
    elif goal == models.GoalEnum.app_installs:
        installs = int(conversions)
        conversions = installs

    # Profit with variance (20-40% margin)
    profit = daily_revenue * random.uniform(0.20, 0.40)

    return {
        "spend": round(Decimal(str(max(daily_spend, 0))), 4),
        "impressions": max(impressions, 0),
        "clicks": max(clicks, 0),
        "conversions": round(Decimal(str(max(conversions, 0))), 4),
        "revenue": round(Decimal(str(max(daily_revenue, 0))), 4),
        "leads": round(Decimal(str(leads)), 4) if leads else None,
        "purchases": purchases if purchases else None,
        "installs": installs if installs else None,
        "visitors": max(visitors, 0),
        "profit": round(Decimal(str(max(profit, 0))), 4),
    }


def distribute_metrics_to_children(
    parent_metrics: dict, num_children: int
) -> list[dict]:
    """Distribute parent metrics to children with realistic variance."""
    children_metrics = []

    # Generate random weights
    weights = [random.uniform(0.5, 1.5) for _ in range(num_children)]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    for weight in normalized_weights:
        child = {}
        for key, value in parent_metrics.items():
            if value is None:
                child[key] = None
            elif isinstance(value, Decimal):
                child[key] = round(value * Decimal(str(weight)), 4)
            elif isinstance(value, int):
                child[key] = max(1, int(value * weight))
            else:
                child[key] = value
        children_metrics.append(child)

    return children_metrics


def _distribute_metrics_with_variance(parent_metrics: dict, weight: float) -> dict:
    """Distribute a portion of parent metrics to a child with added variance."""
    child = {}

    # Add variance to the weight
    actual_weight = weight * random.uniform(0.6, 1.5)

    for key, value in parent_metrics.items():
        if value is None:
            child[key] = None
        elif isinstance(value, Decimal):
            # Add extra variance for each metric
            metric_variance = random.uniform(0.7, 1.4)
            child[key] = round(value * Decimal(str(actual_weight * metric_variance)), 4)
        elif isinstance(value, int):
            metric_variance = random.uniform(0.7, 1.4)
            child[key] = max(0, int(value * actual_weight * metric_variance))
        else:
            child[key] = value

    return child


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================


def find_or_error_user(db: Session) -> models.User:
    """Find existing user by email. Error if not found."""
    user = db.query(models.User).filter(models.User.email == TARGET_EMAIL).first()
    if not user:
        raise ValueError(
            f"User {TARGET_EMAIL} not found in database. This user must exist first."
        )
    print(f"   Found user: {user.name} ({user.email})")
    return user


def create_workspace(db: Session, user: models.User) -> models.Workspace:
    """Create new demo workspace and link user."""

    # Create workspace
    workspace = models.Workspace(
        id=uuid.uuid4(),
        name=WORKSPACE_NAME,
        created_at=datetime.utcnow(),
        billing_status=models.BillingStatusEnum.active,
        billing_tier=models.BillingPlanEnum.starter,
        onboarding_completed=True,
        onboarding_completed_at=datetime.utcnow(),
        domain="gabriels-store.com",
        domain_description="Premium lifestyle e-commerce store selling apparel, accessories, electronics, and home goods.",
        niche="E-commerce",
        target_markets=["United States", "Canada"],
        brand_voice="Professional",
        business_size="smb",
        intended_ad_providers=["google", "meta"],
    )
    db.add(workspace)
    db.flush()
    print(f"   Created workspace: {workspace.name} ({workspace.id})")

    # Create WorkspaceMember link
    membership = models.WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role=models.RoleEnum.owner,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(membership)

    # Update user's active workspace
    user.workspace_id = workspace.id
    print(f"   Linked user to workspace as Owner")

    return workspace


def create_connections(db: Session, workspace_id: uuid.UUID) -> dict:
    """Create Google, Meta, and Shopify connections."""

    connections = {}

    # Google Ads
    conn_google = models.Connection(
        id=uuid.uuid4(),
        provider=models.ProviderEnum.google,
        external_account_id="DEMO-GOOGLE-8571234567",
        name="Gabriel's Store - Google Ads",
        status="active",
        connected_at=datetime.utcnow() - timedelta(days=60),
        workspace_id=workspace_id,
        timezone="America/New_York",
        currency_code="USD",
        sync_frequency="15min",
        last_sync_completed_at=datetime.utcnow() - timedelta(minutes=5),
        sync_status="idle",
    )
    db.add(conn_google)
    connections["google"] = conn_google

    # Meta Ads
    conn_meta = models.Connection(
        id=uuid.uuid4(),
        provider=models.ProviderEnum.meta,
        external_account_id="act_demo_9876543210",
        name="Gabriel's Store - Meta Ads",
        status="active",
        connected_at=datetime.utcnow() - timedelta(days=60),
        workspace_id=workspace_id,
        timezone="America/New_York",
        currency_code="USD",
        sync_frequency="15min",
        last_sync_completed_at=datetime.utcnow() - timedelta(minutes=5),
        sync_status="idle",
    )
    db.add(conn_meta)
    connections["meta"] = conn_meta

    # Shopify
    conn_shopify = models.Connection(
        id=uuid.uuid4(),
        provider=models.ProviderEnum.shopify,
        external_account_id="demo-gabriels-store.myshopify.com",
        name="Gabriel's Store - Shopify",
        status="active",
        connected_at=datetime.utcnow() - timedelta(days=60),
        workspace_id=workspace_id,
        timezone="America/New_York",
        currency_code="USD",
        sync_frequency="15min",
        last_sync_completed_at=datetime.utcnow() - timedelta(minutes=5),
        sync_status="idle",
    )
    db.add(conn_shopify)
    connections["shopify"] = conn_shopify

    db.flush()
    print(f"   Created 3 connections: Google, Meta, Shopify")

    return connections


def create_google_entities(
    db: Session,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> list[tuple[models.Entity, dict]]:
    """Create Google Ads entity hierarchy. Returns list of (entity, config) tuples."""

    entities = []
    campaign_idx = 0

    for config in GOOGLE_CAMPAIGNS:
        campaign_idx += 1

        # Create campaign
        campaign = models.Entity(
            id=uuid.uuid4(),
            level=models.LevelEnum.campaign,
            external_id=f"DEMO-GCAMP-{campaign_idx:03d}",
            name=config["name"],
            status="active",
            goal=config["goal"],
            workspace_id=workspace_id,
            connection_id=connection_id,
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        db.add(campaign)
        entities.append((campaign, config))

        # Check if PMax (uses asset_groups instead of ad_groups)
        if config.get("is_pmax"):
            for ag_config in config.get("asset_groups", []):
                asset_group = models.Entity(
                    id=uuid.uuid4(),
                    level=models.LevelEnum.asset_group,
                    external_id=f"DEMO-GAG-{uuid.uuid4().hex[:8].upper()}",
                    name=f"{config['name']} - {ag_config['name']}",
                    status="active",
                    parent_id=campaign.id,
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    created_at=datetime.utcnow() - timedelta(days=60),
                )
                db.add(asset_group)
                entities.append((asset_group, config))
        else:
            # Standard campaigns with ad_groups and ads
            for ag_config in config.get("ad_groups", []):
                ad_group = models.Entity(
                    id=uuid.uuid4(),
                    level=models.LevelEnum.adset,
                    external_id=f"DEMO-GAG-{uuid.uuid4().hex[:8].upper()}",
                    name=f"{config['name']} - {ag_config['name']}",
                    status="active",
                    parent_id=campaign.id,
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    created_at=datetime.utcnow() - timedelta(days=60),
                )
                db.add(ad_group)
                entities.append((ad_group, config))

                # Create ads
                for ad_name in ag_config.get("ads", []):
                    ad = models.Entity(
                        id=uuid.uuid4(),
                        level=models.LevelEnum.ad,
                        external_id=f"DEMO-GAD-{uuid.uuid4().hex[:8].upper()}",
                        name=ad_name,
                        status="active",
                        parent_id=ad_group.id,
                        workspace_id=workspace_id,
                        connection_id=connection_id,
                        created_at=datetime.utcnow() - timedelta(days=60),
                    )
                    db.add(ad)
                    entities.append((ad, config))

    db.flush()

    # Count entities by level
    campaigns = sum(1 for e, _ in entities if e.level == models.LevelEnum.campaign)
    ad_groups = sum(
        1
        for e, _ in entities
        if e.level in [models.LevelEnum.adset, models.LevelEnum.asset_group]
    )
    ads = sum(1 for e, _ in entities if e.level == models.LevelEnum.ad)
    print(
        f"   Created Google entities: {campaigns} campaigns, {ad_groups} ad groups/asset groups, {ads} ads"
    )

    return entities


def create_meta_entities(
    db: Session,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> list[tuple[models.Entity, dict]]:
    """Create Meta Ads entity hierarchy. Returns list of (entity, config) tuples."""

    entities = []
    campaign_idx = 0

    for config in META_CAMPAIGNS:
        campaign_idx += 1

        # Create campaign
        campaign = models.Entity(
            id=uuid.uuid4(),
            level=models.LevelEnum.campaign,
            external_id=f"DEMO-MCAMP-{campaign_idx:03d}",
            name=config["name"],
            status="active",
            goal=config["goal"],
            workspace_id=workspace_id,
            connection_id=connection_id,
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        db.add(campaign)
        entities.append((campaign, config))

        # Create ad sets
        for adset_config in config.get("ad_sets", []):
            adset = models.Entity(
                id=uuid.uuid4(),
                level=models.LevelEnum.adset,
                external_id=f"DEMO-MAS-{uuid.uuid4().hex[:8].upper()}",
                name=f"{config['name']} - {adset_config['name']}",
                status="active",
                parent_id=campaign.id,
                workspace_id=workspace_id,
                connection_id=connection_id,
                created_at=datetime.utcnow() - timedelta(days=60),
            )
            db.add(adset)
            entities.append((adset, config))

            # Create ads
            for ad_name in adset_config.get("ads", []):
                ad = models.Entity(
                    id=uuid.uuid4(),
                    level=models.LevelEnum.ad,
                    external_id=f"DEMO-MAD-{uuid.uuid4().hex[:8].upper()}",
                    name=ad_name,
                    status="active",
                    parent_id=adset.id,
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    media_type=random.choice(
                        [
                            models.MediaTypeEnum.image,
                            models.MediaTypeEnum.video,
                            models.MediaTypeEnum.carousel,
                        ]
                    ),
                    created_at=datetime.utcnow() - timedelta(days=60),
                )
                db.add(ad)
                entities.append((ad, config))

    db.flush()

    # Count entities by level
    campaigns = sum(1 for e, _ in entities if e.level == models.LevelEnum.campaign)
    ad_sets = sum(1 for e, _ in entities if e.level == models.LevelEnum.adset)
    ads = sum(1 for e, _ in entities if e.level == models.LevelEnum.ad)
    print(
        f"   Created Meta entities: {campaigns} campaigns, {ad_sets} ad sets, {ads} ads"
    )

    return entities


def generate_metric_snapshots(
    db: Session,
    google_entities: list[tuple[models.Entity, dict]],
    meta_entities: list[tuple[models.Entity, dict]],
) -> int:
    """Generate 30 days of MetricSnapshot data for all entities."""

    now = datetime.now(timezone.utc)
    today = now.date()
    total_snapshots = 0

    # Daily revenue targets by provider (55% Google, 45% Meta)
    google_daily_revenue = DAILY_REVENUE * 0.55
    meta_daily_revenue = DAILY_REVENUE * 0.45

    # Process each day (including today = day_offset 0)
    for day_offset in range(30, -1, -1):
        metrics_date = today - timedelta(days=day_offset)

        # For today, use current time; for past days, use end of day
        if day_offset == 0:
            captured_at = now
        else:
            captured_at = datetime.combine(metrics_date, time(23, 59, 59)).replace(
                tzinfo=timezone.utc
            )

        # Generate Google metrics for ALL entity levels
        # First, generate campaign-level metrics, then distribute to children
        google_campaign_metrics = {}
        for entity, config in google_entities:
            if entity.level == models.LevelEnum.campaign:
                campaign_metrics = generate_campaign_metrics(
                    config=config,
                    provider="google",
                    day_offset=day_offset,
                    provider_daily_revenue=google_daily_revenue,
                )
                google_campaign_metrics[entity.id] = campaign_metrics

                _insert_snapshot(
                    db,
                    entity.id,
                    "google",
                    captured_at,
                    metrics_date,
                    campaign_metrics,
                )
                total_snapshots += 1

        # Generate ad group/ad set level metrics (distribute from campaign)
        google_adset_metrics = {}
        for entity, config in google_entities:
            if entity.level in [models.LevelEnum.adset, models.LevelEnum.asset_group]:
                parent_metrics = google_campaign_metrics.get(entity.parent_id)
                if parent_metrics:
                    # Distribute with variance
                    child_metrics = _distribute_metrics_with_variance(
                        parent_metrics, random.uniform(0.3, 0.7)
                    )
                    google_adset_metrics[entity.id] = child_metrics

                    _insert_snapshot(
                        db,
                        entity.id,
                        "google",
                        captured_at,
                        metrics_date,
                        child_metrics,
                    )
                    total_snapshots += 1

        # Generate ad level metrics (distribute from ad group)
        for entity, config in google_entities:
            if entity.level == models.LevelEnum.ad:
                parent_metrics = google_adset_metrics.get(entity.parent_id)
                if parent_metrics:
                    # Distribute with variance
                    child_metrics = _distribute_metrics_with_variance(
                        parent_metrics, random.uniform(0.2, 0.8)
                    )

                    _insert_snapshot(
                        db,
                        entity.id,
                        "google",
                        captured_at,
                        metrics_date,
                        child_metrics,
                    )
                    total_snapshots += 1

        # Generate Meta metrics for ALL entity levels
        meta_campaign_metrics = {}
        for entity, config in meta_entities:
            if entity.level == models.LevelEnum.campaign:
                campaign_metrics = generate_campaign_metrics(
                    config=config,
                    provider="meta",
                    day_offset=day_offset,
                    provider_daily_revenue=meta_daily_revenue,
                )
                meta_campaign_metrics[entity.id] = campaign_metrics

                _insert_snapshot(
                    db,
                    entity.id,
                    "meta",
                    captured_at,
                    metrics_date,
                    campaign_metrics,
                )
                total_snapshots += 1

        # Generate ad set level metrics
        meta_adset_metrics = {}
        for entity, config in meta_entities:
            if entity.level == models.LevelEnum.adset:
                parent_metrics = meta_campaign_metrics.get(entity.parent_id)
                if parent_metrics:
                    child_metrics = _distribute_metrics_with_variance(
                        parent_metrics, random.uniform(0.3, 0.7)
                    )
                    meta_adset_metrics[entity.id] = child_metrics

                    _insert_snapshot(
                        db,
                        entity.id,
                        "meta",
                        captured_at,
                        metrics_date,
                        child_metrics,
                    )
                    total_snapshots += 1

        # Generate ad level metrics
        for entity, config in meta_entities:
            if entity.level == models.LevelEnum.ad:
                parent_metrics = meta_adset_metrics.get(entity.parent_id)
                if parent_metrics:
                    child_metrics = _distribute_metrics_with_variance(
                        parent_metrics, random.uniform(0.2, 0.8)
                    )

                    _insert_snapshot(
                        db,
                        entity.id,
                        "meta",
                        captured_at,
                        metrics_date,
                        child_metrics,
                    )
                    total_snapshots += 1

        # Commit every 5 days to avoid memory issues
        if day_offset % 5 == 0:
            db.flush()

    db.flush()
    print(f"   Created {total_snapshots:,} MetricSnapshot records (30 days)")
    return total_snapshots


def _insert_snapshot(
    db: Session,
    entity_id: uuid.UUID,
    provider: str,
    captured_at: datetime,
    metrics_date: date,
    metrics: dict,
) -> None:
    """Insert a single MetricSnapshot using PostgreSQL UPSERT."""

    snapshot_data = {
        "id": uuid.uuid4(),
        "entity_id": entity_id,
        "provider": provider,
        "captured_at": captured_at,
        "metrics_date": metrics_date,
        "spend": metrics["spend"],
        "impressions": metrics["impressions"],
        "clicks": metrics["clicks"],
        "conversions": metrics["conversions"],
        "revenue": metrics["revenue"],
        "leads": metrics.get("leads"),
        "purchases": metrics.get("purchases"),
        "installs": metrics.get("installs"),
        "visitors": metrics.get("visitors"),
        "profit": metrics.get("profit"),
        "currency": "USD",
        "created_at": datetime.now(timezone.utc),
    }

    stmt = insert(models.MetricSnapshot).values(**snapshot_data)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_metric_snapshots_entity_provider_time",
        set_={
            "spend": stmt.excluded.spend,
            "impressions": stmt.excluded.impressions,
            "clicks": stmt.excluded.clicks,
            "conversions": stmt.excluded.conversions,
            "revenue": stmt.excluded.revenue,
            "leads": stmt.excluded.leads,
            "purchases": stmt.excluded.purchases,
            "installs": stmt.excluded.installs,
            "visitors": stmt.excluded.visitors,
            "profit": stmt.excluded.profit,
            "metrics_date": stmt.excluded.metrics_date,
        },
    )
    db.execute(stmt)


def create_shopify_data(
    db: Session,
    workspace_id: uuid.UUID,
    connection_id: uuid.UUID,
    google_entities: list[tuple[models.Entity, dict]],
    meta_entities: list[tuple[models.Entity, dict]],
) -> tuple[models.ShopifyShop, list, list, list]:
    """Create Shopify shop, products, customers, and orders with attribution."""

    # Create shop
    shop = models.ShopifyShop(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        connection_id=connection_id,
        external_shop_id="gid://shopify/Shop/demo-gabriels-store",
        shop_domain="gabriels-store.myshopify.com",
        shop_name="Gabriel's Store",
        currency="USD",
        timezone="America/New_York",
        country_code="US",
        plan_name="Shopify Plus",
        email="shop@gabriels-store.com",
        last_synced_at=datetime.utcnow(),
    )
    db.add(shop)
    db.flush()

    # Create products
    products = []
    for i, p in enumerate(SHOPIFY_PRODUCTS):
        product = models.ShopifyProduct(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            shop_id=shop.id,
            external_product_id=f"gid://shopify/Product/{10000 + i}",
            handle=p["title"].lower().replace(" ", "-").replace("'", ""),
            title=p["title"],
            product_type=p["type"],
            vendor=p["vendor"],
            status="active",
            price=Decimal(str(p["price"])),
            cost_per_item=Decimal(str(round(p["price"] * p["cost_pct"], 2))),
            cost_source="inventory_item",
            total_inventory=random.randint(100, 1000),
            shopify_created_at=datetime.utcnow()
            - timedelta(days=random.randint(90, 180)),
        )
        products.append(product)
        db.add(product)
    db.flush()
    print(f"   Created Shopify shop and {len(products)} products")

    # Create customers
    customers = []
    for i, (first, last) in enumerate(CUSTOMER_NAMES):
        order_count = random.randint(1, 8)
        total_spent = Decimal(str(round(random.uniform(80, 500) * order_count / 2, 2)))
        customer = models.ShopifyCustomer(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            shop_id=shop.id,
            external_customer_id=f"gid://shopify/Customer/{20000 + i}",
            email=f"{first.lower()}.{last.lower()}@email.com",
            first_name=first,
            last_name=last,
            state="enabled",
            verified_email=True,
            accepts_marketing=random.choice([True, False]),
            total_spent=total_spent,
            order_count=order_count,
            average_order_value=round(total_spent / Decimal(str(order_count)), 2)
            if order_count > 0
            else Decimal("0"),
            first_order_at=datetime.utcnow() - timedelta(days=random.randint(60, 180)),
            last_order_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            shopify_created_at=datetime.utcnow()
            - timedelta(days=random.randint(90, 365)),
        )
        customers.append(customer)
        db.add(customer)
    db.flush()
    print(f"   Created {len(customers)} Shopify customers")

    # Build attribution sources from campaign entities
    attribution_sources = []

    # Google campaigns
    for entity, config in google_entities:
        if entity.level == models.LevelEnum.campaign:
            if "Search" in entity.name:
                attribution_sources.append(
                    {
                        "source": "google",
                        "medium": "cpc",
                        "campaign": entity.name,
                        "entity_id": entity.id,
                        "provider": "google",
                        "weight": config["revenue_share"] * 0.55,  # Google's 55% share
                    }
                )
            elif "Shopping" in entity.name or "PMax" in entity.name:
                attribution_sources.append(
                    {
                        "source": "google",
                        "medium": "shopping",
                        "campaign": entity.name,
                        "entity_id": entity.id,
                        "provider": "google",
                        "weight": config["revenue_share"] * 0.55,
                    }
                )
            elif "Display" in entity.name:
                attribution_sources.append(
                    {
                        "source": "google",
                        "medium": "display",
                        "campaign": entity.name,
                        "entity_id": entity.id,
                        "provider": "google",
                        "weight": config["revenue_share"] * 0.55,
                    }
                )

    # Meta campaigns
    for entity, config in meta_entities:
        if entity.level == models.LevelEnum.campaign:
            attribution_sources.append(
                {
                    "source": "facebook",
                    "medium": "cpc",
                    "campaign": entity.name,
                    "entity_id": entity.id,
                    "provider": "meta",
                    "weight": config["revenue_share"] * 0.45,  # Meta's 45% share
                }
            )

    # Add organic/direct sources
    attribution_sources.extend(
        [
            {
                "source": "google",
                "medium": "organic",
                "campaign": None,
                "entity_id": None,
                "provider": "organic",
                "weight": 0.08,
            },
            {
                "source": "direct",
                "medium": "none",
                "campaign": None,
                "entity_id": None,
                "provider": "direct",
                "weight": 0.05,
            },
            {
                "source": "email",
                "medium": "newsletter",
                "campaign": "weekly_promo",
                "entity_id": None,
                "provider": "email",
                "weight": 0.02,
            },
        ]
    )

    # Normalize weights
    total_weight = sum(s["weight"] for s in attribution_sources)
    for s in attribution_sources:
        s["weight"] = s["weight"] / total_weight

    # Create orders
    orders = []
    order_number = 1001
    now = datetime.utcnow()
    today = now.date()

    # Target: $250K/month = ~$8,333/day
    # With avg AOV of ~$130 (1-2 products @ ~$70 each), we need ~64 orders/day
    target_daily_orders = 65  # ~65 orders/day with ~$130 AOV = ~$8,450/day

    for day_offset in range(30, -1, -1):  # Include today (day_offset=0)
        order_date = today - timedelta(days=day_offset)

        # Apply trend to order count
        trend = apply_trend(day_offset)
        daily_orders = int(target_daily_orders * trend * random.uniform(0.9, 1.1))

        for _ in range(daily_orders):
            customer = random.choice(customers)

            # Select attribution source based on weights
            source = random.choices(
                attribution_sources,
                weights=[s["weight"] for s in attribution_sources],
                k=1,
            )[0]

            # Select 1-2 products (to keep AOV around $85)
            order_products = random.sample(products, random.randint(1, 2))
            subtotal = Decimal("0")
            total_cost = Decimal("0")
            line_items_data = []

            for prod in order_products:
                qty = 1  # Single quantity to keep AOV reasonable
                item_price = prod.price
                item_cost = prod.cost_per_item or Decimal("0")
                line_total = item_price * qty
                line_cost = item_cost * qty
                subtotal += line_total
                total_cost += line_cost
                line_items_data.append(
                    {
                        "product": prod,
                        "quantity": qty,
                        "price": float(item_price),
                        "cost": float(item_cost),
                        "total": float(line_total),
                    }
                )

            # Calculate totals
            discount = (
                round(subtotal * Decimal(str(random.uniform(0, 0.12))), 2)
                if random.random() > 0.7
                else Decimal("0")
            )
            tax = round((subtotal - discount) * Decimal("0.08"), 2)  # 8% tax
            shipping = Decimal(str(random.choice([0, 5.99, 8.99, 12.99])))
            total_price = subtotal - discount + tax + shipping
            profit = subtotal - discount - total_cost

            order_time = datetime.combine(
                order_date, time(random.randint(8, 23), random.randint(0, 59))
            )

            order = models.ShopifyOrder(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                shop_id=shop.id,
                customer_id=customer.id,
                external_order_id=f"gid://shopify/Order/{30000 + order_number}",
                order_number=order_number,
                name=f"#{order_number}",
                total_price=total_price,
                subtotal_price=subtotal,
                total_tax=tax,
                total_shipping=shipping,
                total_discounts=discount,
                currency="USD",
                total_cost=total_cost,
                total_profit=profit,
                has_missing_costs=False,
                financial_status=models.ShopifyFinancialStatusEnum.paid,
                fulfillment_status=random.choice(
                    [
                        models.ShopifyFulfillmentStatusEnum.fulfilled,
                        models.ShopifyFulfillmentStatusEnum.fulfilled,
                        models.ShopifyFulfillmentStatusEnum.fulfilled,
                        models.ShopifyFulfillmentStatusEnum.partial,
                        models.ShopifyFulfillmentStatusEnum.unfulfilled,
                    ]
                ),
                source_name="web",
                utm_source=source["source"],
                utm_medium=source["medium"],
                utm_campaign=source["campaign"],
                order_created_at=order_time,
                order_processed_at=order_time
                + timedelta(minutes=random.randint(1, 10)),
            )
            db.add(order)
            orders.append((order, source))
            order_number += 1

            # Create line items
            for li_data in line_items_data:
                line_profit = Decimal(str(li_data["total"])) - (
                    Decimal(str(li_data["cost"])) * li_data["quantity"]
                )
                line_item = models.ShopifyOrderLineItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_id=li_data["product"].id,
                    external_line_item_id=f"gid://shopify/LineItem/{uuid.uuid4().hex[:12]}",
                    external_product_id=li_data["product"].external_product_id,
                    title=li_data["product"].title,
                    sku=f"SKU-{li_data['product'].handle[:12].upper()}",
                    quantity=li_data["quantity"],
                    price=Decimal(str(li_data["price"])),
                    total_discount=Decimal("0"),
                    cost_per_item=Decimal(str(li_data["cost"])),
                    cost_source="inventory_item",
                    line_profit=round(line_profit, 2),
                )
                db.add(line_item)

        # Flush every 5 days
        if day_offset % 5 == 0:
            db.flush()

    db.flush()

    # Calculate total revenue
    total_revenue = sum(float(o.total_price) for o, _ in orders)
    avg_order_value = total_revenue / len(orders) if orders else 0
    print(
        f"   Created {len(orders):,} Shopify orders (${total_revenue:,.2f} total, ${avg_order_value:.2f} AOV)"
    )

    return shop, products, customers, orders


def create_attribution_data(
    db: Session,
    workspace_id: uuid.UUID,
    orders: list[tuple[models.ShopifyOrder, dict]],
) -> int:
    """Create attribution records linking orders to campaigns."""

    attribution_count = 0

    for order, source in orders:
        # Skip organic/direct/email for attribution records (they don't have entity_id)
        if source["entity_id"] is None:
            continue

        # Determine match type and confidence
        if source["provider"] == "google":
            match_type = "gclid" if random.random() > 0.3 else "utm_campaign"
            confidence = "high" if match_type == "gclid" else "medium"
        else:  # meta
            match_type = "fbclid" if random.random() > 0.4 else "utm_campaign"
            confidence = "high" if match_type == "fbclid" else "medium"

        attribution = models.Attribution(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            shopify_order_id=order.id,
            entity_id=source["entity_id"],
            provider=source["provider"],
            entity_level="campaign",
            match_type=match_type,
            confidence=confidence,
            attribution_model="last_click",
            attribution_window_days=30,
            attributed_revenue=order.total_price,
            attribution_credit=Decimal("1.0"),
            attributed_at=order.order_created_at,
        )
        db.add(attribution)
        attribution_count += 1

    db.flush()
    print(f"   Created {attribution_count:,} attribution records")
    return attribution_count


# =============================================================================
# MAIN SEED FUNCTION
# =============================================================================


def seed_demo():
    """Main seeding function for demo workspace."""

    print("\n" + "=" * 70)
    print(" DEMO WORKSPACE SEED SCRIPT")
    print(" Target: $250K/month revenue, ~3.0 ROAS, upward trend")
    print("=" * 70 + "\n")

    with SessionLocal() as db:
        try:
            # Step 1: Find user
            print("1. Finding user...")
            user = find_or_error_user(db)

            # Step 2: Create workspace
            print("\n2. Creating workspace...")
            workspace = create_workspace(db, user)

            # Step 3: Create connections
            print("\n3. Creating connections...")
            connections = create_connections(db, workspace.id)

            # Step 4: Create Google entities
            print("\n4. Creating Google Ads entities...")
            google_entities = create_google_entities(
                db, workspace.id, connections["google"].id
            )

            # Step 5: Create Meta entities
            print("\n5. Creating Meta Ads entities...")
            meta_entities = create_meta_entities(
                db, workspace.id, connections["meta"].id
            )

            # Step 6: Generate MetricSnapshot data
            print("\n6. Generating MetricSnapshot data (30 days)...")
            snapshot_count = generate_metric_snapshots(
                db, google_entities, meta_entities
            )

            # Step 7: Create Shopify data
            print("\n7. Creating Shopify data...")
            shop, products, customers, orders = create_shopify_data(
                db,
                workspace.id,
                connections["shopify"].id,
                google_entities,
                meta_entities,
            )

            # Step 8: Create attribution data
            print("\n8. Creating attribution records...")
            attribution_count = create_attribution_data(db, workspace.id, orders)

            # Commit all changes
            print("\n9. Committing to database...")
            db.commit()

            print("\n" + "=" * 70)
            print(" SEED COMPLETE!")
            print("=" * 70)
            print(f"   Workspace: {workspace.name}")
            print(f"   Workspace ID: {workspace.id}")
            print(f"   User: {user.email}")
            print(f"   Connections: 3 (Google, Meta, Shopify)")
            print(f"   Google Entities: {len(google_entities)}")
            print(f"   Meta Entities: {len(meta_entities)}")
            print(f"   MetricSnapshots: {snapshot_count:,}")
            print(f"   Shopify Products: {len(products)}")
            print(f"   Shopify Customers: {len(customers)}")
            print(f"   Shopify Orders: {len(orders):,}")
            print(f"   Attributions: {attribution_count:,}")
            print("=" * 70 + "\n")

            return workspace.id

        except Exception as e:
            db.rollback()
            print(f"\n ERROR: {e}")
            raise


if __name__ == "__main__":
    seed_demo()
