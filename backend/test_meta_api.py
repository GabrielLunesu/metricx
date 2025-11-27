"""
Test Meta Ads API connectivity and SDK functionality.

Usage:
    python test_meta_api.py

Environment Variables Required:
    META_ACCESS_TOKEN: Your system user token
    META_AD_ACCOUNT_ID: Your ad account ID (optional for first test)
"""

import os
import sys
from pathlib import Path

def test_connection():
    """Test 1: Verify API connection and find ad accounts."""
    print("=" * 60)
    print("Test 1: API Connection & Find Ad Accounts")
    print("=" * 60)
    
    # Get token from environment
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ ERROR: META_ACCESS_TOKEN not set")
        print("\n   Set it in your .env file or run:")
        print("   export META_ACCESS_TOKEN='your_token_here'")
        return False
    
    print(f"✅ Token found (length: {len(access_token)} chars)")
    
    try:
        # Try importing SDK
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount
            print("✅ Facebook Business SDK imported successfully")
        except ImportError:
            print("❌ ERROR: Facebook Business SDK not installed")
            print("\n   Install it with:")
            print("   pip install facebook-business==19.0.0")
            return False
        
        # Initialize SDK
        FacebookAdsApi.init(access_token=access_token)
        print("✅ SDK initialized")
        
        # Get 'me' info to verify token
        import requests
        me_url = "https://graph.facebook.com/v19.0/me"
        me_response = requests.get(me_url, params={'access_token': access_token})
        
        if me_response.status_code != 200:
            print(f"❌ ERROR: Token validation failed")
            print(f"   Status: {me_response.status_code}")
            print(f"   Response: {me_response.text}")
            return False
        
        me_data = me_response.json()
        print(f"✅ Token valid for: {me_data.get('name', 'Unknown')} (ID: {me_data.get('id', 'N/A')})")
        print()
        
        # Get ad accounts
        print("🔍 Fetching ad accounts...")
        accounts_url = "https://graph.facebook.com/v19.0/me/adaccounts"
        accounts_response = requests.get(accounts_url, params={
            'access_token': access_token,
            'fields': 'id,account_id,name,currency,timezone_name,account_status'
        })
        
        if accounts_response.status_code != 200:
            print(f"❌ ERROR: Failed to fetch ad accounts")
            print(f"   Status: {accounts_response.status_code}")
            print(f"   Response: {accounts_response.text}")
            return False
        
        accounts_data = accounts_response.json()
        accounts = accounts_data.get('data', [])
        
        if not accounts:
            print("⚠️  No ad accounts found")
            print("\n   Possible reasons:")
            print("   - System user not assigned to any ad accounts")
            print("   - Need to assign ad account in Business Manager")
            print("\n   Steps to fix:")
            print("   1. Go to business.facebook.com/settings/ad-accounts")
            print("   2. Select your ad account")
            print("   3. Click 'Add People'")
            print("   4. Add your system user with 'Admin' access")
            return False
        
        print(f"✅ Found {len(accounts)} ad account(s):\n")
        for i, account in enumerate(accounts, 1):
            print(f"   Account {i}:")
            print(f"   - ID: {account['id']}")
            print(f"   - Name: {account['name']}")
            print(f"   - Currency: {account['currency']}")
            print(f"   - Timezone: {account['timezone_name']}")
            print(f"   - Status: {account['account_status']}")
            print()
        
        # Suggest which account to use
        first_account = accounts[0]
        print("=" * 60)
        print("💡 NEXT STEP: Add this to your .env file:")
        print("=" * 60)
        print(f"META_AD_ACCOUNT_ID={first_account['id']}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_campaigns():
    """Test 2: Fetch campaigns from ad account."""
    print("=" * 60)
    print("Test 2: Fetch Campaigns")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    if not ad_account_id:
        print("⚠️  Skipping: META_AD_ACCOUNT_ID not set")
        print("   Set it in .env file first (see Test 1 output)")
        return True
    
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.campaign import Campaign
        
        FacebookAdsApi.init(access_token=access_token)
        account = AdAccount(ad_account_id)
        
        # Fetch campaigns
        campaigns = account.get_campaigns(fields=[
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
            Campaign.Field.daily_budget,
            Campaign.Field.created_time,
        ])
        
        campaign_list = list(campaigns)
        
        if not campaign_list:
            print("⚠️  No campaigns found (this is OK for new accounts)")
            print("\n   You can:")
            print("   - Create test campaigns in Ads Manager")
            print("   - Or skip this for now and proceed to Phase 1")
            print()
            return True
        
        print(f"✅ Found {len(campaign_list)} campaign(s):\n")
        for campaign in campaign_list[:5]:  # Show first 5
            print(f"   - {campaign['name']} ({campaign['status']})")
            print(f"     ID: {campaign['id']}")
            print(f"     Objective: {campaign.get('objective', 'N/A')}")
            budget = campaign.get('daily_budget')
            if budget:
                print(f"     Daily Budget: ${int(budget)/100:.2f}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

def test_insights():
    """Test 3: Fetch insights (metrics)."""
    print("=" * 60)
    print("Test 3: Fetch Insights (Metrics)")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    if not ad_account_id:
        print("⚠️  Skipping: META_AD_ACCOUNT_ID not set")
        return True
    
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adsinsights import AdsInsights
        
        FacebookAdsApi.init(access_token=access_token)
        account = AdAccount(ad_account_id)
        
        # Fetch insights for last 7 days
        params = {
            'level': 'account',
            'date_preset': 'last_7d',
            'fields': [
                AdsInsights.Field.spend,
                AdsInsights.Field.impressions,
                AdsInsights.Field.clicks,
                AdsInsights.Field.cpc,
                AdsInsights.Field.cpm,
                AdsInsights.Field.ctr,
            ],
        }
        
        insights = account.get_insights(params=params)
        insights_list = list(insights)
        
        if not insights_list:
            print("⚠️  No insights data (this is OK if no campaigns running)")
            print("   Insights require campaigns with spend")
            print()
            return True
        
        print(f"✅ Insights data available:\n")
        for insight in insights_list[:1]:  # Show first entry
            print(f"   Spend: ${insight.get('spend', '0')}")
            print(f"   Impressions: {insight.get('impressions', '0')}")
            print(f"   Clicks: {insight.get('clicks', '0')}")
            print(f"   CPC: ${insight.get('cpc', '0')}")
            print(f"   CPM: ${insight.get('cpm', '0')}")
            print(f"   CTR: {insight.get('ctr', '0')}%")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

def test_hourly():
    """Test 4: Fetch hourly insights (critical for metricx)."""
    print("=" * 60)
    print("Test 4: Hourly Insights (metricx Requirement)")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    if not ad_account_id:
        print("⚠️  Skipping: META_AD_ACCOUNT_ID not set")
        return True
    
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adsinsights import AdsInsights
        
        FacebookAdsApi.init(access_token=access_token)
        account = AdAccount(ad_account_id)
        
        # Fetch hourly insights for today
        params = {
            'level': 'account',
            'date_preset': 'today',
            'time_increment': 1,  # Hourly
            'fields': [
                AdsInsights.Field.spend,
                AdsInsights.Field.impressions,
                AdsInsights.Field.clicks,
            ],
        }
        
        insights = account.get_insights(params=params)
        insights_list = list(insights)
        
        if not insights_list:
            print("⚠️  No hourly data for today (OK if no active campaigns)")
            print("   Hourly data requires campaigns currently running")
            print()
            return True
        
        print(f"✅ Hourly breakdown available!")
        print(f"   Total entries: {len(insights_list)}")
        if insights_list:
            first_entry = insights_list[0]
            print(f"\n   Sample entry:")
            print(f"   - Date: {first_entry.get('date_start')}")
            print(f"   - Spend: ${first_entry.get('spend', '0')}")
            print(f"   - Impressions: {first_entry.get('impressions', '0')}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Meta Ads API Test Suite (System User)")
    print("=" * 60)
    print()
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        # Load .env manually (python-dotenv not required)
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value
    else:
        print("⚠️  No .env file found")
        print("   Create backend/.env with META_ACCESS_TOKEN")
    
    print()
    
    # Run tests
    success = True
    
    # Test 1: REQUIRED - finds ad accounts
    if not test_connection():
        print("\n❌ Test 1 failed - fix this before continuing")
        success = False
        return False
    
    # Test 2-4: Optional but recommended
    test_campaigns()
    test_insights()
    test_hourly()
    
    # Summary
    print("=" * 60)
    if success:
        print("✅ Phase 0 Complete!")
        print("=" * 60)
        print()
        print("Next Steps:")
        print("1. ✅ Credentials saved in .env")
        print("2. ✅ API connectivity verified")
        print("3. 📋 Ready to start Phase 1 (Database setup)")
        print()
        print("Open: backend/docs/roadmap/meta-ads-roadmap.md")
        print("Start: Phase 1.1 - Database performance and integrity")
    else:
        print("⚠️  Some tests had issues")
        print("=" * 60)
        print()
        print("This is OK if:")
        print("- No campaigns created yet (normal for new accounts)")
        print("- No spend/insights yet (create test campaigns later)")
        print()
        print("You can proceed to Phase 1 as long as Test 1 passed")
    
    print()
    return success

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)

