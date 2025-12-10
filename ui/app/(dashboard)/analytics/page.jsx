/**
 * Analytics Page - Performance Overview (v2.0 - Server-side filtering)
 * =====================================================================
 *
 * WHAT: Advanced analytics dashboard with server-side chart data
 * WHY: Frontend is dumb - backend handles all filtering for performance
 *
 * LAYOUT:
 *   - Header with title and timeframe selector
 *   - 4 KPI cards (Spend, Revenue, ROAS, Conversions)
 *   - Main area: Large chart (left ~75%) + Sidebar (right ~25%)
 *     - Chart: Metric tabs, server-rendered multi-line chart
 *     - Sidebar: Net Profit widget + Data source selector
 *
 * DATA SOURCES:
 *   - KPIs: /dashboard/unified (aggregated totals)
 *   - Chart: /analytics/chart (server-side filtered series)
 *
 * FILTERING:
 *   - Platform selection triggers server-side re-fetch
 *   - Campaign selection triggers server-side re-fetch
 *   - No client-side filtering - backend does all the work
 *
 * RELATED:
 *   - backend/app/routers/analytics.py (chart endpoint)
 *   - backend/app/routers/dashboard.py (kpi endpoint)
 *   - lib/api.js (fetchAnalyticsChart, fetchUnifiedDashboard)
 */
"use client";
import { useState, useEffect, useMemo, useCallback } from "react";
import { subDays, startOfDay, endOfDay, format } from "date-fns";
import { currentUser } from "@/lib/workspace";
import { fetchUnifiedDashboard, fetchAnalyticsChart, fetchEntityPerformance, fetchConnections } from "@/lib/api";
import { DateRangePicker, PRESETS } from "@/components/ui/date-range-picker";

// Components
import AnalyticsKpiStrip from "./components/AnalyticsKpiStrip";
import AnalyticsGraphEngine from "./components/AnalyticsGraphEngine";
import AnalyticsProfitWidget from "./components/AnalyticsProfitWidget";
import AnalyticsDataSourcePanel from "./components/AnalyticsDataSourcePanel";

