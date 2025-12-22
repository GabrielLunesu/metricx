# Change: Fix Metrics Timezone Consistency (Production-Ready)

## Why
We currently surface confusing and sometimes incorrect-looking dashboard numbers because we mix multiple time semantics (`metrics_date` vs `captured_at`) and the UI formats date-only strings as timestamps. This causes:
- Single-day charts showing a single point at an unexpected time (e.g., `22:45`) instead of “end of day”.
- New connections showing “Today” with only a `01:00` datapoint (date parsed as UTC midnight then shifted by local timezone).
- Users comparing “blended” totals (Google + Meta) to a single platform dashboard, assuming a mismatch.

These issues block trust. The system must be deterministic, explainable, and match platform totals within known limitations (attribution delays, currency, and metric definitions).

## What Changes
- Define and enforce a single time model:
  - `metrics_date`: the calendar day *as reported by the ad account’s timezone* (date-only).
  - `captured_at`: the actual UTC timestamp when we fetched the snapshot (timestamp).
  - **Invariant**: filtering/grouping by day uses `metrics_date`, never `DATE(captured_at)`.
- Fix ingestion so we never write “future” `captured_at` timestamps for “today” during backfill/attribution sync.
- Make the dashboard API return explicit chart metadata (`granularity`, `timezone`) so the UI never guesses.
- Update UI chart formatting to correctly handle date-only vs timestamp buckets (no more `new Date("YYYY-MM-DD")` for intraday).
- **Revenue source becomes Shopify-first**: if Shopify is connected, “Revenue” reflects Shopify revenue for the selected date range; platform-reported conversion value remains available as “Conversion value”.
- Clarify metric meaning in UI: “Conversion value” is platform-reported, and “Blended” is a sum across platforms.
- Add explicit intraday availability messaging: intraday is only available from the moment an account is connected and first sync completes.
- Add reconciliation + observability so mismatches are detected early:
  - log and expose `last_synced_at`, `data_as_of`, and provider-level totals for debugging
  - automated checks comparing stored totals vs API totals for recent dates

## Non-Goals
- Perfect real-time parity with ad dashboards minute-by-minute (platforms have delays).
- Solving attribution modeling differences (this work focuses on platform-reported metrics consistency and time correctness).

## Impact
- Backend: snapshot sync logic, dashboard aggregation, unified metrics service, finance aggregation.
- UI: dashboard chart modules and date formatting helpers.
- Data: existing rows may have `metrics_date` backfilled from UTC date; we will schedule a re-sync to correct it where needed.

## Success Criteria (Acceptance)
- “Today” after connecting a new account shows the latest datapoint near the last sync time (not `01:00`).
- “Yesterday” never shows a misleading timestamp derived from date parsing; either:
  - a proper intraday series (if multiple snapshots exist), or
  - a daily point labeled by date (if only a single daily snapshot exists).
- Dashboard “Revenue” and “Conversions” match Google Ads UI totals for the same date range when filtering to Google only (within documented platform latency).
- If Shopify is connected, dashboard “Revenue” matches Shopify for the same date range (in store timezone).
- Blended totals are clearly labeled and per-platform breakdown is accessible.
- We can answer “where does this number come from?” from a single debug payload (provider, date range, timezone, last sync, and GAQL/fields version).

## Rollout Plan
1. Ship ingestion + API metadata fixes behind a feature flag for internal workspaces.
2. Backfill/resync last 7–30 days for flagged workspaces to correct `metrics_date` and avoid future timestamps.
3. Enable for all workspaces; monitor mismatch alerts and error rates.
