'use client'

import { useEffect, useState } from 'react';
import { Settings, RefreshCw, ExternalLink, Calendar, Trash2, AlertTriangle } from 'lucide-react';
import { currentUser } from '@/lib/auth';
import { fetchConnections, ensureGoogleConnectionFromEnv, ensureMetaConnectionFromEnv, deleteUserAccount, deleteConnection, updateSyncFrequency } from '@/lib/api';
import MetaSyncButton from '@/components/MetaSyncButton';
import GoogleSyncButton from '@/components/GoogleSyncButton';
import GoogleConnectButton from '@/components/GoogleConnectButton';
import MetaConnectButton from '@/components/MetaConnectButton';

/**
 * Settings Page
 * 
 * WHAT: Display and manage connected ad platform accounts
 * WHY: Users need to see their connections and trigger syncs
 * WHERE USED: /settings route
 * 
 * Features:
 * - List all connected ad accounts (Meta, Google, TikTok, etc.)
 * - Sync button for each Meta connection
 * - Connection status and metadata display
 * - Last sync timestamp
 */
export default function SettingsPage() {
  const [user, setUser] = useState(null);
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deletingConnectionId, setDeletingConnectionId] = useState(null);
  const [frequencySavingId, setFrequencySavingId] = useState(null);

  const refreshConnectionsList = async (workspaceId, mounted = true) => {
    let connectionsData = await fetchConnections({ workspaceId });

    const hasGoogle = (connectionsData.connections || []).some(c => c.provider === 'google');
    if (!hasGoogle) {
      await ensureGoogleConnectionFromEnv();
      connectionsData = await fetchConnections({ workspaceId });
    }

    const hasMeta = (connectionsData.connections || []).some(c => c.provider === 'meta');
    if (!hasMeta) {
      await ensureMetaConnectionFromEnv();
      connectionsData = await fetchConnections({ workspaceId });
    }

    if (mounted) setConnections(connectionsData.connections || []);
  };

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        const currentUserData = await currentUser();
        if (!mounted) return;

        setUser(currentUserData);

        if (currentUserData?.workspace_id) {
          await refreshConnectionsList(currentUserData.workspace_id, mounted);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || 'Failed to load settings');
          console.error('Settings load error:', err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSyncComplete = () => {
    if (user?.workspace_id) {
      refreshConnectionsList(user.workspace_id).catch((err) =>
        console.error('Failed to refresh connections:', err)
      );
    }
  };

  const handleDeleteConnection = async (connectionId) => {
    if (!confirm('Are you sure you want to disconnect this ad account? This will remove all synced data for this connection.')) {
      return;
    }
    
    setDeletingConnectionId(connectionId);
    try {
      await deleteConnection(connectionId);
      // Refresh connections list
      if (user?.workspace_id) {
        const data = await fetchConnections({ workspaceId: user.workspace_id });
        setConnections(data.connections || []);
      }
    } catch (err) {
      alert('Failed to delete connection: ' + (err.message || 'Unknown error'));
    } finally {
      setDeletingConnectionId(null);
    }
  };

  const handleFrequencyChange = async (connectionId, value) => {
    if (!user?.workspace_id) return;
    setFrequencySavingId(connectionId);
    try {
      await updateSyncFrequency({ connectionId, syncFrequency: value });
      await refreshConnectionsList(user.workspace_id);
    } catch (err) {
      alert('Failed to update frequency: ' + (err.message || 'Unknown error'));
    } finally {
      setFrequencySavingId(null);
    }
  };

  const handleDeleteAccount = async () => {
    if (!showDeleteConfirm) return;
    
    setDeleteLoading(true);
    try {
      await deleteUserAccount();
      // Redirect to home after successful deletion
      window.location.href = '/';
    } catch (err) {
      alert('Failed to delete account: ' + (err.message || 'Unknown error'));
      setDeleteLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Invalid date';
    }
  };

  const getProviderLabel = (provider) => {
    const labels = {
      meta: 'Meta Ads',
      google: 'Google Ads',
      tiktok: 'TikTok Ads',
      other: 'Other'
    };
    return labels[provider] || provider;
  };

  const formatAccountId = (provider, externalId) => {
    if (!externalId) return '';
    if (provider === 'google') {
      // Hyphenate Google customer ID as ###-###-####
      const digits = String(externalId).replace(/\D/g, '');
      const m = digits.match(/(\d{3})(\d{3})(\d{4})/);
      if (m) return `${m[1]}-${m[2]}-${m[3]}`;
      return digits;
    }
    return externalId;
  };

  const getProviderIcon = (provider) => {
    // Simple emoji-based icons for now
    const icons = {
      meta: '📘',
      google: '🔍',
      tiktok: '🎵',
      other: '🔗'
    };
    return icons[provider] || '📊';
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8">
          <Settings className="w-6 h-6 text-neutral-600" />
          <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-neutral-100 rounded-xl"></div>
          <div className="h-32 bg-neutral-100 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8">
          <Settings className="w-6 h-6 text-neutral-600" />
          <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-6 h-6 text-neutral-600" />
        <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
      </div>

      {/* Connect New Account Section */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">Connect Ad Accounts</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Google Ads */}
          <div className="p-6 bg-white border border-neutral-200 rounded-xl">
            <h3 className="text-base font-semibold text-neutral-900 mb-2">Google Ads</h3>
            <p className="text-sm text-neutral-600 mb-4">
              Connect your Google Ads account to sync campaigns, performance data, and analytics.
            </p>
            <GoogleConnectButton onConnectionComplete={handleSyncComplete} />
          </div>
          
          {/* Meta Ads */}
          <div className="p-6 bg-white border border-neutral-200 rounded-xl">
            <h3 className="text-base font-semibold text-neutral-900 mb-2">Meta Ads</h3>
            <p className="text-sm text-neutral-600 mb-4">
              Connect your Meta (Facebook/Instagram) ad accounts to sync campaigns, performance data, and analytics.
            </p>
            <MetaConnectButton 
              onConnectionComplete={handleSyncComplete}
              existingConnections={connections}
            />
          </div>
        </div>
      </div>

      {/* Connected Accounts Section */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">Connected Ad Accounts</h2>
        
        {connections.length === 0 ? (
          <div className="p-8 bg-neutral-50 border border-neutral-200 rounded-xl text-center text-neutral-600">
            <p className="mb-2">No ad accounts connected yet.</p>
            <p className="text-sm">Use the "Connect Ad Accounts" section above to get started.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((connection) => (
              <div
                key={connection.id}
                className="p-6 bg-white border border-neutral-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-3xl">{getProviderIcon(connection.provider)}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-semibold text-neutral-900">
                          {connection.name || getProviderLabel(connection.provider)}
                        </h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          connection.status === 'active'
                            ? 'bg-emerald-100 text-emerald-700'
                            : connection.status === 'inactive'
                            ? 'bg-neutral-100 text-neutral-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {connection.status || 'unknown'}
                        </span>
                      </div>
                      <p className="text-sm text-neutral-600 mb-2">
                        {getProviderLabel(connection.provider)}
                        {connection.external_account_id && (
                          <span className="ml-2 font-mono text-xs">
                            ({formatAccountId(connection.provider, connection.external_account_id)})
                          </span>
                        )}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-neutral-500">
                        <div className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          <span>Connected: {formatDate(connection.connected_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Delete Connection Button */}
                  <button
                    onClick={() => handleDeleteConnection(connection.id)}
                    disabled={deletingConnectionId === connection.id}
                    className="p-2 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Disconnect account"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>

                {connection.status === 'active' && (
                  <div className="mt-4 pt-4 border-t border-neutral-200 space-y-4">
                    <div className="flex flex-col md:flex-row md:items-center gap-4">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-neutral-900">Sync Frequency</p>
                        <p className="text-xs text-neutral-500">
                          Choose how often AdNavi automatically syncs this account.
                        </p>
                      </div>
                      <select
                        value={connection.sync_frequency || 'manual'}
                        disabled={frequencySavingId === connection.id}
                        onChange={(e) => handleFrequencyChange(connection.id, e.target.value)}
                        className="px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-200"
                      >
                        <option value="manual">Manual</option>
                        <option value="5min">Every 5 min</option>
                        <option value="10min">Every 10 min</option>
                        <option value="30min">Every 30 min</option>
                        <option value="hourly">Hourly</option>
                        <option value="daily">Daily</option>
                        {/* Realtime (~30s) sync remains in code but requires special access (see docs/REALTIME_SYNC_IMPLEMENTATION_SUMMARY.md) */}
                        {/* <option value="realtime">Realtime (~30s)</option> */}
                      </select>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-neutral-600">
                      <div>
                        <p className="text-neutral-500 uppercase tracking-wide text-[10px]">Status</p>
                        <p className="font-medium text-neutral-900">{connection.sync_status || 'idle'}</p>
                      </div>
                      <div>
                        <p className="text-neutral-500 uppercase tracking-wide text-[10px]">Last Attempt</p>
                        <p className="font-medium">{formatDate(connection.last_sync_attempted_at)}</p>
                      </div>
                      <div>
                        <p className="text-neutral-500 uppercase tracking-wide text-[10px]">Last Change</p>
                        <p className="font-medium">{formatDate(connection.last_metrics_changed_at)}</p>
                      </div>
                    </div>

                    {connection.last_sync_error && (
                      <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
                        Last error: {connection.last_sync_error}
                      </div>
                    )}

                    <div className="flex flex-col md:flex-row md:items-center gap-4">
                      <div className="text-xs text-neutral-500 flex-1">
                        Attempts: {connection.total_syncs_attempted} · With Changes: {connection.total_syncs_with_changes}
                      </div>
                      {connection.provider === 'meta' ? (
                        <MetaSyncButton
                          workspaceId={user.workspace_id}
                          connectionId={connection.id}
                          onSyncComplete={handleSyncComplete}
                        />
                      ) : (
                        <GoogleSyncButton
                          workspaceId={user.workspace_id}
                          connectionId={connection.id}
                          onSyncComplete={handleSyncComplete}
                        />
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Section */}
      <div className="mb-8 p-6 bg-neutral-50 border border-neutral-200 rounded-xl">
        <h3 className="text-sm font-semibold text-neutral-900 mb-2">About Syncing</h3>
        <p className="text-sm text-neutral-600 mb-2">
          Syncing fetches the latest campaigns, ad sets, and ads from your ad accounts,
          along with performance metrics for the last 90 days.
        </p>
        <p className="text-sm text-neutral-600">
          The sync process may take a few minutes depending on the size of your account.
          Large accounts with many campaigns may take longer.
        </p>
      </div>

      {/* Delete Account Section */}
      <div className="mb-8 p-6 bg-red-50 border border-red-200 rounded-xl">
        <div className="flex items-start gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-2">Delete Account & Data</h3>
            <p className="text-sm text-red-800 mb-4">
              Permanently delete your account and all associated data. This action cannot be undone.
              All connections, campaigns, and analytics data will be permanently removed.
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
                    className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
                    className="px-4 py-2 bg-white border border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors disabled:opacity-50"
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
