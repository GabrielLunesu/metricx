# Change: Add Polar Billing (Per Workspace) + Access Gating

## Why
We need production-ready monetization where access is enforced server-side and tied to a workspace subscription:
- Users currently can access `/onboarding` and `/dashboard` without selecting a paid plan.
- Workspaces, members, and invites exist in the backend, but billing state is not modeled.
- The UI has members/invites tabs, but invite management is effectively disabled because the frontend user context lacks `memberships`.

This change makes billing per workspace (monthly or annual, both with trial), enforces access rules consistently, and closes “signup without plan” paths.

## What Changes
- Billing is **per workspace**:
  - Each workspace can have its own subscription (Monthly `$79` or Annual `$569`), both with trial.
  - Anyone invited into a subscribed workspace inherits access to that workspace (no per-user subscriptions).
- Server-side access gating:
  - `/onboarding` and `/dashboard` become **subscription-gated** by the *active workspace*.
  - Allowed states: `trialing` and `active`.
  - Owners/Admins get redirected to subscribe when blocked; non-billing members see an “Ask owner/admin to subscribe” screen.
- Polar integration:
  - A “create checkout” backend endpoint creates a Polar checkout for a specific workspace + plan.
  - Polar webhooks update workspace subscription state using `checkout_id` ↔ `subscription_id` linkage (no metadata required).
- Limits and guardrails:
  - Max **10 active members** per workspace (enforced in backend invite/add-member).
  - Unlimited subscribed workspaces; cap **2 pending** (locked/unsubscribed) workspaces per owner/admin to prevent spam.
  - Optional TTL/cleanup for pending workspaces (defined in tasks/design).
- Fix workspace/membership context:
  - Ensure the frontend can reliably determine the user’s role per workspace (`memberships`) so invites and billing management render correctly.

## Non-Goals
- Migrating workspaces and memberships to Clerk Organizations.
- Implementing Polar “seats” as the authoritative member limit (we enforce the 10-member cap in our app).
- Usage-based billing or metered plans.

## Impact
- Backend: new billing fields on `Workspace`, new checkout endpoints, new Polar webhook handler, enforcement in workspace/member endpoints and selected product APIs.
- UI: new `/subscribe` flow per workspace, improved “locked workspace” messaging, “manage billing” entry point, and correct role detection for invites.

## Success Criteria (Acceptance)
- A user cannot access `/onboarding` or `/dashboard` for a workspace unless it has an active/trialing subscription.
- Owner/Admin can subscribe a workspace via Polar checkout and immediately gains access after webhook confirmation.
- Members invited to a subscribed workspace have access; members invited to an unsubscribed workspace are blocked with a clear message.
- Member cap: the 11th active member cannot be invited/added (backend-enforced).
- Pending workspace cap: a user cannot create more than 2 locked/unsubscribed workspaces at a time (backend-enforced).
- Billing portal is available to Owner/Admin for the active workspace.

## Rollout Plan
1. Implement backend billing model + webhook sync; ship gated routes behind a feature flag/env toggle.
2. Add `/subscribe` UI and wire pricing CTA(s) to pass `workspaceId` + `plan`.
3. Enable gating for internal workspaces; validate the full checkout → webhook → unlock flow.
4. Enable for all workspaces; monitor webhook error rate and access-denied logs.

