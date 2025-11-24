# AdNavi UI — Living Document

> How to use this doc  
> - Keep this file current on every UI change (components, routes, API touchpoints, patterns, deps).  
> - Update the changelog section at the bottom with ISO timestamps + short summaries.  
> - Note rationale + references so non-technical readers understand intent.  
> - Remove or flag stale mock data/components as we replace them with real data.  
> - If a section becomes outdated, fix it immediately—do not leave TODOs.

---

## 0) Stack & Conventions
- Framework: Next.js 15.5.4 (App Router), React 19.1.0, JSX only.
- Styling: Tailwind v4 utilities + custom gradients; dark-ish soft shadows on dashboard.
- Icons: lucide-react; Charts: Recharts (sparklines/visitors).
- State: local component state; no global store yet.
- Notifications: `sonner` Toaster via `ui/app/providers.jsx` injected in root layout.
- Errors: `ui/app/global-error.jsx` as global error boundary (renders friendly fallback + retry).
- Forms: `react-hook-form` + `zod` + `@hookform/resolvers` central schemas in `ui/lib/validation.js`.
- Class helpers: `clsx`, `tailwind-merge` (`ui/lib/cn.js`).
- Auth check: dashboard layout calls `/auth/me` (client) via `currentUser` in `ui/lib/auth.js`.

## 1) Routes (App Router)
- `/` → `ui/app/page.jsx` (marketing/home)
- `/login` → `ui/app/login/page.jsx`
- `/dashboard` → `ui/app/(dashboard)/dashboard/page.jsx` (home dashboard)
- `/analytics` → `ui/app/(dashboard)/analytics/page.jsx`
- `/copilot` → `ui/app/(dashboard)/copilot/page.jsx`
- `/finance` → `ui/app/(dashboard)/finance/page.jsx`
- `/campaigns` → `ui/app/(dashboard)/campaigns/page.jsx`
- `/campaigns/[id]` → `ui/app/(dashboard)/campaigns/[id]/page.jsx`
- Layouts: `ui/app/layout.jsx` (global shell + providers) and `ui/app/(dashboard)/layout.jsx` (sidebar chrome + auth gate).

## 2) Data & API Touchpoints
- `ui/lib/api.js` — core client for KPIs, workspace info, QA, connections, sync jobs, auth profile/password, entity performance, etc. Uses `getApiBase()` from `ui/lib/config.js`.
- `ui/lib/financeApiClient.js` — P&L + manual costs CRUD (create/list/update/delete).
- `ui/lib/pnlAdapter.js` — maps finance responses to view models (no business logic in UI).
- `ui/lib/auth.js` — `currentUser()` client fetch for `/auth/me`.
- `ui/lib/validation.js` — shared zod schemas (`profileSchema`, `passwordSchema`, `manualCostSchema`).
- Toasts: `sonner` Toaster in `ui/app/providers.jsx`; used across finance/settings for CRUD success/errors.
- Error handling: fetch helpers throw on non-2xx with contextual messages; UI surfaces via toasts and inline messages.

## 3) Pages & Purpose
- Dashboard (`/dashboard`): KPIs strip (real API), assistant entry, notifications, visitors chart, use cases list.
- Analytics (`/analytics`): mock-driven insights, rules, charts; uses data from `ui/data/analytics/*`.
- Copilot (`/copilot`): chat UI with mock seed messages/context.
- Finance (`/finance`): real P&L via financeApiClient + adapter; manual costs CRUD + AI summary (QA endpoint).
- Campaigns (`/campaigns`, `/campaigns/[id]`): mock campaign table/detail; sorting/filtering client-side.
- Auth/Login: simple form + styling; relies on backend auth endpoints.

## 4) Components Inventory (high-level)
- Shell: `Sidebar`, `AuroraBackground`, `Topbar`, `WorkspaceSummary`, `UserMini`, `FooterDashboard`.
- Primitives: `Card`, `IconBadge`, `KeyValue` (used in canvas nodes), `PillButton`, `TabPill`, `LoadingAnimation`.
- KPI & Data Viz: `KPIStatCard`, `Sparkline`, `LineChart`, `TrendSparkline`, `MiniKPI`.
- Sections: `components/sections/HomeKpiStrip.jsx` (fetches KPIs), `AssistantSection`, analytics section components (controls, KPIs, AdSet carousel, radar, rules), copilot cards, finance cards/tables/modals, campaign table/detail/rules.
- Finance: `TopBar`, `FinancialSummaryCards`, `PLTable`, `ChartsSection`, `ManualCostModal` (form-validated), `AIFinancialSummary`.
- Settings: `ConnectionsTab` (sync controls, delete, frequency with toasts), `ProfileTab` (profile/password forms with validation + toasts).
- Error/Providers: `ui/app/global-error.jsx`, `ui/app/providers.jsx`.
- Canvas (feature): `ui/features/canvas/components/*` for node rendering (uses `KeyValue`).

## 5) Mock Data (still used)
- Dashboard: `ui/data/kpis.js`, `ui/data/notifications.js`, `ui/data/visitors.js`, `ui/data/useCases.js`.
- Analytics: `ui/data/analytics/*` (header, kpis, adsets, chart, opportunities, rules, panel).
- Copilot: `ui/data/copilot/*` (context, seedMessages, suggestions, placeholders).
- Finance: `ui/data/finance/*` (kpis, costs, series, rules, timeRanges) — used as placeholders in some components.
- Campaigns: `ui/data/campaigns/*` (campaigns, detail, rules, sorters).
- Removed as unused: `ui/data/company.js` (legacy card).

## 6) Loading, Errors, Feedback
- Auth gating: dashboard layout shows centered spinner while checking `/auth/me`.
- Finance: `LoadingAnimation` while fetching P&L; toasts on fetch errors.
- KPI Strip: skeleton cards; inline error message if fetch fails.
- Global error boundary: `ui/app/global-error.jsx` shows retry + “Return to dashboard”.
- Toasts: success/error for connections CRUD, sync frequency updates, profile/password save, manual cost CRUD, finance load issues.

## 7) Patterns & Guidance
- Keep data fetching in libs (`ui/lib/*`) and container components; keep presentational components stateless.
- Form validation lives in `ui/lib/validation.js`; reuse across pages.
- Prefer toasts for user-facing feedback; reserve inline errors for form fields.
- When adding routes/components, update this doc (routes, inventory, mock/real data) and `docs/living-docs/ADNAVI_BUILD_LOG.md`.
- Remove or archive mock data when replaced by real API responses; note that in section 5.

## 8) Known Gaps / Opportunities
- Accessibility and responsive polish <1024px still pending.
- Some sections still use mock cards/placeholder data (analytics insights/campaign rules) even though core KPIs and campaign lists call the API; keep swapping mocks for live endpoints.
- No automated UI tests yet (Testing Library/Vitest scaffolded).
- Toast theme currently global; could scope variants per page if needed.

## 9) Changelog
- 2025-11-24T14:05:00Z — Initial UI living doc created; documented routes/components/data/feedback patterns; noted removal of unused `company` mock + `CompanyCard`.
