# Google Ads Integration - Living Status Document

Last Updated: 2025-11-04

Principles: Separation of concerns, single responsibility, modular and elegant code, comment all logic and files (WHAT/WHY/REFERENCES).

---

## How It Works (Non-Technical Overview)

- Two-step sync (like Meta):
  - Step 1 pulls your Google account structure (campaigns, ad groups, ads, and for Performance Max: asset groups and creative assets). We use UPSERT so re-running the sync simply refreshes names/status.
  - Step 2 ingests daily performance metrics only after the hierarchy exists. We ingest at the right level (ads for standard campaigns, asset groups and creatives for PMax) and skip unknown IDs to avoid placeholder/orphan rows.
- Performance Max support:
  - Asset groups are mapped to metricx’s `adset` level; asset group assets are mapped to `creative` level. This makes the UI and QA reflect what you see in Google Ads.
- Safe ingestion prevents bad data:
  - If the hierarchy isn’t present, metrics sync completes as a no‑op (0 ingested) instead of creating "unknown" entities. This mirrors Meta and avoids endless backfills.
- Manual today, automation next:
  - Settings page auto‑creates a Google connection from env credentials and triggers entities → metrics in the right order. Scheduler automation is the next step.


---

## Quick Status

- Current Phase: Phase 2/3 complete — hierarchy + metrics live; automation & OAuth next
- Overall Progress: ~60% (Week 2 of 3–4)
- Env Ready: Yes (vars in `.env`)
- Token Model: Encrypted storage available; OAuth still pending

| Component | Status | Notes |
|-----------|--------|-------|
| Dev token + OAuth client | ✅ Ready | Provided via env vars |
| Google Ads Python SDK | ✅ Added | `backend/requirements.txt` pinned to 23.0.0 |
| Client service | ✅ Complete (with tests) | `app/services/google_ads_client.py` |
| Entity sync | ✅ Complete | Campaign → AdGroup → Ad; PMax AssetGroup → AssetGroupAsset |
| Metrics sync | ✅ Complete | Ad + Asset Group + Creative metrics, 90‑day backfill |
| Connection metadata | ✅ Complete | Stores timezone/currency on connection |
| UI sync button | ✅ Complete | Settings page parity with Meta |
| Auto‑connect from env | ✅ Complete | `POST /connections/google/from-env` |


---

## Phases & Tasks

### Phase 0 — Accounts & Credentials (Complete)
- MCC + developer token configured (SANDBOX/test accounts)
- Google Cloud project + Google Ads API enabled
- OAuth client created; refresh token present in env

Manual verification: build `GoogleAdsClient` from env and run GAQL to list customers/campaigns.

### Phase 1 — Client Service (Complete)
- `app/services/google_ads_client.py` includes env‑based factory, GAQL helpers, rate limiting, retries, and level‑specific metric fetchers.
- Tests: `app/tests/test_google_ads_client.py`, `app/tests/test_google_sync_helpers.py`.

### Phase 2 — Entity Sync (Complete)
- Endpoint: `POST /workspaces/{id}/connections/{id}/sync-google-entities`
- UPSERT hierarchy: campaign → ad group → ad; PMax asset group → asset group asset (stored as creative level).
- Persists status, timezone, currency; robust logging.

### Phase 3 — Metrics Sync (Complete)
- Endpoint: `POST /workspaces/{id}/connections/{id}/sync-google-metrics`
- 90-day backfill, 7‑day chunks, incremental.
- Standard campaigns: ad‑level metrics.
- Performance Max: additionally fetch asset group (adset level) and asset group asset (creative level) metrics.
- Safeguards: zero‑op if hierarchy missing; skip unknown IDs to avoid placeholders.

### Phase 4 — Connection Metadata (Complete)
- Alembic migration `20251104_000001` adds timezone/currency columns.
- Populated during first entity sync per connection.

### Phase 5 — UI Integration (Complete)
- Settings page auto‑connects from env, shows Google sync widget.
- Campaigns page displays PMax label; ad set detail page shows creatives when present.

### Phase 6 — Reliability & Quotas (In Progress)
- Backoff + retries implemented. TODO: automated jobs, quota telemetry.

### Phase 7 — OAuth Flow (Planned)
- Implement authorize/callback endpoints, encrypted token storage per connection, and update UI flow.


---

## Next Actions

1) Integration tests for google_sync router with mocked client.
2) Scheduler automation for nightly entity + metrics sync (with alerting).
3) OAuth handshake to replace env‑based refresh token (Phase 7).
4) Optional: richer creative UI (previews) and quota telemetry dashboards.


---

## Changelog

- 2025-11-04: Added PMax hierarchy + metrics, safe ingestion, QA provider awareness, PMax label UI.

- 2025-11-04: Converted doc into updateable plan; defined phases, tests, mappings
- 2025-11-04: Added google-ads dependency; added connection tz/currency columns; implemented client service and tests
- 2025-11-04: Added Google sync endpoints; added env-based connection creation; updated Settings UI to auto-connect + show Google Sync button; made Token.access_token_enc nullable