export default function AnalyticsPage() {
    // User & workspace
    const [user, setUser] = useState(null);
    const [workspaceId, setWorkspaceId] = useState(null);
    const [loading, setLoading] = useState(true);

    // Dashboard data (for KPIs)
    const [dashboardData, setDashboardData] = useState(null);
    const [dataLoading, setDataLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);

    // Chart data (from new analytics endpoint)
    const [chartData, setChartData] = useState({ series: [], totals: {}, metadata: {} });
    const [chartLoading, setChartLoading] = useState(false);

    // Filter state - date range
    const [preset, setPreset] = useState('last_30_days');
    const [dateRange, setDateRange] = useState(() => ({
        from: startOfDay(subDays(new Date(), 29)),
        to: endOfDay(new Date())
    }));
    const [selectedMetric, setSelectedMetric] = useState('revenue');

    // Compute API parameters based on preset or custom dates
    const apiParams = useMemo(() => {
        if (preset && preset !== 'custom') {
            return { timeframe: preset, startDate: null, endDate: null };
        }
        // Custom date range - format dates for API
        if (dateRange?.from && dateRange?.to) {
            return {
                timeframe: 'custom',
                startDate: format(dateRange.from, 'yyyy-MM-dd'),
                endDate: format(dateRange.to, 'yyyy-MM-dd')
            };
        }
        return { timeframe: 'last_30_days', startDate: null, endDate: null };
    }, [preset, dateRange]);

    // Data source selection (for chart filtering)
    const [connectedPlatforms, setConnectedPlatforms] = useState([]);
    const [selectedPlatforms, setSelectedPlatforms] = useState([]);
    const [selectedCampaigns, setSelectedCampaigns] = useState([]);
    const [campaigns, setCampaigns] = useState([]);

    // Fetch user on mount
    useEffect(() => {
        let mounted = true;
        currentUser()
            .then((u) => {
                if (!mounted) return;
                setUser(u);
                setWorkspaceId(u?.workspace_id);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to get user:", err);
                if (mounted) {
                    setUser(null);
                    setLoading(false);
                }
            });
        return () => { mounted = false; };
    }, []);

    // Fetch dashboard data (for KPIs)
    useEffect(() => {
        if (!workspaceId) return;

        setDataLoading(true);
        fetchUnifiedDashboard({
            workspaceId,
            timeframe: apiParams.timeframe,
            startDate: apiParams.startDate,
            endDate: apiParams.endDate
        })
            .then(data => {
                setDashboardData(data);
                setLastUpdated(new Date());
                setDataLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch dashboard data:", err);
                setDataLoading(false);
            });
    }, [workspaceId, apiParams]);

    // Determine groupBy based on selection
    const chartGroupBy = useMemo(() => {
        // If campaigns are selected, group by campaign
        if (selectedCampaigns && selectedCampaigns.length > 0) {
            return 'campaign';
        }
        // If specific platforms selected (not all), group by platform
        if (selectedPlatforms && selectedPlatforms.length > 0 &&
            connectedPlatforms.length > 0 &&
            selectedPlatforms.length < connectedPlatforms.length) {
            return 'platform';
        }
        // Default: total aggregate
        return 'total';
    }, [selectedPlatforms, selectedCampaigns, connectedPlatforms]);

    // Fetch chart data from new analytics endpoint
    const fetchChartData = useCallback(async () => {
        if (!workspaceId) return;

        setChartLoading(true);
        try {
            const data = await fetchAnalyticsChart({
                workspaceId,
                timeframe: apiParams.timeframe,
                startDate: apiParams.startDate,
                endDate: apiParams.endDate,
                platforms: selectedPlatforms.length > 0 ? selectedPlatforms : null,
                campaignIds: selectedCampaigns.length > 0 ? selectedCampaigns : null,
                groupBy: chartGroupBy,
            });
            setChartData(data);
        } catch (err) {
            console.error("Failed to fetch chart data:", err);
            setChartData({ series: [], totals: {}, metadata: {} });
        } finally {
            setChartLoading(false);
        }
    }, [workspaceId, apiParams, selectedPlatforms, selectedCampaigns, chartGroupBy]);

    // Fetch chart when filters change
    useEffect(() => {
        fetchChartData();
    }, [fetchChartData]);

    // Fetch connected platforms
    useEffect(() => {
        if (!workspaceId) return;

        fetchConnections({ workspaceId, status: 'active' })
            .then(res => {
                const providers = [...new Set(
                    (res?.connections || []).map(c => c.provider?.toLowerCase())
                )].filter(Boolean);
                setConnectedPlatforms(providers);
                // Don't auto-select - empty = all platforms (shown as aggregate)
            })
            .catch(err => console.error('Failed to fetch connections:', err));
    }, [workspaceId]);

    // Fetch campaigns for selector
    useEffect(() => {
        if (!workspaceId) return;

        // Determine days based on preset or custom range
        let days = 30; // default
        if (apiParams.timeframe === 'last_7_days') days = 7;
        else if (apiParams.timeframe === 'last_30_days') days = 30;
        else if (apiParams.timeframe === 'last_90_days') days = 90;
        else if (apiParams.timeframe === 'today' || apiParams.timeframe === 'yesterday') days = 7;

        fetchEntityPerformance({
            workspaceId,
            entityType: 'campaign',
            timeRange: { last_n_days: days },
            limit: 20,
            sortBy: 'spend',
            sortDir: 'desc',
            status: 'all'
        })
            .then(res => setCampaigns(res?.items || []))
            .catch(err => console.error('Failed to fetch campaigns:', err));
    }, [workspaceId, apiParams]);

    // Loading state
    if (loading) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-slate-500 text-sm">Loading analytics...</span>
                </div>
            </div>
        );
    }

    // Not logged in
    if (!user) {
        return (
            <div className="p-6">
                <div className="max-w-2xl mx-auto dashboard-module">
                    <h2 className="text-xl font-medium mb-2 text-slate-900">You must be signed in.</h2>
                    <a href="/sign-in" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
                </div>
            </div>
        );
    }

    return (
        <div className="text-slate-800 font-sans antialiased min-h-screen selection:bg-cyan-200 selection:text-cyan-900 pb-8">
            <main className="max-w-[1920px] mx-auto p-4 md:p-6 space-y-6">

                {/* Header */}
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                            Performance Analytics
                        </h1>
                        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                            <span className="flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                                Live
                            </span>
                            <span>
                                Updated {lastUpdated ? lastUpdated.toLocaleTimeString('en-US', {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                }) : '...'}
                            </span>
                        </div>
                    </div>

                    {/* Date Range Picker */}
                    <DateRangePicker
                        preset={preset}
                        onPresetChange={setPreset}
                        dateRange={dateRange}
                        onDateRangeChange={setDateRange}
                    />
                </header>

                {/* KPI Strip */}
                <AnalyticsKpiStrip
                    data={dashboardData}
                    loading={dataLoading}
                />

                {/* Main Data Area - Chart + Sidebar */}
                <section className="flex flex-col lg:flex-row gap-5">
                    {/* Left: Large Graph Engine */}
                    <AnalyticsGraphEngine
                        series={chartData.series}
                        totals={chartData.totals}
                        metadata={chartData.metadata}
                        loading={chartLoading}
                        selectedMetric={selectedMetric}
                        onMetricChange={setSelectedMetric}
                        currency={dashboardData?.currency || "USD"}
                    />

                    {/* Right: Control & Profit Panel */}
                    <div className="flex flex-col gap-5 lg:w-[320px] lg:min-w-[320px]">
                        {/* Net Profit Widget */}
                        <AnalyticsProfitWidget
                            data={dashboardData}
                            loading={dataLoading}
                        />

                        {/* Data Source Selector */}
                        <AnalyticsDataSourcePanel
                            campaigns={campaigns}
                            connectedPlatforms={connectedPlatforms}
                            selectedPlatforms={selectedPlatforms}
                            onPlatformsChange={setSelectedPlatforms}
                            selectedCampaigns={selectedCampaigns}
                            onCampaignsChange={setSelectedCampaigns}
                        />
                    </div>
                </section>
            </main>
        </div>
    );
}
