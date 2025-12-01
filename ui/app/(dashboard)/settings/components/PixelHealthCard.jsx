'use client';

/**
 * PixelHealthCard component for Settings page.
 *
 * WHAT: Displays Shopify Web Pixel health status, event statistics, and health score
 * WHY: Users need visibility into whether their attribution pixel is working
 *
 * REFERENCES:
 * - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md (Phase 1)
 * - backend/app/routers/attribution.py (pixel health endpoints)
 */

import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, RefreshCw, Eye, ShoppingCart, CreditCard, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { fetchPixelHealth, reinstallPixel } from '@/lib/api';

/**
 * Get status badge styling based on pixel status.
 * @param {string} status - Pixel status (active, degraded, inactive, not_installed)
 * @returns {Object} Tailwind classes and label
 */
function getStatusBadge(status) {
    switch (status) {
        case 'active':
            return {
                classes: 'bg-emerald-100 text-emerald-700',
                label: 'Active',
                icon: CheckCircle
            };
        case 'degraded':
            return {
                classes: 'bg-amber-100 text-amber-700',
                label: 'Degraded',
                icon: AlertTriangle
            };
        case 'inactive':
            return {
                classes: 'bg-red-100 text-red-700',
                label: 'Inactive',
                icon: XCircle
            };
        case 'not_installed':
            return {
                classes: 'bg-neutral-100 text-neutral-700',
                label: 'Not Installed',
                icon: XCircle
            };
        default:
            return {
                classes: 'bg-neutral-100 text-neutral-700',
                label: status || 'Unknown',
                icon: AlertTriangle
            };
    }
}

/**
 * Get health score color based on score value.
 * @param {number} score - Health score 0-100
 * @returns {string} Tailwind color class
 */
function getHealthScoreColor(score) {
    if (score >= 80) return 'text-emerald-600';
    if (score >= 60) return 'text-amber-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
}

/**
 * Get progress bar color based on score.
 * @param {number} score - Health score 0-100
 * @returns {string} Tailwind bg class
 */
function getProgressBarColor(score) {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-amber-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
}

