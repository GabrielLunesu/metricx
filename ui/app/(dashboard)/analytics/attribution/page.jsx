'use client';

/**
 * Attribution Page - Sub-page of Analytics.
 *
 * WHAT: Shows pixel health, attribution KPIs, revenue breakdown, live feed,
 *       campaign warnings, and a setup checklist.
 * WHY: Users need a single place to understand whether their attribution pipeline
 *       is working correctly and which channels drive their sales.
 *
 * BRANDING: Matches the analytics page design system — white panels with neutral
 *           borders, no gradients, clean neutral typography.
 *
 * LOCATION: /analytics/attribution (accessible via Attribution button in AnalyticsHeader)
 *
 * REFERENCES:
 * - backend/app/routers/attribution.py (data endpoints)
 * - backend/app/services/attribution_service.py (attribution pipeline)
 * - ui/app/(dashboard)/analytics/components/AnalyticsHeader.jsx (parent page header)
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
    Target, TrendingUp, AlertTriangle, Activity, DollarSign,
    ShoppingCart, Percent, ArrowUpRight, ArrowDownRight, ArrowLeft,
    CheckCircle, XCircle, Eye, CreditCard,
    HelpCircle, Radio, Minus
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Button } from '@/components/ui/button';
import { currentUser } from '@/lib/workspace';
import {
    fetchAttributionSummary, fetchAttributedCampaigns,
    fetchAttributionFeed, fetchCampaignWarnings,
    fetchPixelHealth, fetchConnections
} from '@/lib/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

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

const TIMEFRAMES = [
    { value: 7, label: '7d' },
    { value: 14, label: '14d' },
    { value: 30, label: '30d' },
    { value: 90, label: '90d' },
];

/** Live feed auto-refresh interval (ms). */
const FEED_REFRESH_INTERVAL = 30_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a numeric value as compact USD currency.
 * @param {number} value - Dollar amount
 * @returns {string} e.g. "$1.2K"
 */
function formatCurrency(value) {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
    return `$${value.toFixed(0)}`;
}

/**
 * Format an ISO date string as a relative time label.
 * @param {string} dateString - ISO 8601 timestamp
 * @returns {string} e.g. "5m ago"
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * Custom Recharts tooltip for the revenue pie chart.
 */
function CustomTooltip({ active, payload }) {
    if (!active || !payload || !payload[0]) return null;
    const { name, value, payload: data } = payload[0];
    return (
        <div className="bg-white border border-neutral-200 rounded-lg p-3 shadow-lg">
            <p className="font-medium text-neutral-900">{name}</p>
            <p className="text-sm text-neutral-600">
                {formatCurrency(value)} ({data.percentage?.toFixed(1)}%)
            </p>
            <p className="text-xs text-neutral-500 mt-1">{data.orders} orders</p>
        </div>
    );
}

/**
 * KPI card — matches analytics page `analytics-kpi-card` pattern.
 */
function KpiCard({ label, value }) {
    return (
        <div className="analytics-kpi-card">
            <div className="text-[11px] font-medium text-neutral-500 uppercase tracking-wider mb-1">
                {label}
            </div>
            <div className="text-lg md:text-xl font-semibold text-neutral-900 tracking-tight tabular-nums">
                {value}
            </div>
        </div>
    );
}

/**
 * Pixel Health section — compact read-only summary.
 *
 * WHY: Users need to see at a glance whether events are flowing into the pixel pipeline.
 */
