"""Clerk Admin Service - API operations for user management.

WHAT: Service for calling Clerk's Backend API for admin operations
WHY: Admin dashboard needs to delete users from Clerk when removing them from platform

REFERENCES:
    - Clerk Backend API: https://clerk.com/docs/reference/backend-api
    - DELETE /users/{user_id}: https://clerk.com/docs/reference/backend-api/tag/Users#operation/DeleteUser
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CLERK_API_BASE = "https://api.clerk.com/v1"


def _get_clerk_secret_key() -> Optional[str]:
    """Get Clerk secret key from environment."""
    return os.getenv("CLERK_SECRET_KEY")


async def delete_clerk_user(clerk_id: str) -> bool:
    """Delete a user from Clerk.

    WHAT: Calls Clerk's Backend API to delete a user
    WHY: When deleting a user from our platform, they should also be removed from Clerk
         so they can't log in anymore

    Args:
        clerk_id: The Clerk user ID (e.g., "user_2abc123...")

    Returns:
        True if deletion was successful, False otherwise

    Note:
        - This is an irreversible operation
        - The user will be immediately signed out of all sessions
        - All user data in Clerk will be permanently deleted
    """
    secret_key = _get_clerk_secret_key()
    if not secret_key:
        logger.error("[CLERK_ADMIN] CLERK_SECRET_KEY not configured")
        return False

    url = f"{CLERK_API_BASE}/users/{clerk_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={
                    "Authorization": f"Bearer {secret_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info(
                    f"[CLERK_ADMIN] Successfully deleted user {clerk_id} from Clerk"
                )
                return True
            elif response.status_code == 404:
                # User already doesn't exist in Clerk - consider this success
                logger.warning(
                    f"[CLERK_ADMIN] User {clerk_id} not found in Clerk (may already be deleted)"
                )
                return True
            else:
                logger.error(
                    f"[CLERK_ADMIN] Failed to delete user {clerk_id} from Clerk: "
                    f"status={response.status_code}, body={response.text}"
                )
                return False

    except httpx.HTTPError as e:
        logger.exception(
            f"[CLERK_ADMIN] HTTP error deleting user {clerk_id} from Clerk: {e}"
        )
        return False
    except Exception as e:
        logger.exception(
            f"[CLERK_ADMIN] Unexpected error deleting user {clerk_id} from Clerk: {e}"
        )
        return False


async def get_clerk_user(clerk_id: str) -> Optional[dict]:
    """Fetch user details from Clerk.

    WHAT: Calls Clerk's Backend API to get user info
    WHY: May be useful for admin dashboard to show Clerk-side data

    Args:
        clerk_id: The Clerk user ID

    Returns:
        User data dict if found, None otherwise
    """
    secret_key = _get_clerk_secret_key()
    if not secret_key:
        logger.error("[CLERK_ADMIN] CLERK_SECRET_KEY not configured")
        return None

    url = f"{CLERK_API_BASE}/users/{clerk_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {secret_key}",
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"[CLERK_ADMIN] Failed to fetch user {clerk_id}: status={response.status_code}"
                )
                return None

    except Exception as e:
        logger.exception(f"[CLERK_ADMIN] Error fetching user {clerk_id}: {e}")
        return None
