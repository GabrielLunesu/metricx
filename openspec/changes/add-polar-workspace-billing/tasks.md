## 1. Polar Setup (External)
- [ ] Create Polar products/prices for Monthly `$79` and Annual `$569`
- [ ] Enable free trial on both prices/products
- [ ] Enable/configure customer portal (manage billing)
- [ ] Configure Polar webhooks pointing to `POST /webhooks/polar`
- [ ] Document Polar webhook signature headers + verification method (needed for production)

## 2. Backend Data Model
- [ ] Add workspace billing fields (status, plan, subscription id, checkout id mapping, trial/period timestamps)
- [ ] Add “pending workspace” tracking fields and enforce pending cap (N=2)
- [ ] Add backend-enforced member cap (10 active members) for invites and direct member adds

## 3. Backend Polar Integration
- [ ] Add endpoint to create a Polar checkout for a workspace + plan
- [ ] Persist `checkout_id` + requested plan for workspace
- [ ] Add `POST /webhooks/polar`:
  - [ ] Verify webhook signatures
  - [ ] Idempotency (event dedupe) using a stored event id (or `type+timestamp+data.id` if Polar lacks event ids)
  - [ ] Handle `checkout.updated` to capture `subscription_id`
  - [ ] Handle `subscription.*` to update workspace billing status and timestamps
- [ ] Add endpoint to fetch “billing status” and “portal URL” for a workspace (Owner/Admin only)

## 4. Access Gating (Backend + UI)
- [ ] Backend: enforce “workspace must be active/trialing” for paid endpoints (define list in design)
- [ ] UI: add `/subscribe` page to start checkout for selected workspace + plan
- [ ] UI: update route protection:
  - [ ] `/onboarding` and `/dashboard` require subscribed active workspace
  - [ ] If blocked and user is Owner/Admin → redirect to `/subscribe`
  - [ ] If blocked and user is not Owner/Admin → show “Ask owner/admin” state

## 5. Workspace + Membership UX Fixes
- [ ] Ensure frontend user context includes `memberships` so invites/billing controls render correctly
- [ ] Update Settings → Workspaces tab:
  - [ ] Show billing status per workspace (Locked/Trial/Active)
  - [ ] On “Create workspace”: if pending cap reached, show a clear message
  - [ ] On “Create workspace”: message that each workspace requires its own subscription
- [ ] Update Settings → Members/Invites:
  - [ ] Block invite flow when member cap reached; show remaining seats (10 - active)

## 6. Validation / Test Matrix
- [ ] New user: sign up → create workspace → subscribe → onboarding → dashboard
- [ ] Member invited to paid workspace: access allowed
- [ ] Member invited to locked workspace: access blocked with clear CTA
- [ ] Cancel subscription: access blocked for that workspace after cancel/period end
- [ ] Pending cap: create 3 locked workspaces → third is blocked
- [ ] Member cap: invite 11th member → blocked

