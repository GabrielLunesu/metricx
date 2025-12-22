/**
 * Analytics Page - Performance Overview (v3.0 - Global Filters)
 * ==============================================================
 *
 * WHAT: Advanced analytics dashboard with global filtering
 * WHY: All filters at top, cascade to entire page
 *
 * LAYOUT:
 *   - Header: Title + Date picker + Data source filters
 *   - KPI strips: Primary (4) + Secondary (4)
 *   - Main chart area
 *   - Bottom: Top campaigns + Profit trend
 *
 * FILTERING:
 *   - Date range: Affects ALL data
 *   - Platform: Affects ALL data (KPIs, chart, campaigns)
 *   - Campaigns: Affects KPIs + charts (command-center mode)
 *   - Meta Ad drill-down: Affects KPIs + entity trend (limited)
 *
 * DATA FLOW:
 *   - Filters live at top
 *   - All fetches include current filters
 *   - Components receive filtered data
 */
"use client";
import { useState, useEffect, useMemo, useCallback } from "react";
import { subDays, startOfDay, endOfDay, format, differenceInCalendarDays } from "date-fns";
import { currentUser } from "@/lib/workspace";
import { fetchUnifiedDashboard, fetchAnalyticsChart, fetchEntityChildren, fetchEntityPerformance, fetchConnections } from "@/lib/api";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { GitCompare, Database } from "lucide-react";

// Components
import AnalyticsFilterBar from "./components/AnalyticsFilterBar";
import AnalyticsKpiStrip from "./components/AnalyticsKpiStrip";
import AnalyticsSecondaryKpis from "./components/AnalyticsSecondaryKpis";
import AnalyticsGraphEngine from "./components/AnalyticsGraphEngine";
import AnalyticsProfitWidget from "./components/AnalyticsProfitWidget";
import TopCampaignsWidget from "./components/TopCampaignsWidget";
import ProfitTrendChart from "./components/ProfitTrendChart";
import EntityTrendChart from "./components/EntityTrendChart";

function toDateString(d) {
    return format(d, "yyyy-MM-dd");
}

function getPreviousPeriod(dateRange) {
    if (!dateRange?.from || !dateRange?.to) return null;
    const days = differenceInCalendarDays(dateRange.to, dateRange.from) + 1;
    const prevStart = subDays(dateRange.from, days);
    const prevEnd = subDays(dateRange.from, 1);
    return { prevStart, prevEnd, days };
}

function aggregateSeriesToChartData(series = []) {
    const byDate = new Map();
    for (const s of series || []) {
        for (const p of s.data || []) {
            const existing = byDate.get(p.date) || { date: p.date, revenue: 0, spend: 0, conversions: 0 };
            existing.revenue += Number(p.revenue || 0);
            existing.spend += Number(p.spend || 0);
            existing.conversions += Number(p.conversions || 0);
            byDate.set(p.date, existing);
        }
    }
    return Array.from(byDate.values()).sort((a, b) => new Date(a.date) - new Date(b.date));
}

