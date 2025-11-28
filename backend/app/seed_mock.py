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
        # Clear Shopify tables before connections (foreign key dependencies)
        db.query(models.ShopifyOrderLineItem).delete()
        db.query(models.ShopifyOrder).delete()
        db.query(models.ShopifyCustomer).delete()
        db.query(models.ShopifyProduct).delete()
        db.query(models.ShopifyShop).delete()
        db.query(models.Connection).delete()
        db.query(models.QaQueryLog).delete()
        db.query(models.ManualCost).delete()
        db.query(models.AuthCredential).delete()
        db.query(models.WorkspaceInvite).delete()
        db.query(models.WorkspaceMember).delete()
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

        conn_shopify = models.Connection(
            id=uuid.uuid4(),
            provider=models.ProviderEnum.shopify,
            external_account_id="SHOPIFY-789",
            name="Demo Store",
            status="active",
            connected_at=datetime.utcnow(),
            workspace_id=workspace.id,
            sync_frequency="hourly"
        )

        db.add_all([conn_google, conn_meta, conn_shopify])
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

        # 8. Create Shopify mock data
        print("🛍️ Creating Shopify mock data...")

        # 8.1 Create Shopify Shop
        shopify_shop = models.ShopifyShop(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            connection_id=conn_shopify.id,
            external_shop_id="gid://shopify/Shop/12345678",
            shop_domain="demo-store.myshopify.com",
            shop_name="Demo Store",
            currency="EUR",
            timezone="Europe/Amsterdam",
            country_code="NL",
            plan_name="Shopify",
            email="shop@demo-store.com",
            last_synced_at=datetime.utcnow()
        )
        db.add(shopify_shop)
        db.flush()

        # 8.2 Create Shopify Products
        product_data = [
            {"title": "Premium T-Shirt", "type": "Apparel", "price": 29.99, "cost": 8.50, "vendor": "Cotton Co"},
            {"title": "Classic Hoodie", "type": "Apparel", "price": 59.99, "cost": 18.00, "vendor": "Cotton Co"},
            {"title": "Running Shoes", "type": "Footwear", "price": 129.99, "cost": 45.00, "vendor": "SportGear"},
            {"title": "Wireless Earbuds", "type": "Electronics", "price": 79.99, "cost": 25.00, "vendor": "TechBrand"},
            {"title": "Smart Watch", "type": "Electronics", "price": 199.99, "cost": 65.00, "vendor": "TechBrand"},
            {"title": "Yoga Mat", "type": "Fitness", "price": 34.99, "cost": 10.00, "vendor": "FitLife"},
            {"title": "Water Bottle", "type": "Accessories", "price": 24.99, "cost": 6.00, "vendor": "EcoGoods"},
            {"title": "Backpack", "type": "Accessories", "price": 89.99, "cost": 28.00, "vendor": "TravelGear"},
        ]

        shopify_products = []
        for i, p in enumerate(product_data):
            product = models.ShopifyProduct(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                shop_id=shopify_shop.id,
                external_product_id=f"gid://shopify/Product/{1000 + i}",
                handle=p["title"].lower().replace(" ", "-"),
                title=p["title"],
                product_type=p["type"],
                vendor=p["vendor"],
                status="active",
                price=p["price"],
                cost_per_item=p["cost"],
                cost_source="inventory_item",
                total_inventory=random.randint(50, 500),
                shopify_created_at=datetime.utcnow() - timedelta(days=random.randint(30, 180))
            )
            shopify_products.append(product)
            db.add(product)
        db.flush()

        # 8.3 Create Shopify Customers
        customer_names = [
            ("Emma", "Johnson", "emma.j@email.com"),
            ("Liam", "Williams", "liam.w@email.com"),
            ("Olivia", "Brown", "olivia.b@email.com"),
            ("Noah", "Jones", "noah.j@email.com"),
            ("Ava", "Garcia", "ava.g@email.com"),
            ("Ethan", "Miller", "ethan.m@email.com"),
            ("Sophia", "Davis", "sophia.d@email.com"),
            ("Mason", "Rodriguez", "mason.r@email.com"),
            ("Isabella", "Martinez", "isabella.m@email.com"),
            ("Lucas", "Hernandez", "lucas.h@email.com"),
            ("Mia", "Lopez", "mia.l@email.com"),
            ("Alexander", "Gonzalez", "alex.g@email.com"),
        ]

        shopify_customers = []
        for i, (first, last, email) in enumerate(customer_names):
            order_count = random.randint(1, 8)
            total_spent = round(random.uniform(50, 800) * order_count / 3, 2)
            customer = models.ShopifyCustomer(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                shop_id=shopify_shop.id,
                external_customer_id=f"gid://shopify/Customer/{2000 + i}",
                email=email,
                first_name=first,
                last_name=last,
                state="enabled",
                verified_email=True,
                accepts_marketing=random.choice([True, False]),
                total_spent=total_spent,
                order_count=order_count,
                average_order_value=round(total_spent / order_count, 2) if order_count > 0 else 0,
                first_order_at=datetime.utcnow() - timedelta(days=random.randint(60, 365)),
                last_order_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                shopify_created_at=datetime.utcnow() - timedelta(days=random.randint(90, 400))
            )
            shopify_customers.append(customer)
            db.add(customer)
        db.flush()

        # 8.4 Create Shopify Orders with attribution
        utm_sources = [
            {"source": "facebook", "medium": "cpc", "campaign": "Meta - Awareness Top Funnel"},
            {"source": "facebook", "medium": "cpc", "campaign": "Meta - Conversions Mid Funnel"},
            {"source": "facebook", "medium": "cpc", "campaign": "Meta - Catalog Sales"},
            {"source": "google", "medium": "cpc", "campaign": "Search - Brand Terms"},
            {"source": "google", "medium": "cpc", "campaign": "Search - Competitor"},
            {"source": "google", "medium": "display", "campaign": "Display - Retargeting"},
            {"source": "instagram", "medium": "social", "campaign": "organic"},
            {"source": "email", "medium": "newsletter", "campaign": "weekly_promo"},
            {"source": "direct", "medium": "none", "campaign": None},
            {"source": "organic", "medium": "search", "campaign": None},
        ]

        shopify_orders = []
        order_number = 1001

        # Generate orders for last 30 days
        for day_offset in range(30, 0, -1):
            # 5-15 orders per day
            orders_today = random.randint(5, 15)
            order_date = datetime.utcnow() - timedelta(days=day_offset)

            for _ in range(orders_today):
                customer = random.choice(shopify_customers)
                utm = random.choice(utm_sources)

                # Select 1-4 products for this order
                order_products = random.sample(shopify_products, random.randint(1, 4))
                subtotal = 0
                total_cost = 0
                line_items_data = []

                for prod in order_products:
                    qty = random.randint(1, 3)
                    item_price = float(prod.price)
                    item_cost = float(prod.cost_per_item) if prod.cost_per_item else 0
                    line_total = item_price * qty
                    line_cost = item_cost * qty
                    subtotal += line_total
                    total_cost += line_cost
                    line_items_data.append({
                        "product": prod,
                        "quantity": qty,
                        "price": item_price,
                        "cost": item_cost,
                        "total": line_total
                    })

                # Calculate totals
                discount = round(subtotal * random.uniform(0, 0.15), 2) if random.random() > 0.7 else 0
                tax = round((subtotal - discount) * 0.21, 2)  # 21% VAT
                shipping = random.choice([0, 4.95, 6.95, 9.95])
                total_price = round(subtotal - discount + tax + shipping, 2)
                profit = round(subtotal - discount - total_cost, 2)

                order = models.ShopifyOrder(
                    id=uuid.uuid4(),
                    workspace_id=workspace.id,
                    shop_id=shopify_shop.id,
                    customer_id=customer.id,
                    external_order_id=f"gid://shopify/Order/{3000 + order_number}",
                    order_number=order_number,
                    name=f"#{order_number}",
                    total_price=total_price,
                    subtotal_price=subtotal,
                    total_tax=tax,
                    total_shipping=shipping,
                    total_discounts=discount,
                    currency="EUR",
                    total_cost=total_cost,
                    total_profit=profit,
                    has_missing_costs=False,
                    financial_status=models.ShopifyFinancialStatusEnum.paid,
                    fulfillment_status=random.choice([
                        models.ShopifyFulfillmentStatusEnum.fulfilled,
                        models.ShopifyFulfillmentStatusEnum.fulfilled,
                        models.ShopifyFulfillmentStatusEnum.partial,
                        models.ShopifyFulfillmentStatusEnum.unfulfilled,
                    ]),
                    source_name="web",
                    utm_source=utm["source"],
                    utm_medium=utm["medium"],
                    utm_campaign=utm["campaign"],
                    order_created_at=order_date + timedelta(hours=random.randint(8, 22)),
                    order_processed_at=order_date + timedelta(hours=random.randint(8, 22), minutes=5),
                )
                db.add(order)
                shopify_orders.append(order)
                order_number += 1

                # Create line items for this order
                for li_data in line_items_data:
                    line_profit = li_data["total"] - (li_data["cost"] * li_data["quantity"])
                    line_item = models.ShopifyOrderLineItem(
                        id=uuid.uuid4(),
                        order_id=order.id,
                        product_id=li_data["product"].id,
                        external_line_item_id=f"gid://shopify/LineItem/{uuid.uuid4().hex[:12]}",
                        external_product_id=li_data["product"].external_product_id,
                        title=li_data["product"].title,
                        sku=f"SKU-{li_data['product'].handle.upper()[:8]}",
                        quantity=li_data["quantity"],
                        price=li_data["price"],
                        total_discount=0,
                        cost_per_item=li_data["cost"],
                        cost_source="inventory_item",
                        line_profit=round(line_profit, 2),
                    )
                    db.add(line_item)

        db.commit()
        print(f"✅ Created Shopify data: 1 shop, {len(shopify_products)} products, {len(shopify_customers)} customers, {len(shopify_orders)} orders")

        # 9. Run Compute Service
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
        print(f"   Connections: 3 (Google, Meta, Shopify)")
        print(f"   Entities: {len(entities_to_seed)}")
        print(f"   Total Facts: {total_facts:,}")
        print(f"   Shopify: 1 shop, {len(shopify_products)} products, {len(shopify_customers)} customers, {len(shopify_orders)} orders")
        print("="*70 + "\n")

if __name__ == "__main__":
    seed()
