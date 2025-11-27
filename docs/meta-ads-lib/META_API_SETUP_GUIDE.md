# Meta Ads API Setup Guide (2025)

**Purpose**: Step-by-step guide to obtain Meta API credentials and set up test environment for metricx integration.

**Last Updated**: 2025-10-30  
**API Version**: v19.0 (check [changelog](https://developers.facebook.com/docs/graph-api/changelog) quarterly)

---

## Overview

This guide covers:
1. Creating a Meta Developer account and app
2. Generating access tokens (with 2025 workarounds for test users)
3. Getting access to ad accounts for testing
4. Verifying API connectivity
5. Installing and testing the Python SDK

**Estimated Time**: 2-3 hours for complete setup

---

## Phase 0.1: Developer Account & App Creation

### Step 1: Create Meta Developer Account

1. **Navigate to**: [developers.facebook.com](https://developers.facebook.com)
2. **Sign in** with your Facebook/Meta account (or create one)
3. **Complete developer registration**:
   - Accept Developer Terms
   - Verify your account (email/phone)
   - You may need to enable 2-factor authentication

### Step 2: Create a New App

1. **Go to**: [developers.facebook.com/apps](https://developers.facebook.com/apps)
2. **Click**: "Create App"
3. **Select Use Case**: 
   - Choose **"Other"** (or "Business" if available)
   - Click **"Next"**
4. **Select App Type**: 
   - Choose **"Business"**
   - Click **"Next"**
5. **App Details**:
   - **App Name**: `metricx Testing` (or your preference)
   - **App Contact Email**: Your email
   - **Business Account**: Create new or select existing
   - Click **"Create App"**

6. **Note Your Credentials**:
   ```
   App ID: [YOUR_APP_ID]
   App Secret: [Click "Show" to reveal]
   ```
   ⚠️ **Store these securely** - you'll need them for token generation

### Step 3: Add Marketing API Product

1. **In your app dashboard**, scroll to **"Add Products"**
2. **Find "Marketing API"**, click **"Set Up"**
3. **Complete any additional setup steps** (may vary by region)

---

## Phase 0.2: Access Token Generation

### Understanding Token Types

| Token Type | Lifespan | Use Case |
|------------|----------|----------|
| **Short-Lived User Token** | 1-2 hours | Initial testing, Graph API Explorer |
| **Long-Lived User Token** | 60 days | Development, manual testing |
| **System User Token** | Permanent | Production (recommended) |
| **Page Access Token** | 60 days or never expires | If managing pages |

### ⚠️ 2025 Update: Test User Creation Issues

**Problem**: As you discovered, Meta has temporarily disabled test user creation for some apps/regions.

**Workarounds** (choose one):

---

### **Option A: Use Your Personal Ad Account (Recommended for Quick Start)**

This is the **fastest** way to get started in 2025.

#### Step A.1: Generate Access Token via Graph API Explorer

1. **Navigate to**: [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)
2. **Select your app** from the "Meta App" dropdown (top right)
3. **Add Permissions**:
   - Click **"Permissions"** (under "User or Page")
   - Search and enable:
     - ✅ `ads_management`
     - ✅ `ads_read`
     - ✅ `business_management`
     - ✅ `read_insights`
   - Click **"Generate Access Token"**
   - **Log in** and accept permissions

4. **You now have a Short-Lived Token** (1-2 hours)
   - Copy it to a safe place

#### Step A.2: Exchange for Long-Lived Token (60 days)

**Using cURL**:

```bash
curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<YOUR_APP_ID>&client_secret=<YOUR_APP_SECRET>&fb_exchange_token=<SHORT_LIVED_TOKEN>"
```

**Expected Response**:
```json
{
  "access_token": "EAAxxxxxxxxxx",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

**Save this token** - it's valid for 60 days.

#### Step A.3: Create a Test Ad Account (Optional)

If you don't want to use your personal ad account:

1. **Go to**: [business.facebook.com/settings/ad-accounts](https://business.facebook.com/settings/ad-accounts)
2. **Click**: "Add" → "Create a new ad account"
3. **Enter**:
   - **Ad Account Name**: `metricx Testing`
   - **Time Zone**: Your timezone
   - **Currency**: USD (or your preference)
4. **Assign yourself** as account admin
5. **Note the Ad Account ID**: `act_1234567890`

---

### **Option B: System User (Production-Ready, More Setup)**

Use this for **production** or if you need a permanent token.

#### Step B.1: Create System User

1. **Go to**: [business.facebook.com/settings/system-users](https://business.facebook.com/settings/system-users)
   - If you don't have a Business Manager, create one first
2. **Click**: "Add" → "Create a new system user"
3. **Enter**:
   - **Name**: `metricx API`
   - **Role**: Admin or Employee
4. **Click**: "Create System User"

#### Step B.2: Generate System User Token

1. **Click on the system user** you just created
2. **Click**: "Generate New Token"
3. **Select your app**: `metricx Testing`
4. **Select permissions**:
   - ✅ `ads_management`
   - ✅ `ads_read`
   - ✅ `business_management`
   - ✅ `read_insights`
5. **Click**: "Generate Token"
6. **Copy and save** - this token doesn't expire unless revoked

#### Step B.3: Assign Ad Account Access

1. **In Business Settings**, go to **"Ad Accounts"**
2. **Select your ad account** (or create one)
3. **Click**: "Add People"
4. **Add your system user** with "Admin" access

---

### **Option C: Request Standard Access (Long-term Solution)**

For **production** apps, you'll eventually need **Standard Access**.

#### When to Apply:
- After you've built core functionality
- When you need higher rate limits
- When you need production-level access

#### How to Apply:
1. **Go to**: Your app dashboard → "App Review" → "Permissions and Features"
2. **Request**: `ads_management`, `business_management`
3. **Submit**:
   - Screencast showing your use case
   - Explanation of how you use the API
   - Privacy policy URL
   - Terms of service URL

**Timeline**: 3-5 business days for review

---

## Phase 0.3: Verify API Access

### Test 1: Check Token & Get Ad Accounts

**Using cURL**:

```bash
# Test 1a: Verify token is valid
curl -G \
  -d "access_token=<YOUR_ACCESS_TOKEN>" \
  https://graph.facebook.com/v19.0/me

# Expected response:
# {
#   "name": "Your Name",
#   "id": "123456789"
# }
```

```bash
# Test 1b: Get ad accounts
curl -G \
  -d "access_token=<YOUR_ACCESS_TOKEN>" \
  https://graph.facebook.com/v19.0/me/adaccounts

# Expected response:
# {
#   "data": [
#     {
#       "account_id": "1234567890",
#       "id": "act_1234567890",
#       "name": "metricx Testing"
#     }
#   ]
# }
```

**Save your Ad Account ID**: `act_1234567890`

### Test 2: Fetch Campaigns

```bash
curl -G \
  -d "fields=id,name,status,objective,daily_budget,created_time" \
  -d "access_token=<YOUR_ACCESS_TOKEN>" \
  https://graph.facebook.com/v19.0/act_<AD_ACCOUNT_ID>/campaigns

# Expected response (if you have campaigns):
# {
#   "data": [
#     {
#       "id": "123456789",
#       "name": "Test Campaign",
#       "status": "PAUSED",
#       "objective": "OUTCOME_SALES",
#       "daily_budget": "1000",
#       "created_time": "2025-01-15T10:00:00+0000"
#     }
#   ]
# }

# If empty (no campaigns yet):
# {
#   "data": []
# }
```

### Test 3: Fetch Insights (Metrics)

```bash
# Get insights for date range
curl -G \
  -d "fields=spend,impressions,clicks,cpc,cpm,ctr" \
  -d "time_range={'since':'2025-01-01','until':'2025-01-31'}" \
  -d "level=campaign" \
  -d "access_token=<YOUR_ACCESS_TOKEN>" \
  https://graph.facebook.com/v19.0/act_<AD_ACCOUNT_ID>/insights

# Expected response:
# {
#   "data": [
#     {
#       "date_start": "2025-01-01",
#       "date_stop": "2025-01-31",
#       "spend": "150.50",
#       "impressions": "5420",
#       "clicks": "234",
#       "cpc": "0.64",
#       "cpm": "27.78",
#       "ctr": "4.32"
#     }
#   ]
# }
```

### Test 4: Hourly Insights (Critical for metricx)

```bash
# Get hourly breakdown for today
curl -G \
  -d "fields=spend,impressions,clicks" \
  -d "date_preset=today" \
  -d "time_increment=1" \
  -d "level=campaign" \
  -d "access_token=<YOUR_ACCESS_TOKEN>" \
  https://graph.facebook.com/v19.0/act_<AD_ACCOUNT_ID>/insights

# Expected response:
# {
#   "data": [
#     {
#       "date_start": "2025-10-30",
#       "date_stop": "2025-10-30",
#       "spend": "12.50",
#       "impressions": "450",
#       "clicks": "18",
#       "hourly_stats_aggregated_by_advertiser_time_zone": "00:00:00"
#     },
#     {
#       "date_start": "2025-10-30",
#       "date_stop": "2025-10-30",
#       "spend": "15.75",
#       "impressions": "523",
#       "clicks": "22",
#       "hourly_stats_aggregated_by_advertiser_time_zone": "01:00:00"
#     }
#   ]
# }
```

---

## Phase 0.4: SDK Installation & Testing

### Step 1: Install Facebook Business SDK

In your metricx backend directory:

```bash
cd /Users/gabriellunesu/Git/metricx/backend

# Activate virtual environment
source bin/activate

# Install SDK (match API version)
pip install facebook-business==19.0.0

# Verify installation
pip list | grep facebook-business
```

### Step 2: Update requirements.txt

```bash
# Add to backend/requirements.txt
echo "facebook-business==19.0.0" >> requirements.txt
```

### Step 3: Create Test Script

Create `backend/test_meta_api.py`:

```python
"""
Test Meta Ads API connectivity and SDK functionality.

Usage:
    python test_meta_api.py

Environment Variables Required:
    META_ACCESS_TOKEN: Your long-lived access token
    META_AD_ACCOUNT_ID: Your ad account ID (e.g., act_1234567890)
"""

import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adsinsights import AdsInsights

def test_connection():
    """Test 1: Verify API connection and credentials."""
    print("=" * 60)
    print("Test 1: API Connection")
    print("=" * 60)
    
    # Get credentials from environment
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    if not access_token or not ad_account_id:
        print("❌ ERROR: Missing environment variables")
        print("   Set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID")
        return False
    
    # Initialize SDK
    FacebookAdsApi.init(access_token=access_token)
    
    # Get account info
    account = AdAccount(ad_account_id)
    account_info = account.api_get(fields=[
        'id',
        'name',
        'currency',
        'timezone_name',
        'account_status',
    ])
    
    print(f"✅ Connected to Ad Account:")
    print(f"   ID: {account_info['id']}")
    print(f"   Name: {account_info['name']}")
    print(f"   Currency: {account_info['currency']}")
    print(f"   Timezone: {account_info['timezone_name']}")
    print(f"   Status: {account_info['account_status']}")
    print()
    
    return True

def test_campaigns():
    """Test 2: Fetch campaigns."""
    print("=" * 60)
    print("Test 2: Fetch Campaigns")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
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
        print("   You can create test campaigns in Ads Manager")
        print()
        return True
    
    print(f"✅ Found {len(campaign_list)} campaign(s):")
    for campaign in campaign_list[:5]:  # Show first 5
        print(f"   - {campaign['name']} ({campaign['status']})")
        print(f"     ID: {campaign['id']}")
        print(f"     Objective: {campaign.get('objective', 'N/A')}")
    print()
    
    return True

def test_insights():
    """Test 3: Fetch insights (metrics)."""
    print("=" * 60)
    print("Test 3: Fetch Insights")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    FacebookAdsApi.init(access_token=access_token)
    account = AdAccount(ad_account_id)
    
    # Fetch insights for last 7 days
    params = {
        'level': 'campaign',
        'time_range': {
            'since': '2025-01-01',
            'until': '2025-01-31'
        },
        'fields': [
            AdsInsights.Field.campaign_id,
            AdsInsights.Field.campaign_name,
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
        print("⚠️  No insights data found (this is OK if no campaigns running)")
        print("   Insights require active campaigns with spend")
        print()
        return True
    
    print(f"✅ Found insights for {len(insights_list)} campaign(s):")
    for insight in insights_list[:3]:  # Show first 3
        print(f"   - {insight.get('campaign_name', 'Unknown')}")
        print(f"     Spend: ${insight.get('spend', '0')}")
        print(f"     Impressions: {insight.get('impressions', '0')}")
        print(f"     Clicks: {insight.get('clicks', '0')}")
        print(f"     CPC: ${insight.get('cpc', '0')}")
    print()
    
    return True

def test_hourly_insights():
    """Test 4: Fetch hourly insights (critical for metricx)."""
    print("=" * 60)
    print("Test 4: Hourly Insights (metricx Requirement)")
    print("=" * 60)
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    
    FacebookAdsApi.init(access_token=access_token)
    account = AdAccount(ad_account_id)
    
    # Fetch hourly insights for today
    params = {
        'level': 'campaign',
        'date_preset': 'today',
        'time_increment': 1,  # Hourly
        'fields': [
            AdsInsights.Field.campaign_id,
            AdsInsights.Field.spend,
            AdsInsights.Field.impressions,
            AdsInsights.Field.clicks,
        ],
    }
    
    insights = account.get_insights(params=params)
    insights_list = list(insights)
    
    if not insights_list:
        print("⚠️  No hourly data for today (this is OK if no active campaigns)")
        print("   Hourly data requires campaigns currently running with spend")
        print()
        return True
    
    print(f"✅ Hourly breakdown available:")
    print(f"   Total entries: {len(insights_list)}")
    if insights_list:
        first_entry = insights_list[0]
        print(f"   Sample entry:")
        print(f"     Date: {first_entry.get('date_start')}")
        print(f"     Spend: ${first_entry.get('spend', '0')}")
        print(f"     Impressions: {first_entry.get('impressions', '0')}")
    print()
    
    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Meta Ads API Test Suite")
    print("=" * 60)
    print()
    
    try:
        # Run tests
        test_connection()
        test_campaigns()
        test_insights()
        test_hourly_insights()
        
        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        print()
        print("Next Steps:")
        print("1. Review the output above")
        print("2. If no campaigns, create test campaigns in Ads Manager")
        print("3. Proceed to Phase 1 of meta-ads-roadmap.md")
        print()
        
    except Exception as e:
        print("=" * 60)
        print("❌ Test failed with error:")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")
        print()
        print("Common issues:")
        print("- Invalid access token (check expiration)")
        print("- Wrong ad account ID format (should be 'act_123456789')")
        print("- Missing permissions (need ads_management, ads_read)")
        print("- Rate limiting (wait and retry)")
        print()
        return False

if __name__ == '__main__':
    main()
```

### Step 4: Run Tests

```bash
# Set environment variables
export META_ACCESS_TOKEN="your_long_lived_token_here"
export META_AD_ACCOUNT_ID="act_1234567890"

# Run test script
python test_meta_api.py
```

**Expected Output**:
```
============================================================
Meta Ads API Test Suite
============================================================

============================================================
Test 1: API Connection
============================================================
✅ Connected to Ad Account:
   ID: act_1234567890
   Name: metricx Testing
   Currency: USD
   Timezone: America/Los_Angeles
   Status: 1

============================================================
Test 2: Fetch Campaigns
============================================================
⚠️  No campaigns found (this is OK for new accounts)
   You can create test campaigns in Ads Manager

============================================================
Test 3: Fetch Insights
============================================================
⚠️  No insights data found (this is OK if no campaigns running)
   Insights require active campaigns with spend

============================================================
Test 4: Hourly Insights (metricx Requirement)
============================================================
⚠️  No hourly data for today (this is OK if no active campaigns)
   Hourly data requires campaigns currently running with spend

============================================================
✅ All tests completed successfully!
============================================================
```

---

## Phase 0.5: Create Test Campaigns (Optional)

If you want realistic test data:

### Option 1: Create via Ads Manager UI

1. **Go to**: [business.facebook.com/adsmanager](https://business.facebook.com/adsmanager)
2. **Click**: "Create" → "Campaign"
3. **Select**: Any objective (e.g., "Sales")
4. **Set**:
   - **Campaign Name**: `Test Campaign 1`
   - **Budget**: $10/day (minimum)
   - **Schedule**: Ongoing
5. **Create Ad Set** and **Ad** (follow wizard)
6. **Pause immediately** to avoid spending money

### Option 2: Create via API (Advanced)

```python
from facebook_business.adobjects.campaign import Campaign

# Create campaign
campaign = Campaign(parent_id='act_1234567890')
campaign[Campaign.Field.name] = 'API Test Campaign'
campaign[Campaign.Field.objective] = Campaign.Objective.outcome_sales
campaign[Campaign.Field.status] = Campaign.Status.paused
campaign[Campaign.Field.special_ad_categories] = []

campaign.remote_create()
print(f"Created campaign: {campaign['id']}")
```

---

## Security Best Practices

### 1. Store Credentials Securely

Create `backend/.env` (already in your `.gitignore`):

```bash
# Meta Ads API Credentials
META_ACCESS_TOKEN=your_long_lived_token_here
META_APP_ID=your_app_id_here
META_APP_SECRET=your_app_secret_here
META_AD_ACCOUNT_ID=act_1234567890

# Token expiration tracking
META_TOKEN_EXPIRES_AT=2025-03-30T00:00:00Z
```

### 2. Never Commit Tokens

Verify `.gitignore` includes:

```gitignore
# Backend environment
backend/.env
backend/cookies.txt
*.log

# Secrets
*.secret
*_token.txt
```

### 3. Implement Token Refresh

For production, implement automatic token refresh:

```python
# backend/app/services/meta_token_refresh.py
import requests
from datetime import datetime, timedelta

def refresh_long_lived_token(current_token, app_id, app_secret):
    """
    Exchange current long-lived token for a new one.
    Should be called ~30 days before expiration.
    """
    url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': current_token
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'access_token' in data:
        return {
            'token': data['access_token'],
            'expires_at': datetime.now() + timedelta(days=60)
        }
    else:
        raise Exception(f"Token refresh failed: {data}")
```

---

## Troubleshooting

### Issue: "Test user creation temporarily disabled"

**Solution**: Use Option A (personal account) or Option B (system user) instead.

### Issue: "Invalid OAuth 2.0 Access Token"

**Causes**:
- Token expired (check expiration date)
- Wrong app selected in Graph API Explorer
- Token revoked manually

**Solution**: Generate new token via Graph API Explorer

### Issue: "Insufficient permissions"

**Causes**:
- Missing `ads_management` or `ads_read` permissions
- App not approved for Standard Access (if needed)

**Solution**: 
1. Regenerate token with correct permissions
2. Or apply for Standard Access in App Review

### Issue: "Ad Account Not Found"

**Causes**:
- Wrong ad account ID format (must be `act_1234567890`, not `1234567890`)
- Account not accessible with current token
- Account disabled

**Solution**:
1. Verify format: `act_` prefix required
2. Check account access in Business Manager
3. Verify account status is active

### Issue: Rate Limit Errors

**Error**: `(#17) User request limit reached`

**Solution**:
- Implement rate limiting (see Phase 2.2 in roadmap)
- Wait 1 hour and retry
- Apply for Standard Access for higher limits

### Issue: No Insights Data

**Causes**:
- No campaigns running
- No spend in selected time range
- Insights data delayed (up to 48 hours for complete data)

**Solution**:
- Create test campaigns with small budget
- Use recent date ranges
- Wait 24-48 hours for historical data

---

## Next Steps

✅ **You've completed Phase 0 when**:
- You have a working access token
- You can fetch ad accounts via API
- You can fetch campaigns (even if empty)
- Python SDK installed and tested

📋 **Ready to proceed to**:
- [Phase 1: Foundational Fixes](../backend/docs/roadmap/meta-ads-roadmap.md#phase-1-foundational-fixes-preMeta)

---

## Additional Resources

### Official Documentation
- [Marketing API Docs](https://developers.facebook.com/docs/marketing-api)
- [Business SDK for Python](https://github.com/facebook/facebook-python-business-sdk)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer)
- [Changelog](https://developers.facebook.com/docs/graph-api/changelog)

### Rate Limits
- [Platform Rate Limits](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)
- Standard Access: 200 calls/hour
- Business Use Case: Higher limits (requires approval)

### Community
- [Stack Overflow - facebook-graph-api](https://stackoverflow.com/questions/tagged/facebook-graph-api)
- [Meta Developer Community](https://developers.facebook.com/community/)

---

## Appendix: JSON Response Schemas

### Campaign Response
```json
{
  "data": [
    {
      "id": "123456789",
      "name": "Holiday Campaign",
      "status": "ACTIVE",
      "objective": "OUTCOME_SALES",
      "daily_budget": "10000",
      "lifetime_budget": null,
      "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
      "created_time": "2025-01-15T10:00:00+0000",
      "updated_time": "2025-01-20T15:30:00+0000",
      "start_time": "2025-01-15T10:00:00+0000",
      "stop_time": null,
      "special_ad_categories": []
    }
  ],
  "paging": {
    "cursors": {
      "before": "...",
      "after": "..."
    }
  }
}
```

### Insights Response (Daily)
```json
{
  "data": [
    {
      "campaign_id": "123456789",
      "campaign_name": "Holiday Campaign",
      "date_start": "2025-01-20",
      "date_stop": "2025-01-20",
      "spend": "150.50",
      "impressions": "5420",
      "clicks": "234",
      "actions": [
        {
          "action_type": "purchase",
          "value": "12"
        },
        {
          "action_type": "add_to_cart",
          "value": "45"
        }
      ],
      "action_values": [
        {
          "action_type": "purchase",
          "value": "1250.00"
        }
      ],
      "cpc": "0.64",
      "cpm": "27.68",
      "ctr": "4.32",
      "cost_per_action_type": [
        {
          "action_type": "purchase",
          "value": "12.54"
        }
      ]
    }
  ]
}
```

### Insights Response (Hourly)
```json
{
  "data": [
    {
      "campaign_id": "123456789",
      "date_start": "2025-10-30",
      "date_stop": "2025-10-30",
      "hourly_stats_aggregated_by_advertiser_time_zone": "00:00:00",
      "spend": "12.50",
      "impressions": "450",
      "clicks": "18",
      "cpc": "0.69",
      "cpm": "27.78",
      "ctr": "4.00"
    },
    {
      "campaign_id": "123456789",
      "date_start": "2025-10-30",
      "date_stop": "2025-10-30",
      "hourly_stats_aggregated_by_advertiser_time_zone": "01:00:00",
      "spend": "15.75",
      "impressions": "523",
      "clicks": "22",
      "cpc": "0.72",
      "cpm": "30.11",
      "ctr": "4.21"
    }
  ]
}
```

### Ad Set Response
```json
{
  "data": [
    {
      "id": "987654321",
      "name": "US Audience - 18-35",
      "campaign_id": "123456789",
      "status": "ACTIVE",
      "daily_budget": "5000",
      "optimization_goal": "OFFSITE_CONVERSIONS",
      "billing_event": "IMPRESSIONS",
      "bid_amount": 250,
      "targeting": {
        "geo_locations": {
          "countries": ["US"]
        },
        "age_min": 18,
        "age_max": 35
      },
      "created_time": "2025-01-15T10:05:00+0000",
      "updated_time": "2025-01-20T15:30:00+0000"
    }
  ]
}
```

### Ad Response
```json
{
  "data": [
    {
      "id": "555666777",
      "name": "Ad Creative 1",
      "adset_id": "987654321",
      "campaign_id": "123456789",
      "status": "ACTIVE",
      "creative": {
        "id": "111222333",
        "title": "Shop Now",
        "body": "Limited time offer",
        "image_url": "https://..."
      },
      "created_time": "2025-01-15T10:10:00+0000",
      "updated_time": "2025-01-20T15:30:00+0000"
    }
  ]
}
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-30  
**Author**: metricx Team  
**Next Review**: Quarterly (check API version updates)

