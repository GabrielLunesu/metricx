# Workspace Billing System (Polar)

**Last Updated**: 2025-12-17
**Version**: 1.1.0
**Status**: Implementation

---

## Overview

metricx uses **Polar** for per-workspace subscription billing. Workspaces start on a **free tier** with limited features, and can upgrade to **Starter** for full access.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Billing provider | Polar | Developer-focused, simple API, handles tax/invoicing |
| Billing unit | Per workspace | Teams share subscription, not per-user |
| Tiers | Free / Starter | Free tier for onboarding, Starter for power users |
| Starter pricing | Monthly $79 / Annual $569 | Annual saves 40% |
| Free tier access | Dashboard only | Get users hooked, then upsell |
| Access gating | Server-side + UI locks | Prevents bypass, clear UX for locked features |

---

## Free Tier vs Starter

metricx uses a **freemium model** with two billing tiers:

| Feature | Free Tier | Starter Tier |
|---------|-----------|--------------|
| **Ad accounts** | 1 total (Meta OR Google) | Unlimited |
| **Shopify** | Yes | Yes |
| **Dashboard** | Full access | Full access |
| **Analytics** | Locked | Full access |
| **Finance** | Locked | Full access |
| **Campaigns** | Locked | Full access |
| **Copilot AI** | Locked | Full access |
| **Team invites** | No | Up to 10 members |
| **Price** | Free | $79/mo or $569/yr |

### How It Works

1. **New signups** start with `billing_tier = 'free'` and `billing_status = 'active'`
2. **Free users** can access Dashboard and connect 1 ad account
3. **Locked features** show lock icons in nav; clicking shows UpgradeModal
4. **Direct URL access** to locked pages redirects to Dashboard with upgrade prompt
5. **Upgrading** via Polar checkout sets `billing_tier = 'starter'`

### Database Fields

The workspace has two billing-related fields:

| Field | Purpose | Values |
|-------|---------|--------|
| `billing_status` | Payment/subscription state | locked, trialing, active, canceled, etc. |
| `billing_tier` | Feature access tier | `free`, `starter` |

**Important:** A workspace can have `billing_status = 'active'` AND `billing_tier = 'free'`. This means they have access (not locked out) but are on the free tier with limited features.

---

## Architecture

```
                        BILLING FLOW OVERVIEW

  USER                 FRONTEND              BACKEND              POLAR


   1. Click "Subscribe"
        ----------------->

                          2. POST /billing/checkout
                             ----------------------->

                                               3. Create checkout
                                                  --------------->

                                               4. Store mapping
                                                  (checkout -> workspace)

                          5. Return checkout_url
                             <-----------------------

   6. Redirect to Polar
        <-----------------

   7. Complete payment on Polar
        ---------------------------------------------------->

                                               8. Webhook: checkout.updated
                                                  <----------------

                                               9. Update workspace
                                                  billing_status

                          10. Redirect to /dashboard?checkout=success
        <-----------------


  WEBHOOK PROCESSING (Idempotent)

  POLAR                           BACKEND                     DATABASE


   webhook event
   ----------------------->

                           1. Verify signature
                              (HMAC SHA256)

                           2. Compute event_key
                              (type:id:timestamp)

                           3. Check if processed
                              ----------------------->

                           4. Skip if duplicate
                              (idempotent)

                           5. Process event
                              Update workspace billing

                           6. Record event
                              ----------------------->
```

---

## Billing States

### billing_status (Subscription State)

The workspace `billing_status` field tracks subscription/payment state:

| Status | Access Allowed | Description |
|--------|----------------|-------------|
| `locked` | No | Blocked from all access |
| `trialing` | Yes | Free trial period active |
| `active` | Yes | Free tier OR paid subscription active |
| `canceled` | Yes* | Canceled but access until period end |
| `past_due` | No | Payment failed, needs update |
| `incomplete` | No | Checkout started but not completed |
| `revoked` | No | Subscription revoked (fraud, chargeback) |

*Canceled workspaces retain access until `current_period_end`.

### billing_tier (Feature Tier)

The workspace `billing_tier` field determines feature access:

| Tier | Description | Default |
|------|-------------|---------|
| `free` | Limited features (Dashboard only, 1 ad account, no invites) | Yes (new signups) |
| `starter` | Full features (all pages, unlimited accounts, team invites) | After upgrade |

**Note:** `billing_status` and `billing_tier` are independent:
- Free tier users have `billing_status = 'active'` (they can access the app)
- But `billing_tier = 'free'` (limited features)
- After upgrading, `billing_tier = 'starter'` (full features)