function kpiArrayFromTotals({ totals, prevTotals }) {
    const spend = Number(totals?.spend || 0);
    const revenue = Number(totals?.revenue || 0);
    const conversions = Number(totals?.conversions || 0);
    const roas = Number(totals?.roas ?? (spend > 0 ? revenue / spend : 0));

    const clicks = Number(totals?.clicks || 0);
    const impressions = Number(totals?.impressions || 0);
    const cpc = totals?.cpc ?? (clicks > 0 ? spend / clicks : 0);
    const ctr = totals?.ctr ?? (impressions > 0 ? (clicks / impressions) * 100 : 0);

    const prevSpend = prevTotals ? Number(prevTotals.spend || 0) : null;
    const prevRevenue = prevTotals ? Number(prevTotals.revenue || 0) : null;
    const prevConversions = prevTotals ? Number(prevTotals.conversions || 0) : null;
    const prevRoas = prevTotals ? Number(prevTotals.roas || (prevSpend > 0 ? prevRevenue / prevSpend : 0)) : null;
    const prevClicks = prevTotals ? Number(prevTotals.clicks || 0) : null;
    const prevImpressions = prevTotals ? Number(prevTotals.impressions || 0) : null;
    const prevCpc = prevTotals && prevClicks > 0 ? prevSpend / prevClicks : null;
    const prevCtr = prevTotals && prevImpressions > 0 ? (prevClicks / prevImpressions) * 100 : null;

    const deltaPct = (curr, prev) => {
        if (prev === null || prev === undefined) return null;
        if (prev === 0) return null;
        return (curr - prev) / Math.abs(prev);
    };

    return [
        { key: "spend", value: spend, prev: prevSpend, delta_pct: deltaPct(spend, prevSpend) },
        { key: "revenue", value: revenue, prev: prevRevenue, delta_pct: deltaPct(revenue, prevRevenue) },
        { key: "roas", value: roas, prev: prevRoas, delta_pct: deltaPct(roas, prevRoas) },
        { key: "conversions", value: conversions, prev: prevConversions, delta_pct: deltaPct(conversions, prevConversions) },
        { key: "cpc", value: cpc, prev: prevCpc, delta_pct: deltaPct(cpc, prevCpc) },
        { key: "ctr", value: ctr, prev: prevCtr, delta_pct: deltaPct(ctr, prevCtr) },
    ];
}

