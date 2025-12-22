"""
Live API Exceptions
===================

**Version**: 1.0.0
**Created**: 2025-12-17

Custom exception types for live API operations in the AI Copilot.

WHY THIS FILE EXISTS
--------------------
Live API calls have unique failure modes that differ from database queries:
- API quota exhaustion
- OAuth token expiry
- Per-workspace rate limiting
- Missing provider connections

These exceptions allow for precise error handling and user-friendly messaging.

RELATED FILES
-------------
- app/agent/live_api_tools.py: Raises these exceptions
- app/agent/nodes.py: Catches and handles these exceptions
- app/agent/rate_limiter.py: Raises WorkspaceRateLimitError
"""

from typing import Optional


class LiveApiError(Exception):
    """
    Base exception for all live API errors.

    WHAT:
        Parent class for all live API-related exceptions.

    WHY:
        Allows catching all live API errors with a single except clause
        while still being able to handle specific error types.

    USAGE:
        try:
            result = live_tools.get_live_metrics(...)
        except LiveApiError as e:
            # Handle any live API error
            return {"error": str(e)}
    """

    def __init__(self, message: str, provider: Optional[str] = None):
        """
        Initialize with error message and optional provider.

        PARAMETERS:
            message: Human-readable error description
            provider: The ad platform (google, meta) if applicable
        """
        super().__init__(message)
        self.provider = provider
        self.message = message

    def to_user_message(self) -> str:
        """
        Convert to user-friendly error message.

        RETURNS:
            String suitable for display to end users.
        """
        return self.message


