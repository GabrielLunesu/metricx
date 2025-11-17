def require_env(name: str) -> str:
    """Return the value of a mandatory environment variable or raise RuntimeError.
    WHY: Fail-fast during application startup when critical configuration is missing.
    """
    import os
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