function PixelHealthSection({ pixelHealth, loading }) {
    if (loading) {
        return (
            <div className="bg-white border border-neutral-200 rounded-xl p-4 animate-pulse">
                <div className="h-4 w-40 bg-neutral-100 rounded mb-3" />
                <div className="h-4 w-64 bg-neutral-100 rounded" />
            </div>
        );
    }

    if (!pixelHealth) {
        return (
            <div className="bg-white border border-neutral-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                    <Radio className="w-4 h-4 text-neutral-400" />
                    <span className="text-sm font-medium text-neutral-900">Pixel Status</span>
                    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-neutral-100 text-neutral-500">
                        Unknown
                    </span>
                </div>
                <p className="text-xs text-neutral-500 mt-2">Unable to load pixel health data.</p>
            </div>
        );
    }

    const isActive = pixelHealth.status === 'active';
    const isDegraded = pixelHealth.status === 'degraded';
    const isNotInstalled = pixelHealth.status === 'not_installed';

    const statusLabel = isActive ? 'Active' : isDegraded ? 'Degraded' : isNotInstalled ? 'Not Installed' : 'Inactive';
    const statusClasses = isActive
        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
        : isDegraded
        ? 'bg-amber-50 text-amber-700 border border-amber-200'
        : 'bg-red-50 text-red-700 border border-red-200';

    const events = pixelHealth.events_24h || {};

    return (
        <div className="bg-white border border-neutral-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <Radio className={`w-4 h-4 ${isActive ? 'text-emerald-500' : isDegraded ? 'text-amber-500' : 'text-red-500'}`} />
                    <span className="text-sm font-medium text-neutral-900">Shopify Pixel</span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-md ${statusClasses}`}>
                        {statusLabel}
                    </span>
                </div>
                {pixelHealth.health_score !== undefined && (
                    <span className={`text-sm font-semibold tabular-nums ${
                        pixelHealth.health_score >= 80 ? 'text-emerald-600' :
                        pixelHealth.health_score >= 60 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                        {pixelHealth.health_score}%
                    </span>
                )}
            </div>

            {!isNotInstalled && (
                <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
                    <span>{(events.page_viewed || 0).toLocaleString()} page views</span>
                    <span>{(events.product_added_to_cart || 0).toLocaleString()} add to carts</span>
                    <span>{(events.checkout_completed || 0).toLocaleString()} checkouts</span>
                    <span className="text-neutral-400">last 24h</span>
                </div>
            )}

            {pixelHealth.issues && pixelHealth.issues.length > 0 && (
                <div className="mt-2 space-y-1">
                    {pixelHealth.issues.map((issue, idx) => (
                        <p key={idx} className="text-xs text-amber-600 flex items-center gap-1.5">
                            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                            {issue}
                        </p>
                    ))}
                </div>
            )}

            {isNotInstalled && (
                <p className="text-xs text-neutral-500 mt-2">
                    Connect your Shopify store to enable pixel tracking.{' '}
                    <Link href="/settings?tab=connections" className="text-neutral-900 hover:underline font-medium">
                        Go to Settings
                    </Link>
                </p>
            )}
        </div>
    );
}

/**
 * Setup checklist — shows what's connected and what's missing.
 *
 * WHY: Users asked for a "what's missing" view so they can quickly diagnose
 *      why attribution isn't working or is incomplete.
 *
 * NOTE: Meta Ads and Google Ads are shown as OPTIONAL — many stores only run
 *       one platform. They appear as informational ("Connected" or "Not connected")
 *       rather than red/broken.
 */
