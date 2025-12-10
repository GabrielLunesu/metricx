/**
 * Workspace utilities for Clerk-authenticated sessions.
 *
 * WHAT: Provides workspace context for dashboard pages
 * WHY: After Clerk migration, we get user identity from Clerk but workspace from backend
 *
 * MIGRATION NOTE (2025-12-09):
 *   Replaced lib/auth.js currentUser() with this approach:
 *   - Clerk handles auth (user identity, session, tokens)
 *   - Backend maps clerk_id to user + active workspace
 *   - This file provides the bridge for workspace context
 *
 * USAGE:
 *   const user = await currentUser(); // uses window.Clerk
 *
 * REFERENCES:
 *   - backend/app/deps.py (get_current_user maps Clerk JWT to user)
 *   - backend/app/routers/workspaces.py (workspace endpoints)
 */

import { getApiBase } from './config';

const BASE = getApiBase();

/**
 * Get the Clerk session token for API requests.
 * Waits for Clerk to be ready if needed.
 */
async function getClerkToken() {
  // Only works client-side
  if (typeof window === 'undefined') {
    return null;
  }

  // Wait for Clerk to be ready (max 5 seconds)
  let attempts = 0;
  while (!window.Clerk?.session && attempts < 50) {
    await new Promise(resolve => setTimeout(resolve, 100));
    attempts++;
  }

  if (window.Clerk?.session) {
    try {
      return await window.Clerk.session.getToken();
    } catch (e) {
      console.error('Failed to get Clerk token:', e);
      return null;
    }
  }

  return null;
}

/**
 * Make an authenticated API request using Clerk token.
 */
export async function authFetch(url, options = {}) {
  const token = await getClerkToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });
}

/**
 * Fetch the current user's active workspace from backend.
 * The backend validates the Clerk JWT and returns the user's workspace.
 *
 * If user not found (404), automatically attempts repair via /webhooks/clerk/repair.
 * This handles the case where Clerk webhook failed during signup.
 *
 * @returns {Promise<{workspace_id: string, workspace_name: string, user_id: string}>}
 */
export async function getActiveWorkspace() {
  const res = await authFetch(`${BASE}/workspaces/active`, {
    method: 'GET',
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Not authenticated');
    }

    // Handle "User not found" - attempt automatic repair
    if (res.status === 404) {
      console.log('[workspace] User not found, attempting repair...');
      const repairRes = await authFetch(`${BASE}/webhooks/clerk/repair`, {
        method: 'POST',
      });

      if (repairRes.ok) {
        const repairData = await repairRes.json();
        console.log('[workspace] Repair successful:', repairData.status);
        // Retry the original request
        const retryRes = await authFetch(`${BASE}/workspaces/active`, {
          method: 'GET',
        });
        if (retryRes.ok) {
          return retryRes.json();
        }
      }

      // If repair failed, throw original error
      throw new Error('User not found. Please try signing out and back in, or contact support.');
    }

    const msg = await res.text();
    throw new Error(`Failed to get active workspace: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Get just the active workspace ID (convenience wrapper).
 * @returns {Promise<string>} The workspace UUID
 */
export async function getActiveWorkspaceId() {
  const data = await getActiveWorkspace();
  return data.workspace_id;
}

/**
 * Compatibility shim for pages still using the old currentUser pattern.
 * Returns an object matching the old auth.js currentUser() shape.
 *
 * @deprecated Use getActiveWorkspace() for new code
 * @returns {Promise<{workspace_id: string}>}
 */
export async function currentUser() {
  const data = await getActiveWorkspace();
  return {
    workspace_id: data.workspace_id,
    id: data.user_id,
    name: data.user_name,
    email: data.user_email
  };
}