export default function AnalyticsPage() {
    // User & workspace
    const [user, setUser] = useState(null);
    const [workspaceId, setWorkspaceId] = useState(null);
    const [loading, setLoading] = useState(true);

    // Dashboard data (for KPIs)
    const [dashboardData, setDashboardData] = useState(null);
    const [dataLoading, setDataLoading] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);

    // Chart data (from analytics endpoint)
    const [chartData, setChartData] = useState({ series: [], totals: {}, metadata: {} });
    const [chartLoading, setChartLoading] = useState(false);

    // Previous-period chart totals (used for campaign-filtered KPI deltas)
    const [prevChartTotals, setPrevChartTotals] = useState(null);
    const [prevChartLoading, setPrevChartLoading] = useState(false);

    // Compare mode (previous period overlay)
    const [compareEnabled, setCompareEnabled] = useState(false);
    const [compareChartData, setCompareChartData] = useState(null);
    const [compareChartLoading, setCompareChartLoading] = useState(false);

    // ============================================
    // GLOBAL FILTERS - These affect the ENTIRE page
    // ============================================

    // Date range filter
    const [preset, setPreset] = useState('last_30_days');
    const [dateRange, setDateRange] = useState(() => ({
        from: startOfDay(subDays(new Date(), 29)),
        to: endOfDay(new Date())
    }));

    // Platform filter (null = all/blended, 'google' or 'meta')
    const [selectedPlatform, setSelectedPlatform] = useState(null);

    // Campaign filter (array of campaign IDs)
    const [selectedCampaigns, setSelectedCampaigns] = useState([]);

    // Meta drill-down selection
    const [adSets, setAdSets] = useState([]);
    const [ads, setAds] = useState([]);
    const [selectedAdSetId, setSelectedAdSetId] = useState(null);
    const [selectedAdId, setSelectedAdId] = useState(null);
    const [adLoading, setAdLoading] = useState(false);

    // Chart metric selection
    const [selectedMetric, setSelectedMetric] = useState('revenue');

    // Connected platforms (for filter dropdown)
    const [connectedPlatforms, setConnectedPlatforms] = useState([]);

    // Campaigns list (filtered by platform and timeframe)
    const [campaigns, setCampaigns] = useState([]);

    // ============================================
    // COMPUTED VALUES
    // ============================================

    // Compute API parameters based on preset or custom dates
    const apiParams = useMemo(() => {
        if (preset && preset !== 'custom') {
            return { timeframe: preset, startDate: null, endDate: null };
        }
        if (dateRange?.from && dateRange?.to) {
            return {
                timeframe: 'custom',
                startDate: format(dateRange.from, 'yyyy-MM-dd'),
                endDate: format(dateRange.to, 'yyyy-MM-dd')
            };
        }
        return { timeframe: 'last_30_days', startDate: null, endDate: null };
    }, [preset, dateRange]);

    // Entity-performance endpoints expect end-exclusive date ranges; we pass inclusive dates here and let the API helper adjust.
    const entityTimeRange = useMemo(() => {
        if (!dateRange?.from || !dateRange?.to) return { last_n_days: 30 };
        return { start: toDateString(dateRange.from), end: toDateString(dateRange.to) };
    }, [dateRange]);

    // Chart groupBy based on selection
    const chartGroupBy = useMemo(() => {
        if (selectedCampaigns.length > 0) return 'campaign';
        if (selectedPlatform) return 'platform';
        return 'total';
    }, [selectedPlatform, selectedCampaigns]);

    const selectedCampaignId = selectedCampaigns.length === 1 ? selectedCampaigns[0] : null;
    const selectedCampaign = useMemo(() => {
        if (!selectedCampaignId) return null;
        return campaigns.find(c => c.id === selectedCampaignId) || null;
    }, [campaigns, selectedCampaignId]);

    const selectedAd = useMemo(() => {
        if (!selectedAdId) return null;
        return ads.find(a => a.id === selectedAdId) || null;
    }, [ads, selectedAdId]);

    // Data source label for display
    const dataSourceLabel = useMemo(() => {
        if (selectedAd) return `Ad: ${selectedAd.name}`;
        if (selectedCampaigns.length > 0) {
            return `${selectedCampaigns.length} Campaign${selectedCampaigns.length > 1 ? 's' : ''}`;
        }
        if (selectedPlatform === 'google') return 'Google Ads';
        if (selectedPlatform === 'meta') return 'Meta Ads';
        return 'Blended Data';
    }, [selectedPlatform, selectedCampaigns, selectedAd]);

    const isCampaignFiltered = selectedCampaigns.length > 0;
    const isAdView = Boolean(selectedAdId && selectedAd);

    const revenueSource = useMemo(() => {
        if (isAdView || isCampaignFiltered) return { label: "Ads attributed", hint: "Campaign/ad views use platform-attributed revenue (Shopify orders can’t be reliably mapped to campaigns)." };
        if (dashboardData?.has_shopify && dashboardData?.data_source === "shopify") return { label: "Shopify truth", hint: "Revenue comes from Shopify orders (with blended attribution where available)." };
        return { label: "Platform totals", hint: "Revenue comes from ad platform conversion value totals." };
    }, [dashboardData, isAdView, isCampaignFiltered]);

    // "Meta ad" drilldown is available when a single Meta campaign is selected.
    const canMetaDrillDown = useMemo(() => {
        if (!selectedCampaignId) return false;
        const campaignPlatform = (selectedCampaign?.platform || selectedCampaign?.provider || "").toLowerCase();
        if (selectedPlatform && selectedPlatform !== "meta") return false;
        return campaignPlatform === "meta" || selectedPlatform === "meta";
    }, [selectedCampaignId, selectedCampaign, selectedPlatform]);

    // KPI data source: for campaign/ad filters we use chart/entity totals (platform-attributed), otherwise unified dashboard (Shopify-first).
    const effectiveData = useMemo(() => {
        const currency = dashboardData?.currency || "USD";

        if (isAdView && selectedAd) {
            const totals = {
                spend: selectedAd.spend || 0,
                revenue: selectedAd.revenue || 0,
                conversions: selectedAd.conversions || 0,
                roas: selectedAd.roas || 0,
                clicks: selectedAd.clicks || 0,
                impressions: selectedAd.impressions || 0,
            };
            return {
                currency,
                kpis: kpiArrayFromTotals({ totals, prevTotals: null }),
                chart_data: [],
                data_source: "platform",
                has_shopify: Boolean(dashboardData?.has_shopify),
            };
        }

        if (isCampaignFiltered) {
            const selectedRows = (campaigns || []).filter((c) => selectedCampaigns.includes(c.id));
            const derivedTotals = (() => {
                if (!selectedRows.length) return null;
                let spend = 0;
                let revenue = 0;
                let conversions = 0;
                let clicks = 0;
                let impressions = 0;

                for (const row of selectedRows) {
                    const rowSpend = Number(row.spend || 0);
                    const rowRevenue = Number(row.revenue || 0);
                    const rowConv = Number(row.conversions || 0);
                    spend += rowSpend;
                    revenue += rowRevenue;
                    conversions += rowConv;

                    const rowCpc = Number(row.cpc || 0);
                    const rowCtrPct = Number(row.ctr_pct || 0);
                    const rowClicks = rowCpc > 0 ? rowSpend / rowCpc : 0;
                    const rowImpressions = rowCtrPct > 0 ? rowClicks / (rowCtrPct / 100) : 0;
                    clicks += rowClicks;
                    impressions += rowImpressions;
                }

                const roas = spend > 0 ? revenue / spend : 0;
                const cpc = clicks > 0 ? spend / clicks : 0;
                const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;

                return { spend, revenue, conversions, roas, clicks, impressions, cpc, ctr };
            })();

            return {
                currency,
                kpis: kpiArrayFromTotals({ totals: derivedTotals || chartData?.totals, prevTotals: prevChartTotals }),
                chart_data: aggregateSeriesToChartData(chartData?.series || []),
                data_source: "platform",
                has_shopify: Boolean(dashboardData?.has_shopify),
            };
        }

        return dashboardData;
    }, [dashboardData, isAdView, isCampaignFiltered, selectedAd, chartData, prevChartTotals, selectedCampaignId, selectedCampaign]);

    const effectiveLoading = isAdView ? adLoading : (isCampaignFiltered ? (chartLoading || prevChartLoading) : dataLoading);

    // ============================================
    // DATA FETCHING
    // ============================================

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

    // Fetch connected platforms
    useEffect(() => {
        if (!workspaceId) return;

        fetchConnections({ workspaceId, status: 'active' })
            .then(res => {
                const providers = [...new Set(
                    (res?.connections || []).map(c => c.provider?.toLowerCase())
                )].filter(Boolean);
                setConnectedPlatforms(providers);
            })
            .catch(err => console.error('Failed to fetch connections:', err));
    }, [workspaceId]);

    // Fetch dashboard data (KPIs) - respects platform filter
    useEffect(() => {
        if (!workspaceId) return;

        setDataLoading(true);
        fetchUnifiedDashboard({
            workspaceId,
            timeframe: apiParams.timeframe,
            startDate: apiParams.startDate,
            endDate: apiParams.endDate,
            platform: selectedPlatform, // Pass platform filter
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
    }, [workspaceId, apiParams, selectedPlatform]);

    // Fetch campaigns - respects timeframe AND platform filter
    useEffect(() => {
        if (!workspaceId) return;

        fetchEntityPerformance({
            workspaceId,
            entityType: 'campaign',
            timeRange: entityTimeRange,
            provider: selectedPlatform, // Pass platform filter
            limit: 50,
            sortBy: 'spend',
            sortDir: 'desc',
            status: 'all'
        })
            .then(res => setCampaigns(res?.items || []))
            .catch(err => console.error('Failed to fetch campaigns:', err));
    }, [workspaceId, entityTimeRange, selectedPlatform]);

    // Fetch meta drill-down (ad sets → ads/creatives) when eligible
    useEffect(() => {
        if (!workspaceId) return;

        // Reset when drilldown is not available
        if (!canMetaDrillDown) {
            setAdSets([]);
            setAds([]);
            setSelectedAdSetId(null);
            setSelectedAdId(null);
            return;
        }

        // Fetch ad sets under selected campaign
        setAdLoading(true);
        fetchEntityChildren({
            entityId: selectedCampaignId,
            timeRange: entityTimeRange,
            provider: "meta",
            limit: 50,
            sortBy: "spend",
            sortDir: "desc",
            status: "all",
        })
            .then((res) => {
                setAdSets(res?.items || []);
                setAds([]);
                setSelectedAdSetId(null);
                setSelectedAdId(null);
            })
            .catch((err) => {
                console.error("Failed to fetch ad sets:", err);
                setAdSets([]);
            })
            .finally(() => setAdLoading(false));
    }, [workspaceId, canMetaDrillDown, selectedCampaignId, entityTimeRange]);

    useEffect(() => {
        if (!workspaceId) return;
        if (!selectedAdSetId) {
            setAds([]);
            setSelectedAdId(null);
            return;
        }

        setAdLoading(true);
        fetchEntityChildren({
            entityId: selectedAdSetId,
            timeRange: entityTimeRange,
            provider: "meta",
            limit: 50,
            // If user is looking at ROAS tab, pull ROAS trend; otherwise revenue trend.
            sortBy: selectedMetric === "roas" ? "roas" : "revenue",
            sortDir: "desc",
            status: "all",
        })
            .then((res) => {
                setAds(res?.items || []);
                // Keep selection only if still present
                if (selectedAdId && !(res?.items || []).some((a) => a.id === selectedAdId)) {
                    setSelectedAdId(null);
                }
            })
            .catch((err) => {
                console.error("Failed to fetch ads:", err);
                setAds([]);
            })
            .finally(() => setAdLoading(false));
    }, [workspaceId, selectedAdSetId, entityTimeRange, selectedMetric, selectedAdId]);

    // Fetch chart data - respects all filters
    const fetchChartData = useCallback(async () => {
        if (!workspaceId) return;
        if (isAdView) return; // Ad view uses entity-performance trend instead of analytics chart.

        setChartLoading(true);
        try {
            const data = await fetchAnalyticsChart({
                workspaceId,
                timeframe: apiParams.timeframe,
                startDate: apiParams.startDate,
                endDate: apiParams.endDate,
                platforms: selectedPlatform ? [selectedPlatform] : null,
                campaignIds: selectedCampaigns.length > 0 ? selectedCampaigns : null,
                groupBy: chartGroupBy,
            });
            setChartData(data);
            setLastUpdated(new Date());
        } catch (err) {
            console.error("Failed to fetch chart data:", err);
            setChartData({ series: [], totals: {}, metadata: {} });
        } finally {
            setChartLoading(false);
        }
    }, [workspaceId, apiParams, selectedPlatform, selectedCampaigns, chartGroupBy, isAdView]);

    useEffect(() => {
        fetchChartData();
    }, [fetchChartData]);

    // Fetch previous period totals when campaign-filtered (for KPI deltas)
    useEffect(() => {
        if (!workspaceId) return;
        if (!isCampaignFiltered || isAdView) {
            setPrevChartTotals(null);
            return;
        }
        const prev = getPreviousPeriod(dateRange);
        if (!prev) return;

        setPrevChartLoading(true);
        fetchAnalyticsChart({
            workspaceId,
            timeframe: "custom",
            startDate: toDateString(prev.prevStart),
            endDate: toDateString(prev.prevEnd),
            platforms: selectedPlatform ? [selectedPlatform] : null,
            campaignIds: selectedCampaigns.length > 0 ? selectedCampaigns : null,
            groupBy: chartGroupBy,
        })
            .then((data) => setPrevChartTotals(data?.totals || null))
            .catch((err) => {
                console.error("Failed to fetch previous totals:", err);
                setPrevChartTotals(null);
            })
            .finally(() => setPrevChartLoading(false));
    }, [workspaceId, isCampaignFiltered, isAdView, dateRange, selectedPlatform, selectedCampaigns, chartGroupBy]);

    // Fetch previous period series when compare is enabled (chart overlay)
    useEffect(() => {
        if (!workspaceId) return;
        if (!compareEnabled || isAdView) {
            setCompareChartData(null);
            return;
        }
        const prev = getPreviousPeriod(dateRange);
        if (!prev) return;

        setCompareChartLoading(true);
        fetchAnalyticsChart({
            workspaceId,
            timeframe: "custom",
            startDate: toDateString(prev.prevStart),
            endDate: toDateString(prev.prevEnd),
            platforms: selectedPlatform ? [selectedPlatform] : null,
            campaignIds: selectedCampaigns.length > 0 ? selectedCampaigns : null,
            groupBy: chartGroupBy,
        })
            .then((data) => setCompareChartData(data))
            .catch((err) => {
                console.error("Failed to fetch compare series:", err);
                setCompareChartData(null);
            })
            .finally(() => setCompareChartLoading(false));
    }, [workspaceId, compareEnabled, isAdView, dateRange, selectedPlatform, selectedCampaigns, chartGroupBy]);

    const alignedCompareSeries = useMemo(() => {
        if (!compareEnabled) return null;
        const currentSeries = chartData?.series || [];
        const prevSeries = compareChartData?.series || [];
        if (!currentSeries.length || !prevSeries.length) return null;

        const currentByKey = new Map(currentSeries.map((s) => [s.key, s]));
        const aligned = [];
        for (const s of prevSeries) {
            const curr = currentByKey.get(s.key);
            if (!curr?.data?.length) continue;
            const currDates = [...curr.data].sort((a, b) => new Date(a.date) - new Date(b.date)).map((p) => p.date);
            const prevData = [...(s.data || [])].sort((a, b) => new Date(a.date) - new Date(b.date));
            const len = Math.min(currDates.length, prevData.length);
            aligned.push({
                ...s,
                key: `${s.key}__prev`,
                label: `${s.label} (prev)`,
                data: prevData.slice(0, len).map((p, i) => ({ ...p, date: currDates[i] })),
                isCompare: true,
            });
        }
        return aligned.length ? aligned : null;
    }, [compareEnabled, chartData, compareChartData]);

    // ============================================
    // RENDER
    // ============================================

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
        <div className="relative text-slate-800 font-sans antialiased selection:bg-cyan-200 selection:text-cyan-900 pb-8 space-y-5">
            {/* Soft grid overlay (subtle command-center texture) */}
            <div
                className="pointer-events-none absolute inset-0 -z-10 opacity-30"
                style={{
                    backgroundImage:
                        "linear-gradient(rgba(148,163,184,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.12) 1px, transparent 1px)",
                    backgroundSize: "2.5rem 2.5rem",
                    maskImage:
                        "radial-gradient(circle at 50% 25%, rgba(0,0,0,1), rgba(0,0,0,0.35), rgba(0,0,0,0))",
                }}
            />

            {/* Top bar */}
            <header className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                            Paid Growth Command Center
                        </h1>
                        <button
                            type="button"
                            title={revenueSource.hint}
                            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white/60 border border-white/70 text-slate-700 hover:bg-white/80 transition-colors"
                        >
                            <Database className="w-4 h-4 text-slate-500" />
                            Revenue: {revenueSource.label}
                        </button>
                        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
                            <span className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="font-medium">Live sync</span>
                            </span>
                            <span className="text-slate-300">|</span>
                            <span>
                                Updated{" "}
                                {lastUpdated
                                    ? lastUpdated.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
                                    : "..."}
                            </span>
                        </div>
                    </div>
                    <p className="mt-2 text-xs text-slate-500 max-w-3xl">
                        Everything updates with your selected time range and filters (platform, campaign, and Meta ad drill-down).
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                    <div className="flex gap-2">
                        <DateRangePicker preset={preset} onPresetChange={setPreset} dateRange={dateRange} onDateRangeChange={setDateRange} />
                        <button
                            type="button"
                            onClick={() => setCompareEnabled((v) => !v)}
                            className={`
                                px-4 py-2 rounded-xl text-xs font-semibold border flex items-center gap-2 transition-colors
                                ${compareEnabled
                                    ? "bg-slate-900 text-white border-white/10"
                                    : "glass-panel text-slate-700 hover:text-slate-900 border-white/70"
                                }
                            `}
                        >
                            <GitCompare className="w-4 h-4" />
                            Compare
                        </button>
                    </div>
                </div>
            </header>

            {/* Global Filter Bar */}
            <div className="glass-panel rounded-2xl p-4 relative z-[9999]">
                <AnalyticsFilterBar
                    connectedPlatforms={connectedPlatforms}
                    campaigns={campaigns}
                    selectedPlatform={selectedPlatform}
                    onPlatformChange={setSelectedPlatform}
                    selectedCampaigns={selectedCampaigns}
                    onCampaignsChange={(ids) => {
                        setSelectedCampaigns(ids);
                        setSelectedAdSetId(null);
                        setSelectedAdId(null);
                    }}
                    adSets={canMetaDrillDown ? adSets : []}
                    ads={canMetaDrillDown ? ads : []}
                    selectedAdSetId={selectedAdSetId}
                    onAdSetChange={setSelectedAdSetId}
                    selectedAdId={selectedAdId}
                    onAdChange={setSelectedAdId}
                    adLoading={adLoading}
                    loading={dataLoading}
                    currency={dashboardData?.currency || "EUR"}
                />
            </div>

            {/* Primary KPIs */}
            <AnalyticsKpiStrip data={effectiveData} loading={effectiveLoading} dataSource={dataSourceLabel} />

            {/* Secondary KPIs */}
            <AnalyticsSecondaryKpis
                data={effectiveData}
                campaigns={campaigns}
                loading={effectiveLoading}
                currency={effectiveData?.currency || "USD"}
                dataSource={dataSourceLabel}
            />

            {/* Main workspace */}
            <section className="grid grid-cols-1 xl:grid-cols-12 gap-5">
                <div className="xl:col-span-8 min-w-0">
                    {isAdView ? (
                        <EntityTrendChart
                            title={selectedAd?.name || "Selected ad"}
                            subtitle="Entity trend"
                            trend={selectedAd?.trend || []}
                            trendMetric={selectedAd?.trend_metric === "roas" ? "roas" : "revenue"}
                            currency={effectiveData?.currency || "USD"}
                            loading={adLoading}
                            disclaimer="Ad-level trend is currently limited to Revenue or ROAS from snapshot data."
                        />
                    ) : (
                        <AnalyticsGraphEngine
                            series={chartData.series}
                            compareSeries={alignedCompareSeries || []}
                            compareLoading={compareChartLoading}
                            compareEnabled={compareEnabled}
                            totals={chartData.totals}
                            metadata={chartData.metadata}
                            loading={chartLoading}
                            selectedMetric={selectedMetric}
                            onMetricChange={setSelectedMetric}
                            currency={effectiveData?.currency || "USD"}
                            dataSource={dataSourceLabel}
                        />
                    )}
                </div>

                <div className="xl:col-span-4 min-w-0 flex flex-col gap-5">
                    <AnalyticsProfitWidget data={effectiveData} loading={effectiveLoading} />
                    <ProfitTrendChart chartData={effectiveData?.chart_data || []} loading={effectiveLoading} currency={effectiveData?.currency || "USD"} />
                </div>
            </section>

            {/* Top Campaigns - commented out for now */}
            {/* <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <TopCampaignsWidget
                    campaigns={campaigns.filter((c) => (selectedCampaigns.length ? selectedCampaigns.includes(c.id) : true))}
                    loading={dataLoading}
                    currency={effectiveData?.currency || "USD"}
                    limit={5}
                />
            </section> */}
        </div>
    );
}