function SetupChecklist({ connections, pixelHealth, summary, loading }) {
    if (loading) {
        return (
            <div className="bg-white border border-neutral-200 rounded-xl p-4 animate-pulse">
                <div className="h-4 w-40 bg-neutral-100 rounded mb-4" />
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-4 w-full bg-neutral-100 rounded mb-3" />
                ))}
            </div>
        );
    }

    const hasShopify = connections.some(c => c.provider === 'shopify' && c.status === 'active');
    const hasMeta = connections.some(c => c.provider === 'meta' && c.status === 'active');
    const hasGoogle = connections.some(c => c.provider === 'google' && c.status === 'active');
    const pixelInstalled = pixelHealth && pixelHealth.status !== 'not_installed';
    const pixelActive = pixelHealth?.status === 'active';
    const eventsFlowing = pixelHealth?.events_24h
        && ((pixelHealth.events_24h.page_viewed || 0) + (pixelHealth.events_24h.checkout_completed || 0)) > 0;
    const ordersAttributed = summary && summary.total_orders > 0;

    // Required items — these must be done for attribution to work
    const requiredItems = [
        {
            label: 'Shopify connected',
            done: hasShopify,
            hint: hasShopify ? 'Receiving order webhooks' : 'Required for order webhooks and pixel',
            fixHref: '/settings?tab=connections',
            fixLabel: 'Connect',
        },
        {
            label: 'Tracking pixel installed',
            done: pixelInstalled,
            hint: pixelInstalled
                ? (pixelActive ? 'Active and healthy' : 'Installed but may have issues')
                : 'Needed to track customer journeys',
            fixHref: '/settings?tab=connections',
            fixLabel: 'Install',
        },
        {
            label: 'Pixel events flowing',
            done: eventsFlowing,
            hint: eventsFlowing
                ? 'Events received in last 24h'
                : 'No events in 24h — is your store getting traffic?',
        },
        {
            label: 'Orders attributed',
            done: ordersAttributed,
            hint: ordersAttributed
                ? `${summary.total_orders} orders in this period`
                : 'Ensure UTM parameters are set on campaigns',
        },
    ];

    // Optional items — informational, not required
    const optionalItems = [
        {
            label: 'Meta Ads',
            done: hasMeta,
            hint: hasMeta ? 'Connected — syncing campaigns' : 'Optional — connect to attribute Meta campaigns',
            fixHref: '/settings?tab=connections',
            fixLabel: 'Connect',
            optional: true,
        },
        {
            label: 'Google Ads',
            done: hasGoogle,
            hint: hasGoogle ? 'Connected — syncing campaigns' : 'Optional — connect to resolve gclids',
            fixHref: '/settings?tab=connections',
            fixLabel: 'Connect',
            optional: true,
        },
    ];

    const requiredDone = requiredItems.filter(i => i.done).length;

    return (
        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-neutral-400" />
                    <span className="text-sm font-medium text-neutral-900">Setup Checklist</span>
                </div>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-md ${
                    requiredDone === requiredItems.length
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                    {requiredDone}/{requiredItems.length} required
                </span>
            </div>

            {/* Required items */}
            <div className="divide-y divide-neutral-100">
                {requiredItems.map((item, idx) => (
                    <div key={idx} className="px-4 py-2.5 flex items-center gap-3">
                        {item.done ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        ) : (
                            <XCircle className="w-4 h-4 text-neutral-300 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                            <p className={`text-sm ${item.done ? 'text-neutral-900' : 'text-neutral-500'}`}>
                                {item.label}
                            </p>
                            <p className="text-xs text-neutral-400 truncate">{item.hint}</p>
                        </div>
                        {!item.done && item.fixHref && (
                            <Link
                                href={item.fixHref}
                                className="text-xs text-neutral-600 hover:text-neutral-900 font-medium flex-shrink-0"
                            >
                                {item.fixLabel}
                            </Link>
                        )}
                    </div>
                ))}
            </div>

            {/* Optional items — separated visually */}
            <div className="px-4 py-2 bg-neutral-50 border-t border-neutral-100">
                <p className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
                    Ad Platforms (optional)
                </p>
            </div>
            <div className="divide-y divide-neutral-100">
                {optionalItems.map((item, idx) => (
                    <div key={idx} className="px-4 py-2.5 flex items-center gap-3">
                        {item.done ? (
                            <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        ) : (
                            <Minus className="w-4 h-4 text-neutral-300 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                            <p className={`text-sm ${item.done ? 'text-neutral-900' : 'text-neutral-500'}`}>
                                {item.label}
                            </p>
                            <p className="text-xs text-neutral-400 truncate">{item.hint}</p>
                        </div>
                        {!item.done && item.fixHref && (
                            <Link
                                href={item.fixHref}
                                className="text-xs text-neutral-400 hover:text-neutral-600 font-medium flex-shrink-0"
                            >
                                {item.fixLabel}
                            </Link>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function AttributionPage() {
    const router = useRouter();
    const [user, setUser] = useState(null);
    const [days, setDays] = useState(7);
    const [loading, setLoading] = useState(true);
    const [summary, setSummary] = useState(null);
    const [campaigns, setCampaigns] = useState([]);
    const [feed, setFeed] = useState({ items: [], total_count: 0 });
    const [warnings, setWarnings] = useState([]);
    const [pixelHealth, setPixelHealth] = useState(null);
    const [connections, setConnections] = useState([]);
    const [error, setError] = useState(null);

    useEffect(() => {
        currentUser().then(setUser).catch(console.error);
    }, []);

    /**
     * Refresh only the live feed — called on interval.
     * WHY: The feed should auto-update so users see new attributions without manual refresh.
     */
    const refreshFeed = useCallback(async () => {
        if (!user?.workspace_id) return;
        try {
            const feedData = await fetchAttributionFeed({ workspaceId: user.workspace_id, limit: 15 });
            setFeed(feedData);
        } catch (err) {
            console.warn('Feed refresh failed:', err.message);
        }
    }, [user?.workspace_id]);

    // Load all attribution data when user or timeframe changes
    useEffect(() => {
        if (!user?.workspace_id) return;

        async function loadData() {
            setLoading(true);
            setError(null);
            try {
                const [summaryData, campaignsData, feedData, warningsData, pixelData, connectionsData] = await Promise.all([
                    fetchAttributionSummary({ workspaceId: user.workspace_id, days }),
                    fetchAttributedCampaigns({ workspaceId: user.workspace_id, days, limit: 10 }),
                    fetchAttributionFeed({ workspaceId: user.workspace_id, limit: 15 }),
                    fetchCampaignWarnings({ workspaceId: user.workspace_id, days }),
                    fetchPixelHealth({ workspaceId: user.workspace_id }).catch(() => null),
                    fetchConnections({ workspaceId: user.workspace_id }).catch(() => ({ connections: [] })),
                ]);
                setSummary(summaryData);
                setCampaigns(campaignsData.campaigns || []);
                setFeed(feedData);
                setWarnings(warningsData.warnings || []);
                setPixelHealth(pixelData);
                setConnections(connectionsData.connections || []);
            } catch (err) {
                console.error('Failed to load attribution data:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [user?.workspace_id, days]);

    // Auto-refresh live feed every 30 seconds
    useEffect(() => {
        if (!user?.workspace_id) return;
        const interval = setInterval(refreshFeed, FEED_REFRESH_INTERVAL);
        return () => clearInterval(interval);
    }, [user?.workspace_id, refreshFeed]);

    // Chart data
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

    // ----- Loading skeleton -----
    if (loading && !summary) {
        return (
            <div className="animate-pulse">
                <div className="h-6 w-32 bg-neutral-200/50 rounded mb-4" />
                <div className="h-16 bg-neutral-200/50 rounded-xl mb-4" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 md:gap-4 mb-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="analytics-kpi-card h-20" />
                    ))}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="h-64 bg-neutral-200/50 rounded-xl" />
                    <div className="h-64 bg-neutral-200/50 rounded-xl" />
                </div>
            </div>
        );
    }

    // ----- Error state -----
    if (error) {
        return (
            <div>
                <div className="bg-white border border-neutral-200 rounded-xl p-8 text-center">
                    <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
                    <h2 className="text-base font-medium text-neutral-900 mb-1">Unable to load attribution data</h2>
                    <p className="text-sm text-neutral-500 mb-4">{error}</p>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.location.reload()}
                    >
                        Try Again
                    </Button>
                </div>
            </div>
        );
    }

    const hasData = summary && summary.total_orders > 0;

    return (
        <div className="space-y-4 md:space-y-6 pb-16 md:pb-0">
            {/* Header — matches analytics page pattern */}
            <header className="pb-2">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2 md:gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-neutral-400 hover:text-neutral-900"
                            onClick={() => router.push('/analytics')}
                            aria-label="Back to Analytics"
                        >
                            <ArrowLeft className="w-4 h-4" />
                        </Button>
                        <h1 className="text-lg md:text-xl font-semibold tracking-tight text-neutral-900">
                            Attribution
                        </h1>
                    </div>
                </div>

                {/* Timeframe filter — matches analytics filter row style */}
                <div className="flex items-center gap-2">
                    {TIMEFRAMES.map(tf => (
                        <Button
                            key={tf.value}
                            variant={days === tf.value ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setDays(tf.value)}
                            className={`h-8 px-2.5 text-xs shrink-0 ${
                                days === tf.value
                                    ? 'bg-neutral-900 text-white hover:bg-neutral-800'
                                    : 'bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300'
                            }`}
                        >
                            {tf.label}
                        </Button>
                    ))}
                </div>
            </header>

            {/* Pixel Health — always visible */}
            <PixelHealthSection pixelHealth={pixelHealth} loading={loading} />

            {!hasData ? (
                /* Empty State — show checklist so the user knows what to do */
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="bg-white border border-neutral-200 rounded-xl p-10 text-center">
                        <Target className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                        <h2 className="text-base font-medium text-neutral-900 mb-1">No attribution data yet</h2>
                        <p className="text-sm text-neutral-500 max-w-sm mx-auto mb-4">
                            Connect your Shopify store and add UTM parameters to your ad campaigns to start attributing orders.
                        </p>
                        <Link href="/settings?tab=connections">
                            <Button variant="outline" size="sm">
                                Go to Settings
                            </Button>
                        </Link>
                    </div>
                    <SetupChecklist
                        connections={connections}
                        pixelHealth={pixelHealth}
                        summary={summary}
                        loading={false}
                    />
                </div>
            ) : (
                <>
                    {/* KPI Strip — matches analytics-kpi-card grid */}
                    <section className="grid grid-cols-2 md:grid-cols-4 gap-2.5 md:gap-4">
                        <KpiCard
                            label="Attributed Revenue"
                            value={formatCurrency(summary.total_attributed_revenue)}
                        />
                        <KpiCard
                            label="Orders"
                            value={summary.total_orders.toLocaleString()}
                        />
                        <KpiCard
                            label="Attribution Rate"
                            value={`${summary.attribution_rate.toFixed(0)}%`}
                        />
                        <KpiCard
                            label="Avg Order Value"
                            value={formatCurrency(summary.total_attributed_revenue / summary.total_orders)}
                        />
                    </section>

                    {/* Charts */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {/* Revenue by Channel */}
                        <div className="bg-white border border-neutral-200 rounded-xl p-4">
                            <h3 className="text-sm font-medium text-neutral-900 mb-4">Revenue by Channel</h3>
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
                                <div className="space-y-2 self-center">
                                    {summary.by_provider.slice(0, 5).map(item => (
                                        <div key={item.provider} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className="w-2.5 h-2.5 rounded-full"
                                                    style={{ backgroundColor: PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown }}
                                                />
                                                <span className="text-xs text-neutral-700">
                                                    {PROVIDER_NAMES[item.provider] || item.provider}
                                                </span>
                                            </div>
                                            <div className="text-right">
                                                <span className="text-xs font-medium text-neutral-900 tabular-nums">
                                                    {formatCurrency(item.revenue)}
                                                </span>
                                                <span className="text-[10px] text-neutral-400 ml-1.5">
                                                    {item.percentage.toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Top Campaigns */}
                        <div className="bg-white border border-neutral-200 rounded-xl p-4">
                            <h3 className="text-sm font-medium text-neutral-900 mb-4">Top Campaigns</h3>
                            {barChartData.length > 0 ? (
                                <div className="h-48">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={barChartData} layout="vertical">
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
                                            <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                                            <Tooltip
                                                formatter={(value) => formatCurrency(value)}
                                                labelFormatter={(label) => label}
                                            />
                                            <Bar dataKey="revenue" fill="#171717" radius={[0, 4, 4, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            ) : (
                                <div className="h-48 flex items-center justify-center text-sm text-neutral-400">
                                    No campaign data available
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bottom Grid — 3 panels */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Live Attribution Feed */}
                        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
                            <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Activity className="w-4 h-4 text-neutral-500" />
                                        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                                    </div>
                                    <span className="text-sm font-medium text-neutral-900">Live Feed</span>
                                </div>
                                <span className="text-[10px] text-neutral-400 tabular-nums">
                                    {feed.total_count.toLocaleString()} total
                                </span>
                            </div>
                            <div className="max-h-[300px] overflow-y-auto">
                                {feed.items.length === 0 ? (
                                    <div className="p-8 text-center">
                                        <DollarSign className="w-8 h-8 mx-auto mb-2 text-neutral-200" />
                                        <p className="text-xs text-neutral-400">No attributions yet</p>
                                    </div>
                                ) : (
                                    feed.items.map(item => (
                                        <div key={item.id} className="px-4 py-3 border-b border-neutral-50 last:border-b-0 hover:bg-neutral-50/50 transition-colors">
                                            <div className="flex items-center justify-between mb-0.5">
                                                <span className="text-sm font-medium text-neutral-900 tabular-nums">
                                                    {formatCurrency(item.revenue)}
                                                </span>
                                                <span className="text-[10px] text-neutral-400">
                                                    {formatRelativeTime(item.attributed_at)}
                                                </span>
                                            </div>
                                            <p className="text-xs text-neutral-500 truncate mb-1">
                                                {item.campaign_name || 'Unknown Campaign'}
                                            </p>
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className="px-1.5 py-0.5 text-[10px] font-medium rounded"
                                                    style={{
                                                        backgroundColor: `${PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown}10`,
                                                        color: PROVIDER_COLORS[item.provider] || PROVIDER_COLORS.unknown,
                                                    }}
                                                >
                                                    {PROVIDER_NAMES[item.provider] || item.provider}
                                                </span>
                                                <span className="text-[10px] text-neutral-400">via {item.match_type}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Campaign Warnings */}
                        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
                            <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                                    <span className="text-sm font-medium text-neutral-900">Warnings</span>
                                </div>
                                {warnings.length > 0 && (
                                    <span className="px-2 py-0.5 text-[10px] font-medium rounded-md bg-amber-50 text-amber-700 border border-amber-200">
                                        {warnings.length}
                                    </span>
                                )}
                            </div>
                            <div className="max-h-[300px] overflow-y-auto">
                                {warnings.length === 0 ? (
                                    <div className="p-8 text-center">
                                        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-200" />
                                        <p className="text-xs text-neutral-400">All campaigns tracking properly</p>
                                    </div>
                                ) : (
                                    warnings.map((warning, idx) => (
                                        <div key={idx} className="px-4 py-3 border-b border-neutral-50 last:border-b-0">
                                            <p className="text-xs font-medium text-neutral-900 truncate">
                                                {warning.campaign_name}
                                            </p>
                                            <p className="text-[10px] text-neutral-500 mt-0.5">
                                                {warning.warning_type === 'no_attribution'
                                                    ? 'No attributed orders — check UTMs'
                                                    : warning.warning_type === 'low_confidence'
                                                    ? 'Low confidence — review match types'
                                                    : warning.warning_type === 'no_utm'
                                                    ? 'Missing UTM parameters'
                                                    : warning.message || warning.warning_type}
                                            </p>
                                            <p className="text-[10px] text-neutral-400 mt-0.5">
                                                {PROVIDER_NAMES[warning.provider] || warning.provider}
                                            </p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Setup Checklist */}
                        <SetupChecklist
                            connections={connections}
                            pixelHealth={pixelHealth}
                            summary={summary}
                            loading={false}
                        />
                    </div>
                </>
            )}
        </div>
    );
}
