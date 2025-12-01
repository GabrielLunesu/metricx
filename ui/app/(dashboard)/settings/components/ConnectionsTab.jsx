'use client';

import { useState, useEffect } from 'react';
import { Trash2, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { fetchConnections, deleteConnection, updateSyncFrequency } from '@/lib/api';
import MetaSyncButton from '@/components/MetaSyncButton';
import GoogleSyncButton from '@/components/GoogleSyncButton';
import GoogleConnectButton from '@/components/GoogleConnectButton';
import MetaConnectButton from '@/components/MetaConnectButton';
import ShopifyConnectButton from '@/components/ShopifyConnectButton';
import ShopifySyncButton from '@/components/ShopifySyncButton';
import PixelHealthCard from './PixelHealthCard';
import UTMSetupGuide from './UTMSetupGuide';

export default function ConnectionsTab({ user }) {
    const [connections, setConnections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deletingConnectionId, setDeletingConnectionId] = useState(null);
    const [frequencySavingId, setFrequencySavingId] = useState(null);

    const refreshConnectionsList = async (workspaceId, mounted = true) => {
        const connectionsData = await fetchConnections({ workspaceId });
        if (mounted) setConnections(connectionsData.connections || []);
    };

    useEffect(() => {
        let mounted = true;

        const loadData = async () => {
            try {
                if (user?.workspace_id) {
                    await refreshConnectionsList(user.workspace_id, mounted);
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || 'Failed to load connections');
                    console.error('Connections load error:', err);
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
    }, [user]);

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
            toast.success("Connection removed");
        } catch (err) {
            toast.error(err?.message || 'Failed to delete connection');
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
            toast.success("Sync frequency updated");
        } catch (err) {
            toast.error(err?.message || 'Failed to update sync frequency');
        } finally {
            setFrequencySavingId(null);
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
            shopify: 'Shopify',
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
            shopify: '🛍️',
            other: '🔗'
        };
        return icons[provider] || '📊';
    };

    if (loading) {
        return (
            <div className="animate-pulse space-y-4">
                <div className="h-32 bg-neutral-100 rounded-xl"></div>
                <div className="h-32 bg-neutral-100 rounded-xl"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
                Error: {error}
            </div>
        );
    }

    return (
        <div>
            {/* Connect New Account Section */}
            <div className="mb-8">
                <h2 className="text-lg font-semibold text-neutral-900 mb-4">Connect Accounts</h2>

                {/* Ad Platforms */}
                <h3 className="text-sm font-medium text-neutral-500 mb-3 uppercase tracking-wide">Ad Platforms</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
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

                {/* E-commerce Platforms */}
                <h3 className="text-sm font-medium text-neutral-500 mb-3 uppercase tracking-wide">E-commerce</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Shopify */}
                    <div className="p-6 bg-white border border-neutral-200 rounded-xl">
                        <h3 className="text-base font-semibold text-neutral-900 mb-2">Shopify</h3>
                        <p className="text-sm text-neutral-600 mb-4">
                            Connect your Shopify store to sync orders, products, and customers for revenue and LTV tracking.
                        </p>
                        <ShopifyConnectButton onConnectionComplete={handleSyncComplete} />
                    </div>
                </div>
            </div>

            {/* Connected Accounts Section */}
            <div className="mb-8">
                <h2 className="text-lg font-semibold text-neutral-900 mb-4">Connected Accounts</h2>

                {connections.length === 0 ? (
                    <div className="p-8 bg-neutral-50 border border-neutral-200 rounded-xl text-center text-neutral-600">
                        <p className="mb-2">No accounts connected yet.</p>
                        <p className="text-sm">Use the "Connect Accounts" section above to get started.</p>
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
                                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${connection.status === 'active'
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
                                                    Choose how often metricx automatically syncs this account.
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
                                            ) : connection.provider === 'shopify' ? (
                                                <ShopifySyncButton
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

            {/* Pixel Health Section - Show if Shopify connection exists */}
            {connections.some(c => c.provider === 'shopify') && (
                <div className="mb-8">
                    <h2 className="text-lg font-semibold text-neutral-900 mb-4">Attribution Pixel</h2>
                    <PixelHealthCard
                        workspaceId={user?.workspace_id}
                        hasShopifyConnection={connections.some(c => c.provider === 'shopify' && c.status === 'active')}
                    />
                </div>
            )}

            {/* UTM Setup Guide - Show if any ad platform connection exists */}
            {connections.some(c => ['meta', 'google', 'tiktok'].includes(c.provider)) && (
                <div className="mb-8">
                    <h2 className="text-lg font-semibold text-neutral-900 mb-4">Attribution Setup</h2>
                    <UTMSetupGuide />
                </div>
            )}

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
        </div>
    );
}
