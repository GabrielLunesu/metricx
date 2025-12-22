## 1. Investigation / Repro (must be written down)
- [ ] Create a minimal repro matrix (workspace timezone vs account timezone) for: `today`, `yesterday`, `last_7_days`
- [ ] Capture current payloads for `/workspaces/{id}/dashboard/unified` and identify whether `chart_data[].date` is `YYYY-MM-DD` or ISO timestamp
- [ ] Confirm whether backfill/attribution writes `captured_at` in the future for “today”

## 2. Time Model (backend contract)
- [ ] Document the time model in `design.md` and make it the authoritative rule
- [ ] Add a shared backend utility for: account “today”, date ranges, and bucket labeling

## 3. Ingestion Fix (no future timestamps)
- [ ] Update Meta sync: for non-realtime modes, use `captured_at=now` for rows where `metrics_date == account_today`
- [ ] Update Google sync: same as above
- [ ] Add unit tests asserting no snapshot is written with `captured_at > now + 1m`

## 4. Dashboard API Metadata
- [ ] Add explicit fields to the unified dashboard response:
  - [ ] `chart_granularity`: `intraday_15m | daily`
  - [ ] `chart_timezone`: the reporting timezone used for chart rendering (see design)
  - [ ] `data_as_of`: ISO timestamp (latest `captured_at` included in aggregates)
- [ ] Add intraday availability fields:
  - [ ] `intraday_available_from`: ISO timestamp (first included point for the day)
  - [ ] `intraday_reason_unavailable`: null or short string when falling back to daily
- [ ] For timeframe `today/yesterday`, only use intraday granularity when we have enough intraday buckets; otherwise return daily
- [ ] Add regression tests for `_get_date_range` and intraday fallback behavior

## 5. UI Fixes (no more date parsing bugs)
- [ ] Update dashboard chart modules to use `chart_granularity` instead of `timeframe` to decide tick formatting
- [ ] Add a safe formatter for date-only strings (render `MMM D` without timezone shifts)
- [ ] Ensure intraday timestamps render in the intended timezone (reporting timezone by default)
- [ ] Add a callout state: “Intraday data starts from first sync after you connect” when `intraday_available_from` is after start-of-day

## 6. Metric Definition Clarity
- [ ] Shopify-first: “Revenue” displays Shopify revenue when Shopify is connected
- [ ] Add a separate “Conversion value” metric (platform-reported) for direct platform comparisons
- [ ] Add a “Blended” explanation and a per-platform toggle or breakdown surface

## 7. Consistency Across Endpoints
- [ ] Refactor `UnifiedMetricService` to use `metrics_date` for daily queries (not `captured_at::date`)
- [ ] Refactor finance endpoints using `func.date(captured_at)` to use `metrics_date`
- [ ] Add a single shared aggregator used by dashboard + analytics + finance (or clearly document why not)

## 8. Reconciliation & Observability
- [ ] Add a “metrics consistency check” job (last 7 days) comparing API totals vs DB totals for Google/Meta
- [ ] Store discrepancy records and surface them in logs + Sentry context
- [ ] Add structured log fields: `workspace_id`, `connection_id`, `provider`, `metrics_date`, `captured_at`, `timezone`

## 9. Data Backfill / Cleanup
- [ ] Create a safe backfill plan to recompute `metrics_date` for existing snapshots (or re-sync last 30–90 days)
- [ ] Verify no `captured_at` values are in the future; fix if found