/**
 * Format a timestamp for display.
 * @param {string} dateString - ISO timestamp
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
    if (!dateString) return 'Never';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;

        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return 'Invalid date';
    }
}

export default function PixelHealthCard({ workspaceId, hasShopifyConnection = false }) {
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [reinstalling, setReinstalling] = useState(false);
    const [error, setError] = useState(null);

    // Fetch pixel health on mount
    useEffect(() => {
        if (!workspaceId) return;

        async function loadHealth() {
            try {
                setLoading(true);
                const data = await fetchPixelHealth({ workspaceId });
                setHealth(data);
                setError(null);
            } catch (err) {
                console.error('Failed to load pixel health:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadHealth();
    }, [workspaceId]);

    // Handle pixel reinstall
    const handleReinstall = async () => {
        if (!confirm('This will delete your current pixel and create a new one. Continue?')) {
            return;
        }

        setReinstalling(true);
        try {
            const result = await reinstallPixel({ workspaceId });
            if (result.success) {
                toast.success('Pixel reinstalled successfully');
                // Refresh health data
                const data = await fetchPixelHealth({ workspaceId });
                setHealth(data);
            } else {
                toast.error(result.message || 'Failed to reinstall pixel');
            }
        } catch (err) {
            toast.error(err.message || 'Failed to reinstall pixel');
        } finally {
            setReinstalling(false);
        }
    };

    // Handle refresh
    const handleRefresh = async () => {
        if (!workspaceId) return;
        setLoading(true);
        try {
            const data = await fetchPixelHealth({ workspaceId });
            setHealth(data);
            setError(null);
            toast.success('Refreshed pixel health');
        } catch (err) {
            setError(err.message);
            toast.error('Failed to refresh');
        } finally {
            setLoading(false);
        }
    };

    // Loading state
    if (loading) {
        return (
            <div className="p-6 bg-white border border-neutral-200 rounded-xl animate-pulse">
                <div className="h-6 w-48 bg-neutral-100 rounded mb-4"></div>
                <div className="h-4 w-64 bg-neutral-100 rounded mb-2"></div>
                <div className="h-4 w-32 bg-neutral-100 rounded"></div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
                <div className="flex items-center gap-2 text-red-700">
                    <AlertTriangle className="w-5 h-5" />
                    <span>Failed to load pixel health: {error}</span>
                </div>
                <button
                    onClick={handleRefresh}
                    className="mt-2 text-sm text-red-600 hover:text-red-700"
                >
                    Try again
                </button>
            </div>
        );
    }

    // No Shopify connection
    if (!health || health.status === 'not_installed') {
        return (
            <div className="p-6 bg-white border border-neutral-200 rounded-xl">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-neutral-100 rounded-lg">
                        <Activity className="w-5 h-5 text-neutral-600" />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold text-neutral-900">Pixel Status</h3>
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-neutral-100 text-neutral-700">
                            Not Installed
                        </span>
                    </div>
                </div>
                <p className="text-sm text-neutral-600">
                    {health?.issues?.[0] || 'Connect your Shopify store to enable pixel tracking for attribution.'}
                </p>
            </div>
        );
    }

    const statusBadge = getStatusBadge(health.status);
    const StatusIcon = statusBadge.icon;

    return (
        <div className="p-6 bg-white border border-neutral-200 rounded-xl">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${health.status === 'active' ? 'bg-emerald-100' : health.status === 'degraded' ? 'bg-amber-100' : 'bg-red-100'}`}>
                        <Activity className={`w-5 h-5 ${health.status === 'active' ? 'text-emerald-600' : health.status === 'degraded' ? 'text-amber-600' : 'text-red-600'}`} />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold text-neutral-900">Pixel Status</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusBadge.classes}`}>
                            <StatusIcon className="w-3 h-3 inline mr-1" />
                            {statusBadge.label}
                        </span>
                    </div>
                </div>

                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="p-2 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {/* Pixel Info */}
            <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div>
                    <p className="text-neutral-500 text-xs uppercase tracking-wide">Pixel ID</p>
                    <p className="font-mono text-neutral-900 truncate" title={health.pixel_id}>
                        {health.pixel_id ? health.pixel_id.split('/').pop() : 'N/A'}
                    </p>
                </div>
                <div>
                    <p className="text-neutral-500 text-xs uppercase tracking-wide">Shop</p>
                    <p className="text-neutral-900 truncate">{health.shop_domain || 'N/A'}</p>
                </div>
                <div>
                    <p className="text-neutral-500 text-xs uppercase tracking-wide">Installed</p>
                    <p className="text-neutral-900">{formatDate(health.installed_at)}</p>
                </div>
                <div>
                    <p className="text-neutral-500 text-xs uppercase tracking-wide">Last Event</p>
                    <p className="text-neutral-900">{formatDate(health.last_event_at)}</p>
                </div>
            </div>

            {/* Health Score */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-neutral-700">Health Score</span>
                    <span className={`text-lg font-bold ${getHealthScoreColor(health.health_score)}`}>
                        {health.health_score}%
                    </span>
                </div>
                <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                        className={`h-full ${getProgressBarColor(health.health_score)} transition-all duration-500`}
                        style={{ width: `${health.health_score}%` }}
                    />
                </div>
            </div>

            {/* Event Counts */}
            <div className="mb-6">
                <h4 className="text-sm font-medium text-neutral-700 mb-3">Last 24 Hours</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 bg-neutral-50 rounded-lg">
                        <div className="flex items-center gap-2 text-neutral-600 mb-1">
                            <Eye className="w-4 h-4" />
                            <span className="text-xs">Page Views</span>
                        </div>
                        <p className="text-lg font-semibold text-neutral-900">
                            {(health.events_24h?.page_viewed || 0).toLocaleString()}
                        </p>
                    </div>
                    <div className="p-3 bg-neutral-50 rounded-lg">
                        <div className="flex items-center gap-2 text-neutral-600 mb-1">
                            <Eye className="w-4 h-4" />
                            <span className="text-xs">Products</span>
                        </div>
                        <p className="text-lg font-semibold text-neutral-900">
                            {(health.events_24h?.product_viewed || 0).toLocaleString()}
                        </p>
                    </div>
                    <div className="p-3 bg-neutral-50 rounded-lg">
                        <div className="flex items-center gap-2 text-neutral-600 mb-1">
                            <ShoppingCart className="w-4 h-4" />
                            <span className="text-xs">Add to Cart</span>
                        </div>
                        <p className="text-lg font-semibold text-neutral-900">
                            {(health.events_24h?.product_added_to_cart || 0).toLocaleString()}
                        </p>
                    </div>
                    <div className="p-3 bg-neutral-50 rounded-lg">
                        <div className="flex items-center gap-2 text-neutral-600 mb-1">
                            <CreditCard className="w-4 h-4" />
                            <span className="text-xs">Checkouts</span>
                        </div>
                        <p className="text-lg font-semibold text-neutral-900">
                            {(health.events_24h?.checkout_completed || 0).toLocaleString()}
                        </p>
                    </div>
                </div>
                <p className="text-xs text-neutral-500 mt-2">
                    {health.unique_visitors_24h?.toLocaleString() || 0} unique visitors
                </p>
            </div>

            {/* Issues */}
            {health.issues && health.issues.length > 0 && (
                <div className="mb-6">
                    <h4 className="text-sm font-medium text-amber-700 mb-2 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        Issues Detected
                    </h4>
                    <ul className="text-sm text-amber-600 space-y-1">
                        {health.issues.map((issue, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                                <span className="text-amber-400 mt-1">-</span>
                                {issue}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-neutral-200">
                <button
                    onClick={handleReinstall}
                    disabled={reinstalling}
                    className="px-4 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {reinstalling ? (
                        <>
                            <RefreshCw className="w-4 h-4 inline mr-2 animate-spin" />
                            Reinstalling...
                        </>
                    ) : (
                        'Reinstall Pixel'
                    )}
                </button>
            </div>
        </div>
    );
}
