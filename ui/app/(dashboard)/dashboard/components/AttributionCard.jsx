'use client';

/**
 * AttributionCard component for Dashboard.
 *
 * WHAT: Displays revenue attribution breakdown by channel with pie chart
 * WHY: Users need to see which channels are driving their sales at a glance
 *
 * REFERENCES:
 * - docs/ATTRIBUTION_UX_COMPREHENSIVE_PLAN.md (Phase 2)
 * - backend/app/routers/attribution.py (attribution endpoints)
 */

import { useState, useEffect, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { TrendingUp, AlertTriangle, ExternalLink } from 'lucide-react';
import { fetchAttributionSummary } from '@/lib/api';

/**
 * Get provider display name and color.
 * @param {string} provider - Provider key (meta, google, direct, etc.)
 * @returns {Object} Display name and color
 */
function getProviderInfo(provider) {
    const providers = {
        meta: { name: 'Meta Ads', color: '#1877F2' },
        google: { name: 'Google Ads', color: '#4285F4' },
        tiktok: { name: 'TikTok Ads', color: '#000000' },
        direct: { name: 'Direct', color: '#10B981' },
        organic: { name: 'Organic', color: '#8B5CF6' },
        email: { name: 'Email', color: '#F59E0B' },
        referral: { name: 'Referral', color: '#EC4899' },
        unknown: { name: 'Unknown', color: '#9CA3AF' },
    };
    return providers[provider?.toLowerCase()] || { name: provider || 'Unknown', color: '#9CA3AF' };
}

/**
 * Format currency value.
 * @param {number} value - Dollar amount
 * @returns {string} Formatted currency string
 */
function formatCurrency(value) {
    if (value >= 1000000) {
        return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `$${(value / 1000).toFixed(1)}K`;
    }
    return `$${value.toFixed(0)}`;
}

/**
 * Custom tooltip for pie chart.
 */
function CustomTooltip({ active, payload }) {
    if (!active || !payload || !payload[0]) return null;

    const { name, value, payload: data } = payload[0];
    return (
        <div className="bg-white/95 backdrop-blur-sm border border-neutral-200 rounded-lg p-3 shadow-lg">
            <p className="font-medium text-neutral-900">{name}</p>
            <p className="text-sm text-neutral-600">
                {formatCurrency(value)} ({data.percentage?.toFixed(1)}%)
            </p>
            <p className="text-xs text-neutral-500 mt-1">
                {data.orders} orders
            </p>
        </div>
    );
}

/**
 * Get the timeframe days from timeframe string.
 * @param {string} timeframe - Timeframe like 'last_7_days'
 * @returns {number} Number of days
 */
function getTimeframeDays(timeframe) {
    const mapping = {
        'yesterday': 1,
        'last_7_days': 7,
        'last_14_days': 14,
        'last_30_days': 30,
        'last_90_days': 90,
        'this_month': 30,
        'this_quarter': 90,
    };
    return mapping[timeframe] || 7;
}

export default function AttributionCard({ workspaceId, timeframe = 'last_7_days' }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const days = useMemo(() => getTimeframeDays(timeframe), [timeframe]);

    useEffect(() => {
        if (!workspaceId) return;

        async function loadData() {
            try {
                setLoading(true);
                const result = await fetchAttributionSummary({ workspaceId, days });
                setData(result);
                setError(null);
            } catch (err) {
                console.error('Failed to load attribution:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [workspaceId, days]);

    // Prepare chart data
    const chartData = useMemo(() => {
        if (!data?.by_provider) return [];
        return data.by_provider.map(item => ({
            name: getProviderInfo(item.provider).name,
            value: item.revenue,
            percentage: item.percentage,
            orders: item.orders,
            fill: getProviderInfo(item.provider).color,
        }));
    }, [data]);

    // Loading state
    if (loading) {
        return (
            <div className="glass-panel rounded-2xl p-6 animate-pulse">
                <div className="h-6 w-48 bg-neutral-100 rounded mb-4"></div>
                <div className="h-48 bg-neutral-100 rounded-xl"></div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex items-center gap-2 text-amber-600">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="text-sm">Attribution data unavailable</span>
                </div>
            </div>
        );
    }

    // No data state
    if (!data || data.total_orders === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-cyan-500" />
                        Revenue Attribution
                    </h3>
                </div>
                <div className="text-center py-8 text-neutral-500">
                    <p className="text-sm">No attributed orders yet</p>
                    <p className="text-xs mt-1">Connect Shopify and set up UTM tracking to see attribution</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-2xl p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-slate-800 tracking-tight flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-cyan-500" />
                    Revenue Attribution
                </h3>
                <a
                    href="/analytics"
                    className="text-xs text-cyan-600 hover:text-cyan-700 flex items-center gap-1"
                >
                    View Details
                    <ExternalLink className="w-3 h-3" />
                </a>
            </div>

            {/* Main Content */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Pie Chart */}
                <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={chartData}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                innerRadius={45}
                                outerRadius={70}
                                paddingAngle={2}
                            >
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                ))}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Breakdown List */}
                <div className="space-y-3">
                    {data.by_provider.slice(0, 5).map((item) => {
                        const info = getProviderInfo(item.provider);
                        return (
                            <div key={item.provider} className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: info.color }}
                                    />
                                    <span className="text-sm text-neutral-700">{info.name}</span>
                                </div>
                                <div className="text-right">
                                    <span className="text-sm font-medium text-neutral-900">
                                        {formatCurrency(item.revenue)}
                                    </span>
                                    <span className="text-xs text-neutral-500 ml-2">
                                        {item.percentage.toFixed(0)}%
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Footer Stats */}
            <div className="mt-6 pt-4 border-t border-neutral-200 grid grid-cols-3 gap-4 text-center">
                <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wide">Total Attributed</p>
                    <p className="text-lg font-semibold text-neutral-900">
                        {formatCurrency(data.total_attributed_revenue)}
                    </p>
                </div>
                <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wide">Orders</p>
                    <p className="text-lg font-semibold text-neutral-900">
                        {data.total_orders.toLocaleString()}
                    </p>
                </div>
                <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wide">Attribution Rate</p>
                    <p className={`text-lg font-semibold ${data.attribution_rate >= 80 ? 'text-emerald-600' : data.attribution_rate >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                        {data.attribution_rate.toFixed(0)}%
                    </p>
                </div>
            </div>
        </div>
    );
}
