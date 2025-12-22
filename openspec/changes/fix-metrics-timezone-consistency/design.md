# Design: Metrics Time & Correctness Model

## Problem Summary
We currently overload `captured_at` to mean both:
1) “when we fetched the data”, and
2) “which day the data belongs to”.

This creates timezone bugs and UI confusion, especially when:
- backfill assigns `captured_at` to “end of day” (which can be in the future for today),
- intraday charts filter by `captured_at`,
- UI parses date-only strings as UTC timestamps (`new Date("YYYY-MM-DD")`).

## Canonical Definitions
### `metrics_date` (date-only)
- **Meaning**: the calendar day the metrics represent, as reported by the ad platform in the ad account’s timezone.
- **Source**: Google `segments.date`, Meta `date_stop` (or equivalent).
- **Usage**: all daily filtering, grouping, and “yesterday/today” boundaries.

### `captured_at` (timestamp, UTC)
- **Meaning**: when our system fetched and stored this snapshot.
- **Source**: server time at ingestion.
- **Usage**: freshness, ordering (“latest snapshot for a day”), and intraday bucketing.

## API Contract for Charts
Dashboard endpoints must return:
- `chart_granularity`:
  - `intraday_15m`: `chart_data[].date` is ISO timestamp
  - `daily`: `chart_data[].date` is `YYYY-MM-DD`
- `chart_timezone`: IANA reporting timezone for UI rendering
- `data_as_of`: ISO timestamp of the newest included snapshot

UI must **never infer** granularity from timeframe; it must trust the contract.

## Reporting Timezone (single source of truth for the UI)
The dashboard needs a single timezone for consistent UX. We define:

- If Shopify is connected: `chart_timezone = shop_timezone` (store timezone)
- Else: `chart_timezone = primary_ad_account_timezone` (first connected ad account with a timezone)
- Else: `UTC`

If ad accounts have different timezones (rare but possible), we still render in `chart_timezone` and expose per-provider timezones in a debug payload; we also show a warning banner suggesting aligning account timezones.

## Intraday Rules
- Intraday charts represent **cumulative daily totals over time** (snapshots), not per-hour segmented stats.
- If only daily snapshots exist for a single-day timeframe (e.g., after a new connection backfills yesterday), the API should return `daily` granularity to avoid misleading intraday charts.
  - In this case the API SHOULD include `intraday_reason_unavailable` so the UI can message: “Hourly data starts after you connect and we start syncing.”

## Backfill Snapshot Timestamps (pragmatic constraint)
Today we deduplicate snapshots with a unique key that includes `captured_at`. During backfills we ingest many `metrics_date` rows in one run, so we must ensure `captured_at` is unique per `metrics_date` (or evolve the constraint).

Short-term, we keep `captured_at` “anchored” within each `metrics_date`:
- For historical days: `captured_at = end_of_day(metrics_date, account_timezone)` (stable and inside that day window)
- For the current day (`metrics_date == account_today`): `captured_at = now_utc_rounded_to_15m` (never in the future, enables intraday charts)

Long-term, consider evolving the unique constraint to include `metrics_date` so `captured_at` can always mean “ingestion time” without special casing.

## Known Platform Constraints (Documented)
- Same-day conversion value may change over time (attribution delay); we expose `data_as_of`.
- Currency is account currency; UI must display it and avoid implicit conversion.