---

## Database Schema

### Workspace Billing Fields

```sql
-- Added to workspaces table
billing_status       VARCHAR(20) DEFAULT 'active'   -- Payment state
billing_tier         VARCHAR(20) DEFAULT 'free'     -- Feature tier: 'free' or 'starter'
billing_plan         VARCHAR(20)                    -- 'monthly' or 'annual' (for starter)
polar_subscription_id VARCHAR(255)                  -- Polar subscription ID
polar_customer_id    VARCHAR(255)                   -- Polar customer ID
trial_end            TIMESTAMP                      -- When trial expires
current_period_start TIMESTAMP                      -- Current billing period start
current_period_end   TIMESTAMP                      -- Current billing period end
pending_since        TIMESTAMP                      -- For pending workspace cap
```

### Checkout Mapping Table

```sql
-- Maps Polar checkout_id to workspace_id
CREATE TABLE polar_checkout_mappings (
    id               UUID PRIMARY KEY,
    workspace_id     UUID NOT NULL REFERENCES workspaces(id),
    polar_checkout_id VARCHAR(255) NOT NULL UNIQUE,
    polar_subscription_id VARCHAR(255),
    requested_plan   VARCHAR(20) NOT NULL,
    status           VARCHAR(50) DEFAULT 'pending',
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);
```

### Webhook Event Table (Idempotency)

```sql
-- Prevents duplicate webhook processing
CREATE TABLE polar_webhook_events (
    id               UUID PRIMARY KEY,
    event_key        VARCHAR(512) NOT NULL UNIQUE,
    event_type       VARCHAR(100) NOT NULL,
    polar_data_id    VARCHAR(255),
    payload_json     JSONB,
    processing_result VARCHAR(100),
    created_at       TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### GET /billing/status

Returns billing status for the current workspace.

**Response:**
```json
{
  "workspace_id": "uuid",
  "workspace_name": "My Company",
  "billing": {
    "billing_status": "active",
    "billing_tier": "free",
    "billing_plan": null,
    "trial_end": null,
    "current_period_start": null,
    "current_period_end": null,
    "is_access_allowed": true,
    "can_manage_billing": true,
    "portal_url": null
  }
}
```

**Note:** `billing_tier` determines feature access:
- `"free"` = Limited features (Dashboard only, 1 ad account)
- `"starter"` = Full features (all pages, unlimited accounts)

### POST /billing/checkout

Creates a Polar checkout session.

**Request:**
```json
{
  "workspace_id": "uuid",
  "plan": "monthly",  // or "annual"
  "success_url": "https://app.metricx.io/dashboard?checkout=success"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.polar.sh/...",
  "checkout_id": "polar-checkout-id"
}
```

**Requirements:**
- User must be Owner or Admin of workspace
- Workspace must not have active subscription

### GET /billing/portal

Returns Polar customer portal URL for subscription management.

**Query Params:** `workspace_id=uuid`

**Response:**
```json
{
  "portal_url": "https://polar.sh/portal/..."
}
```

**Requirements:**
- User must be Owner or Admin
- Workspace must have `polar_customer_id`

### POST /webhooks/polar

Receives Polar webhook events.

**Headers:**
- `Polar-Signature`: HMAC signature for verification

**Handled Events:**
| Event | Action |
|-------|--------|
| `checkout.updated` | Link subscription to workspace, update status |
| `subscription.active` | Set `billing_status = active` |
| `subscription.canceled` | Set `billing_status = canceled` |
| `subscription.revoked` | Set `billing_status = revoked` |
| `subscription.updated` | Update period dates, status |

---

## Frontend Integration

### Files

| File | Purpose |
|------|---------|
| `ui/lib/workspace.js` | Billing API functions |
| `ui/app/subscribe/page.jsx` | Upgrade page (free → starter) |
| `ui/app/(dashboard)/DashboardShell.jsx` | Billing + tier gating logic |
| `ui/app/(dashboard)/components/shared/Sidebar.jsx` | Nav with lock icons |
| `ui/app/(dashboard)/components/shared/NavItem.jsx` | Nav item with lock badge |
| `ui/components/UpgradeModal.jsx` | Upgrade prompt modal |
| `ui/app/(dashboard)/settings/components/UsersTab.jsx` | Invite restrictions |
| `ui/app/(dashboard)/settings/components/ConnectionsTab.jsx` | Connection limit UI |
| `ui/app/(dashboard)/settings/components/BillingTab.jsx` | Billing settings |
| `backend/app/routers/admin.py` | Admin endpoints for bulk upgrades |

### Gating Logic (DashboardShell)

```javascript
// 1. Check billing status
const { billing } = await getBillingStatus();

