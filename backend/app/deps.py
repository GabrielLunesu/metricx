"""Dependency providers and settings management."""

import os
from functools import lru_cache
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token


class Settings(BaseSettings):
    """Application settings loaded from environment or .env."""

    BACKEND_CORS_ORIGINS: str = "https://www.metricx.ai,http://localhost:3000"
    # Cookie domain must NOT include protocol (https://)
    # Set to None for same-origin cookies (works for both localhost and production)
    COOKIE_DOMAIN: Optional[str] = None
    ADMIN_SECRET_KEY: str = "supersecretkey-change-this-in-production"
    OPENAI_API_KEY: str | None = None
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CONTEXT_MAX_HISTORY: int = 5
    CONTEXT_TTL_SECONDS: int = 3600  # 1 hour

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[call-arg]


def get_current_user(
    db: Session = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None, alias="access_token"),
) -> User:
    """Resolve the current user from the `access_token` cookie.

    The cookie value is expected to be in the form: "Bearer <jwt>".
    """
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Remove optional "Bearer " prefix
    if access_token.startswith("Bearer "):
        token = access_token[len("Bearer ") :]
    else:
        token = access_token

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = (
        db.query(User)
        .filter(User.email == subject)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


