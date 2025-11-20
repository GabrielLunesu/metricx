"""Security utilities for JWTs and provider token encryption.

WHAT:
    Centralizes password hashing, JWT helpers, and (Phase 2.1) symmetric
    encryption for provider access tokens.

WHY:
    - JWT helpers are used by `/auth` endpoints.
    - Token encryption keeps provider credentials out of plaintext storage.

REFERENCES:
    - docs/living-docs/META_INTEGRATION_STATUS.md (Phase 2.1 scope)
    - backend/docs/roadmap/meta-ads-roadmap.md (Token storage milestone)
"""

import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken
from jose import jwt, JWTError
from passlib.hash import bcrypt


ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "10080"))
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")

logger = logging.getLogger(__name__)


if not JWT_SECRET or not TOKEN_ENCRYPTION_KEY:
    # Attempt to load from local .env if running in dev
    # Attempt to load from local .env if running in dev
    from app.utils.env import load_env_file
    load_env_file()
    JWT_SECRET = JWT_SECRET or os.getenv("JWT_SECRET", "")
    JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "10080"))
    TOKEN_ENCRYPTION_KEY = TOKEN_ENCRYPTION_KEY or os.getenv("TOKEN_ENCRYPTION_KEY", "")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set. Ensure backend/.env is created or env var is exported.")

if not TOKEN_ENCRYPTION_KEY:
    raise RuntimeError(
        "TOKEN_ENCRYPTION_KEY is not set. Generate a 32-byte Fernet key and export it "
        "or add it to backend/.env (see backend/docs/roadmap/meta-ads-roadmap.md)."
    )

try:
    # Validate key length by decoding without storing plaintext material.
    base64.urlsafe_b64decode(TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    _cipher = Fernet(TOKEN_ENCRYPTION_KEY)
except (ValueError, TypeError) as exc:
    raise RuntimeError(
        "TOKEN_ENCRYPTION_KEY must be a URL-safe base64-encoded 32-byte string. "
        "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    ) from exc


def encrypt_secret(plaintext: str, *, context: str) -> str:
    """Encrypt provider secrets before persisting.

    WHAT:
        Symmetric encryption wrapper around Fernet for storing Meta tokens.
    WHY:
        Prevents raw tokens from landing in the database or logs.
    REFERENCES:
        docs/living-docs/META_INTEGRATION_STATUS.md#-next-steps (Phase 2.1)

    Args:
        plaintext: Raw secret to encrypt (e.g., Meta access token).
        context:   Friendly label for logs (provider/account).

    Returns:
        URL-safe base64 ciphertext suitable for DB storage.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty secret.")

    ciphertext = _cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    logger.info("[TOKEN_ENCRYPT] Secret encrypted for %s (length=%d)", context, len(plaintext))
    return ciphertext


def decrypt_secret(ciphertext: str, *, context: str) -> str:
    """Decrypt provider secrets when restoring tokens for API calls.

    WHAT:
        Reverses `encrypt_secret` using the shared Fernet key.
    WHY:
        Meta sync (Phase 2) and future automation (Phase 3) require plaintext tokens.
    REFERENCES:
        backend/app/routers/meta_sync.py::_get_access_token

    Args:
        ciphertext: Encrypted token retrieved from DB.
        context:    Friendly label for logs (provider/account).

    Returns:
        Plaintext secret string.

    Raises:
        ValueError: If the stored value cannot be decrypted.
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty secret.")

    try:
        plaintext = _cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        logger.info("[TOKEN_DECRYPT] Secret decrypted for %s (length=%d)", context, len(plaintext))
        return plaintext
    except InvalidToken as exc:
        logger.error("[TOKEN_DECRYPT] Invalid ciphertext for %s", context)
        raise ValueError("Unable to decrypt stored token.") from exc


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT for the given subject (e.g., user email)."""
    if expires_minutes is None:
        expires_minutes = JWT_EXPIRES_MINUTES
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    to_encode: Dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, returning its payload.

    Raises jose.JWTError on failure.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise exc


