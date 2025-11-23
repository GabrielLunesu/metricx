def require_env(name: str) -> str:
    """Return the value of a mandatory environment variable or raise RuntimeError.
    WHY: Fail-fast during application startup when critical configuration is missing.
    """
    import os
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_env_file() -> None:
    """Load environment variables from .env file if not already set.
    
    WHAT:
        Loads variables from a local .env file into os.environ.
        Does NOT overwrite existing environment variables.
    WHY:
        Allows developers to use a local .env file for development
        without risking overwriting production variables.
    """
    import os
    import logging
    from dotenv import load_dotenv

    # Configure logging for this module if not already configured
    logger = logging.getLogger(__name__)
    
    # load_dotenv(override=False) is the default, but being explicit helps.
    # It returns True if the file was loaded, False otherwise.
    # Note: It returns True even if no vars were set, as long as the file exists.
    loaded = load_dotenv(override=False)
    
    if loaded:
        logger.info("Loaded local .env file (existing variables were NOT overwritten)")
    else:
        logger.debug("No local .env file found or loaded")

