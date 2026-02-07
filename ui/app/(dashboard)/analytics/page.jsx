/**
 * Analytics Page v3.0 - Redesigned Performance Dashboard
 * ======================================================
 *
 * WHAT: Clean, minimalistic analytics page with new design system
 * WHY: Improved UX with clearer data hierarchy and better filtering
 *
 * LAYOUT:
 *   - Sticky glass header: Title, platform filter, date picker, compare toggle
 *   - 8 KPI cards: Horizontal responsive grid
 *   - Chart section: Metric tabs + area chart with compare overlay
 *   - Campaign table: Multi-select, expandable Meta ad sets, export
 *
 * FILTERING:
 *   - Platform: All / Meta / Google (header dropdown)
 *   - Date range: Presets + custom (header picker)
 *   - Campaigns: Multi-select from table (click rows)
 *   - Compare: Toggle for previous period overlay
 *
 * DATA FLOW:
 *   - Header filters → all data endpoints
 *   - Campaign selection → KPIs + chart filtered
 *   - Ad Set expansion → fetch children from API
 */
"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { subDays, startOfDay, endOfDay, format, differenceInCalendarDays } from "date-fns";
import { currentUser } from "@/lib/workspace";
import {
  fetchUnifiedDashboard,
  fetchAnalyticsChart,
  fetchEntityChildren,
  fetchEntityPerformance,
  fetchConnections,
} from "@/lib/api";

// New Components
import AnalyticsHeader from "./components/AnalyticsHeader";
import AnalyticsKpiGrid from "./components/AnalyticsKpiGrid";
import AnalyticsChart from "./components/AnalyticsChart";
import AnalyticsCampaignTable from "./components/AnalyticsCampaignTable";

// ============================================
// HELPERS
// ============================================

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

/**
 * Aggregate chart series data to flat array for chart component
 */
function aggregateSeriesToChartData(series = []) {
  const byDate = new Map();
  for (const s of series || []) {
    for (const p of s.data || []) {
      const existing = byDate.get(p.date) || {
        date: p.date,
        revenue: 0,
        spend: 0,
        conversions: 0,
        roas: 0,
      };
      existing.revenue += Number(p.revenue || 0);
      existing.spend += Number(p.spend || 0);
      existing.conversions += Number(p.conversions || 0);
      byDate.set(p.date, existing);
    }
  }

  // Calculate ROAS for aggregated data
  const result = Array.from(byDate.values())
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .map((d) => ({
      ...d,
      roas: d.spend > 0 ? d.revenue / d.spend : 0,
    }));

  return result;
}

/**
 * Compute KPIs from campaign data when filtered
 */
