/**
 * Campaigns Page v2.0 - Campaign Performance Overview
 * ====================================================
 *
 * WHAT: Lists all campaigns with performance metrics and detail modal
 * WHY: Server-side queries, dumb UI - follows analytics page pattern
 *
 * ARCHITECTURE:
 *   - All data fetching via fetchEntityPerformance
 *   - Campaign detail shown in modal (replaces /campaigns/[id] pages)
 *   - StatusBadge shows ACTIVE, PAUSED, LEARNING states
 *   - Creatives shown for Meta campaigns only
 *
 * DATA FLOW:
 *   1. Page fetches campaign list from backend
 *   2. Click on campaign opens CampaignDetailModal
 *   3. Modal fetches adsets/creatives as children
 *   4. All calculations done server-side
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/analytics/page.jsx (pattern to follow)
 *   - ui/components/campaigns/CampaignDetailModal.jsx
 *   - backend/app/routers/entity_performance.py
 */
"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { ArrowDownUp, Layers } from "lucide-react";
import { currentUser } from "@/lib/workspace";
import { fetchEntityPerformance, fetchWorkspaceProviders } from "@/lib/api";

// Components
import CampaignDetailModal from "@/components/campaigns/CampaignDetailModal";
import StatusBadge, { StatusDot, normalizeStatus } from "@/components/campaigns/StatusBadge";
import PlatformBadge from "@/components/campaigns/PlatformBadge";
import TrendSparkline from "@/components/campaigns/TrendSparkline";
import { formatMetricValue } from "@/lib/utils";

/**
 * CampaignRow - Single campaign row with click-to-open modal.
 */