// 2. If access not allowed (billing_status blocked)
if (!billing.is_access_allowed) {
  if (billing.can_manage_billing) {
    router.push('/subscribe');
  } else {
    showBlockedMessage();
  }
}

// 3. Free tier page gating (billing_tier check)
const PAID_ONLY_ROUTES = ['/analytics', '/finance', '/campaigns', '/copilot'];
if (billing.billing_tier === 'free') {
  if (PAID_ONLY_ROUTES.some(r => pathname.startsWith(r))) {
    router.replace('/dashboard');
    setUpgradeModal({ open: true, feature: 'this feature' });
  }
}
```

### Sidebar Lock Icons

```javascript
// Nav items with requiresPaid flag
const navItems = [
  { href: "/dashboard", label: "Dashboard", requiresPaid: false },
  { href: "/analytics", label: "Analytics", requiresPaid: true },
  { href: "/copilot", label: "Copilot AI", requiresPaid: true },
  { href: "/finance", label: "Finance", requiresPaid: true },
  { href: "/campaigns", label: "Campaigns", requiresPaid: true },
];

// Render with lock state
{navItems.map((item) => {
  const isLocked = item.requiresPaid && billingTier === 'free';
  return <NavItem {...item} isLocked={isLocked} onLockedClick={showUpgradeModal} />;
})}
```

### API Functions

```javascript
// Get billing status
export async function getBillingStatus() {
  const res = await fetch('/api/billing/status');
  return res.json();
}

// Create checkout
export async function createCheckout(workspaceId, plan) {
  const res = await fetch('/api/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId, plan }),
  });
  return res.json(); // { checkout_url, checkout_id }
}

// Get billing portal URL
export async function getBillingPortalUrl(workspaceId) {
  const res = await fetch(`/api/billing/portal?workspace_id=${workspaceId}`);
  return res.json(); // { portal_url }
}
```

---

## Limits & Caps

| Limit | Value | Enforced By |
|-------|-------|-------------|
| Members per workspace | 10 active | `add_workspace_member()`, `create_invite()` |
| Pending workspaces per owner | 2 | `create_workspace()` |

**Pending workspace**: A workspace with `billing_status = locked` where user is Owner/Admin. Prevents creating unlimited free workspaces.

---

## Environment Variables

```bash
# Polar API Configuration
POLAR_API_URL=https://api.polar.sh
POLAR_ACCESS_TOKEN=polar_at_xxx          # Organization access token
POLAR_WEBHOOK_SECRET=whsec_xxx           # Webhook signing secret
POLAR_ORGANIZATION_ID=org_xxx            # Your Polar org ID

# Product IDs (from Polar dashboard)
POLAR_MONTHLY_PRODUCT_ID=xxx             # Monthly plan product ID
POLAR_ANNUAL_PRODUCT_ID=xxx              # Annual plan product ID

# Frontend URL (for redirects)
FRONTEND_URL=http://localhost:3000       # Or production URL
```

---

## Polar Dashboard Setup

### 1. Create Products

Create two products in Polar:

| Product | Price | Billing |
|---------|-------|---------|
| metricx Monthly | $79/month | Recurring monthly |
| metricx Annual | $569/year | Recurring yearly |

Copy the **Product IDs** (not Price IDs) to your environment.

### 2. Configure Webhook

1. Go to Settings > Webhooks
2. Create webhook with URL: `https://your-domain.com/webhooks/polar`
3. Select events:
   - `checkout.updated`
   - `subscription.active`
   - `subscription.canceled`
   - `subscription.revoked`
   - `subscription.updated`
4. Copy webhook secret to `POLAR_WEBHOOK_SECRET`

### 3. Generate Access Token

1. Go to Settings > Access Tokens
2. Create organization token with scopes:
   - `checkouts:read`
   - `checkouts:write`
   - `subscriptions:read`
   - `customers:read`
   - `customers:write`
3. Copy to `POLAR_ACCESS_TOKEN`

---

## Testing

### Local Development

1. Use ngrok to expose webhook endpoint:
   ```bash
   ngrok http 8000
   ```

2. Update Polar webhook URL to ngrok URL

3. Create test checkout, complete payment

4. Verify webhook received and workspace updated

