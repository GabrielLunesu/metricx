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
import Link from "next/link";
import { Search, ArrowRight, Zap, X } from "lucide-react";
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

  // Connect banner dismissal state
  const [showConnectBanner, setShowConnectBanner] = useState(true);

  // Check localStorage for dismissed banner on mount
  useEffect(() => {
    const dismissed = localStorage.getItem('dismissedConnectBanner');
    if (dismissed === 'true') {
      setShowConnectBanner(false);
    }
  }, []);

  // Handle dismiss banner
  const handleDismissConnectBanner = () => {
    localStorage.setItem('dismissedConnectBanner', 'true');
    setShowConnectBanner(false);
  };

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
    <div className="pb-16 md:pb-8">
      {/* Hero Header - Centered */}
      <HeroHeader
        user={user}
        lastSyncedAt={dashboardData?.last_synced_at}
        actions={<TimeframeSelector value={timeframe} onChange={setTimeframe} />}
      />

      {/* AI Search Bar - Centered */}
      <div className="max-w-lg mx-auto mb-8 md:mb-16 px-4 md:px-0">
        <form onSubmit={handleSearchSubmit} className="relative group">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
            <Search className="w-4 h-4 text-neutral-400" />
          </div>
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Ask Copilot anything..." 
            className="w-full pl-11 pr-24 py-3.5 bg-white/70 hover:bg-white/90 focus:bg-white rounded-2xl border border-neutral-200/60 hover:border-neutral-300/60 focus:border-neutral-300 shadow-sm hover:shadow-md focus:shadow-md text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all duration-200"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-neutral-100/80 rounded text-[10px] font-medium text-neutral-400 border border-neutral-200/60">
              <span>⌘</span>K
            </kbd>
            <button 
              type="submit"
              className="w-8 h-8 rounded-lg bg-neutral-900 flex items-center justify-center hover:bg-neutral-800 transition-colors duration-150"
            >
              <ArrowRight className="w-3.5 h-3.5 text-white" />
            </button>
          </div>
        </form>
      </div>

      {/* Connect Ad Accounts Banner - shows when no connections and not dismissed */}
      {!showSkeleton && showConnectBanner && 
       (!dashboardData?.connected_platforms || dashboardData.connected_platforms.length === 0) && (
        <div className="max-w-2xl mx-auto mb-8 p-5 bg-gradient-to-r from-indigo-50 to-cyan-50 rounded-2xl border border-indigo-100/60 relative">
          <button
            onClick={handleDismissConnectBanner}
            className="absolute top-3 right-3 p-1 text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
          <div className="flex items-start gap-4 pr-6">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0">
              <Zap className="w-5 h-5 text-indigo-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-slate-900 mb-1">Connect your ad accounts</h3>
              <p className="text-sm text-slate-600 mb-3">
                Start tracking your advertising performance by connecting Meta Ads or Google Ads.
              </p>
              <Link 
                href="/settings?tab=connections" 
                className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
              >
                Go to Settings → Connections
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}

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