function computeKpisFromCampaigns(campaigns = [], selectedIds = []) {
  const filtered = selectedIds.length > 0
    ? campaigns.filter((c) => selectedIds.includes(c.id))
    : campaigns;

  if (filtered.length === 0) return null;

  let spend = 0;
  let revenue = 0;
  let conversions = 0;
  let clicks = 0;
  let impressions = 0;

  for (const row of filtered) {
    spend += Number(row.spend || 0);
    revenue += Number(row.revenue || 0);
    conversions += Number(row.conversions || 0);

    // Estimate clicks/impressions from CPC and CTR if available
    const rowCpc = Number(row.cpc || 0);
    const rowCtrPct = Number(row.ctr_pct || 0);
    const rowClicks = rowCpc > 0 ? Number(row.spend || 0) / rowCpc : 0;
    const rowImpressions = rowCtrPct > 0 ? rowClicks / (rowCtrPct / 100) : 0;
    clicks += rowClicks;
    impressions += rowImpressions;
  }

  return {
    spend,
    revenue,
    conversions,
    roas: spend > 0 ? revenue / spend : 0,
    cpc: clicks > 0 ? spend / clicks : null,
    ctr: impressions > 0 ? (clicks / impressions) * 100 : null,
    aov: null, // AOV requires Shopify data
    // Deltas would require previous period data
  };
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

export default function AnalyticsPage() {
  // User & workspace
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [loading, setLoading] = useState(true);

  // Data loading states
  const [dashboardData, setDashboardData] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  // Chart data
  const [chartData, setChartData] = useState({ series: [], totals: {}, metadata: {} });
  const [chartLoading, setChartLoading] = useState(false);

  // Compare data
  const [compareChartData, setCompareChartData] = useState(null);
  const [compareChartLoading, setCompareChartLoading] = useState(false);

  // Campaigns list
  const [campaigns, setCampaigns] = useState([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignPage, setCampaignPage] = useState(1);
  const [campaignTotal, setCampaignTotal] = useState(0);

  // Ad Sets (for expanded Meta campaigns)
  const [adSetsMap, setAdSetsMap] = useState({});
  const [expandedCampaignId, setExpandedCampaignId] = useState(null);
  const [adSetsLoading, setAdSetsLoading] = useState(false);

  // Connected platforms
  const [connectedPlatforms, setConnectedPlatforms] = useState([]);

  // ============================================
  // GLOBAL FILTERS
  // ============================================

  // Date range
  const [preset, setPreset] = useState("last_30_days");
  const [dateRange, setDateRange] = useState(() => ({
    from: startOfDay(subDays(new Date(), 29)),
    to: endOfDay(new Date()),
  }));

  // Platform filter
  const [selectedPlatform, setSelectedPlatform] = useState(null);

  // Campaign selection (multi-select)
  const [selectedCampaignIds, setSelectedCampaignIds] = useState([]);

  // Compare mode
  const [compareEnabled, setCompareEnabled] = useState(false);

  // Chart metric
  const [selectedMetric, setSelectedMetric] = useState("revenue");

  // ============================================
  // COMPUTED VALUES
  // ============================================

  // API params based on date selection
  const apiParams = useMemo(() => {
    if (preset && preset !== "custom") {
      return { timeframe: preset, startDate: null, endDate: null };
    }
    if (dateRange?.from && dateRange?.to) {
      return {
        timeframe: "custom",
        startDate: format(dateRange.from, "yyyy-MM-dd"),
        endDate: format(dateRange.to, "yyyy-MM-dd"),
      };
    }
    return { timeframe: "last_30_days", startDate: null, endDate: null };
  }, [preset, dateRange]);

  // Entity time range for campaign fetching
  const entityTimeRange = useMemo(() => {
    if (!dateRange?.from || !dateRange?.to) return { last_n_days: 30 };
    return {
      start: toDateString(dateRange.from),
      end: toDateString(dateRange.to),
    };
  }, [dateRange]);

  // Chart groupBy based on filters
  const chartGroupBy = useMemo(() => {
    if (selectedCampaignIds.length > 0) return "campaign";
    if (selectedPlatform) return "platform";
    return "total";
  }, [selectedPlatform, selectedCampaignIds]);

  // KPI data - use dashboard data when no campaigns selected, otherwise compute from campaigns
  const kpiData = useMemo(() => {
    if (selectedCampaignIds.length > 0) {
      return computeKpisFromCampaigns(campaigns, selectedCampaignIds);
    }

    if (!dashboardData) return null;

    // Extract KPIs from dashboard data
    const kpis = dashboardData.kpis || [];
    const findKpi = (key) => kpis.find((k) => k.key === key);

    return {
      revenue: findKpi("revenue")?.value ?? dashboardData.revenue ?? null,
      spend: findKpi("spend")?.value ?? dashboardData.spend ?? null,
      roas: findKpi("roas")?.value ?? dashboardData.roas ?? null,
      conversions: findKpi("conversions")?.value ?? dashboardData.conversions ?? null,
      cpc: findKpi("cpc")?.value ?? dashboardData.cpc ?? null,
      ctr: findKpi("ctr")?.value ?? dashboardData.ctr ?? null,
      aov: dashboardData.aov ?? null,
      // Deltas
      delta_revenue: findKpi("revenue")?.delta_pct ?? null,
      delta_spend: findKpi("spend")?.delta_pct ?? null,
      delta_roas: findKpi("roas")?.delta_pct ?? null,
      delta_conversions: findKpi("conversions")?.delta_pct ?? null,
      delta_cpc: findKpi("cpc")?.delta_pct ?? null,
      delta_ctr: findKpi("ctr")?.delta_pct ?? null,
    };
  }, [dashboardData, campaigns, selectedCampaignIds]);

  // Chart data for display
  const displayChartData = useMemo(() => {
    return aggregateSeriesToChartData(chartData?.series || []);
  }, [chartData]);

  // Compare chart data for display
  const displayCompareData = useMemo(() => {
    if (!compareEnabled || !compareChartData) return null;
    return aggregateSeriesToChartData(compareChartData?.series || []);
  }, [compareEnabled, compareChartData]);

  // Currency from dashboard
  const currency = dashboardData?.currency || "USD";

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
    return () => {
      mounted = false;
    };
  }, []);

  // Fetch connected platforms
  useEffect(() => {
    if (!workspaceId) return;

    fetchConnections({ workspaceId, status: "active" })
      .then((res) => {
        const providers = [
          ...new Set(
            (res?.connections || []).map((c) => c.provider?.toLowerCase())
          ),
        ].filter(Boolean);
        setConnectedPlatforms(providers);
      })
      .catch((err) => console.error("Failed to fetch connections:", err));
  }, [workspaceId]);

  // Fetch dashboard data (KPIs)
  useEffect(() => {
    if (!workspaceId) return;

    setDashboardLoading(true);
    fetchUnifiedDashboard({
      workspaceId,
      timeframe: apiParams.timeframe,
      startDate: apiParams.startDate,
      endDate: apiParams.endDate,
      platform: selectedPlatform,
    })
      .then((data) => {
        setDashboardData(data);
        setDashboardLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch dashboard data:", err);
        setDashboardLoading(false);
      });
  }, [workspaceId, apiParams, selectedPlatform]);

  // Fetch campaigns
  useEffect(() => {
    if (!workspaceId) return;

    setCampaignsLoading(true);
    fetchEntityPerformance({
      workspaceId,
      entityType: "campaign",
      timeRange: entityTimeRange,
      provider: selectedPlatform,
      limit: 25,
      offset: (campaignPage - 1) * 25,
      sortBy: "spend",
      sortDir: "desc",
      status: "all",
    })
      .then((res) => {
        setCampaigns(res?.items || []);
        setCampaignTotal(res?.total || 0);
        setCampaignsLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch campaigns:", err);
        setCampaignsLoading(false);
      });
  }, [workspaceId, entityTimeRange, selectedPlatform, campaignPage]);

  // Fetch chart data
  const fetchChart = useCallback(async () => {
    if (!workspaceId) return;

    setChartLoading(true);
    try {
      const data = await fetchAnalyticsChart({
        workspaceId,
        timeframe: apiParams.timeframe,
        startDate: apiParams.startDate,
        endDate: apiParams.endDate,
        platforms: selectedPlatform ? [selectedPlatform] : null,
        campaignIds: selectedCampaignIds.length > 0 ? selectedCampaignIds : null,
        groupBy: chartGroupBy,
      });
      setChartData(data);
    } catch (err) {
      console.error("Failed to fetch chart data:", err);
      setChartData({ series: [], totals: {}, metadata: {} });
    } finally {
      setChartLoading(false);
    }
  }, [workspaceId, apiParams, selectedPlatform, selectedCampaignIds, chartGroupBy]);

  useEffect(() => {
    fetchChart();
  }, [fetchChart]);

  // Fetch compare data when enabled
  useEffect(() => {
    if (!workspaceId || !compareEnabled) {
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
      campaignIds: selectedCampaignIds.length > 0 ? selectedCampaignIds : null,
      groupBy: chartGroupBy,
    })
      .then((data) => setCompareChartData(data))
      .catch((err) => {
        console.error("Failed to fetch compare data:", err);
        setCompareChartData(null);
      })
      .finally(() => setCompareChartLoading(false));
  }, [workspaceId, compareEnabled, dateRange, selectedPlatform, selectedCampaignIds, chartGroupBy]);

  // Fetch ad sets when campaign is expanded
  const handleExpandCampaign = useCallback(
    async (campaignId) => {
      setExpandedCampaignId(campaignId);

      if (!campaignId || adSetsMap[campaignId]) return;

      setAdSetsLoading(true);
      try {
        const res = await fetchEntityChildren({
          entityId: campaignId,
          timeRange: entityTimeRange,
          provider: "meta",
          limit: 50,
          sortBy: "spend",
          sortDir: "desc",
          status: "all",
        });
        setAdSetsMap((prev) => ({
          ...prev,
          [campaignId]: res?.items || [],
        }));
      } catch (err) {
        console.error("Failed to fetch ad sets:", err);
        setAdSetsMap((prev) => ({
          ...prev,
          [campaignId]: [],
        }));
      } finally {
        setAdSetsLoading(false);
      }
    },
    [entityTimeRange, adSetsMap]
  );

  // ============================================
  // EVENT HANDLERS
  // ============================================

  const handlePlatformChange = (platform) => {
    setSelectedPlatform(platform);
    setSelectedCampaignIds([]);
    setCampaignPage(1);
  };

  const handleClearCampaigns = () => {
    setSelectedCampaignIds([]);
  };

  const handleExport = () => {
    // Build CSV from KPIs + campaign data
    const rows = [];

    // KPI row
    if (kpiData) {
      rows.push([
        "KPI Summary",
        `Revenue: ${kpiData.revenue}`,
        `Spend: ${kpiData.spend}`,
        `ROAS: ${kpiData.roas?.toFixed(2)}x`,
        `Conversions: ${kpiData.conversions}`,
      ].join(","));
      rows.push("");
    }

    // Campaign headers
    rows.push(
      ["Campaign", "Platform", "Status", "Spend", "Revenue", "ROAS", "Conversions", "CPA"].join(",")
    );

    // Campaign rows
    const exportCampaigns = selectedCampaignIds.length > 0
      ? campaigns.filter((c) => selectedCampaignIds.includes(c.id))
      : campaigns;

    for (const c of exportCampaigns) {
      const cpa = c.conversions > 0 ? (c.spend / c.conversions).toFixed(2) : "-";
      rows.push(
        [
          `"${c.name}"`,
          c.platform || c.provider || "",
          c.status || "",
          c.spend?.toFixed(2) || "0",
          c.revenue?.toFixed(2) || "0",
          c.roas?.toFixed(2) || "0",
          c.conversions || "0",
          cpa,
        ].join(",")
      );
    }

    // Download CSV
    const csv = rows.join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analytics-export-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ============================================
  // RENDER
  // ============================================

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          <span className="text-neutral-500 text-sm">Loading analytics...</span>
        </div>
      </div>
    );
  }

  // Not signed in
  if (!user) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">
            You must be signed in.
          </h2>
          <a
            href="/sign-in"
            className="text-neutral-600 hover:text-neutral-900 underline"
          >
            Go to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Sticky Header */}
      <AnalyticsHeader
        selectedPlatform={selectedPlatform}
        onPlatformChange={handlePlatformChange}
        connectedPlatforms={connectedPlatforms}
        preset={preset}
        onPresetChange={setPreset}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        compareEnabled={compareEnabled}
        onCompareToggle={() => setCompareEnabled((v) => !v)}
        selectedCampaigns={selectedCampaignIds}
        onClearCampaigns={handleClearCampaigns}
        onExport={handleExport}
        loading={dashboardLoading || chartLoading}
      />

      {/* Main Content */}
      <main className="space-y-4 md:space-y-6 pb-16 md:pb-0">
        {/* KPI Grid */}
        <AnalyticsKpiGrid
          data={kpiData}
          loading={dashboardLoading}
          currency={currency}
        />

        {/* Chart Section */}
        <div className="bg-white border border-neutral-200 rounded-xl p-3 md:p-4">
          <AnalyticsChart
            data={displayChartData}
            compareData={displayCompareData}
            selectedMetric={selectedMetric}
            onMetricChange={setSelectedMetric}
            compareEnabled={compareEnabled}
            loading={chartLoading || compareChartLoading}
            currency={currency}
          />
        </div>

        {/* Campaign Table */}
        <AnalyticsCampaignTable
          campaigns={campaigns}
          selectedIds={selectedCampaignIds}
          onSelectionChange={setSelectedCampaignIds}
          loading={campaignsLoading}
          currency={currency}
          page={campaignPage}
          pageSize={25}
          total={campaignTotal}
          onPageChange={setCampaignPage}
          adSetsMap={adSetsMap}
          onExpandCampaign={handleExpandCampaign}
          expandedCampaignId={expandedCampaignId}
          adSetsLoading={adSetsLoading}
          onExport={handleExport}
        />
      </main>
    </>
  );
}