function CampaignRow({ campaign, onRowClick, selected }) {
  const { name, platform, status, trend, display } = campaign;
  const normalizedStatus = normalizeStatus(status);
  const isLearning = normalizedStatus === "learning";
  const isPaused = normalizedStatus === "paused";
  const isArchived = normalizedStatus === "archived";
  const dimmed = isPaused || isArchived;

  return (
    <div
      onClick={() => onRowClick(campaign)}
      className={`
        group grid grid-cols-[40px_minmax(0,3fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.8fr)]
        gap-4 items-center px-6 py-4 cursor-pointer transition-all duration-200
        ${selected ? "bg-cyan-50/40" : "hover:bg-slate-50/80"}
        ${dimmed ? "opacity-70 hover:opacity-100" : ""}
        hover:shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] relative z-0 hover:z-10
      `}
    >
      {/* Checkbox placeholder */}
      <div className="flex items-center">
        <input
          type="checkbox"
          className="custom-checkbox cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Campaign name + platform icon */}
      <div className="flex items-center gap-3 min-w-0">
        <PlatformBadge platform={platform} size="md" iconOnly className="flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className={`text-sm font-semibold truncate ${dimmed ? "text-slate-500 line-through decoration-slate-300" : "text-slate-800"}`}>
              {name}
            </p>
            {campaign.kindLabel && (
              <span className="px-2 py-0.5 text-[10px] uppercase tracking-wide rounded-full bg-cyan-500/10 text-cyan-600 border border-cyan-500/30 flex-shrink-0">
                {campaign.kindLabel}
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5 truncate group-hover:text-cyan-600 transition-colors">
            {display?.subtitle || "—"}
          </p>
        </div>
      </div>

      {/* Platform badge */}
      <div>
        <PlatformBadge platform={platform} />
      </div>

      {/* Status */}
      <div>
        <StatusBadge status={status} showDot={isLearning} showIcon={!isLearning} />
      </div>

      {/* Spend */}
      <div className="text-right tabular-nums text-sm text-slate-600">
        {display?.spend || "—"}
      </div>

      {/* Revenue */}
      <div className="text-right tabular-nums text-sm font-semibold text-slate-800">
        {display?.revenue || "—"}
      </div>

      {/* ROAS */}
      <div className="text-right">
        {campaign.roasRaw != null ? (
          <span className={`text-sm font-bold px-2 py-0.5 rounded ${
            campaign.roasRaw >= 3 ? "text-emerald-600 bg-emerald-50/50" :
            campaign.roasRaw >= 1 ? "text-amber-600 bg-amber-50/50" :
            "text-red-600 bg-red-50/50"
          }`}>
            {display?.roas}
          </span>
        ) : (
          <span className="text-sm text-slate-400">—</span>
        )}
      </div>

      {/* Trend sparkline */}
      <div className="flex items-center justify-end">
        <TrendSparkline data={trend?.map((p) => p.value) || []} />
      </div>
    </div>
  );
}

/**
 * CampaignTableHeader - Column headers for the campaign table.
 */
function CampaignTableHeader() {
  return (
    <div className="grid grid-cols-[40px_minmax(0,3fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.8fr)] gap-4 px-6 py-3 text-[10px] uppercase tracking-wider font-semibold text-slate-400 border-b border-slate-100 bg-slate-50/50">
      <div></div>
      <div>Campaign</div>
      <div>Platform</div>
      <div>Status</div>
      <div className="text-right">Spend</div>
      <div className="text-right">Revenue</div>
      <div className="text-right">ROAS</div>
      <div className="text-right">Trend</div>
    </div>
  );
}

/**
 * SummaryStrip - Shows aggregate stats (active count, total spend, avg ROAS).
 */
function SummaryStrip({ campaigns }) {
  const summary = useMemo(() => {
    if (!campaigns || campaigns.length === 0) return null;

    const activeCount = campaigns.filter((c) => normalizeStatus(c.status) === "active").length;
    const totalSpend = campaigns.reduce((sum, c) => sum + (c.spendRaw || 0), 0);
    const totalRevenue = campaigns.reduce((sum, c) => sum + (c.revenueRaw || 0), 0);
    const avgRoas = totalSpend > 0 ? totalRevenue / totalSpend : null;

    return {
      activeCount,
      totalSpend: formatMetricValue(totalSpend, "currency"),
      avgRoas: avgRoas != null ? `${avgRoas.toFixed(1)}x` : "—",
    };
  }, [campaigns]);

  if (!summary) return null;

  return (
    <div className="flex items-center gap-6 text-xs px-4 py-2 bg-white/60 border border-white/70 rounded-full backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Active</span>
        <span className="font-semibold text-slate-700">{summary.activeCount}</span>
      </div>
      <div className="w-px h-3 bg-slate-300" />
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Spend</span>
        <span className="font-semibold text-slate-700">{summary.totalSpend}</span>
      </div>
      <div className="w-px h-3 bg-slate-300" />
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Avg ROAS</span>
        <span className="font-semibold text-emerald-600">{summary.avgRoas}</span>
      </div>
    </div>
  );
}

/**
 * FilterBar - Platform and status filters.
 */
function FilterBar({ platforms, selectedPlatform, onPlatformChange, selectedStatus, onStatusChange, loading }) {
  const statusOptions = ["all", "active", "paused"];

  return (
    <div className="flex items-center gap-3 overflow-x-auto no-scrollbar pb-1 md:pb-0">
      {/* Platform filter */}
      <div className="flex items-center p-1 bg-white/70 border border-slate-200 rounded-full backdrop-blur-sm">
        <button
          onClick={() => onPlatformChange(null)}
          className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
            selectedPlatform === null ? "bg-slate-800 text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          All
        </button>
        {platforms.map((provider) => (
          <button
            key={provider}
            onClick={() => onPlatformChange(provider)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full capitalize transition-all ${
              selectedPlatform === provider ? "bg-slate-800 text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {provider}
          </button>
        ))}
      </div>

      <div className="w-px h-6 bg-slate-200 mx-1" />

      {/* Status filter */}
      <div className="flex items-center gap-2">
        {statusOptions.map((status) => (
          <button
            key={status}
            onClick={() => onStatusChange(status)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all capitalize ${
              selectedStatus === status
                ? status === "active"
                  ? "bg-emerald-50 text-emerald-600 border border-emerald-200"
                  : "bg-slate-100 text-slate-900 border border-slate-200"
                : "bg-white border border-slate-200 text-slate-500 hover:text-slate-700"
            }`}
          >
            {status === "all" ? "All Status" : status}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Main CampaignsPage component.
 */
export default function CampaignsPage() {
  // User & workspace state
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);

  // Data state
  const [campaigns, setCampaigns] = useState([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ total: 0, page: 1, pageSize: 25 });

  // Filter state
  // NOTE: Defaults are ACTIVE campaigns sorted by REVENUE (highest first)
  // per product decision - users want to see top performers first
  const [platforms, setPlatforms] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState("active"); // Always default to active
  const [sortBy, setSortBy] = useState("revenue"); // Default to revenue (highest first)
  const [sortDir, setSortDir] = useState("desc");
  const [timeframe, setTimeframe] = useState("7d");

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);

  // Fetch user on mount
  useEffect(() => {
    let mounted = true;
    currentUser()
      .then((u) => {
        if (!mounted) return;
        setUser(u);
        setWorkspaceId(u?.workspace_id);
        setInitialLoading(false);
      })
      .catch((err) => {
        console.error("Failed to get user:", err);
        if (mounted) {
          setUser(null);
          setInitialLoading(false);
        }
      });
    return () => { mounted = false; };
  }, []);

  // Fetch available platforms
  useEffect(() => {
    if (!workspaceId) return;

    fetchWorkspaceProviders({ workspaceId })
      .then((data) => setPlatforms(data.providers || []))
      .catch((err) => console.error("Failed to fetch providers:", err));
  }, [workspaceId]);

  // Fetch campaigns
  const fetchCampaigns = useCallback(async () => {
    if (!workspaceId) return;

    setDataLoading(true);
    setError(null);

    try {
      const days = timeframe === "30d" ? 30 : timeframe === "today" ? 1 : timeframe === "yesterday" ? 1 : 7;
      const result = await fetchEntityPerformance({
        workspaceId,
        entityType: "campaign",
        timeRange: { last_n_days: days },
        limit: 50,
        sortBy,
        sortDir,
        status: selectedStatus,
        provider: selectedPlatform,
      });

      // Adapt the response to our row format
      const rows = (result?.items || []).map((row) => ({
        id: row.id,
        name: row.name,
        platform: row.platform,
        status: row.status,
        kindLabel: row.kind_label || null,
        revenueRaw: row.revenue,
        spendRaw: row.spend,
        roasRaw: row.roas,
        conversionsRaw: row.conversions,
        cpcRaw: row.cpc,
        ctr_pctRaw: row.ctr_pct,
        trend: row.trend || [],
        thumbnail_url: row.thumbnail_url,
        image_url: row.image_url,
        media_type: row.media_type,
        display: {
          revenue: formatMetricValue(row.revenue, "currency"),
          spend: formatMetricValue(row.spend, "currency"),
          roas: row.roas != null ? `${row.roas.toFixed(2)}x` : "—",
          conversions: row.conversions?.toLocaleString() || "—",
          subtitle: row.last_updated_at
            ? `Updated ${formatRelativeTime(row.last_updated_at)}`
            : "—",
        },
      }));

      setCampaigns(rows);
      setPagination(result?.meta || { total: rows.length, page: 1, pageSize: 50 });
    } catch (err) {
      console.error("Failed to fetch campaigns:", err);
      setError("Failed to load campaigns. Please try again.");
      setCampaigns([]);
    } finally {
      setDataLoading(false);
      setLoading(false);
    }
  }, [workspaceId, timeframe, sortBy, sortDir, selectedStatus, selectedPlatform]);

  // Fetch campaigns when filters change
  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  // Handle campaign row click
  const handleCampaignClick = (campaign) => {
    setSelectedCampaign(campaign);
    setModalOpen(true);
  };

  // Handle modal close
  const handleModalClose = () => {
    setModalOpen(false);
    // Delay clearing selected campaign to allow animation
    setTimeout(() => setSelectedCampaign(null), 300);
  };

  // Time range options
  const timeRanges = [
    { id: "today", label: "Today" },
    { id: "yesterday", label: "Yesterday" },
    { id: "7d", label: "7d" },
    { id: "30d", label: "30d" },
  ];

  // Loading state
  if (initialLoading) {
    return (
      <div className="p-12 text-center">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-500">Loading campaigns...</p>
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="p-12 text-center">
        <div className="glass-card rounded-3xl border border-slate-200/60 p-6 max-w-md mx-auto">
          <h2 className="text-xl font-medium mb-2 text-slate-900">You must be signed in.</h2>
          <a href="/sign-in" className="text-cyan-600 hover:text-cyan-700 underline">
            Go to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <header className="pt-2 pb-2">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Campaigns</h1>
              {dataLoading && <span className="text-[11px] text-cyan-500">Syncing…</span>}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              All paid campaigns across Meta & Google in one view.
            </p>
          </div>

          {/* Time range + sort */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Time range pills */}
            <div className="flex bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
              {timeRanges.map((range) => (
                <button
                  key={range.id}
                  onClick={() => setTimeframe(range.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    timeframe === range.id
                      ? "text-slate-900 bg-slate-100 shadow-sm"
                      : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>

            {/* Sort dropdown */}
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="pl-8 pr-10 py-2 rounded-full bg-white border border-slate-200 text-xs font-medium text-slate-700 shadow-sm hover:border-slate-300 transition-all appearance-none cursor-pointer"
              >
                <option value="roas">Sort by ROAS</option>
                <option value="revenue">Sort by Revenue</option>
                <option value="spend">Sort by Spend</option>
                <option value="conversions">Sort by Conversions</option>
              </select>
              <ArrowDownUp className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Filters row */}
        <div className="mt-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <FilterBar
            platforms={platforms}
            selectedPlatform={selectedPlatform}
            onPlatformChange={setSelectedPlatform}
            selectedStatus={selectedStatus}
            onStatusChange={setSelectedStatus}
            loading={dataLoading}
          />
          <SummaryStrip campaigns={campaigns} />
        </div>
      </header>

      {/* Table */}
      <div className="rounded-[24px] border border-slate-200 bg-white shadow-lg shadow-slate-200/50 overflow-hidden">
        <CampaignTableHeader />

        <div className="divide-y divide-slate-50">
          {dataLoading && campaigns.length === 0 && (
            <div className="p-8 text-center text-slate-500">Loading campaigns...</div>
          )}

          {error && (
            <div className="p-8 text-center text-red-500">
              {error}
              <button onClick={fetchCampaigns} className="ml-2 text-cyan-600 hover:underline">
                Retry
              </button>
            </div>
          )}

          {!dataLoading && !error && campaigns.length === 0 && (
            <div className="p-12 text-center">
              <Layers className="w-12 h-12 mx-auto mb-4 text-slate-300" />
              <p className="text-slate-500">No campaigns found for the selected filters.</p>
              <p className="text-xs text-slate-400 mt-1">
                Try adjusting your filters or connecting an ad platform.
              </p>
            </div>
          )}

          {campaigns.map((campaign) => (
            <CampaignRow
              key={campaign.id}
              campaign={campaign}
              onRowClick={handleCampaignClick}
              selected={selectedCampaign?.id === campaign.id}
            />
          ))}
        </div>

        {/* Pagination */}
        {campaigns.length > 0 && (
          <div className="flex items-center justify-between px-6 py-3 text-[11px] text-slate-400 border-t border-slate-100 bg-white">
            <span>
              Showing {campaigns.length} of {pagination.total} campaigns
            </span>
          </div>
        )}
      </div>

      {/* Campaign Detail Modal */}
      <CampaignDetailModal
        isOpen={modalOpen}
        onClose={handleModalClose}
        campaign={selectedCampaign}
        workspaceId={workspaceId}
        timeframe={timeframe}
      />
    </div>
  );
}

/**
 * Format a timestamp as relative time (e.g., "2h ago").
 */
function formatRelativeTime(isoDate) {
  if (!isoDate) return "—";
  const now = new Date();
  const then = new Date(isoDate);
  const diff = Math.max(0, now.getTime() - then.getTime());
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
