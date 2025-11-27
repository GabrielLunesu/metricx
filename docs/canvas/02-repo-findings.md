---
title: metricx Canvas — Repo Findings
status: research-only (no code changes)
date: 2025-11-05
---

# WHAT
Read-only scan of the codebase to identify where to hook the new Campaign Canvas (React Flow) without breaking existing pages, routes, types, or API contracts.

# WHY
De-risk the implementation by mapping current routing, data-fetch, unified entity model, and design system; surface gaps and safe integration points for a read-only canvas view.

# SUMMARY
- Frontend: Next.js App Router with a `(dashboard)` group, JSX (no TypeScript). Local component state; data fetched via thin API clients; tailwind v4 CSS with light “glass” UI primitives (no shadcn registry in use).
- Backend: FastAPI with unified entity schema and an `entity-performance` router that exposes list and children endpoints used by the Campaigns UI.
- Telemetry/QA: Structured logging in backend. No Sentry in UI found. Vitest present for UI; backend has tests and QA scripts.
- Recommended: Add the Canvas as a new page under the dashboard group, read-only, behind a feature flag, and reuse the existing `entity-performance` endpoints + adapters.

---

## Frontend

Routing (Next.js App Router)
- Root layout and globals: `ui/app/layout.jsx:1`, `ui/app/globals.css:1`
- Dashboard group: `ui/app/(dashboard)/layout.jsx:1`, with routes:
  - Dashboard: `ui/app/(dashboard)/dashboard/page.jsx:11`
  - Analytics: `ui/app/(dashboard)/analytics/page.jsx:13`
  - Campaigns (list + details):
    - List: `ui/app/(dashboard)/campaigns/page.jsx:12`
    - Campaign detail: `ui/app/(dashboard)/campaigns/[id]/page.jsx:12`
    - Ad set detail: `ui/app/(dashboard)/campaigns/[id]/[adsetId]/page.jsx:9`
- Login: `ui/app/login/page.jsx:6`

State & Data Fetch
- No Redux/Zustand/SWR/TanStack usage in source (deps appear in lock only).
- Local state + thin API clients:
  - Campaigns client: `ui/lib/campaignsApiClient.js:30` (GET `/entity-performance/list`, `/{id}/children`)
  - Adapter (formatting, trend alignment): `ui/lib/campaignsAdapter.js:1`
  - Generic API utilities (sync, connections, settings): `ui/lib/api.js:1`
  - Auth current user: `ui/lib/auth.js:9`
  - Config (API base/env): `ui/lib/config.js:1`

Design System
- Tailwind v4 via PostCSS: `ui/postcss.config.mjs:2`, CSS utilities in `ui/app/globals.css:1`.
- Primitives: `ui/components/Card.jsx:1`, `ui/components/PillButton.jsx`, `ui/components/StatusPill.jsx`, `ui/components/Sparkline.jsx`.
- Class merge helper: `ui/lib/cn.js:6`.
- No generated shadcn registry/components.json found; package `shadcn` exists but not used.

Campaigns Page (current behavior)
- Uses `campaignsApiClient.fetchEntityPerformance` and `campaignsAdapter.adaptEntityPerformance` with filters/timeframe/sort/pagination.
- File: `ui/app/(dashboard)/campaigns/page.jsx:1`

Implication for Canvas
- Reuse the Campaigns API client + adapter to build `nodes` (campaign/adset/ad/creative) and `edges` on the client.
- Keep all mapping client-side; do not change backend.
- New page location proposal (read-only): `ui/app/(dashboard)/canvas/page.jsx`
- Feature folder proposal: `ui/features/canvas/*` (components, hooks, lib, mock).

Branding & Styling
- Current aesthetic is “premium minimal” with cyan accents and glass effects in `globals.css`. Canvas can reuse these tokens and classes (e.g., `.glass-card`, subtle shadows, 150–200ms easings).

Accessibility
- Existing components are mostly semantic HTML with Tailwind classes. Canvas should add ARIA labels for node roles and keyboard focus around the React Flow viewport.

---

## Backend (FastAPI)

Unified Model & Enums
- Provider: `backend/app/models.py:23` (`google`, `meta`, `tiktok`, `other`)
- Levels: `backend/app/models.py:32` (`campaign`, `adset`, `ad`, `creative`, …)
- Used across schemas and routers.

Entity Performance API (used by UI)
- Router: `backend/app/routers/entity_performance.py`
  - List: `@router.get("/list")` → `backend/app/routers/entity_performance.py:375`
  - Children: `@router.get("/{entity_id}/children")` → `backend/app/routers/entity_performance.py:500`
- Contract: `backend/app/schemas.py` → `EntityPerformanceResponse` (meta, pagination, rows with metrics + trend).
- Filters/params: `entity_level`, `parent_id`, `timeframe` (`7d`/`30d`), `platform`, `status`, sorting, pagination.
- Time bucketing and trend series builder provided server-side.

