/**
 * Dashboard Page - 2x2 Grid Layout
 *
 * WHAT: Main dashboard with 4 glassmorphic modules in a 2x2 grid
 * WHY: Clean, focused view of key metrics with Apple-inspired design
 *
 * MODULES:
 *   1. Blended Metrics - Main chart with metric selector (Revenue, ROAS, Spend, Conversions)
 *   2. AI Insights - Data-driven actionable insights
 *   3. KPI Cards - 4 clickable metric cards that update the main chart
 *   4. Revenue Bar Chart - Last 7 days revenue visualization
 *
 * REFERENCES:
 *   - Design inspiration: Apple glassmorphism with blue tints
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 */
"use client";
import { useEffect, useState } from "react";
import { currentUser } from "../../../lib/workspace";
import { fetchUnifiedDashboard } from "../../../lib/api";
import HeroHeader from "./components/HeroHeader";
import TimeframeSelector from "./components/TimeframeSelector";
import BlendedMetricsModule from "./components/BlendedMetricsModule";
import AiInsightsModule from "./components/AiInsightsModule";
import KpiCardsModule from "./components/KpiCardsModule";
import RevenueBarModule from "./components/RevenueBarModule";

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('last_7_days');

  // Unified dashboard data - fetched in ONE request
  const [dashboardData, setDashboardData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);

  // Selected metric for the main chart (controlled by KPI cards)
  const [selectedMetric, setSelectedMetric] = useState('revenue');

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
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-slate-500 text-sm">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto glass-panel rounded-3xl p-6">
          <h2 className="text-xl font-medium mb-2 text-slate-900">You must be signed in.</h2>
          <a href="/sign-in" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  // Show skeleton while data is loading
  const showSkeleton = dataLoading || !dashboardData;

  return (
    <div className="pb-8">
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

      {/* 2x2 Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-8">
        {/* Module 1: KPI Cards - Performance Overview (Top Left) */}
        <KpiCardsModule
          data={dashboardData}
          loading={showSkeleton}
          selectedMetric={selectedMetric}
          onMetricClick={setSelectedMetric}
        />

        {/* Module 2: Blended Metrics Chart (Top Right) */}
        <BlendedMetricsModule
          data={dashboardData}
          loading={showSkeleton}
          timeframe={timeframe}
          selectedMetric={selectedMetric}
          onMetricChange={setSelectedMetric}
        />

        {/* Module 3: AI Insights (Bottom Left) */}
        <AiInsightsModule
          data={dashboardData}
          loading={showSkeleton}
          workspaceId={user?.workspace_id}
        />

        {/* Module 4: Revenue Bar Chart (Bottom Right) */}
        <RevenueBarModule
          workspaceId={user?.workspace_id}
          loading={showSkeleton}
        />
      </div>
    </div>
  );
}
