# Google OAuth Implementation Guide

## ✅ Completed

### 1. Legal Pages (GDPR/CCPA Compliant)
- **Privacy Policy** (`/privacy`)
  - Comprehensive data collection, usage, and retention details
  - GDPR/CCPA rights outlined (access, deletion, portability)
  - Cookie policy and third-party services disclosure
  - Published at: `https://www.metricx.ai/privacy`

- **Terms of Service** (`/terms`)
  - Service usage terms and acceptable use policy
  - Account termination and liability clauses
  - Intellectual property and dispute resolution
  - Published at: `https://www.metricx.ai/terms`

### 2. Account Deletion (GDPR Right to Erasure)
- **Backend Endpoint**: `DELETE /auth/delete-account`
  - Deletes user account
  - Removes all workspace data if user is sole member
  - Cascades deletion to: connections, entities, metrics, queries, tokens
  - Clears authentication cookies
  - Logs all deletion operations

- **Frontend UI**:
  - Settings page (`/settings`) has dedicated "Delete Account & Data" section
  - Two-step confirmation to prevent accidental deletion
  - "Delete My Data" link in all footers (homepage, privacy, terms, dashboard)

### 3. Google OAuth Backend Flow
- **Authorization Endpoint**: `GET /auth/google/authorize`
  - Generates Google OAuth URL with required scopes
  - Scopes: `https://www.googleapis.com/auth/adwords`
  - Redirects user to Google consent screen
  - Includes state parameter for security

- **Callback Endpoint**: `GET /auth/google/callback`
  - Exchanges authorization code for access/refresh tokens
  - Fetches Google Ads customer details (ID, name, timezone, currency)
  - Encrypts and stores tokens using `token_service`
  - Creates/updates `Connection` with OAuth credentials
  - Redirects to `/settings` with success/error status

- **Router Registration**: Added to `main.py` as `/auth` prefix

### 4. Google OAuth Frontend UI
- **GoogleConnectButton** Component (`/components/GoogleConnectButton.jsx`)
  - "Connect Google Ads" button on Settings page
  - Redirects to backend OAuth authorize endpoint
  - Handles OAuth callback with query parameters
  - Shows success/error messages
  - Auto-refreshes connections on successful connection

- **Settings Page Updates** (`/settings`)
  - "Connect Ad Accounts" section with Google OAuth button
  - Lists all connected accounts
  - Per-connection sync buttons
  - Account deletion section

### 5. Token Security
- Tokens encrypted with Fernet encryption (`security.py`)
- Stored in `tokens` table with separate columns:
  - `access_token_enc` - Encrypted access token
  - `refresh_token_enc` - Encrypted refresh token
- Encryption key from `SECRET_KEY` environment variable
- Decryption only happens at request time

### 6. Database Models
No new migrations needed - using existing schema:
- `Connection` - Links workspace to provider account
- `Token` - Stores encrypted OAuth credentials
- `User` - User account with workspace relationship

## 📋 Next Steps: Google Cloud Console Configuration

### 1. OAuth Consent Screen
Navigate to: [Google Cloud Console - OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)

**User Type**: External (for public access)

**App Information**:
- App name: `metricx`
- User support email: `[Your Support Email]`
- App logo: Upload `ui/public/metricx.png`
- Application home page: `https://www.metricx.ai`
- Application privacy policy link: `https://www.metricx.ai/privacy`
- Application terms of service link: `https://www.metricx.ai/terms`
- Authorized domains: `metricx.ai`

**Developer Contact Information**:
- Email addresses: `[Your Contact Email]`

**Scopes**:
Add the following scope:
- `https://www.googleapis.com/auth/adwords` (View and manage your Google Ads data)

