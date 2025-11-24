# Workspace Management — Living Plan

> How to use this doc  
> - Keep this file up-to-date while implementing multi-workspace, invites, roles, and switching.  
> - Record decisions and testability notes as they happen; do not leave TODOs.  
> - Mirror changes in `docs/living-docs/ADNAVI_BUILD_LOG.md` and relevant UI/Backend docs when finalized.

---

## 0) Goal & Scope
- Enable true multi-workspace tenancy: a user can belong to multiple workspaces and switch between them.
- Features: create workspace, invite existing users by email, remove users, role management (Owner/Admin/Viewer), workspace switching UI, invite acceptance/decline.
- Robustness: permission enforcement across API + UI, testable flows (unit + integration + E2E happy/edge paths).

Non-Goals (for now):
- SSO/OAuth invites, magic links, email delivery.
- Billing per workspace.
- Granular permissions beyond Owner/Admin/Viewer.

## 1) Current State (from build logs)
- Frontend: Next.js 15 / React 19 (JSX), auth via `currentUser()` call to `/auth/me` client-side; single workspace assumed.
- Backend: FastAPI + SQLAlchemy; JWT cookie auth; single workspace per user by default; roles hardcoded/basic.
- UI Docs: `docs/living-docs/ui/living-ui-doc.md` for routes/components; no workspace switching UI.
- No multi-workspace data model or invitation flows yet.
- Registration today: creates a default workspace implicitly (single owner assumption).

New requirements from product:
- Exactly one owner per workspace (for now). Do not allow multiple owners; enforce owner floor = 1 and ceiling = 1.
- On registration: auto-create a workspace named `<FirstName>'s Workspace` (or similar) and add user as Owner; set as active workspace.
- Invites: sent by email (to existing users); recipients view pending invites in Settings and can accept/decline.

## 2) Target Architecture (High-Level)
- Data model:
  - `Workspace` (existing).
  - `User` (existing).
  - New join table `WorkspaceMember` with `role` enum {owner, admin, viewer}, `status` {active, removed}, timestamps.
  - New `WorkspaceInvite` with `id`, `workspace_id`, `email`, `role` (admin/viewer only), `invited_by`, `status` {pending, accepted, declined, expired}, `token` (optional for future email links), timestamps.
  - Invariants: each workspace must have exactly 1 owner; user may have multiple memberships; soft-remove members by status; invite acceptance only for existing users whose email matches.
- API surface (proposed):
  - `GET /workspaces` → list memberships for current user.
  - `POST /workspaces` → create workspace (requires auth) → auto-add creator as owner.
  - `POST /workspaces/{id}/members` → add existing user to workspace with role (owner cannot be added via this route to preserve single owner).
  - `PATCH /workspaces/{id}/members/{user_id}` → change role.
  - `DELETE /workspaces/{id}/members/{user_id}` → remove member (respect owner floor).
  - `GET /workspaces/{id}` → workspace detail incl. members (paginated).
  - Invites: `POST /workspaces/{id}/invites` (create invite for existing user email; roles admin/viewer), `GET /me/invites` (pending invites for current user), `POST /invites/{id}/accept`, `POST /invites/{id}/decline`.
  - `POST /workspaces/{id}/switch` or client-side selection with `active_workspace_id` in JWT/session? (see switching below).
- Workspace switching:
  - Option A: store `active_workspace_id` in session/JWT claims; update via `/workspaces/switch`.
  - Option B: client stores selection and passes `workspace_id` on each call. **Recommendation:** Option A for consistency + fewer footguns; still allow explicit `workspace_id` params for multi-tab safety.
- Roles/permissions:
  - Owner: single per workspace; manage roles/members, delete workspace (if allowed), all admin capabilities.
  - Admin: manage members (except owner role), manage data.
  - Viewer: read-only, no mutations.
  - Enforcement at router dependency layer; shared permission helper; prevent creating additional owners.

## 3) UI Plan
- Workspace switcher: add to topbar/sidebar (`ui/app/(dashboard)/layout.jsx` shell) showing active workspace name + dropdown to switch; pull from `GET /workspaces` memberships.
- Workspace creation: modal/form (name defaulting to `<FirstName>'s Workspace`) → calls `POST /workspaces` → switches to new workspace.
- Member management UI: settings page tab:
  - List members (name/email/role/status).
  - Add member (existing user email lookup) with role select (admin/viewer only).
  - Change role, remove member (guard owner).
  - Inline toasts + optimistic updates.
