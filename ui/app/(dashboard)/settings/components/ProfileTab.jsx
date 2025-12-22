'use client';

/**
 * ProfileTab - Hybrid Clerk + Custom profile management
 *
 * WHAT: Provides user profile management combining Clerk's UserProfile component
 * with a custom account deletion section.
 *
 * WHY: Clerk handles auth-related profile changes (name, email, password, 2FA)
 * while our custom delete section ensures all workspace data is properly cleaned up.
 *
 * REFERENCES:
 * - backend/app/routers/clerk_webhooks.py (syncs Clerk changes to local DB)
 * - backend/app/routers/auth.py (delete-account endpoint with full data cleanup)
 */

import { useState } from 'react';
import { UserProfile, useClerk } from '@clerk/nextjs';
import { AlertTriangle, Trash2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { deleteUserAccount } from '@/lib/api';

export default function ProfileTab() {
  const { user } = useClerk();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  /**
   * Handle account deletion with proper data cleanup.
   *
   * WHAT: Deletes user account and all associated workspace data.
   * WHY: GDPR/CCPA compliance requires complete data removal.
   *
   * Flow:
   * 1. Call our /auth/delete-account endpoint to clean up local data
   *    (query logs, credentials, entities, connections, etc.)
   * 2. Delete Clerk user via SDK (also triggers webhook as backup)
   * 3. Redirect to home page
   */
  const handleDeleteAccount = async () => {
    if (!showDeleteConfirm) return;

    setDeleteLoading(true);
    try {
      // Step 1: Delete all local data via our endpoint
      // This cleans up: QaQueryLog, AuthCredential, ManualCost, MetricFact,
      // Entity, Connection, Token, WorkspaceMember, User, and Workspace (if sole member)
      await deleteUserAccount();

      // Step 2: Delete Clerk user (this also triggers user.deleted webhook as backup)
      await user.delete();

      toast.success('Account deleted successfully');
      window.location.href = '/';
    } catch (err) {
      toast.error(err?.message || 'Failed to delete account');
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Clerk UserProfile for profile/password management */}
      <UserProfile
        appearance={{
          elements: {
            rootBox: 'w-full',
            card: 'shadow-none border border-neutral-200 rounded-xl',
            navbar: 'hidden',
            pageScrollBox: 'p-0',
          }
        }}
        routing="hash"
      />

      {/* Custom Delete Account Section */}
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-2">
              Delete Account & Data
            </h3>
            <p className="text-sm text-red-800 mb-4">
              Permanently delete your account and all associated data. This action
              cannot be undone. All connections, campaigns, and analytics data will
              be permanently removed.
            </p>

            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 bg-white border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete My Account
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-red-900">
                  Are you absolutely sure? This cannot be undone.
                </p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleteLoading}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {deleteLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Yes, Delete Everything
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={deleteLoading}
                    className="px-4 py-2 bg-white border border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
