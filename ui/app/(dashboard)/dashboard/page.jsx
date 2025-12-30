/**
 * Dashboard Page - Metricx v3.0 Design
 *
 * WHAT: Main dashboard with centered hero, AI search, KPI cards, and chart
 * WHY: Clean, focused view of key metrics with soft, minimalistic design
 *
 * LAYOUT:
 *   1. Hero Header - Centered greeting with Live Updates badge
 *   2. AI Search Bar - Centered search to navigate to Copilot
 *   3. KPI Cards - 4-column grid (Revenue, Spend, ROAS, Orders)
 *   4. Performance Chart - Main metric visualization
 *
 * CHANGES (2025-12-30):
 *   - New centered layout design
 *   - Removed AI Insights and Revenue Bar modules
 *   - Default timeframe changed to 'today'
 *   - Added centered AI search bar component
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 */
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { currentUser } from "../../../lib/workspace";
import { fetchUnifiedDashboard } from "../../../lib/api";
import HeroHeader from "./components/HeroHeader";
import TimeframeSelector from "./components/TimeframeSelector";
import KpiCardsModule from "./components/KpiCardsModule";
import BlendedMetricsModule from "./components/BlendedMetricsModule";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('today'); // Default to today

  // Unified dashboard data - fetched in ONE request
  const [dashboardData, setDashboardData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);

  // Selected metric for the main chart (controlled by KPI cards)
  const [selectedMetric, setSelectedMetric] = useState('revenue');

  // AI Search state
  const [searchQuery, setSearchQuery] = useState('');

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

  // Handle AI search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    const params = new URLSearchParams({
      q: searchQuery.trim(),
      ws: user.workspace_id
    });
    router.push(`/copilot?${params.toString()}`);
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-neutral-500 text-sm">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  // Not signed in
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="card-soft rounded-[32px] p-8 max-w-md text-center">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">You must be signed in.</h2>
          <a href="/sign-in" className="text-neutral-600 hover:text-neutral-900 underline">
            Go to sign in
          </a>
        </div>
      </div>
    );
  }

  // Show skeleton while data is loading
  const showSkeleton = dataLoading || !dashboardData;

  return (
    <div className="pb-8">
      {/* Hero Header - Centered */}
      <HeroHeader
        user={user}
        lastSyncedAt={dashboardData?.last_synced_at}
        actions={<TimeframeSelector value={timeframe} onChange={setTimeframe} />}
      />

      {/* AI Search Bar - Centered */}
      <div className="max-w-xl mx-auto mb-20">
        <form onSubmit={handleSearchSubmit} className="relative search-glow">
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Ask AI anything about your metrics..." 
            className="w-full pl-6 pr-16 py-4 bg-white/80 backdrop-blur-xl rounded-[20px] border border-white/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)] text-base text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-200/50 transition-all duration-300 text-center"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <button 
              type="submit"
              className="w-10 h-10 rounded-xl bg-neutral-900 flex items-center justify-center hover:scale-105 transition-transform duration-300"
            >
              <ArrowRight className="w-4 h-4 text-white" />
            </button>
          </div>
        </form>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 max-w-4xl mx-auto">
          Failed to load dashboard: {error}
        </div>
      )}

      {/* KPI Cards - 4 Column Grid */}
      <KpiCardsModule
        data={dashboardData}
        loading={showSkeleton}
        selectedMetric={selectedMetric}
        onMetricClick={setSelectedMetric}
      />

      {/* Performance Chart */}
      <BlendedMetricsModule
        data={dashboardData}
        loading={showSkeleton}
        timeframe={timeframe}
        selectedMetric={selectedMetric}
        onMetricChange={setSelectedMetric}
      />
    </div>
  );
}
