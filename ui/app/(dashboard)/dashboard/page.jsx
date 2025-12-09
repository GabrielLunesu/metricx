/**
 * Dashboard Page - Primary ad analytics view.
 *
 * WHAT: Main dashboard showing ad performance metrics, charts, and insights
 * WHY: Users need a single place to see how their ads are performing
 *
 * PERFORMANCE OPTIMIZATION (v2):
 *   - Uses unified dashboard endpoint (1 request instead of 8+)
 *   - AI insights use dashboard data directly (no separate API calls)
 *   - Data is fetched once and passed to child components
 *
 * CONDITIONAL RENDERING:
 *   - Attribution section only shows if Shopify is connected (has_shopify)
 *   - KPI source indicators show connected platforms dynamically
 *
 * REFERENCES:
 *   - docs/PERFORMANCE_INVESTIGATION.md
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - Strategic vision: Ad Analytics First, Attribution Second
 */
"use client";
import { useEffect, useState } from "react";
import { currentUser } from "../../../lib/auth";
import { fetchUnifiedDashboard } from "../../../lib/api";
import HeroHeader from "./components/HeroHeader";
import KpiStripUnified from "./components/KpiStripUnified";
import MoneyPulseChartUnified from "./components/MoneyPulseChartUnified";
import TopCreativeUnified from "./components/TopCreativeUnified";
import SpendMixUnified from "./components/SpendMixUnified";
import AttributionCardUnified from "./components/AttributionCardUnified";
import LiveAttributionFeedUnified from "./components/LiveAttributionFeedUnified";
// import UnitEconomicsTable from "./components/UnitEconomicsTable";
import TimeframeSelector from "./components/TimeframeSelector";
import AiInsightsPanel from "./components/AiInsightsPanel";

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('last_7_days');

  // Unified dashboard data - fetched in ONE request
  const [dashboardData, setDashboardData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch user on mount
  useEffect(() => {
    let mounted = true;
    currentUser()
      .then((u) => {
        if (mounted) setUser(u);
      })
      .catch((err) => {
        console.error("Failed to get user:", err);
        if (mounted) setUser(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, []);

  // Fetch unified dashboard data when user/timeframe changes
  useEffect(() => {
    if (!user?.workspace_id) return;

    let mounted = true;
    setDataLoading(true);
    setError(null);

    fetchUnifiedDashboard({
      workspaceId: user.workspace_id,
      timeframe
    })
      .then((data) => {
        if (mounted) {
          setDashboardData(data);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch dashboard:", err);
        if (mounted) setError(err.message);
      })
      .finally(() => {
        if (mounted) setDataLoading(false);
      });

    return () => { mounted = false; };
  }, [user?.workspace_id, timeframe]);

  if (loading) {
    return <div className="p-6 text-slate-500">Loading dashboard...</div>;
  }

  if (!user) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto glass-panel rounded-3xl p-6">
          <h2 className="text-xl font-medium mb-2 text-slate-900">You must be signed in.</h2>
          <a href="/login" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  // Show skeleton while data is loading
  const showSkeleton = dataLoading || !dashboardData;

  return (
    <div>
      {/* Hero Header */}
      <HeroHeader
        user={user}
        actions={<TimeframeSelector value={timeframe} onChange={setTimeframe} />}
        lastSyncedAt={dashboardData?.last_synced_at}
      />

      {/* Error Banner */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          Failed to load dashboard: {error}
        </div>
      )}

      {/* KPI Strip - uses unified data */}
      <div className="mt-8">
        <KpiStripUnified
          data={dashboardData}
          loading={showSkeleton}
        />
      </div>

      {/* Middle Section: Money Pulse & AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <MoneyPulseChartUnified
          data={dashboardData}
          loading={showSkeleton}
          timeframe={timeframe}
        />
        {/* AI Insights - uses dashboard data directly (no API calls) */}
        <AiInsightsPanel data={dashboardData} loading={showSkeleton} workspaceId={user?.workspace_id} />
      </div>

      {/* Attribution Section - Only show if Shopify is connected */}
      {dashboardData?.has_shopify && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8">
          <AttributionCardUnified
            data={dashboardData}
            loading={showSkeleton}
          />
          <LiveAttributionFeedUnified
            data={dashboardData}
            loading={showSkeleton}
          />
        </div>
      )}

      {/* Bottom Section: Top Ads & Platform Mix */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-8 pb-8">
        <TopCreativeUnified
          data={dashboardData}
          loading={showSkeleton}
        />
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-slate-800 tracking-tight">Platform Spend Mix</h3>
          </div>
          <SpendMixUnified
            data={dashboardData}
            loading={showSkeleton}
          />
          {/* <UnitEconomicsTable workspaceId={user.workspace_id} timeframe={timeframe} /> */}
        </div>
      </div>
    </div>
  );
}
