# Meta OAuth Implementation Guide

## 📋 Overview

This guide walks you through implementing Meta (Facebook) OAuth authentication for metricx, following the same pattern as our Google OAuth implementation. This allows users to connect their Meta ad accounts without manual token setup.

**Estimated Time**: 12-18 hours total
- Backend: 6-8 hours
- Frontend: 4-6 hours  
- Meta Dashboard Setup: 2-4 hours

---

## ✅ Prerequisites

Before starting, ensure you have:
- ✅ Meta Developer account (create at [developers.facebook.com](https://developers.facebook.com))
- ✅ Meta App created with Marketing API product added
- ✅ Privacy Policy and Terms of Service published (same as Google OAuth)
- ✅ Backend token encryption working (Phase 2.1 complete)
- ✅ Redis configured (for temporary OAuth session storage)

---

## 🎯 Step 1: Meta Dashboard Configuration

### 1.1 Create/Configure Meta App

**Navigate to**: [developers.facebook.com/apps](https://developers.facebook.com/apps)

1. **If you don't have an app yet**:
   - Click "Create App"
   - Select **"Business"** as app type
   - App Name: `metricx`
   - App Contact Email: `[Your Support Email]`
   - Click "Create App"

2. **If you already have an app**:
   - Select your existing app from the dashboard

3. **Add Marketing API Product**:
   - In app dashboard, find "Add Products" section
   - Find "Marketing API" and click "Set Up"
   - Complete any additional setup steps

### 1.2 Configure OAuth Settings

**Navigate to**: [developers.facebook.com/apps/YOUR_APP_ID/settings/basic](https://developers.facebook.com/apps)

**App Domains**:
- Add: `metricx.ai`
- Add: `www.metricx.ai`
- Add: `api.metricx.ai`

**Privacy Policy URL**:
- `https://www.metricx.ai/privacy`

**Terms of Service URL**:
- `https://www.metricx.ai/terms`

**App Icon**:
- Upload: `ui/public/metricx.png`

**Category**:
- Select: "Business" or "Advertising"

**Save Changes**

### 1.3 Configure OAuth Redirect URIs

https://api.metricx.ai/auth/meta/callback
http://localhost:8000/auth/meta/callback
- For local testing, use `localhost:8000`

**Save Changes**

### 1.4 Get App Credentials

**Navigate to**: [developers.facebook.com/apps/YOUR_APP_ID/settings/basic](https://developers.facebook.com/apps/YOUR_APP_ID/settings/basic)

**Note down**:
- **App ID**: `[YOUR_APP_ID]`
- **App Secret**: Click "Show" to reveal `[YOUR_APP_SECRET]`

⚠️ **Store these securely** - you'll need them for environment variables.

### 1.5 Request Required Permissions

**Navigate to**: [developers.facebook.com/apps/YOUR_APP_ID/permissions](https://developers.facebook.com/apps/YOUR_APP_ID/permissions)

**Required Permissions** (for Marketing API):
- ✅ `ads_management` - Manage ads
- ✅ `ads_read` - Read ads data
- ✅ `business_management` - Access Business Manager
- ✅ `read_insights` - Read ad insights/analytics

**Note**: 
- **Standard Access**: Automatically granted for development/testing
- **Advanced Access**: Requires App Review (needed for production)

**For Development**:
- Standard access is sufficient to test OAuth flow
- You can test with your own ad accounts

**For Production**:
- You'll need to submit for App Review to get Advanced Access
- See Step 5 for App Review requirements

---

## 🔧 Step 2: Backend Implementation

### 2.1 Create Meta OAuth Router

**File**: `backend/app/routers/meta_oauth.py`

This will follow the same pattern as `google_oauth.py`:

**Endpoints to implement**:
1. `GET /auth/meta/authorize` - Redirects to Meta OAuth consent screen
2. `GET /auth/meta/callback` - Handles OAuth callback, exchanges code for token
3. `GET /auth/meta/accounts` - Lists available ad accounts for selection
4. `POST /auth/meta/connect-selected` - Creates connections for selected accounts

**Key differences from Google OAuth**:
- Meta uses `https://www.facebook.com/v24.0/dialog/oauth` for authorization
- Token exchange uses `https://graph.facebook.com/v24.0/oauth/access_token`
- Ad accounts are fetched via `/me/adaccounts` endpoint
- Long-lived tokens require exchange from short-lived tokens

# Meta OAuth Configuration
META_APP_ID="[YOUR_APP_ID]" 
META_APP_SECRET="[YOUR_APP_SECRET]"
META_OAUTH_REDIRECT_URI="https://api.metricx.ai/auth/meta/callback"

# For local testing:
# META_OAUTH_REDIRECT_URI="http://localhost:8000/auth/meta/callback"
```

### 2.3 OAuth Flow Details

**Authorization URL**:
```
https://www.facebook.com/v24.0/dialog/oauth?
  client_id={app-id}
  &redirect_uri={redirect-uri}
  &scope={comma-separated-scopes}
  &state={state-parameter}
  &response_type=code
```

**Required Scopes**:
```
ads_management,ads_read,business_management,read_insights
```

**Token Exchange**:
```
POST https://graph.facebook.com/v24.0/oauth/access_token
  client_id={app-id}
  &redirect_uri={redirect-uri}
  &client_secret={app-secret}
  &code={authorization-code}
```

**Response**:
```json
{
  "access_token": "EAA...",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

**Note**: Meta tokens are typically long-lived (60 days) but can be extended. Short-lived tokens (1-2 hours) need to be exchanged for long-lived tokens.

**Exchange Short-Lived to Long-Lived**:
```
GET https://graph.facebook.com/v24.0/oauth/access_token?
  grant_type=fb_exchange_token
  &client_id={app-id}
  &client_secret={app-secret}
  &fb_exchange_token={short-lived-token}
```

### 2.4 Fetch Ad Accounts

After getting access token, fetch user's ad accounts:

```
GET https://graph.facebook.com/v24.0/me/adaccounts?
  fields=id,name,account_id,currency,timezone_name
  &access_token={access-token}
```

**Response**:
```json
{
  "data": [
    {
      "id": "act_123456789",
      "name": "My Ad Account",
      "account_id": "123456789",
      "currency": "USD",
      "timezone_name": "America/New_York"
    }
  ]
}
```

### 2.5 Register Router

**File**: `backend/app/main.py`

Add:
```python
from .routers import meta_oauth as meta_oauth_router

app.include_router(meta_oauth_router.router, prefix="/auth/meta", tags=["Meta OAuth"])
```

---

## 🎨 Step 3: Frontend Implementation

### 3.1 Create MetaConnectButton Component

**File**: `ui/components/MetaConnectButton.jsx`

Follow the same pattern as `GoogleConnectButton.jsx`:

**Features**:
- "Connect Meta Ads" button
- Redirects to backend `/auth/meta/authorize` endpoint
- Handles callback with success/error states
- Shows account selection modal if multiple accounts

### 3.2 Create MetaAccountSelectionModal Component

**File**: `ui/components/MetaAccountSelectionModal.jsx`

Similar to `GoogleAccountSelectionModal.jsx`:

**Features**:
- Lists all available Meta ad accounts
- Allows user to select which accounts to connect
- Shows account name, ID, currency, timezone
- Calls `/auth/meta/connect-selected` endpoint

### 3.3 Update Settings Page

**File**: `ui/app/(dashboard)/settings/page.jsx`

Add Meta OAuth button alongside Google OAuth button:

```jsx
<MetaConnectButton onConnectionComplete={refreshConnections} />
```

---

## 🧪 Step 4: Testing

### 4.1 Local Testing

1. **Start Backend**:
   ```bash
   cd backend
   source bin/activate
   python start_api.py
   ```

2. **Start Frontend**:
   ```bash
   cd ui
   npm run dev
   ```

3. **Test OAuth Flow**:
   - Visit `http://localhost:3000`
   - Login/Register
   - Navigate to Settings
   - Click "Connect Meta Ads"
   - Complete Meta OAuth flow
   - Select ad accounts
   - Verify connections appear in Settings

### 4.2 Test Endpoints Manually

**1. Test Authorize Endpoint**:
```bash
# Login first to get cookie
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt

# Test authorize (will redirect to Meta)
curl -L http://localhost:8000/auth/meta/authorize \
  -b cookies.txt \
  -v
```

**2. Test Callback Error Handling**:
```bash
curl http://localhost:8000/auth/meta/callback?error=access_denied \
  -v
```

### 4.3 Verify Token Storage

After successful connection:
```bash
# Check tokens table (should show encrypted tokens)
psql $DATABASE_URL -c "SELECT provider, scope, expires_at FROM tokens WHERE provider='meta';"

# Check connections table
psql $DATABASE_URL -c "SELECT provider, name, external_account_id FROM connections WHERE provider='meta';"
```

---

## 📝 Step 5: App Review (For Production)

**When**: Before deploying to production

**Navigate to**: [developers.facebook.com/apps/YOUR_APP_ID/app-review](https://developers.facebook.com/apps/YOUR_APP_ID/app-review)

### 5.1 Required Information

**App Details**:
- App Name: `metricx`
- Category: Business/Advertising
- Privacy Policy: `https://www.metricx.ai/privacy`
- Terms of Service: `https://www.metricx.ai/terms`

**Permissions Justification**:

**`ads_management`**:
```
metricx is a marketing analytics platform that helps businesses manage and optimize their Meta ad campaigns.

We require ads_management permission to:
- Create and edit ad campaigns, ad sets, and ads
- Update campaign budgets and targeting
- Pause/resume campaigns
- Provide campaign management features within our platform

Users explicitly grant permission through OAuth and can disconnect accounts at any time.
```

**`ads_read`**:
```
We require ads_read permission to:
- Read campaign data, ad sets, ads, and performance metrics
- Sync campaign structure and performance data into our platform
- Provide unified reporting and analytics across multiple ad platforms
- Calculate ROI, ROAS, and other key performance indicators

Users explicitly grant permission through OAuth and can select which ad accounts to connect.
```

**`business_management`**:
```
We require business_management permission to:
- Access Business Manager accounts and ad accounts
- List available ad accounts for user selection
- Manage connections between metricx and Meta Business Manager

Users explicitly grant permission through OAuth and can disconnect accounts at any time.
```

**`read_insights`**:
```
We require read_insights permission to:
- Read ad performance metrics (impressions, clicks, spend, conversions)
- Sync historical performance data for analysis
- Provide analytics and reporting features
- Calculate performance metrics and trends

Users explicitly grant permission through OAuth and can disconnect accounts at any time.
```

### 5.2 Verification Video

**Create a 3-5 minute demo video** showing:

**Part 1: Introduction (30 seconds)**
- Show metricx homepage
- Show Privacy Policy and Terms links
- Navigate to Settings page

**Part 2: OAuth Flow (1-2 minutes)**
- Click "Connect Meta Ads" button
- Show Meta OAuth consent screen (highlight requested permissions)
- Complete OAuth flow
- Show account selection modal (if multiple accounts)
- Select accounts to connect
- Show success message

**Part 3: Data Usage (1-2 minutes)**
- Click "Sync Meta Ads" on connected account
- Show sync process completing
- Navigate to campaigns/analytics page
- Show Meta campaigns and metrics
- Demonstrate how data is used for reporting

**Part 4: Security & Compliance (30 seconds)**
- Show that tokens are encrypted
- Show account deletion feature
- Highlight Privacy Policy compliance

**Upload Video**:
- Upload to YouTube as **Unlisted**
- Or upload to Google Drive with shareable link
- Include URL in App Review submission

### 5.3 Submit for Review

1. Go to App Review → Permissions and Features
2. Click "Request Advanced Access" for each permission
3. Fill out justification forms
4. Upload verification video
5. Submit for review

**Review Time**: Typically 3-7 business days

---

## 🔒 Step 6: Security Checklist

- [ ] Tokens encrypted at rest (using `token_service`)
- [ ] HTTPS enforced in production
- [ ] Secure HTTP-only cookies for authentication
- [ ] CORS configured for production domain
- [ ] State parameter in OAuth flow (CSRF protection)
- [ ] No tokens logged or exposed in responses
- [ ] User data deletion capability (GDPR compliance)
- [ ] Privacy policy and ToS published
- [ ] App Secret stored securely (never in code)

---

## 📚 Step 7: Implementation Reference

### Backend Files Created/Modified

**New Files**:
- ✅ `backend/app/routers/meta_oauth.py` - OAuth endpoints (complete)
- ⏳ `backend/test_meta_oauth.py` - OAuth test script (optional)

**Modified Files**:
- ✅ `backend/app/main.py` - Registered meta_oauth router
- ✅ `backend/app/routers/connections.py` - Enhanced deletion cascade
- ✅ `backend/.env` - Add Meta OAuth credentials

### Frontend Files Created/Modified

**New Files**:
- ✅ `ui/components/MetaConnectButton.jsx` - Connect button component (complete)
- ✅ `ui/components/MetaAccountSelectionModal.jsx` - Account selection modal (complete)

**Modified Files**:
- ✅ `ui/app/(dashboard)/settings/page.jsx` - Added Meta OAuth button
- ✅ `ui/lib/api.js` - Uses existing connection API functions

### Database

**No new migrations needed** - Uses existing:
- `Connection` model (provider='meta')
- `Token` model (encrypted storage)
- Redis (for temporary OAuth session storage)

---

## 🎯 Step 8: Implementation Checklist

### Backend Implementation
- [x] Create `meta_oauth.py` router
- [x] Implement `/auth/meta/authorize` endpoint
- [x] Implement `/auth/meta/callback` endpoint
- [x] Implement `/auth/meta/accounts` endpoint
- [x] Implement `/auth/meta/connect-selected` endpoint
- [x] Add token exchange (short-lived → long-lived)
- [x] Add ad account fetching logic
- [x] Register router in `main.py`
- [x] Add environment variables
- [x] Add error handling and logging
- [x] Add account deduplication (by numeric account_id)
- [x] Fix connection deletion cascade (proper FK order)

### Frontend Implementation
- [x] Create `MetaConnectButton.jsx` component
- [x] Create `MetaAccountSelectionModal.jsx` component
- [x] Update Settings page with Meta button
- [x] Add success/error message handling
- [x] Add connection refresh after OAuth
- [x] Show "Already Connected" badge for existing accounts
- [x] Disable selection for already-connected accounts

### Meta Dashboard Setup
- [x] Create/configure Meta App
- [x] Add Marketing API product
- [x] Configure OAuth redirect URIs
- [x] Get App ID and App Secret
- [x] Request required permissions
- [x] Configure app domains
- [x] Add Privacy Policy and ToS URLs

### Testing
- [x] Test OAuth flow locally
- [x] Test with single ad account
- [x] Test with multiple ad accounts
- [x] Test error handling
- [x] Verify token encryption
- [x] Verify connection creation
- [x] Test sync functionality with OAuth tokens
- [x] Test account deduplication
- [x] Test connection deletion with cascade

### Production Preparation
- [x] Update environment variables for production
- [x] Configure production redirect URIs
- [ ] Submit App Review (if needed)
- [ ] Wait for App Review approval
- [ ] Deploy to production
- [ ] Test OAuth flow on production

---

## 🚀 Quick Start Commands

### Backend Setup
```bash
cd backend
source bin/activate

# Add to .env:
# META_APP_ID="your-app-id"
# META_APP_SECRET="your-app-secret"
# META_OAUTH_REDIRECT_URI="http://localhost:8000/auth/meta/callback"

python start_api.py
```

### Frontend Setup
```bash
cd ui
npm run dev
```

### Test OAuth Flow
1. Visit `http://localhost:3000`
2. Login/Register
3. Go to Settings
4. Click "Connect Meta Ads"
5. Complete OAuth flow

---

## 📖 Key Differences: Meta vs Google OAuth

| Aspect | Google OAuth | Meta OAuth |
|--------|-------------|------------|
| **Authorization URL** | `accounts.google.com/o/oauth2/v2/auth` | `www.facebook.com/v24.0/dialog/oauth` |
| **Token Exchange** | `oauth2.googleapis.com/token` | `graph.facebook.com/v24.0/oauth/access_token` |
| **Scopes Format** | Space-separated | Comma-separated |
| **Token Lifespan** | Refresh token (permanent) | Long-lived (60 days, extendable) |
| **Account Structure** | MCC → Child Accounts | Direct Ad Accounts |
| **Account Fetching** | Google Ads API | Graph API `/me/adaccounts` |
| **State Parameter** | Required (CSRF protection) | Required (CSRF protection) |

---

## 🐛 Troubleshooting

### Common Issues

**1. "Invalid OAuth Redirect URI"**
- **Solution**: Ensure redirect URI matches exactly in Meta App settings
- Check: No trailing slashes, correct protocol (http/https)

**2. "App Not Setup: This app is still in development mode"**
- **Solution**: Add test users in App Dashboard → Roles → Test Users
- Or: Submit for App Review to make app public

**3. "Invalid App ID or App Secret"**
- **Solution**: Double-check environment variables
- Ensure no extra spaces or quotes

**4. "Missing Required Permissions"**
- **Solution**: Ensure all required permissions are requested in OAuth scope
- Check: `ads_management,ads_read,business_management,read_insights`

**5. "Token Exchange Failed"**
- **Solution**: Ensure authorization code hasn't expired (codes expire quickly)
- Check: Redirect URI matches exactly

---

## 📞 Support Resources

**Meta Developer Resources**:
- [Meta Marketing API Docs](https://developers.facebook.com/docs/marketing-api)
- [OAuth Authentication Guide](https://developers.facebook.com/docs/marketing-api/get-started/authentication)
- [App Review Guide](https://developers.facebook.com/docs/app-review)
- [Meta Developer Community](https://developers.facebook.com/community)

**Internal References**:
- `docs/GOOGLE_OAUTH_IMPLEMENTATION.md` - Google OAuth implementation (similar pattern)
- `backend/app/routers/google_oauth.py` - Google OAuth router (reference implementation)
- `docs/living-docs/META_INTEGRATION_STATUS.md` - Meta integration status

---

## ✅ Next Steps After Implementation

1. **Test thoroughly** with real Meta ad accounts
2. **Monitor logs** for any OAuth errors
3. **Submit App Review** if deploying to production
4. **Update documentation** with any learnings
5. **Consider token refresh** automation (if needed)

---

**Last Updated**: 2025-01-XX  
**Status**: ✅ Complete  
**Current Phase**: Implementation → Production Ready

---

## ✅ Implementation Complete

### What Was Implemented

**Backend** (`backend/app/routers/meta_oauth.py`):
- ✅ OAuth authorization endpoint (`GET /auth/meta/authorize`)
- ✅ OAuth callback endpoint (`GET /auth/meta/callback`)
- ✅ Account listing endpoint (`GET /auth/meta/accounts`)
- ✅ Account connection endpoint (`POST /auth/meta/connect-selected`)
- ✅ Token exchange (short-lived → long-lived)
- ✅ Ad account fetching via Meta Graph API
- ✅ Account deduplication (prevents duplicate connections from Business portfolios)
- ✅ Token encryption and storage
- ✅ Connection deletion with proper cascade (P&L → MetricFacts → Entities → Imports → Fetches → Connection → Token)

**Frontend**:
- ✅ `MetaConnectButton.jsx` - OAuth initiation button
- ✅ `MetaAccountSelectionModal.jsx` - Account selection modal
- ✅ Settings page integration
- ✅ "Already Connected" badge for existing accounts
- ✅ Disabled selection for already-connected accounts

**Key Features**:
- ✅ Account deduplication: Prevents duplicate connections when same account appears through direct ownership + Business portfolio
- ✅ Cascade deletion: Properly deletes all related data (entities, metrics, tokens) when connection is deleted
- ✅ Token management: Encrypted storage, long-lived token exchange
- ✅ Error handling: Comprehensive error messages for all failure cases

### Known Issues Fixed

1. **Duplicate Accounts**: Fixed by deduplicating accounts by numeric `account_id` before showing in selection modal
2. **Deletion Cascade**: Fixed FK constraint violations by deleting in correct order:
   - P&L snapshots → Metric facts → Entities → Imports → Fetches → Connection → Token
3. **Token Deletion**: Fixed by deleting connection before token to remove FK reference

### Next Steps

1. **App Review**: Submit for Meta App Review if deploying to production
2. **Production Testing**: Test OAuth flow on production domain
3. **Token Refresh**: Consider implementing automatic token refresh (Meta tokens expire after 60 days)
4. **Monitoring**: Monitor OAuth flow and connection creation in production logs

