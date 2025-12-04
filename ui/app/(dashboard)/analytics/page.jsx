/**
 * Analytics Page - Deep dive into ad performance data.
 *
 * WHAT: Advanced analytics with graphs, intelligence zone, and drill-down capabilities
 * WHY: Users need detailed analysis tools beyond the dashboard summary
 *
 * FEATURES:
 *   - KPI strip with key metrics
 *   - Graph engine for visualizations
 *   - Intelligence zone for AI insights
 *   - Attribution unlock widget (shows when Shopify is connected)
 *
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - /analytics/attribution page (accessible via widget when Shopify connected)
 */
"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Target, ChevronRight, Lock } from "lucide-react";
import { currentUser } from "@/lib/auth";

// New Components
import AnalyticsHeader from "./components/AnalyticsHeader";
import AnalyticsKpiStrip from "./components/AnalyticsKpiStrip";
import AnalyticsGraphEngine from "./components/AnalyticsGraphEngine";
import AnalyticsIntelligenceZone from "./components/AnalyticsIntelligenceZone";
import AnalyticsCustomDashboards from "./components/AnalyticsCustomDashboards";
import AnalyticsDrillDown from "./components/AnalyticsDrillDown";
import FilterModal from './components/FilterModal';
import { fetchWorkspaceKpis, fetchWorkspaceProviders, fetchWorkspaceStatus } from '@/lib/api';

