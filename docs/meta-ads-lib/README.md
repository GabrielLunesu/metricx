# Meta Ads API Integration Documentation

**Purpose**: Central hub for Meta Ads API integration documentation and resources.

---

## 📚 Documentation Index

### 1. **Setup Guide** (START HERE)
**File**: [META_API_SETUP_GUIDE.md](./META_API_SETUP_GUIDE.md)  
**Purpose**: Step-by-step guide to obtain Meta API credentials and verify connectivity  
**Time**: 2-3 hours  
**When**: Complete this BEFORE starting any integration work

**Covers**:
- Developer account creation
- App setup with Marketing API
- Access token generation (3 methods)
- API verification with test script
- SDK installation
- Troubleshooting common issues
- **2025 Update**: Workarounds for test user creation being disabled

---

### 2. **Integration Roadmap**
**File**: [../../backend/docs/roadmap/meta-ads-roadmap.md](../../backend/docs/roadmap/meta-ads-roadmap.md)  
**Purpose**: Phased implementation plan for Meta Ads integration  
**Time**: 4 weeks  
**When**: After completing setup guide

**Phases**:
- **Phase 0**: Meta API access setup (PREREQUISITE - see setup guide)
- **Phase 1**: Database & ingestion fixes (2-3 hours)
- **Phase 2**: Meta API connection (16-22 hours)
- **Phase 3**: Data pipeline (16-22 hours)
- **Phase 4**: Query layer enhancements (12-16 hours)
- **Phase 5**: Testing & validation (8-12 hours)
- **Phase 6**: Production hardening (14-20 hours)

---

### 3. **Meta Marketing API Reference**
**File**: [marketing-api.md](./marketing-api.md)  
**Purpose**: Extracted API documentation from Meta's official docs  
**When**: Reference during implementation

**Contents**:
- API endpoints and parameters
- Request/response examples
- SDK code samples (Python, Ruby, PHP, Java)
- Conversions API examples
- Advantage+ Creative features
- Real Estate Ads specifics

---

## 🎯 Quick Start Checklist

### Before You Start
- [ ] Read setup guide introduction
- [ ] Understand the 3 token generation options
- [ ] Choose your approach (personal account recommended for quick start)

### Setup (2-3 hours)
- [ ] Create Meta Developer account
- [ ] Create app with Marketing API product
- [ ] Generate long-lived access token
- [ ] Verify API access (4 test scenarios)
- [ ] Install Python SDK (`facebook-business==19.0.0`)
- [ ] Run test script and confirm all tests pass

### Integration (4 weeks)
- [ ] Complete Phase 1 (database prep)
- [ ] Complete Phase 2 (Meta connection)
- [ ] Complete Phase 3 (data pipeline)
- [ ] Complete Phase 4 (query layer)
- [ ] Complete Phase 5 (testing)
- [ ] Complete Phase 6 (hardening)

---

## 🔑 Key Resources

