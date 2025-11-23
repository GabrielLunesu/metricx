"""Seed script to populate the database with realistic mock data for testing.

Features:
- Realtime Data Simulation: Hourly data points for the last 48 hours.
- Real Providers: Google and Meta (plus TikTok/Other).
- Realistic Hierarchy: Campaigns > AdSets > Ads.
- Incremental Data: Hourly data is incremental so aggregation remains correct.

Usage:
    cd backend
    python -m app.seed_mock
"""

from datetime import datetime, timedelta, time
import os
import random
import uuid
import math

from app.database import SessionLocal
from app import models
from app.security import get_password_hash
from app.services.token_service import store_connection_token
from app.services.compute_service import run_compute_snapshot


def generate_hourly_curve(hour: int) -> float:
    """Return a multiplier (0.0 to ~2.0) representing activity level for a given hour (0-23).
    Simulates a typical day: low at night, rising morning, peak afternoon/evening.
    """
    # Simple sinusoidal curve + offset
    # Peak around 14:00-20:00, trough around 03:00-05:00
    if 0 <= hour < 6:
        return 0.1 + (hour / 10)  # 0.1 to 0.7
    elif 6 <= hour < 12:
        return 0.7 + ((hour - 6) / 6)  # 0.7 to 1.7
    elif 12 <= hour < 18:
        return 1.7 + (random.uniform(-0.2, 0.2)) # Plateau ~1.7
    else: # 18-23
        return 1.7 - ((hour - 18) / 5) # 1.7 down to 0.7

def generate_random_metrics(goal: str, provider: str, is_hourly: bool = False):
    """Generate realistic ad metrics.
    
    Args:
        goal: Campaign objective
        provider: Ad provider
        is_hourly: If True, generates smaller numbers (approx 1/24th of daily)
    """
    
    # Base: impressions (daily scale)
    base_impressions = random.randint(1000, 10000)
    
    if is_hourly:
        # Scale down for hourly, but apply some randomness so it's not uniform
        base_impressions = int(base_impressions / 15) # A bit more than 1/24 to account for active hours
    
    impressions = base_impressions
    
    # Provider-specific CTR ranges
    ctr_ranges = {
        "google": (0.02, 0.05),  # 2-5% (search ads)
        "meta": (0.01, 0.03),    # 1-3% (social ads)
        "tiktok": (0.015, 0.035), # 1.5-3.5% (social video)
        "other": (0.01, 0.025),  # 1-2.5% (display)
    }
    ctr = random.uniform(*ctr_ranges.get(provider, (0.01, 0.025)))
    clicks = int(impressions * ctr)
    
    # Goal-specific conversion rates and metrics
    conversions = 0
    revenue = 0
    leads = 0
    installs = 0
    purchases = 0
    visitors = 0
    
    if goal == "awareness":
        conversions = random.uniform(0, 0.5) # Very low
        visitors = int(clicks * random.uniform(0.8, 0.95))
        
    elif goal == "traffic":
        conversions = random.uniform(0.5, 2)
        visitors = int(clicks * random.uniform(0.85, 0.98))
        
    elif goal == "leads":
        leads = clicks * random.uniform(0.1, 0.25)
        conversions = leads
        revenue = conversions * random.uniform(0, 10)
        visitors = int(clicks * 0.9)
        
    elif goal == "app_installs":
        installs = int(clicks * random.uniform(0.05, 0.15))
        conversions = installs
        revenue = installs * random.uniform(0, 5)
        
    elif goal == "purchases":
        purchases = int(clicks * random.uniform(0.02, 0.08))
        conversions = purchases
        revenue = purchases * random.uniform(50, 200)
        visitors = int(clicks * 0.92)
        
    else:  # conversions
        conversions = clicks * random.uniform(0.03, 0.12)
        revenue = conversions * random.uniform(40, 120)
        visitors = int(clicks * 0.88)
    
    # Spend: derived from CPM
    cpm_ranges = {
        "google": (8, 20),
        "meta": (5, 15),
        "tiktok": (6, 18),
        "other": (5, 12),
    }
    cpm = random.uniform(*cpm_ranges.get(provider, (5, 12)))
    spend = (impressions / 1000) * cpm
    
    # Profit
    margin = random.uniform(0.2, 0.4)
    profit = revenue * margin if revenue > 0 else 0
    
    return {
        'spend': round(spend, 2),
        'impressions': impressions,
        'clicks': clicks,
        'conversions': round(conversions, 2),
        'revenue': round(revenue, 2),
        'leads': round(leads, 2) if leads > 0 else None,
        'installs': int(installs) if installs > 0 else None,
        'purchases': int(purchases) if purchases > 0 else None,
        'visitors': int(visitors) if visitors > 0 else None,
        'profit': round(profit, 2) if profit > 0 else None,
    }