### Test Scenarios

| Scenario | Expected Result |
|----------|-----------------|
| New user signs up | Workspace: `billing_status = active`, `billing_tier = free` |
| Free user visits Dashboard | Full access |
| Free user clicks Analytics nav | UpgradeModal shown |
| Free user visits /analytics directly | Redirected to /dashboard, UpgradeModal shown |
| Free user connects 1 ad account | Success |
| Free user connects 2nd ad account | Error: "Free plan allows only 1 ad account" |
| Free user tries to invite | Error: "Team invites require a paid plan" |
| Owner clicks Upgrade | Redirected to Polar checkout |
| Complete checkout | Webhook sets `billing_tier = starter` |
| Starter user accesses all pages | Full access |
| Cancel subscription | Status changes to `canceled`, access until period end |
| Period ends after cancel | Access revoked (billing_status changes) |

---

## Admin Operations

### Bulk Upgrade Workspaces (Giveaways/Promotions)

Use the admin endpoint to upgrade multiple workspaces at once for giveaways or promotions.

**Endpoint:** `POST /admin/upgrade-workspaces`

**Security:** Requires `X-Admin-Secret` header (set via `ADMIN_SECRET` env var)

#### Setup

Add to your `.env`:
```bash
ADMIN_SECRET=your-secure-secret-here
```

#### Upgrade by Email

```bash
curl -X POST https://api.yourapp.com/admin/upgrade-workspaces \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: your-secure-secret-here" \
  -d '{
    "user_emails": [
      "winner1@example.com",
      "winner2@example.com",
      "winner3@example.com"
    ],
    "tier": "starter"
  }'
```

#### Upgrade by Workspace ID

```bash
curl -X POST https://api.yourapp.com/admin/upgrade-workspaces \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: your-secure-secret-here" \
  -d '{
    "workspace_ids": [
      "540c956d-b31b-4c3c-8185-29cc49979b25",
      "ebfa8c68-bafb-487f-94f1-31265fc8ee21"
    ],
    "tier": "starter"
  }'
```

#### Response

```json
{
  "upgraded": 3,
  "failed": 0,
  "details": [
    {"email": "winner1@example.com", "workspace": "Winner's Workspace", "status": "upgraded"},
    {"email": "winner2@example.com", "workspace": "Another Workspace", "status": "upgraded"},
    {"email": "winner3@example.com", "status": "user_not_found"}
  ]
}
```

#### Options

| Parameter | Description |
|-----------|-------------|
| `user_emails` | List of user emails to upgrade (finds their primary workspace) |
| `workspace_ids` | List of workspace UUIDs to upgrade directly |
| `tier` | `"starter"` (upgrade) or `"free"` (downgrade) |

#### Other Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/workspace/{id}` | GET | Get workspace billing details |

---

## Migration Notes

### Adding billing_tier Column

The migration (`20251217_000001_add_billing_tier.py`) adds the `billing_tier` column:

```python
# In alembic migration
op.add_column('workspaces', sa.Column('billing_tier', ...))

# Migrate existing data:
# - Workspaces with polar_subscription_id → "starter" (paid users)
# - Workspaces without → "free" (new default)
op.execute("""
    UPDATE workspaces
    SET billing_tier = CASE
        WHEN polar_subscription_id IS NOT NULL THEN 'starter'
        ELSE 'free'
    END
""")
```

### Grandfathering Existing Workspaces

Existing paid users keep full access:
- If `polar_subscription_id` exists → `billing_tier = 'starter'`
- Otherwise → `billing_tier = 'free'` (limited features)

**Note:** This may affect existing users who haven't paid but had full access. Review workspace list before migration if needed.

---

## Troubleshooting

### "Method Not Allowed" from Polar

- Check endpoint: should be `/v1/checkouts/`
- Check payload: use `products: [product_id]` array

### Webhook not received

- Verify ngrok is running (local dev)
- Check Polar webhook delivery history
- Verify `POLAR_WEBHOOK_SECRET` matches

### User can't access dashboard after payment

1. Check webhook was received (backend logs)
2. Verify `polar_checkout_mappings` has entry
3. Check workspace `billing_status` in database
4. Try Polar "Replay" to resend webhook

### "Price does not exist" error

- You're using Product ID, not Price ID (correct)
- Ensure payload uses `products: [id]` array format

---

## Related Documentation

- [AUTH.md](./AUTH.md) - Authentication system
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [Polar API Docs](https://docs.polar.sh) - Official Polar documentation
