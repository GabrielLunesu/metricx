# Design: Polar Per-Workspace Billing + Gating

## Core Principle
Subscription state is a property of `Workspace`. Access is granted per workspace.

## Mapping Polar → Workspace
Do not rely on `metadata` being present in webhook payloads.

Instead:
- When creating a Polar checkout for a workspace, persist:
  - `workspace_id`
  - `polar_checkout_id`
  - `requested_plan` (`monthly|annual`)
  - `created_by_user_id`
- On webhook `checkout.updated`:
  - Use `data.id` (checkout id) to locate the workspace
  - Persist `data.subscription_id` onto workspace (or a mapping table)
- On webhook `subscription.updated`:
  - Use `data.checkout_id` to locate the workspace (preferred)
  - Fallback: use `data.id` if workspace already has `polar_subscription_id`

## Access Rules
- Allowed subscription states: `trialing`, `active`
- Blocked subscription states: everything else (including `incomplete`, `canceled`, `revoked`, `past_due` if present)

Notes:
- Polar also emits discrete events (`subscription.active`, `subscription.canceled`, etc.). Treat them as authoritative transitions.
- Always keep backend as the final enforcement point; UI gating is only UX.

## Caps / Guardrails
- Pending workspace cap: max 2 workspaces per user where:
  - user is Owner/Admin AND
  - workspace subscription is not active/trialing AND
  - workspace was created within the pending window (field `pending_since`)
- Member cap: max 10 active members per workspace (including Owner/Admin/Viewer).

## Idempotency
Polar event envelope does not show an `id` field in the schema snippet.
Implementation MUST deduplicate deliveries. Preferred approaches:
1) Use a provider-supplied event id (if present in headers/body) and persist it.
2) If none exists, use a deterministic hash of `(type, timestamp, data.id)` plus raw body, store for a TTL window, and ignore duplicates.