def seed():
    """Main seeding function."""
    with SessionLocal() as db:
        print("🧹 Clearing existing data...")
        
        # Clear data in reverse dependency order
        db.query(models.Pnl).delete()
        db.query(models.ComputeRun).delete()
        db.query(models.MetricFact).delete()
        db.query(models.Entity).delete()
        db.query(models.Import).delete()
        db.query(models.Fetch).delete()
        db.query(models.Connection).delete()
        db.query(models.QaQueryLog).delete()
        db.query(models.ManualCost).delete()
        db.query(models.AuthCredential).delete()
        db.query(models.User).delete()
        db.query(models.Token).delete()
        db.query(models.Workspace).delete()
        db.commit()
        
        print("✅ Old data cleared")
        
        # 1. Create workspace
        print("🏢 Creating workspace...")
        workspace = models.Workspace(
            id=uuid.uuid4(),
            name="Defang Labs",
            created_at=datetime.utcnow()
        )
        db.add(workspace)
        db.flush()
        
        # 2. Create users
        print("👥 Creating users...")
        owner_id = uuid.uuid4()
        viewer_id = uuid.uuid4()
        
        owner = models.User(
            id=owner_id,
            email="owner@defanglabs.com",
            name="Owner User",
            role=models.RoleEnum.owner,
            workspace_id=workspace.id
        )
        
        viewer = models.User(
            id=viewer_id,
            email="viewer@defanglabs.com",
            name="Viewer User", 
            role=models.RoleEnum.viewer,
            workspace_id=workspace.id
        )
        
        db.add_all([owner, viewer])
        db.flush()
        
        # Create auth credentials
        owner_credential = models.AuthCredential(
            user_id=owner_id,
            password_hash=get_password_hash("password123"),
            created_at=datetime.utcnow()
        )
        
        viewer_credential = models.AuthCredential(
            user_id=viewer_id,
            password_hash=get_password_hash("password123"),
            created_at=datetime.utcnow()
        )
        
        db.add_all([owner_credential, viewer_credential])
        
        # 3. Create connections (Google & Meta)
        print("🔗 Creating connections...")
        
        conn_google = models.Connection(
            id=uuid.uuid4(),
            provider=models.ProviderEnum.google,
            external_account_id="GOOGLE-123",
            name="Google Ads Account",
            status="active",
            connected_at=datetime.utcnow(),
            workspace_id=workspace.id,
            sync_frequency="hourly"
        )
        
        conn_meta = models.Connection(
            id=uuid.uuid4(),
            provider=models.ProviderEnum.meta,
            external_account_id="META-456",
            name="Meta Ads Account",
            status="active",
            connected_at=datetime.utcnow(),
            workspace_id=workspace.id,
            sync_frequency="hourly"
        )
        
        db.add_all([conn_google, conn_meta])
        db.flush()

        # Seed encrypted provider token if available (optional)
        system_token = os.getenv("META_ACCESS_TOKEN")
        if system_token:
            print("🔐 Seeding encrypted Meta system token...")
            store_connection_token(
                db,
                conn_meta,
                access_token=system_token,
                refresh_token=None,
                expires_at=None,
                scope="system-user",
                ad_account_ids=["META-456"],
            )
        
        # 4. Create fetch and import
        print("📥 Creating fetch and import records...")
        fetch = models.Fetch(
            id=uuid.uuid4(),
            kind="mock_data",
            status="completed", 
            started_at=datetime.utcnow() - timedelta(hours=1),
            finished_at=datetime.utcnow(),
            range_start=datetime.utcnow() - timedelta(days=30),
            range_end=datetime.utcnow(),
            connection_id=conn_google.id # Just link to one for simplicity
        )
        db.add(fetch)
        db.flush()
        
        import_record = models.Import(
            id=uuid.uuid4(),
            as_of=datetime.utcnow(),
            created_at=datetime.utcnow(),
            note="Mock seed data import",
            fetch_id=fetch.id
        )
        db.add(import_record)
        db.flush()
        
        # 5. Create entity hierarchy
        print("🏗️ Creating entity hierarchy...")
        campaigns = []
        adsets = []
        ads = []
        
        # Campaign Configs
        campaign_configs = [
            # Google Campaigns
            {"name": "Search - Brand Terms", "goal": models.GoalEnum.traffic, "provider": models.ProviderEnum.google, "conn": conn_google, "status": "active"},
            {"name": "Search - Competitor", "goal": models.GoalEnum.leads, "provider": models.ProviderEnum.google, "conn": conn_google, "status": "active"},
            {"name": "Display - Retargeting", "goal": models.GoalEnum.conversions, "provider": models.ProviderEnum.google, "conn": conn_google, "status": "active"},
            
            # Meta Campaigns
            {"name": "Meta - Awareness Top Funnel", "goal": models.GoalEnum.awareness, "provider": models.ProviderEnum.meta, "conn": conn_meta, "status": "active"},
            {"name": "Meta - Conversions Mid Funnel", "goal": models.GoalEnum.conversions, "provider": models.ProviderEnum.meta, "conn": conn_meta, "status": "active"},
            {"name": "Meta - Catalog Sales", "goal": models.GoalEnum.purchases, "provider": models.ProviderEnum.meta, "conn": conn_meta, "status": "active"},
        ]
        
        for i, config in enumerate(campaign_configs, start=1):
            campaign = models.Entity(
                id=uuid.uuid4(),
                level=models.LevelEnum.campaign,
                external_id=f"CAMP-{i:03d}",
                name=config["name"],
                status=config["status"],
                parent_id=None,
                workspace_id=workspace.id,
                connection_id=config["conn"].id,
                goal=config["goal"]
            )
            campaigns.append(campaign)
            db.add(campaign)
        
        db.flush()
        
        # Create AdSets
        adset_suffixes = ["Broad", "Interest", "Lookalike"]
        for campaign in campaigns:
            for j, suffix in enumerate(adset_suffixes):
                adset = models.Entity(
                    id=uuid.uuid4(),
                    level=models.LevelEnum.adset,
                    external_id=f"ADSET-{campaign.external_id}-{j+1:03d}",
                    name=f"{campaign.name} - {suffix}",
                    status=campaign.status,
                    parent_id=campaign.id,
                    workspace_id=workspace.id,
                    connection_id=campaign.connection_id
                )
                adsets.append(adset)
                db.add(adset)
        
        db.flush()
        
        # Create Ads
        ad_types = ["Image", "Video", "Carousel"]
        for adset in adsets:
            for k, ad_type in enumerate(ad_types):
                ad = models.Entity(
                    id=uuid.uuid4(),
                    level=models.LevelEnum.ad,
                    external_id=f"AD-{adset.external_id}-{k+1:03d}",
                    name=f"{adset.name} - {ad_type} #{k+1}",
                    status=adset.status,
                    parent_id=adset.id,
                    workspace_id=workspace.id,
                    connection_id=adset.connection_id
                )
                ads.append(ad)
                db.add(ad)
        
        db.flush()
        
        # 6. Generate MetricFact data
        print("📊 Generating metric facts...")
        
        # Map campaign ID to config for quick lookup
        campaign_config_map = {c.id: next(cfg for cfg in campaign_configs if cfg["name"] == c.name) for c in campaigns}
        
        now = datetime.utcnow()
        today_date = now.date()
        
        # We will generate data for:
        # - Historical: Day -30 to Day -2 (Daily granularity)
        # - Recent: Day -1 to Now (Hourly granularity)
        
        entities_to_seed = campaigns + adsets + ads
        total_facts = 0
        
        for entity in entities_to_seed:
            # Resolve goal/provider
            if entity.level == models.LevelEnum.campaign:
                config = campaign_config_map[entity.id]
            elif entity.level == models.LevelEnum.adset:
                parent = next(c for c in campaigns if c.id == entity.parent_id)
                config = campaign_config_map[parent.id]
            else: # ad
                parent_adset = next(a for a in adsets if a.id == entity.parent_id)
                parent_campaign = next(c for c in campaigns if c.id == parent_adset.parent_id)
                config = campaign_config_map[parent_campaign.id]
            
            goal = config["goal"].value
            provider = config["provider"].value
            
            # 6.1 Historical Daily Data (30 days ago -> 2 days ago)
            for day_offset in range(30, 1, -1):
                event_date = today_date - timedelta(days=day_offset)
                event_datetime = datetime.combine(event_date, time(0, 0)) # Midnight
                
                metrics = generate_random_metrics(goal, provider, is_hourly=False)
                
                fact = models.MetricFact(
                    id=uuid.uuid4(),
                    entity_id=entity.id,
                    provider=config["provider"],
                    level=entity.level,
                    event_at=event_datetime,
                    event_date=event_datetime,
                    spend=metrics['spend'],
                    impressions=metrics['impressions'],
                    clicks=metrics['clicks'],
                    conversions=metrics['conversions'],
                    revenue=metrics['revenue'],
                    leads=metrics['leads'],
                    installs=metrics['installs'],
                    purchases=metrics['purchases'],
                    visitors=metrics['visitors'],
                    profit=metrics['profit'],
                    currency="EUR",
                    natural_key=f"{entity.id}-{event_date}", # Daily key
                    ingested_at=now,
                    import_id=import_record.id
                )
                db.add(fact)
                total_facts += 1
            
            # 6.2 Recent Hourly Data (Yesterday and Today)
            # Yesterday: All 24 hours
            # Today: Up to current hour
            
            # Yesterday
            yesterday_date = today_date - timedelta(days=1)
            for hour in range(24):
                event_datetime = datetime.combine(yesterday_date, time(hour, 0))
                
                # Apply hourly curve
                curve = generate_hourly_curve(hour)
                metrics = generate_random_metrics(goal, provider, is_hourly=True)
                
                # Adjust metrics by curve
                for k in ['spend', 'impressions', 'clicks', 'conversions', 'revenue', 'leads', 'installs', 'purchases', 'visitors', 'profit']:
                    if metrics[k] is not None:
                        metrics[k] = metrics[k] * curve
                        if k in ['impressions', 'clicks', 'installs', 'purchases', 'visitors']:
                            metrics[k] = int(metrics[k])
                        else:
                            metrics[k] = round(metrics[k], 2)

                fact = models.MetricFact(
                    id=uuid.uuid4(),
                    entity_id=entity.id,
                    provider=config["provider"],
                    level=entity.level,
                    event_at=event_datetime,
                    event_date=event_datetime, # Still associated with the date
                    spend=metrics['spend'],
                    impressions=metrics['impressions'],
                    clicks=metrics['clicks'],
                    conversions=metrics['conversions'],
                    revenue=metrics['revenue'],
                    leads=metrics['leads'],
                    installs=metrics['installs'],
                    purchases=metrics['purchases'],
                    visitors=metrics['visitors'],
                    profit=metrics['profit'],
                    currency="EUR",
                    natural_key=f"{entity.id}-{yesterday_date}-{hour}", # Hourly key
                    ingested_at=now,
                    import_id=import_record.id
                )
                db.add(fact)
                total_facts += 1
                
            # Today (up to current hour)
            current_hour = now.hour
            for hour in range(current_hour + 1):
                event_datetime = datetime.combine(today_date, time(hour, 0))
                
                curve = generate_hourly_curve(hour)
                metrics = generate_random_metrics(goal, provider, is_hourly=True)
                
                for k in ['spend', 'impressions', 'clicks', 'conversions', 'revenue', 'leads', 'installs', 'purchases', 'visitors', 'profit']:
                    if metrics[k] is not None:
                        metrics[k] = metrics[k] * curve
                        if k in ['impressions', 'clicks', 'installs', 'purchases', 'visitors']:
                            metrics[k] = int(metrics[k])
                        else:
                            metrics[k] = round(metrics[k], 2)

                fact = models.MetricFact(
                    id=uuid.uuid4(),
                    entity_id=entity.id,
                    provider=config["provider"],
                    level=entity.level,
                    event_at=event_datetime,
                    event_date=event_datetime,
                    spend=metrics['spend'],
                    impressions=metrics['impressions'],
                    clicks=metrics['clicks'],
                    conversions=metrics['conversions'],
                    revenue=metrics['revenue'],
                    leads=metrics['leads'],
                    installs=metrics['installs'],
                    purchases=metrics['purchases'],
                    visitors=metrics['visitors'],
                    profit=metrics['profit'],
                    currency="EUR",
                    natural_key=f"{entity.id}-{today_date}-{hour}",
                    ingested_at=now,
                    import_id=import_record.id
                )
                db.add(fact)
                total_facts += 1
                
        db.commit()
        print(f"✅ Generated {total_facts:,} metric facts (Daily history + Hourly recent)")

        # 7. Create manual costs
        print("💰 Creating manual costs...")
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
        db.add(hubspot_cost)
        db.commit()
        
        # 8. Run Compute Service
        print("💰 Running compute service to generate P&L snapshots...")
        try:
            run_id = run_compute_snapshot(
                db=db,
                workspace_id=str(workspace.id),
                as_of=datetime.utcnow(),
                reason="Mock seed data snapshot",
                kind="snapshot"
            )
            print(f"✅ Compute run created: {run_id}")
        except Exception as e:
            print(f"⚠️  Compute service error: {e}")

        print("\n" + "="*70)
        print("🎉 SEED COMPLETE!")
        print("="*70)
        print(f"   Workspace: {workspace.name}")
        print(f"   Connections: 2 (Google, Meta)")
        print(f"   Entities: {len(entities_to_seed)}")
        print(f"   Total Facts: {total_facts:,}")
        print("="*70 + "\n")

if __name__ == "__main__":
    seed()