export default function AnalyticsPage() {
  // User & workspace
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);

  // Workspace status for conditional rendering (Attribution widget)
  // WHY: Only show Attribution unlock if Shopify is connected
  const [status, setStatus] = useState(null);

  // Top filter state
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('all'); // 'all', 'meta', 'google', 'tiktok', 'other'

  // Unified time filter state - single source of truth
  const [timeFilters, setTimeFilters] = useState({
    type: 'preset',      // 'preset' | 'custom'
    preset: '30d',       // '7d' | '30d' | null
    customStart: null,   // YYYY-MM-DD string or null
    customEnd: null,     // YYYY-MM-DD string or null
    rangeDays: 30        // number (for calculations and backwards compat)
  });

  // Filter state
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);

  // Loading state
  const [loading, setLoading] = useState(true);

  // Fetch user and workspace ID on mount
  useEffect(() => {
    let mounted = true;
    currentUser()
      .then((u) => {
        if (!mounted) return;
        setUser(u);
        setWorkspaceId(u?.workspace_id);
        setLoading(false);

        // Fetch workspace status for conditional UI (Attribution widget)
        if (u?.workspace_id) {
          fetchWorkspaceStatus({ workspaceId: u.workspace_id })
            .then((s) => {
              if (mounted) setStatus(s);
            })
            .catch((err) => {
              console.error("Failed to fetch workspace status:", err);
              // Don't block analytics if status fetch fails
            });
        }
      })
      .catch((err) => {
        console.error("Failed to get user:", err);
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
      });

    // Fetch providers
    if (workspaceId) {
      fetchWorkspaceProviders({ workspaceId })
        .then(data => {
          if (mounted) setProviders(data.providers || []);
        })
        .catch(err => console.error("Failed to fetch providers:", err));
    }

    return () => {
      mounted = false;
    };
  }, [workspaceId]);

  // Handlers
  const handleProviderChange = (provider) => {
    setSelectedProvider(provider);
  };

  /**
   * Unified time filter handler
   * Replaces separate handleTimeframeChange and handleCustomDateApply
   */
  const handleTimeFilterChange = (newFilters) => {
    setTimeFilters(newFilters);
  };

  if (loading) {
    return (
      <div className="p-12 text-center min-h-screen flex items-center justify-center aurora-container">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-12 text-center min-h-screen flex items-center justify-center aurora-container">
        <div className="glass-panel rounded-3xl p-6 max-w-md mx-auto">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">You must be signed in.</h2>
          <a href="/login" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  return (
    <div className=" min-h-screen relative overflow-hidden text-slate-800  antialiased selection:bg-cyan-200 selection:text-cyan-900">

      {/* Ambient Parallax Layers */}
      <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="blob-1 absolute top-[-10%] left-[10%] w-[60vw] h-[60vw] animate-pulse-slow rounded-full blur-3xl opacity-60"></div>
        <div className="blob-2 absolute bottom-[-10%] right-[0%] w-[50vw] h-[50vw] animate-pulse-slow rounded-full blur-3xl opacity-50" style={{ animationDelay: '-4s' }}></div>
        <div className="blob-3 absolute top-[40%] left-[30%] w-[40vw] h-[40vw] animate-pulse-slow rounded-full blur-3xl opacity-40" style={{ animationDelay: '-8s' }}></div>
      </div>

      <div className="w-full px-3 md:px-6 space-y-6">

        {/* Header */}
        <AnalyticsHeader
          workspaceId={workspaceId}
          selectedProvider={selectedProvider}
          onProviderChange={setSelectedProvider}
          timeFilters={timeFilters}
          onTimeFilterChange={handleTimeFilterChange}
          selectedCampaign={selectedCampaign}
          onFilterClick={() => setIsFilterModalOpen(true)}
          onClearCampaign={() => setSelectedCampaign(null)}
          providers={providers}
        />

        {/* KPI Strip */}
        <AnalyticsKpiStrip
          workspaceId={workspaceId}
          selectedProvider={selectedProvider}
          timeFilters={timeFilters}
          campaignId={selectedCampaign?.id}
        />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Graph Engine */}
          <AnalyticsGraphEngine
            workspaceId={workspaceId}
            selectedProvider={selectedProvider}
            timeFilters={timeFilters}
            campaignId={selectedCampaign?.id}
          />

          {/* Intelligence Zone */}
          <AnalyticsIntelligenceZone
            workspaceId={workspaceId}
            selectedProvider={selectedProvider}
            timeFilters={timeFilters}
            campaignId={selectedCampaign?.id}
            campaignName={selectedCampaign?.name}
          />
        </div>

        {/* Attribution Unlock Widget */}
        {/* WHY: Attribution is a premium feature unlocked with Shopify connection.
            Shows clickable card when Shopify is connected, locked card when not.
            Reference: docs/living-docs/FRONTEND_REFACTOR_PLAN.md */}
        <div className="mt-6">
          {status?.has_shopify ? (
            <Link
              href="/analytics/attribution"
              className="block glass-panel p-5 rounded-2xl hover:ring-2 ring-cyan-200/50 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 shadow-lg shadow-cyan-500/20">
                    <Target className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-neutral-900 text-lg">Attribution Analytics</h3>
                    <p className="text-sm text-neutral-500">
                      See which channels and campaigns drive your verified revenue
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-6 h-6 text-neutral-400 group-hover:text-cyan-500 group-hover:translate-x-1 transition-all" />
              </div>
              {status?.attribution_ready && (
                <div className="mt-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs text-emerald-600 font-medium">Pixel active - receiving events</span>
                </div>
              )}
            </Link>
          ) : (
            <div className="glass-panel p-5 rounded-2xl opacity-70">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-neutral-200">
                    <Target className="w-6 h-6 text-neutral-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-neutral-500 text-lg">Attribution Analytics</h3>
                    <p className="text-sm text-neutral-400">
                      Connect Shopify to unlock verified revenue attribution
                    </p>
                  </div>
                </div>
                <Lock className="w-5 h-5 text-neutral-300" />
              </div>
              <div className="mt-3">
                <Link
                  href="/settings?tab=connections"
                  className="text-xs text-cyan-600 hover:text-cyan-700 font-medium"
                >
                  Connect Shopify →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Custom Dashboards (Removed for now) */}
        {/* <AnalyticsCustomDashboards
          workspaceId={workspaceId}
          selectedProvider={selectedProvider}
          rangeDays={rangeDays}
          customStartDate={customStartDate}
          customEndDate={customEndDate}
        /> */}

        {/* Drill Down Section */}
        <AnalyticsDrillDown
          workspaceId={workspaceId}
          selectedProvider={selectedProvider}
          timeFilters={timeFilters}
          selectedCampaign={selectedCampaign}
        />

      </div>

      {/* Filter Modal */}
      <FilterModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        onSelect={(campaign) => {
          setSelectedCampaign(campaign);
          setIsFilterModalOpen(false);
        }}
        workspaceId={workspaceId}
        selectedProvider={selectedProvider}
        selectedCampaignId={selectedCampaign?.id}
      />
    </div>
  );
}
