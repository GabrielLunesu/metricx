# Phase 2.1 – Token Encryption Implementation

**Date**: 2025-11-01  
**Owner**: Meta Integration Squad  
**References**: `backend/app/security.py`, `backend/app/services/token_service.py`, `backend/tests/services/test_token_service.py`

---

## 1. What We Shipped

- Added Fernet-backed encryption helpers for provider credentials. (`encrypt_secret`, `decrypt_secret`)
- Relaxed the `tokens` table so refresh/expiry metadata is optional and added `ad_account_ids`.
- Introduced `store_connection_token` service to own encryption + persistence.
- Seed script now stores the system Meta token encrypted when available.
- Manual Meta sync retrieves decrypted tokens before calling the API.
- Added unit tests covering new token service behaviour.

---

## 2. Why This Matters

- Removes plaintext Meta tokens from the database, satisfying the security goal in Phase 2.1.
- Centralizes token handling so future OAuth callbacks (Phase 7) reuse the same utilities.
- Makes it safe to persist system-user tokens during Phase 2–3 manual flows.

---

## 3. System Impact

| Area | Impact |
| ---- | ------ |
| **Backend bootstrap** | Requires `TOKEN_ENCRYPTION_KEY` to be present before importing `app.security`. |
| **Database** | New Alembic revision `20251101_000001_update_tokens_encryption.py` (adds `ad_account_ids`, relaxes NOT NULL constraints). |
| **Seed flow** | Seeds encrypted token when `META_ACCESS_TOKEN` is set. |
| **Meta Sync** | Uses decrypted token if a connection has one; falls back to `.env` token otherwise. |
| **Testing** | Added pytest fixture to set encryption key and coverage for token service. |

---

## 4. Deployment & Migration Steps

1. Generate a Fernet key (only once per environment):  
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Export the key alongside `JWT_SECRET` (e.g. in `backend/.env`):  
   ```
   TOKEN_ENCRYPTION_KEY=<generated-key>
   ```
3. Install updated requirements:  
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Run migrations:  
   ```bash
   alembic upgrade head
   ```
5. Restart the backend process so the environment variables are loaded.

---

## 5. Validation Checklist

- ✅ Pytest coverage: `pytest backend/tests/services/test_token_service.py`
- ✅ Manual smoke: launch backend with `TOKEN_ENCRYPTION_KEY` set and trigger Meta sync button.
- ✅ Database: confirm encrypted token payload (non-readable) in `tokens.access_token_enc`.
- ✅ Logs: look for `[TOKEN_ENCRYPT]` and `[TOKEN_DECRYPT]` entries confirming encryption/decryption attempts.

---

## 6. Rollback Plan

1. Revert to commit prior to Phase 2.1 changes.
2. Downgrade migration: `alembic downgrade db163fecca9d`.
3. Remove `TOKEN_ENCRYPTION_KEY` requirement and restart backend.

---

## 7. Next Considerations

- Update connection admin UI to show token metadata safely.
- Extend token service to handle automatic refresh once OAuth is introduced.
- Add integration test validating Meta sync uses decrypted token end-to-end.

