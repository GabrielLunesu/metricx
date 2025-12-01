'use client';

/**
 * LiveAttributionFeed component for Dashboard.
 *
 * WHAT: Real-time feed showing recent attributions as they happen
 * WHY: Creates WOW factor - users see their sales being attributed in real-time
 *
 * REFERENCES:
 * - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md (Live Feed section)
 * - backend/app/routers/attribution.py (feed endpoint)
 */

import { useState, useEffect, useCallback } from 'react';
import { Activity, RefreshCw, DollarSign, ChevronRight } from 'lucide-react';
import { fetchAttributionFeed } from '@/lib/api';

/**
 * Get provider styling
 */
function getProviderStyle(provider) {
    const styles = {
        meta: { bg: 'bg-blue-100', text: 'text-blue-700', icon: '📘' },
        google: { bg: 'bg-red-100', text: 'text-red-700', icon: '🔍' },
        tiktok: { bg: 'bg-neutral-900', text: 'text-white', icon: '🎵' },
        direct: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: '🎯' },
        organic: { bg: 'bg-purple-100', text: 'text-purple-700', icon: '🌱' },
        unknown: { bg: 'bg-neutral-100', text: 'text-neutral-700', icon: '❓' },
    };
    return styles[provider?.toLowerCase()] || styles.unknown;
}

/**
 * Get confidence badge styling
 */
function getConfidenceBadge(confidence) {
    const badges = {
        high: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'High' },
        medium: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Medium' },
        low: { bg: 'bg-red-100', text: 'text-red-700', label: 'Low' },
    };
    return badges[confidence?.toLowerCase()] || badges.low;
}

/**
 * Format currency with symbol
 */
function formatCurrency(value, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(value);
}

/**
 * Format relative time
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

/**
 * Single feed item
 */
function FeedItem({ item, isNew }) {
    const providerStyle = getProviderStyle(item.provider);
    const confidenceBadge = getConfidenceBadge(item.confidence);

    return (
        <div
            className={`p-4 border-b border-neutral-100 last:border-b-0 transition-all duration-500 ${
                isNew ? 'bg-cyan-50 animate-pulse' : 'bg-white hover:bg-neutral-50'
            }`}
        >
            <div className="flex items-start gap-3">
                {/* Icon */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-full ${providerStyle.bg} flex items-center justify-center text-lg`}>
                    {providerStyle.icon}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-neutral-900">
                            {formatCurrency(item.revenue, item.currency)}
                        </span>
                        <span className="text-xs text-neutral-500">
                            {formatRelativeTime(item.attributed_at)}
                        </span>
                    </div>

                    <p className="text-sm text-neutral-600 truncate mb-2">
                        {item.campaign_name || 'Unknown Campaign'}
                    </p>

                    <div className="flex items-center gap-2 flex-wrap">
                        {/* Provider badge */}
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${providerStyle.bg} ${providerStyle.text}`}>
                            {item.provider?.charAt(0).toUpperCase() + item.provider?.slice(1) || 'Unknown'}
                        </span>

                        {/* Match type */}
                        <span className="text-xs text-neutral-500">
                            via {item.match_type}
                        </span>

                        {/* Confidence */}
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${confidenceBadge.bg} ${confidenceBadge.text}`}>
                            {confidenceBadge.label}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LiveAttributionFeed({ workspaceId }) {
    const [feed, setFeed] = useState({ items: [], total_count: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newItemIds, setNewItemIds] = useState(new Set());
    const [autoRefresh, setAutoRefresh] = useState(true);

    // Fetch feed data
    const loadFeed = useCallback(async (showLoading = true) => {
        if (!workspaceId) return;

        try {
            if (showLoading) setLoading(true);
            const data = await fetchAttributionFeed({ workspaceId, limit: 15 });

            // Track new items for animation
            if (feed.items.length > 0) {
                const existingIds = new Set(feed.items.map(i => i.id));
                const newIds = new Set(data.items.filter(i => !existingIds.has(i.id)).map(i => i.id));
                if (newIds.size > 0) {
                    setNewItemIds(newIds);
                    setTimeout(() => setNewItemIds(new Set()), 3000);
                }
            }

            setFeed(data);
            setError(null);
        } catch (err) {
            console.error('Failed to load attribution feed:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [workspaceId, feed.items]);

    // Initial load
    useEffect(() => {
        loadFeed();
    }, [workspaceId]);

    // Auto-refresh every 30 seconds
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            loadFeed(false); // Silent refresh
        }, 30000);

        return () => clearInterval(interval);
    }, [autoRefresh, loadFeed]);

    // Manual refresh
    const handleRefresh = () => {
        loadFeed(true);
    };

    // Loading state
    if (loading && feed.items.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6 animate-pulse">
                <div className="h-6 w-48 bg-neutral-100 rounded mb-4"></div>
                <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-20 bg-neutral-100 rounded"></div>
                    ))}
                </div>
            </div>
        );
    }

    // Error state
    if (error && feed.items.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <div className="text-center text-neutral-500">
                    <p className="text-sm">Unable to load attribution feed</p>
                    <button
                        onClick={handleRefresh}
                        className="mt-2 text-cyan-600 hover:text-cyan-700 text-sm"
                    >
                        Try again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Activity className="w-5 h-5 text-cyan-500" />
                        {autoRefresh && (
                            <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                        )}
                    </div>
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight">
                        Live Attribution Feed
                    </h3>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setAutoRefresh(!autoRefresh)}
                        className={`text-xs px-2 py-1 rounded ${
                            autoRefresh
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-neutral-100 text-neutral-600'
                        }`}
                    >
                        {autoRefresh ? 'Live' : 'Paused'}
                    </button>
                    <button
                        onClick={handleRefresh}
                        disabled={loading}
                        className="p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Feed Items */}
            <div className="max-h-[400px] overflow-y-auto">
                {feed.items.length === 0 ? (
                    <div className="p-8 text-center text-neutral-500">
                        <DollarSign className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
                        <p className="text-sm">No attributions yet</p>
                        <p className="text-xs mt-1">Attributions will appear here as orders come in</p>
                    </div>
                ) : (
                    feed.items.map((item) => (
                        <FeedItem
                            key={item.id}
                            item={item}
                            isNew={newItemIds.has(item.id)}
                        />
                    ))
                )}
            </div>

            {/* Footer */}
            {feed.total_count > 0 && (
                <div className="p-3 border-t border-neutral-200 bg-neutral-50 flex items-center justify-between">
                    <span className="text-xs text-neutral-500">
                        {feed.total_count.toLocaleString()} total attributions
                    </span>
                    <a
                        href="/analytics"
                        className="text-xs text-cyan-600 hover:text-cyan-700 flex items-center gap-1"
                    >
                        View All
                        <ChevronRight className="w-3 h-3" />
                    </a>
                </div>
            )}
        </div>
    );
}