Other Endpoints Used in UI
- Sync endpoints referenced by UI: `ui/lib/api.js` (Meta/Google sync for entities/metrics)
- Finance/P&L endpoints: `ui/lib/financeApiClient.js:32`
- Auth/session with cookies; UI sets `credentials: 'include'` on fetches.

Auth & Workspace Scoping
- `get_current_user` provides `workspace_id`; routers filter by workspace.
- Example: `backend/app/routers/entity_performance.py:410`.

Rate Limits / Feature Flags
- No explicit rate limiting or feature flags detected in code. Feature-flagging Canvas should be implemented client-side initially.

---

## Telemetry & QA

Telemetry/Logging
- Backend structured logging present (e.g., QA pipeline): `backend/app/services/qa_service.py:38`, `backend/app/state.py:29`.
- No Sentry SDK usage detected in UI or API.

Tests
- UI: `ui/vitest.config.js:1`, `ui/tests`/`ui/test` present.
- Backend: `backend/app/tests`, plus QA scripts and test results in `backend/test-results`.

---

## Integration Plan (non-breaking)

Page & Feature Folders
- New page (read-only): `ui/app/(dashboard)/canvas/page.jsx`.
- Feature folder (tree only, no coupling): `ui/features/canvas/{components,hooks,lib,mock}`.
- Ensure no changes to existing routes/exports.

Data Contract & Mapping (client-only)
- Respect unified model. Build `CanvasNode/CanvasEdge` locally from `EntityPerformanceResponse` using a new client-side mapper.
- Idempotent node ids/positions for caching (persist layout in `localStorage` keyed by `workspaceId`).
- Reuse existing query params (`timeframe`, `platform`, `status`).

UI System
- Reuse Tailwind v4 and existing glass tokens/classes. Keep payload low and lazy-load React Flow (`@xyflow/react`) only on Canvas page.
- Interactions: pan/zoom/select/drag (local only), hover, light motion.

Accessibility
- Focus rings on nodes, ARIA roles for node/edge/toolbar; keyboard panning via React Flow options.

Feature Flag
- `features.canvas` boolean (client-side only to start). Hide nav link and route if disabled.

---

## Gaps & Risks (with mitigations)

1) Library footprint (bundle size)
- Risk: React Flow adds >200KB if not handled.
- Mitigation: Route-level dynamic import (Next.js `dynamic` with `ssr: false`), split Canvas feature code, avoid global imports.

2) No shared query lib (SWR/TanStack)
- Risk: Cache/stale states for Canvas fetches.
- Mitigation: Reuse existing `campaignsApiClient` with simple in-file memo or add a tiny hook for cache; keep scope local to Canvas.

3) No TypeScript in UI
- Risk: Harder to type Canvas nodes/edges.
- Mitigation: Use JSDoc typedefs in `ui/features/canvas/lib/types.js` and docstrings across mapping/hooks.

4) Feature flag infra absent
- Risk: Accidental exposure in prod.
- Mitigation: Add a simple `features.js` in UI with `canvas: false` default; guard route/link rendering.

5) A11y focus in Flow viewport
- Risk: Keyboard users can’t navigate nodes.
- Mitigation: Ensure tabbable nodes, aria-labels, and visible focus; rely on React Flow keyboard handlers, add outline styles.

6) Telemetry for UI events
- Risk: No current UI telemetry sink.
- Mitigation: If a frontend logger exists later, wire minimal “opened panel / dragged / filtered” events; for now, no-op stubs.

7) Backend assumptions (creative level)
- Note: Backend may return `creative` under ad sets (PMax). Canvas should treat `creative` as leaf nodes along with `ad`.

---

## Next Steps (proposed PR sequence)

1) PR-1 (chore):
- Scaffold `ui/features/canvas/*` (components/hooks/lib/mocks), docs in `docs/canvas/01-functional-spec.md` and `README`.
- Add `features.js` with `canvas: false`.

2) PR-2 (page):
- Create `ui/app/(dashboard)/canvas/page.jsx` with `FlowViewport` and mock data; lazy-load React Flow; flag off by default.

3) PR-3 (data):
- Implement `useCanvasData` to fetch campaigns + children (adsets/ads/creatives) and map to nodes/edges; loading/empty states.

4) PR-4 (polish):
- Sidebars, toolbar, legends; a11y adjustments; visual parity with provided inspo.

5) PR-5 (telemetry & docs):
- Optional UI telemetry stubs; finalize README and changelog.

---

## References
- React Flow docs: `docs/docs-for-context/react-flow.md`
- Backend entity performance router: `backend/app/routers/entity_performance.py:375`, `backend/app/routers/entity_performance.py:500`
- Adapter used today: `ui/lib/campaignsAdapter.js:1`
- Campaigns page using the API: `ui/app/(dashboard)/campaigns/page.jsx:1`
- Design tokens/styles: `ui/app/globals.css:1`

