/**
 * Admin API Client - Functions for admin dashboard operations.
 *
 * WHAT: API client for admin endpoints (user/workspace management)
 * WHY: Centralized admin API calls for the admin dashboard
 *
 * SECURITY: All endpoints require superuser access (checked by backend)
 */

import { authFetch } from './api';
import { getApiBase } from './config';

const BASE = getApiBase();

/**
 * Check if current user has admin access.
 *
 * @returns {Promise<{is_superuser: boolean, user_id: string, email: string}>}
 */
export async function getAdminStatus() {
  const res = await authFetch(`${BASE}/admin/me`);
  if (!res.ok) {
    if (res.status === 403) {
      return { is_superuser: false, user_id: null, email: null };
    }
    throw new Error('Failed to fetch admin status');
  }
  return res.json();
}

/**
 * Get all users with their workspace memberships.
 *
 * @param {Object} options - Query options
 * @param {number} [options.skip=0] - Number of users to skip
 * @param {number} [options.limit=100] - Max users to return
 * @param {string} [options.search] - Search by email or name
 * @returns {Promise<{users: Array, total: number}>}
 */
export async function getUsers({ skip = 0, limit = 100, search = '' } = {}) {
  const params = new URLSearchParams();
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  if (search) params.set('search', search);

  const res = await authFetch(`${BASE}/admin/users?${params.toString()}`);
  if (!res.ok) {
    throw new Error('Failed to fetch users');
  }
  return res.json();
}

/**
 * Delete a user (from DB and Clerk).
 *
 * WARNING: This is irreversible! User will be removed from Clerk and all
 * their owned workspaces will be deleted.
 *
 * @param {string} userId - User UUID to delete
 * @returns {Promise<{success: boolean, user_id: string, clerk_deleted: boolean, workspaces_deleted: number, message: string}>}
 */
export async function deleteUser(userId) {
  const res = await authFetch(`${BASE}/admin/users/${userId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to delete user' }));
    throw new Error(error.detail || 'Failed to delete user');
  }
  return res.json();
}

/**
 * Toggle superuser status for a user.
 *
 * @param {string} userId - User UUID
 * @param {boolean} isSuperuser - New superuser status
 * @returns {Promise<Object>} - Updated user object
 */
export async function toggleSuperuser(userId, isSuperuser) {
  const res = await authFetch(`${BASE}/admin/users/${userId}/superuser`, {
    method: 'PATCH',
    body: JSON.stringify({ is_superuser: isSuperuser }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to update superuser status' }));
    throw new Error(error.detail || 'Failed to update superuser status');
  }
  return res.json();
}

/**
 * Get all workspaces with billing info.
 *
 * @param {Object} options - Query options
 * @param {number} [options.skip=0] - Number of workspaces to skip
 * @param {number} [options.limit=100] - Max workspaces to return
 * @param {string} [options.search] - Search by workspace name
 * @returns {Promise<{workspaces: Array, total: number}>}
 */
export async function getWorkspaces({ skip = 0, limit = 100, search = '' } = {}) {
  const params = new URLSearchParams();
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  if (search) params.set('search', search);

  const res = await authFetch(`${BASE}/admin/workspaces?${params.toString()}`);
  if (!res.ok) {
    throw new Error('Failed to fetch workspaces');
  }
  return res.json();
}

/**
 * Update workspace billing tier.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} billingTier - New tier: 'free' or 'starter'
 * @returns {Promise<Object>} - Updated workspace object
 */
export async function updateBillingTier(workspaceId, billingTier) {
  const res = await authFetch(`${BASE}/admin/workspaces/${workspaceId}/billing`, {
    method: 'PATCH',
    body: JSON.stringify({ billing_tier: billingTier }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to update billing tier' }));
    throw new Error(error.detail || 'Failed to update billing tier');
  }
  return res.json();
}