### 2. OAuth Credentials
Navigate to: [Google Cloud Console - Credentials](https://console.cloud.google.com/apis/credentials)

**Create OAuth 2.0 Client ID**:
- Application type: `Web application`
- Name: `metricx Production`
- Authorized JavaScript origins:
  - `https://www.metricx.ai`
  - `http://localhost:3000` (for testing)
- Authorized redirect URIs:
  - `https://api.metricx.ai/auth/google/callback` (production)
  - `http://localhost:8000/auth/google/callback` (for testing)

**Update Environment Variables**:
```bash
# Backend .env
GOOGLE_CLIENT_ID="[Your Client ID from above]"
GOOGLE_CLIENT_SECRET="[Your Client Secret from above]"
GOOGLE_OAUTH_REDIRECT_URI="https://api.metricx.ai/auth/google/callback"

# Frontend .env
NEXT_PUBLIC_API_BASE="https://api.metricx.ai"
```

### 3. Google Ads API Configuration
Ensure you have:
- Google Ads API enabled in your GCP project
- Developer token (apply at: https://developers.google.com/google-ads/api/docs/get-started/dev-token)
- Manager account (MCC) for production access

```bash
# Backend .env
GOOGLE_DEVELOPER_TOKEN="[Your Developer Token]"
```

### 4. Google OAuth Verification Submission

**Important**: When publishing your OAuth consent screen for external users, Google **requires verification** for the `https://www.googleapis.com/auth/adwords` scope. You'll need to provide:

1. **Scope Justification** - Explain why you need this scope
2. **Demo Video** - Show how your app uses Google Ads data

**Verification Requirements**:
1. **App Homepage**: Live at `https://www.metricx.ai` ✅
2. **Privacy Policy**: Live at `https://www.metricx.ai/privacy` ✅
3. **Terms of Service**: Live at `https://www.metricx.ai/terms` ✅
4. **OAuth Consent Screen**: Configured as above
5. **Authorized Domains**: Verified ownership of `metricx.ai`
6. **Scope Justification**: Written explanation of why you need the scope
7. **Verification Video**: 3-5 minute demo video showing OAuth flow and data usage

## 📹 Verification Video (Required)

**Required**: You must create and submit a verification video to publish your OAuth consent screen. Here's the complete guide:

**Video Script (Step-by-Step)**:

**Part 1: Introduction & Account Setup (30 seconds)**
1. Start on metricx homepage (`https://www.metricx.ai`)
2. Show Privacy Policy and Terms of Service links in footer
3. Click "Get Started" or "Sign In"
4. Register a new account or log in with existing credentials
5. Navigate to Settings page (`/settings`)

**Part 2: OAuth Connection Flow (1-2 minutes)**
6. Show "Connect Ad Accounts" section
7. Click "Connect Google Ads" button
8. **Google OAuth Consent Screen appears** - Show the consent screen clearly
   - Highlight that it requests `https://www.googleapis.com/auth/adwords` scope
   - Explain what permissions are being requested
9. Click "Allow" to grant permissions
10. **Account Selection Modal appears** (this is unique to metricx)
    - Show MCC accounts (Manager Accounts) displayed as headers
    - Show child ad accounts listed under each MCC
    - Demonstrate selecting which ad accounts to connect
    - Explain that users can choose specific accounts, not all accounts automatically
    - Click "Connect Selected Accounts"
11. Show success message: "Successfully connected X Google Ads account(s)"
12. Show connected account(s) appearing in the connections list

**Part 3: Data Usage & Features (1-2 minutes)**
13. Click "Sync Entities" button on a connected account
14. Show sync process completing successfully
15. Navigate to dashboard or campaigns view
16. **Demonstrate actual Google Ads data being used**:
    - Show campaigns synced from Google Ads
    - Show ad groups and ads
    - Show metrics (impressions, clicks, spend, conversions)
    - Explain how this data is used for analysis/reporting
17. Show connection management:
    - Delete a connection (trash icon)
    - Confirm deletion
    - Show connection removed from list

**Part 4: Security & Compliance (30 seconds)**
18. Open browser Developer Tools → Network tab
19. Show that tokens are never exposed in API responses
20. Show that all API calls use encrypted tokens
21. Navigate to Privacy Policy page
22. Highlight GDPR compliance features (account deletion, data export)

**Video Production Tips**:
- **Screen Resolution**: Record at 1920x1080 (1080p) minimum
- **Audio**: Clear narration explaining each step
- **Pacing**: Don't rush - pause briefly at important screens
- **Zoom**: Zoom in on important UI elements (consent screen, account selection modal)
- **Editing**: Remove any pauses or errors, keep it smooth
- **Duration**: Aim for 3-5 minutes total
- **Format**: MP4, H.264 codec recommended
- **File Size**: Keep under 100MB if possible

**What to Emphasize**:
✅ **User Control**: Show that users explicitly select which accounts to connect
✅ **Data Usage**: Clearly demonstrate how Google Ads data is used (campaigns, metrics, reporting)
✅ **Security**: Show that tokens are encrypted and never exposed
✅ **Compliance**: Show Privacy Policy and Terms of Service
✅ **Real Functionality**: Use real Google Ads accounts with actual data

**What NOT to Show**:
❌ Don't show any API keys, tokens, or secrets
❌ Don't show backend code or database contents
❌ Don't show test/development environments (use production or staging)
❌ Don't show error messages or broken functionality

**Upload Video**:
- Upload to YouTube as **Unlisted** (not private, not public)
- Or upload to Google Drive with shareable link
- Include the video URL in OAuth verification submission form
- Video title: "metricx - Google Ads OAuth Integration Demo"

**Scope Justification** (Required Text):
When submitting for verification, you'll need to provide a justification for why you need the `auth/adwords` scope. Use this text:

```
metricx is a marketing analytics platform that helps businesses analyze and optimize their Google Ads campaigns. 

We require the Google Ads API scope (https://www.googleapis.com/auth/adwords) to:
- Read campaign data, ad groups, ads, and performance metrics from users' Google Ads accounts
- Sync this data into our platform for unified reporting and analysis
- Calculate ROI, ROAS, and other key performance indicators
- Provide optimization recommendations based on campaign performance

Users explicitly grant permission through OAuth and can select which specific ad accounts to connect from their MCC accounts. Users can disconnect accounts at any time through the settings page.

We store encrypted OAuth tokens securely and only use the data for analysis and reporting purposes within the user's workspace.
```

**Submit for Verification**:
1. Navigate to: [Google Cloud Console - OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
2. Click "Publish App" or "Submit for Verification"
3. Complete the verification form:
   - **App Purpose**: Use the scope justification text above
   - **Data Usage**: Explain how you use Google Ads data (see justification above)
   - **Data Storage**: "We store encrypted OAuth tokens securely. Campaign and performance data is stored in our database for analysis and reporting purposes."
   - **User Control**: "Users can connect/disconnect accounts at any time. They can select which specific ad accounts to connect from their MCC accounts."
4. Upload verification video (follow script above)
5. Submit and wait for Google review (typically 3-7 business days)

## 🔒 Security Checklist

- [x] Tokens encrypted at rest
- [x] HTTPS enforced in production
- [x] Secure HTTP-only cookies for authentication
- [x] CORS configured for production domain
- [x] State parameter in OAuth flow (CSRF protection)
- [x] No tokens logged or exposed in responses
- [x] User data deletion capability (GDPR compliance)
- [x] Privacy policy and ToS published

## 🧪 Testing Before Submission

### Automated Testing
Run the test script to verify endpoints:
```bash
cd backend
python test_google_oauth.py
```

This will test:
- API health check
- User registration/login
- OAuth configuration validation
- Authorize endpoint (redirect validation)
- Callback endpoint error handling

### Local Testing
1. Start backend: `cd backend && source bin/activate && python start_api.py`
2. Start frontend: `cd ui && npm run dev`
3. Visit: `http://localhost:3000`
4. Register/login
5. Navigate to Settings
6. Click "Connect Google Ads"
7. Complete OAuth flow
8. Verify connection appears in Settings
9. Test sync functionality
10. Test account deletion

### Manual Endpoint Testing
```bash
# 1. Login and get cookie
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt

# 2. Test authorize endpoint (will redirect to Google)
curl -L http://localhost:8000/auth/google/authorize \
  -b cookies.txt \
  -v

# 3. Test callback error handling
curl http://localhost:8000/auth/google/callback?error=access_denied \
  -v
```

### Production Testing
1. Deploy backend to production server
2. Deploy frontend to production server
3. Configure production environment variables
4. Test full OAuth flow on production domain
5. Record verification video on production

## 📚 References

- **Backend OAuth Router**: `backend/app/routers/google_oauth.py`
  - Account selection endpoints: `GET /auth/google/accounts`, `POST /auth/google/connect-selected`
- **Frontend Connect Button**: `ui/components/GoogleConnectButton.jsx`
- **Account Selection Modal**: `ui/components/GoogleAccountSelectionModal.jsx`
- **Settings Page**: `ui/app/(dashboard)/settings/page.jsx`
- **Google Sync Router**: `backend/app/routers/google_sync.py`
  - Sync endpoints with MCC support: `POST /sync-google-entities`, `POST /sync-google-metrics`
- **Token Service**: `backend/app/services/token_service.py`
  - Stores parent MCC ID for client accounts
- **Google Ads Client**: `backend/app/services/google_ads_client.py`
  - `_build_client_from_tokens()` with `login_customer_id` support
- **Delete Account Endpoint**: `backend/app/routers/auth.py` (DELETE `/auth/delete-account`)
- **Connection Deletion**: `DELETE /connections/{connection_id}` (in `backend/app/routers/connections.py`)
- **Privacy Policy**: `docs/PRIVACY_POLICY.md` + `ui/app/privacy/page.jsx`
- **Terms of Service**: `docs/TERMS_OF_SERVICE.md` + `ui/app/terms/page.jsx`

## 🎯 Current Status

**Backend Implementation**:
- ✅ OAuth authorize endpoint (`GET /auth/google/authorize`)
- ✅ OAuth callback endpoint (`GET /auth/google/callback`)
- ✅ State parameter validation and workspace verification
- ✅ Comprehensive error handling for all failure cases
- ✅ Token encryption and storage via `token_service`
- ✅ Connection creation/update logic
- ✅ Google Ads API integration for customer data fetching
- ✅ Account selection flow with Redis temporary storage
- ✅ MCC (Manager Account) detection and child account fetching
- ✅ Parent MCC ID storage for client account sync
- ✅ `login-customer-id` header support for MCC hierarchy
- ✅ Connection deletion endpoint (`DELETE /connections/{connection_id}`)
- ✅ Missing logger import fixed in `auth.py`
- ✅ Test script created (`backend/test_google_oauth.py`)

**Frontend Implementation**:
- ✅ GoogleConnectButton component
- ✅ GoogleAccountSelectionModal component (MCC/child account selection)
- ✅ Error message handling for all error cases
- ✅ Success/error state management
- ✅ Settings page integration
- ✅ Connection deletion UI with confirmation dialog

**Ready for**:
- ✅ Google Cloud Console OAuth configuration
- ✅ Local testing of OAuth flow
- ✅ Account selection modal with MCC/child account support
- ✅ Parent MCC ID storage for sync operations
- ✅ Connection deletion functionality
- ⏳ **Verification submission** - Required before production

**Not Yet Done**:
- ⏳ Record verification video
- ⏳ Submit OAuth verification request
- ⏳ Wait for Google approval (3-7 business days)
- ⏳ Update environment variables with OAuth credentials
- ⏳ Domain verification for `metricx.ai` in Google Cloud Console
- ⏳ Deploy to production (after verification approval)

## 🎬 Next Steps: Verification & Production Deployment

**Priority**: Record verification video and submit for Google review BEFORE deploying to production.

**Timeline**:
1. **Week 1, Day 1**: Configure OAuth consent screen in Google Cloud Console
2. **Week 1, Day 1**: Create OAuth 2.0 Client ID credentials
3. **Week 1, Day 2**: Record verification video (follow script above)
4. **Week 1, Day 2**: Upload video to YouTube (unlisted) or Google Drive
5. **Week 1, Day 2**: Submit OAuth verification request with scope justification and video
6. **Week 2-3**: Wait for Google review (3-7 business days typical)
7. **After Approval**: Update environment variables and deploy to production
8. **After Deployment**: Monitor OAuth flow and user connections

**Pre-Verification Checklist**:
- [ ] Configure OAuth consent screen (App name, logo, Privacy Policy, Terms of Service)
- [ ] Create OAuth 2.0 Client ID (Web application type)
- [ ] Add authorized redirect URIs (production callback URL)
- [ ] Test OAuth flow end-to-end on staging/localhost
- [ ] Prepare demo Google Ads account with real campaigns/data
- [ ] Record verification video (3-5 minutes, follow script above)
- [ ] Edit video to remove errors/pauses
- [ ] Upload video to YouTube (unlisted) or Google Drive
- [ ] Prepare scope justification text (see above)
- [ ] Submit verification request in Google Cloud Console

**Post-Verification Checklist** (After Google Approval):
- [ ] Update backend `.env` with `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- [ ] Update frontend `.env` with production API URL
- [ ] Deploy to production
- [ ] Test OAuth flow end-to-end on production
- [ ] Verify account selection modal works correctly
- [ ] Test sync functionality with connected accounts
- [ ] Monitor logs for any OAuth errors

## 🚀 Deployment Notes

1. Ensure production domains are live before OAuth verification
2. SSL certificates must be valid (Let's Encrypt recommended)
3. Frontend must be accessible at `https://www.metricx.ai`
4. Backend API must be accessible at `https://api.metricx.ai`
5. Test OAuth flow on production before submitting for verification
6. Monitor logs during verification review for any issues

## 📞 Support

For Google OAuth verification issues:
- [Google OAuth Support](https://support.google.com/code/contact/oauth_verification)
- [Google Ads API Forum](https://groups.google.com/g/adwords-api)