class QuotaExhaustedError(LiveApiError):
    """
    API quota exceeded - cannot make more calls.

    WHAT:
        Raised when Google Ads or Meta Ads API daily/hourly quota is exhausted.

    WHY:
        Signals that we should fall back to snapshot data instead of
        retrying the API call.

    ATTRIBUTES:
        provider: Which API (google, meta)
        retry_after: Seconds until quota resets (if known)

    RECOVERY:
        Fall back to snapshot data from MetricSnapshot table.
    """

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
    ):
        """
        Initialize quota exhausted error.

        PARAMETERS:
            provider: "google" or "meta"
            retry_after: Seconds until quota resets (None if unknown)
            message: Custom error message (optional)
        """
        self.retry_after = retry_after

        if message is None:
            if retry_after:
                message = f"{provider.title()} Ads API quota exceeded. Resets in {retry_after} seconds."
            else:
                message = f"{provider.title()} Ads API quota exceeded. Using cached data instead."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about quota exhaustion."""
        if self.retry_after and self.retry_after < 300:  # Less than 5 minutes
            return f"The {self.provider.title()} Ads API is temporarily unavailable. Please try again in a few minutes."
        return f"I'm using cached data because the {self.provider.title()} Ads API is at its limit."


class TokenExpiredError(LiveApiError):
    """
    OAuth token has expired - user action required.

    WHAT:
        Raised when the access token for Google/Meta Ads has expired
        and refresh token also failed (or doesn't exist).

    WHY:
        User needs to re-authenticate to continue using live API features.

    ATTRIBUTES:
        provider: Which API (google, meta)
        connection_id: UUID of the Connection that needs re-auth

    RECOVERY:
        User must re-connect their ad account in Settings.
    """

    def __init__(
        self,
        provider: str,
        connection_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """
        Initialize token expired error.

        PARAMETERS:
            provider: "google" or "meta"
            connection_id: UUID of the affected Connection
            message: Custom error message (optional)
        """
        self.connection_id = connection_id

        if message is None:
            message = f"Your {provider.title()} Ads connection needs to be re-authorized."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about token expiry."""
        return (
            f"Your {self.provider.title()} Ads connection has expired. "
            f"Please reconnect in Settings to continue using live data."
        )


class WorkspaceRateLimitError(LiveApiError):
    """
    Per-workspace rate limit hit - must wait before retrying.

    WHAT:
        Raised when a workspace has exceeded its allowed API call rate.
        This is our internal rate limit, not the provider's quota.

    WHY:
        Prevents any single workspace from monopolizing API resources
        and affecting other users.

    ATTRIBUTES:
        retry_after: Seconds until rate limit resets
        workspace_id: UUID of the rate-limited workspace

    RECOVERY:
        Wait for retry_after seconds, or use snapshot data.
    """

    def __init__(
        self,
        retry_after: int,
        workspace_id: Optional[str] = None,
        provider: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """
        Initialize rate limit error.

        PARAMETERS:
            retry_after: Seconds until limit resets
            workspace_id: UUID of the workspace
            provider: Which API hit the limit (optional)
            message: Custom error message (optional)
        """
        self.retry_after = retry_after
        self.workspace_id = workspace_id

        if message is None:
            message = f"Rate limit exceeded. Please wait {retry_after} seconds before trying again."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about rate limiting."""
        if self.retry_after <= 10:
            return "Processing too many requests. Please wait a moment and try again."
        return f"You've made many API requests recently. Please wait {self.retry_after} seconds."


class ProviderNotConnectedError(LiveApiError):
    """
    No active connection for the requested provider.

    WHAT:
        Raised when trying to query a provider (Google/Meta) that
        the workspace hasn't connected yet.

    WHY:
        Provides clear guidance that the user needs to connect
        their ad account first.

    ATTRIBUTES:
        provider: Which provider is missing (google, meta)

    RECOVERY:
        User must connect their ad account in Settings.
    """

    def __init__(
        self,
        provider: str,
        message: Optional[str] = None,
    ):
        """
        Initialize not connected error.

        PARAMETERS:
            provider: "google" or "meta"
            message: Custom error message (optional)
        """
        if message is None:
            message = f"No {provider.title()} Ads account connected to this workspace."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about missing connection."""
        return (
            f"You haven't connected a {self.provider.title()} Ads account yet. "
            f"Go to Settings > Connections to add one."
        )


class LiveApiTimeoutError(LiveApiError):
    """
    Live API call timed out.

    WHAT:
        Raised when a live API call takes too long and times out.

    WHY:
        Prevents the copilot from hanging indefinitely on slow API responses.

    ATTRIBUTES:
        provider: Which API timed out
        timeout_seconds: How long we waited

    RECOVERY:
        Fall back to snapshot data.
    """

    def __init__(
        self,
        provider: str,
        timeout_seconds: int = 30,
        message: Optional[str] = None,
    ):
        """
        Initialize timeout error.

        PARAMETERS:
            provider: "google" or "meta"
            timeout_seconds: How long we waited before timing out
            message: Custom error message (optional)
        """
        self.timeout_seconds = timeout_seconds

        if message is None:
            message = f"{provider.title()} Ads API call timed out after {timeout_seconds} seconds."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about timeout."""
        return (
            f"The {self.provider.title()} Ads API is responding slowly. "
            f"I'm using cached data instead."
        )


class LiveApiPermissionError(LiveApiError):
    """
    Insufficient permissions for the requested operation.

    WHAT:
        Raised when the connected account doesn't have permission
        to access the requested data.

    WHY:
        Helps users understand they may need to update their OAuth scopes
        or use a different account with proper access.

    ATTRIBUTES:
        provider: Which API denied access
        required_permission: What permission is needed (if known)

    RECOVERY:
        Reconnect with proper permissions, or use a different account.
    """

    def __init__(
        self,
        provider: str,
        required_permission: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """
        Initialize permission error.

        PARAMETERS:
            provider: "google" or "meta"
            required_permission: What permission is needed
            message: Custom error message (optional)
        """
        self.required_permission = required_permission

        if message is None:
            if required_permission:
                message = f"Missing permission '{required_permission}' for {provider.title()} Ads."
            else:
                message = f"Insufficient permissions for {provider.title()} Ads API."

        super().__init__(message, provider)

    def to_user_message(self) -> str:
        """User-friendly message about permission issues."""
        return (
            f"Your {self.provider.title()} Ads account doesn't have access to this data. "
            f"Please check your account permissions or try reconnecting."
        )
