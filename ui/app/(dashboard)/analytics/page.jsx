"use client";
import { useState, useEffect } from "react";
import { currentUser } from "@/lib/auth";

// New Components
import AnalyticsHeader from "./components/AnalyticsHeader";
import AnalyticsKpiStrip from "./components/AnalyticsKpiStrip";
import AnalyticsGraphEngine from "./components/AnalyticsGraphEngine";
import AnalyticsIntelligenceZone from "./components/AnalyticsIntelligenceZone";
import AnalyticsCustomDashboards from "./components/AnalyticsCustomDashboards";
import AnalyticsDrillDown from "./components/AnalyticsDrillDown";
import FilterModal from './components/FilterModal';
import { fetchWorkspaceKpis, fetchWorkspaceProviders } from '@/lib/api';

export default function AnalyticsPage() {
  // User & workspace
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);

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
