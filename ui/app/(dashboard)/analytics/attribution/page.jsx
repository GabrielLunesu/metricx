'use client';

/**
 * Attribution Page - Unified view of all attribution data.
 *
 * WHAT: Shows revenue attribution breakdown, top campaigns, live feed, and warnings
 * WHY: Users need a single place to understand which channels drive their sales
 *
 * LOCATION: /analytics/attribution (moved from /dashboard/attribution)
 * This page is now a sub-page of Analytics, accessible only when Shopify is connected.
 *
 * REFERENCES:
 * - docs/living-docs/ATTRIBUTION_ENGINE.md
 * - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 * - backend/app/routers/attribution.py
 */

import { useState, useEffect, useMemo } from 'react';
import { Target, TrendingUp, AlertTriangle, Activity, DollarSign, ShoppingCart, Percent, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { currentUser } from '@/lib/workspace';
import { fetchAttributionSummary, fetchAttributedCampaigns, fetchAttributionFeed, fetchCampaignWarnings } from '@/lib/api';

// Provider colors for consistent branding
const PROVIDER_COLORS = {
    meta: '#1877F2',
    google: '#4285F4',
    tiktok: '#000000',
    direct: '#10B981',
    organic: '#8B5CF6',
    email: '#F59E0B',
    referral: '#EC4899',
    unknown: '#9CA3AF',
};

const PROVIDER_NAMES = {
    meta: 'Meta Ads',
    google: 'Google Ads',
    tiktok: 'TikTok Ads',
    direct: 'Direct',
    organic: 'Organic',
    email: 'Email',
    referral: 'Referral',
    unknown: 'Unknown',
};

/**
 * Format currency value.
 */
function formatCurrency(value) {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
    return `$${value.toFixed(0)}`;
}

/**
 * Format relative time.
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
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
            <p className="text-xs text-neutral-500 mt-1">{data.orders} orders</p>
        </div>
    );
}

/**
 * KPI Card component.
 */
function KpiCard({ label, value, icon: Icon, trend, trendValue, color = 'cyan' }) {
    const isPositive = trend === 'up';
    return (
        <div className="glass-panel rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-lg bg-${color}-100`}>
                    <Icon className={`w-5 h-5 text-${color}-600`} />
                </div>
                {trendValue !== undefined && (
                    <div className={`flex items-center gap-1 text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                        {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {Math.abs(trendValue).toFixed(1)}%
                    </div>
                )}
            </div>
            <p className="text-2xl font-bold text-neutral-900">{value}</p>
            <p className="text-xs text-neutral-500 uppercase tracking-wide mt-1">{label}</p>
        </div>
    );
}

/**
 * Timeframe selector.
 */
const TIMEFRAMES = [
    { value: 7, label: '7 days' },
    { value: 14, label: '14 days' },
    { value: 30, label: '30 days' },
    { value: 90, label: '90 days' },
];

export default function AttributionPage() {
    const [user, setUser] = useState(null);
    const [days, setDays] = useState(7);
    const [loading, setLoading] = useState(true);
    const [summary, setSummary] = useState(null);
    const [campaigns, setCampaigns] = useState([]);
    const [feed, setFeed] = useState({ items: [], total_count: 0 });
    const [warnings, setWarnings] = useState([]);
    const [error, setError] = useState(null);

    // Load user on mount
    useEffect(() => {
        currentUser().then(setUser).catch(console.error);
    }, []);

    // Load all attribution data when user or timeframe changes
    useEffect(() => {
        if (!user?.workspace_id) return;

        async function loadData() {
            setLoading(true);
            setError(null);
            try {
                const [summaryData, campaignsData, feedData, warningsData] = await Promise.all([
                    fetchAttributionSummary({ workspaceId: user.workspace_id, days }),
                    fetchAttributedCampaigns({ workspaceId: user.workspace_id, days, limit: 10 }),
                    fetchAttributionFeed({ workspaceId: user.workspace_id, limit: 15 }),
                    fetchCampaignWarnings({ workspaceId: user.workspace_id, days }),
                ]);
                setSummary(summaryData);
                setCampaigns(campaignsData.campaigns || []);
                setFeed(feedData);
                setWarnings(warningsData.warnings || []);
            } catch (err) {
                console.error('Failed to load attribution data:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [user?.workspace_id, days]);

    // Prepare chart data
    const pieChartData = useMemo(() => {
        if (!summary?.by_provider) return [];
        return summary.by_provider.map(item => ({
            name: PROVIDER_NAMES[item.provider] || item.provider,
            value: item.revenue,
            percentage: item.percentage,
            orders: item.orders,
            fill: PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown,
        }));
    }, [summary]);

    const barChartData = useMemo(() => {
        return campaigns.slice(0, 5).map(c => ({
            name: c.campaign_name?.length > 20 ? c.campaign_name.substring(0, 20) + '...' : c.campaign_name,
            revenue: c.revenue,
            orders: c.orders,
        }));
    }, [campaigns]);

    if (loading && !summary) {
        return (
            <div className="p-6 md:p-8 animate-pulse">
                <div className="h-8 w-48 bg-neutral-100 rounded mb-6"></div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-28 bg-neutral-100 rounded-2xl"></div>
                    ))}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="h-80 bg-neutral-100 rounded-2xl"></div>
                    <div className="h-80 bg-neutral-100 rounded-2xl"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 md:p-8">
                <div className="glass-panel rounded-2xl p-8 text-center">
                    <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
                    <h2 className="text-lg font-semibold text-neutral-900 mb-2">Unable to load attribution data</h2>
                    <p className="text-neutral-600 mb-4">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    const hasData = summary && summary.total_orders > 0;

    return (
        <div className="p-6 md:p-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600">
                        <Target className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-neutral-900">Attribution</h1>
                        <p className="text-sm text-neutral-500">Track which channels drive your revenue</p>
                    </div>
                </div>

                {/* Timeframe Selector */}
                <div className="flex items-center gap-2">
                    {TIMEFRAMES.map(tf => (
                        <button
                            key={tf.value}
                            onClick={() => setDays(tf.value)}
                            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                                days === tf.value
                                    ? 'bg-cyan-600 text-white'
                                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                            }`}
                        >
                            {tf.label}
                        </button>
                    ))}
                </div>
            </div>

            {!hasData ? (
                /* Empty State */
                <div className="glass-panel rounded-2xl p-12 text-center">
                    <Target className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-neutral-900 mb-2">No attribution data yet</h2>
                    <p className="text-neutral-600 max-w-md mx-auto mb-6">
                        Connect your Shopify store and set up UTM tracking on your ad campaigns to start seeing attribution data.
                    </p>
                    <a
                        href="/settings?tab=connections"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
                    >
                        Go to Settings
                    </a>
                </div>
            ) : (
                <>
                    {/* KPI Strip */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <KpiCard
                            label="Attributed Revenue"
                            value={formatCurrency(summary.total_attributed_revenue)}
                            icon={DollarSign}
                            color="emerald"
                        />
                        <KpiCard
                            label="Orders"
                            value={summary.total_orders.toLocaleString()}
                            icon={ShoppingCart}
                            color="blue"
                        />
                        <KpiCard
                            label="Attribution Rate"
                            value={`${summary.attribution_rate.toFixed(0)}%`}
                            icon={Percent}
                            color={summary.attribution_rate >= 70 ? 'emerald' : summary.attribution_rate >= 50 ? 'amber' : 'red'}
                        />
                        <KpiCard
                            label="Avg Order Value"
                            value={formatCurrency(summary.total_attributed_revenue / summary.total_orders)}
                            icon={TrendingUp}
                            color="purple"
                        />
                    </div>

                    {/* Main Content Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                        {/* Revenue by Channel */}
                        <div className="glass-panel rounded-2xl p-6">
                            <h3 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
                                <TrendingUp className="w-5 h-5 text-cyan-500" />
                                Revenue by Channel
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="h-48">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={pieChartData}
                                                dataKey="value"
                                                nameKey="name"
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={40}
                                                outerRadius={70}
                                                paddingAngle={2}
                                            >
                                                {pieChartData.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                                ))}
                                            </Pie>
                                            <Tooltip content={<CustomTooltip />} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="space-y-2">
                                    {summary.by_provider.slice(0, 5).map(item => (
                                        <div key={item.provider} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className="w-3 h-3 rounded-full"
                                                    style={{ backgroundColor: PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown }}
                                                />
                                                <span className="text-sm text-neutral-700">
                                                    {PROVIDER_NAMES[item.provider] || item.provider}
                                                </span>
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
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Top Campaigns */}
                        <div className="glass-panel rounded-2xl p-6">
                            <h3 className="text-lg font-semibold text-neutral-900 mb-4">Top Campaigns</h3>
                            {barChartData.length > 0 ? (
                                <div className="h-48">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={barChartData} layout="vertical">
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" tickFormatter={formatCurrency} />
                                            <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                                            <Tooltip
                                                formatter={(value) => formatCurrency(value)}
                                                labelFormatter={(label) => label}
                                            />
                                            <Bar dataKey="revenue" fill="#06B6D4" radius={[0, 4, 4, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            ) : (
                                <div className="h-48 flex items-center justify-center text-neutral-500">
                                    No campaign data available
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bottom Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Live Attribution Feed */}
                        <div className="glass-panel rounded-2xl overflow-hidden">
                            <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Activity className="w-5 h-5 text-cyan-500" />
                                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-neutral-900">Live Feed</h3>
                                </div>
                                <span className="text-xs text-neutral-500">
                                    {feed.total_count.toLocaleString()} total
                                </span>
                            </div>
                            <div className="max-h-[300px] overflow-y-auto">
                                {feed.items.length === 0 ? (
                                    <div className="p-8 text-center text-neutral-500">
                                        <DollarSign className="w-10 h-10 mx-auto mb-2 text-neutral-300" />
                                        <p className="text-sm">No attributions yet</p>
                                    </div>
                                ) : (
                                    feed.items.map(item => (
                                        <div key={item.id} className="p-4 border-b border-neutral-100 last:border-b-0 hover:bg-neutral-50">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-semibold text-neutral-900">
                                                    {formatCurrency(item.revenue)}
                                                </span>
                                                <span className="text-xs text-neutral-500">
                                                    {formatRelativeTime(item.attributed_at)}
                                                </span>
                                            </div>
                                            <p className="text-sm text-neutral-600 truncate mb-1">
                                                {item.campaign_name || 'Unknown Campaign'}
                                            </p>
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className="px-2 py-0.5 text-xs font-medium rounded-full"
                                                    style={{
                                                        backgroundColor: `${PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown}20`,
                                                        color: PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown,
                                                    }}
                                                >
                                                    {PROVIDER_NAMES[item.provider] || item.provider}
                                                </span>
                                                <span className="text-xs text-neutral-500">via {item.match_type}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Campaign Warnings */}
                        <div className="glass-panel rounded-2xl overflow-hidden">
                            <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                                    <h3 className="text-lg font-semibold text-neutral-900">Attribution Warnings</h3>
                                </div>
                                {warnings.length > 0 && (
                                    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
                                        {warnings.length} issues
                                    </span>
                                )}
                            </div>
                            <div className="max-h-[300px] overflow-y-auto">
                                {warnings.length === 0 ? (
                                    <div className="p-8 text-center text-neutral-500">
                                        <AlertTriangle className="w-10 h-10 mx-auto mb-2 text-neutral-300" />
                                        <p className="text-sm">No warnings - all campaigns tracking properly</p>
                                    </div>
                                ) : (
                                    warnings.map((warning, idx) => (
                                        <div key={idx} className="p-4 border-b border-neutral-100 last:border-b-0">
                                            <div className="flex items-start gap-3">
                                                <div className="p-1.5 rounded-lg bg-amber-100">
                                                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium text-neutral-900 truncate">
                                                        {warning.campaign_name}
                                                    </p>
                                                    <p className="text-xs text-neutral-600 mt-0.5">
                                                        {warning.warning_type === 'no_attribution'
                                                            ? 'No attributed orders - check UTM tracking'
                                                            : warning.warning_type === 'low_confidence'
                                                            ? 'Low confidence attributions - review match types'
                                                            : warning.warning_type === 'no_utm'
                                                            ? 'Missing UTM parameters'
                                                            : warning.message || warning.warning_type}
                                                    </p>
                                                    <p className="text-xs text-neutral-500 mt-1">
                                                        {PROVIDER_NAMES[warning.provider] || warning.provider}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