### Official Meta Documentation
- [Marketing API Docs](https://developers.facebook.com/docs/marketing-api)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer)
- [Business SDK for Python](https://github.com/facebook/facebook-python-business-sdk)
- [API Changelog](https://developers.facebook.com/docs/graph-api/changelog)

### Tools
- **Graph API Explorer**: Generate tokens, test endpoints
- **Events Manager**: Track conversions, verify events
- **Ads Manager**: Create test campaigns, view data
- **Business Manager**: Manage accounts, create system users

### Support
- [Meta Developer Community](https://developers.facebook.com/community/)
- [Stack Overflow - facebook-graph-api](https://stackoverflow.com/questions/tagged/facebook-graph-api)

---

## ⚠️ Known Issues (2025)

### Test User Creation Disabled
**Issue**: Meta has temporarily disabled test user creation for some apps/regions  
**Impact**: Cannot create test users via traditional method  
**Workaround**: Use personal ad account or system user (see setup guide)  
**Status**: Ongoing as of 2025-10-30

### API Version Updates
**Current**: v19.0 (as of 2025-10-30)  
**Update Frequency**: Quarterly  
**Action Required**: Check changelog every 3 months, update SDK version

---

## 🚨 Important Notes

### Security
- **Never commit tokens to git** - use `.env` file
- **Rotate tokens regularly** - long-lived tokens expire in 60 days
- **Use system users for production** - personal tokens not recommended

### Rate Limits
- **Standard Access**: 200 calls/hour per user
- **Business Access**: Higher limits (requires approval)
- **Recommendation**: Implement rate limiting in Phase 2.2

### Data Freshness
- **Insights API**: Data may be delayed up to 48 hours
- **Real-time data**: Use recent date ranges (today, yesterday)
- **Historical data**: Most accurate after 48-hour window

---

## 📊 Data Formats (2025)

### API Version
Current: **v19.0**  
Update: Quarterly  
Check: [Changelog](https://developers.facebook.com/docs/graph-api/changelog)

### Response Format
All responses are **JSON**

### Hierarchy
```
Ad Account
  └─ Campaign
      └─ Ad Set
          └─ Ad
```

### Key Endpoints

#### 1. Campaigns
```bash
GET /{ad_account_id}/campaigns?fields=id,name,status,objective
```

#### 2. Insights (Daily)
```bash
GET /{ad_account_id}/insights?fields=spend,impressions,clicks&level=campaign
```

#### 3. Insights (Hourly) - **metricx Requirement**
```bash
GET /{ad_account_id}/insights?time_increment=1&level=campaign
```

#### 4. Ad Sets
```bash
GET /{campaign_id}/adsets?fields=id,name,status,optimization_goal
```

#### 5. Ads
```bash
GET /{adset_id}/ads?fields=id,name,status,creative
```

---

## 🛠️ Test Script Usage

### Setup Environment
```bash
cd /Users/gabriellunesu/Git/metricx/backend

# Set credentials (use your actual values)
export META_ACCESS_TOKEN="your_long_lived_token_here"
export META_AD_ACCOUNT_ID="act_1234567890"
```

### Run Tests
```bash
python test_meta_api.py
```

### Expected Output
- ✅ API connection verified
- ✅ Ad account info retrieved
- ⚠️ No campaigns (OK for new accounts)
- ⚠️ No insights (OK if no spend)
- ⚠️ No hourly data (OK if no active campaigns)

---

## 📁 File Structure

```
metricx/
├── docs/
│   └── meta-ads-lib/
│       ├── README.md (this file)
│       ├── META_API_SETUP_GUIDE.md (setup guide)
│       └── marketing-api.md (API reference)
├── backend/
│   ├── docs/
│   │   └── roadmap/
│   │       └── meta-ads-roadmap.md (integration roadmap)
│   ├── test_meta_api.py (test script - to be created in Phase 0)
│   └── app/
│       └── services/
│           └── meta_ads_client.py (to be created in Phase 2)
```

---

## 🎓 Learning Path

### Beginner
1. Read setup guide introduction
2. Create developer account
3. Generate access token (personal account method)
4. Run test script to verify connectivity

### Intermediate
1. Create system user in Business Manager
2. Understand rate limiting
3. Explore Graph API Explorer
4. Test different insights endpoints

### Advanced
1. Apply for Standard Access
2. Implement token refresh logic
3. Set up production monitoring
4. Optimize for rate limits

---

## 📞 Support

### Internal
- **Build Log**: [metricx_BUILD_LOG.md](../metricx_BUILD_LOG.md)
- **Architecture Docs**: `backend/docs/architecture/`
- **QA System**: `backend/docs/QA_SYSTEM_ARCHITECTURE.md`

### External
- **Meta Support**: [developers.facebook.com/support](https://developers.facebook.com/support)
- **Community Forum**: [developers.facebook.com/community](https://developers.facebook.com/community)
- **Bug Reports**: [developers.facebook.com/bugs](https://developers.facebook.com/bugs)

---

## ✅ Success Criteria

### Phase 0 Complete When:
- ✅ Can fetch ad accounts via API
- ✅ Test script runs without errors
- ✅ Token stored securely in `.env`
- ✅ SDK installed and verified

### Integration Complete When:
- ✅ Meta campaigns sync to metricx
- ✅ Hourly metrics ingestion working
- ✅ QA system can query Meta data
- ✅ Rate limiting implemented
- ✅ Error handling and retries working
- ✅ Production monitoring in place

---

**Last Updated**: 2025-10-30  
**Maintainer**: metricx Team  
**Next Review**: Quarterly (API version updates)

