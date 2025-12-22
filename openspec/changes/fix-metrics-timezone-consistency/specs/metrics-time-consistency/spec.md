## ADDED Requirements

### Requirement: Deterministic Time Semantics
The system SHALL treat `metrics_date` as the sole calendar-day dimension for ad metrics and SHALL NOT derive day boundaries from `captured_at`.

#### Scenario: “Today” is correct in account timezone
- **GIVEN** an ad account timezone different from UTC
- **WHEN** the dashboard requests `timeframe=today`
- **THEN** the system returns metrics for the account’s current calendar day
- **AND** the response includes the account timezone used

### Requirement: No Future-Captured Snapshots
The system SHALL NOT persist ad metric snapshots with `captured_at` later than the ingestion time.

#### Scenario: Backfill includes the current day
- **GIVEN** a backfill sync that includes `metrics_date == account_today`
- **WHEN** snapshots are written
- **THEN** those snapshots have `captured_at` close to the actual sync time (not end-of-day)

### Requirement: Chart Granularity Contract
The system SHALL return explicit chart granularity metadata so the UI can format axes without guessing.

#### Scenario: Single-day request returns daily data
- **GIVEN** the dashboard requests `timeframe=yesterday`
- **AND** only one daily snapshot exists for that day
- **WHEN** the system returns chart data
- **THEN** it returns `chart_granularity=daily`
- **AND** `chart_data[].date` is `YYYY-MM-DD`
- **AND** it returns `intraday_reason_unavailable` so the UI can explain why hourly data isn’t shown

### Requirement: Metric Naming Clarity
The system SHALL show Shopify-first revenue when Shopify is connected and SHALL clearly indicate when totals are blended across platforms.

#### Scenario: User compares Google Ads UI to dashboard
- **GIVEN** a dashboard showing blended totals
- **WHEN** the user views the “Revenue” metric
- **THEN** the UI indicates the revenue source (Shopify vs platform conversion value)
- **AND** provides a Google-only view for direct comparison