- Invites tab:
  - List pending invites for current user; Accept/Decline buttons.
  - Create invite form (email + role); shows errors for non-existent users.
- Role-awareness: hide/disable admin actions for Viewer; show badges.

## 4) Backend Tasks (proposed)
- Add `WorkspaceMember` model + migration.
- Add `WorkspaceInvite` model + migration.
- Seed default owner membership on user creation if none exists (compat path).
- Permission dependency: `require_membership(workspace_id, roles=[...])`.
- Endpoints listed above; extend `/auth/me` to include memberships + active workspace; extend `/workspaces` list to include roles.
- Switching endpoint to set active workspace in session/JWT.
- Validation: prevent removing or demoting the sole owner; disallow creating additional owners; invite acceptance must match user email; disallow accepting twice; decline keeps record.
- Tests:
  - Unit: membership creation, role transitions, guards; invite accept/decline.
  - Integration: API flows (create workspace, add member, invite, accept/decline, switch, permission denial, last-owner guard).

## 5) Frontend Tasks (proposed)
- Client models: extend `currentUser` shape to include `memberships` + `active_workspace_id` + pending invites.
- Add workspace switcher component (shell) + hook to refetch `currentUser` on switch.
- Settings → Members tab: list, add, role change, remove.
- Settings → Invites tab: list pending invites with Accept/Decline; create invite form (email + role).
- Workspace creation modal (dashboard entry point or settings), default name `<FirstName>'s Workspace`.
- Remove single-workspace assumptions: ensure API calls use active workspace (from auth context) or selected context.
- Toast + error handling consistent with `sonner`; form validation via `zod`.
- Tests: component tests for switcher, member table, invite accept/decline; integration (happy + unauthorized) with mocked fetch.

## 6) Data Migration / Compatibility
- Migration adds `workspace_members` table + `workspace_invites` table.
- Backfill: for each existing user/workspace pair, create owner membership if missing (script/migration). Enforce single owner by selecting primary owner (e.g., earliest created user) if multiple inferred; log for review.
- JWT/session update to carry `active_workspace_id`; fallback to first membership if missing.

## 7) Risks & Mitigations
- Risk: orphaned workspace with zero owners. Mitigate with DB constraint + app-level checks; single-owner rule.
- Risk: stale active workspace in session. Mitigate with `active_workspace_id` validation on each request (must be in user memberships).
- Risk: UI calling APIs without workspace context. Mitigate by centralizing workspace id in auth context/hook.
- Risk: Invite flow limited to existing users. Mitigate by clear error UX + copy; optional future magic-link tokens.
- Risk: Hardcoded workspace IDs lingering (campaign detail pages). Mitigate by refactoring to use auth context before launch.

## 8) Testing Strategy
- Backend integration tests per endpoint: happy, unauthorized, forbidden, last-owner guard, invite accept/decline.
- Frontend: component tests for switcher + member table + invites tab; E2E happy path (create workspace → switch → invite user → accept → change role → remove).
- Manual checklist: switcher across tabs, role-based visibility, API denial for viewer mutations, last-owner protection, invite accept/decline UX.

## 9) Open Questions
- Should workspace deletion be supported now? (default: no).
- Do we allow multiple owners? (assume yes; minimum 1).
- How to surface invites for users not yet registered? (out of scope now).

## 10) Work Log (update as we progress)
- 2025-11-24T17:59:29Z — Added frontend workspace switcher (dashboard shell) using `/workspaces/{id}/switch` and refreshed user context; lint clean.
- 2025-11-24T16:40:00Z — Tightened connection permissions: connection create/update/delete/sync require Owner/Admin membership; viewing connections allowed for all members (backend guard).
- 2025-11-24T16:14:45Z — Backend scaffolding: added `workspace_members` + `workspace_invites` models/migration, single-owner enforcement helpers, workspace list/create/switch + member CRUD + invite accept/decline APIs, auth hydration returns memberships/pending invites.
- 2025-11-24: Created living plan document; defined data model, API/UI plan, risks, and test strategy. Added single-owner requirement, default workspace on registration, invite accept/decline flow.
