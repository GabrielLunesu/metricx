/**
 * Campaigns Page v3.0 - Redesigned Campaign Performance Overview
 * ==============================================================
 *
 * WHAT: Lists all campaigns with expandable cards and performance metrics
 * WHY: Clean, minimalistic design with expandable rows for detailed view
 *
 * ARCHITECTURE:
 *   - Expandable campaign cards (one expanded at a time)
 *   - Infinite scroll with IntersectionObserver
 *   - Filter bar with platform, status, date range, search
 *   - Optional modal for full campaign details
 *
 * DATA FLOW:
 *   1. Page fetches campaign list from backend
 *   2. Click on campaign expands card to show ad sets
 *   3. "View Full Details" opens CampaignDetailModal
 *   4. Infinite scroll loads more campaigns
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - ui/components/campaigns/CampaignCard.jsx
 *   - ui/components/campaigns/CampaignFilters.jsx
 */
"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Layers } from "lucide-react";
import { startOfDay, endOfDay, subDays } from "date-fns";
import { currentUser } from "@/lib/workspace";
import { fetchEntityPerformance, fetchWorkspaceProviders } from "@/lib/api";
import { formatMetricValue } from "@/lib/utils";

// Components
import CampaignCard from "@/components/campaigns/CampaignCard";
import CampaignFilters from "@/components/campaigns/CampaignFilters";
import CampaignDetailModal from "@/components/campaigns/CampaignDetailModal";

/**
 * Default date range (Last 7 Days)
 */
function getDefaultDateRange() {
  return {
    from: startOfDay(subDays(new Date(), 6)),
    to: endOfDay(new Date()),
  };
}

/**
 * Table Header Row
 */
function TableHeader() {
  return (
    <div className="hidden md:flex items-center px-4 py-3 mb-2 text-xs font-medium text-neutral-400 uppercase tracking-wider border-b border-neutral-100 sticky top-0 bg-white z-20">
      <div className="flex-1 pl-2">Campaign</div>
      <div className="w-24 text-center">Status</div>
      <div className="w-28 text-right">Spend</div>
      <div className="w-28 text-right">Revenue</div>
      <div className="w-24 text-right">ROAS</div>
      <div className="w-24 text-right pr-2">Conv.</div>
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

/**
 * Main CampaignsPage component.
 */
export default function CampaignsPage() {
  // User & workspace state
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);

  // Data state
  const [campaigns, setCampaigns] = useState([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Filter state
  const [platforms, setPlatforms] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState("active");
  const [dateRange, setDateRange] = useState(getDefaultDateRange);
  const [searchQuery, setSearchQuery] = useState("");

  // UI state
  const [expandedId, setExpandedId] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);

  // Infinite scroll ref
  const sentinelRef = useRef(null);

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

  // Fetch campaigns (initial or append)
  const fetchCampaigns = useCallback(async (pageNum = 1, append = false) => {
    if (!workspaceId) return;

    setDataLoading(true);
    setError(null);

    try {
      // Calculate days from date range
      const days = dateRange?.from && dateRange?.to
        ? Math.ceil((dateRange.to - dateRange.from) / (1000 * 60 * 60 * 24)) + 1
        : 7;

      const result = await fetchEntityPerformance({
        workspaceId,
        entityType: "campaign",
        timeRange: { last_n_days: days },
        limit: pageSize,
        offset: (pageNum - 1) * pageSize,
        sortBy: "revenue",
        sortDir: "desc",
        status: selectedStatus,
        provider: selectedPlatform,
      });

      // Adapt the response to our row format
      const rows = (result?.items || []).map((row) => {
        // Base metrics from API
        const spend = row.spend || 0;
        const revenue = row.revenue || 0;
        const clicks = row.clicks || 0;
        const impressions = row.impressions || 0;
        const conversions = row.conversions || 0;
        
        // Calculated metrics
        const roas = spend > 0 ? revenue / spend : null;
        const cpc = clicks > 0 ? spend / clicks : null;
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : null;
        const cpm = impressions > 0 ? (spend / impressions) * 1000 : null;
        const cpa = conversions > 0 ? spend / conversions : null;
        const conversionRate = clicks > 0 ? (conversions / clicks) * 100 : null;
        
        return {
          id: row.id,
          name: row.name,
          platform: row.platform,
          status: row.status,
          kindLabel: row.kind_label || null,
          // Raw metrics for KPI grid
          spendRaw: spend,
          revenueRaw: revenue,
          roasRaw: roas,
          clicksRaw: clicks,
          impressionsRaw: impressions,
          conversionsRaw: conversions,
          cpcRaw: cpc,
          cpmRaw: cpm,
          ctrRaw: ctr,
          cpaRaw: cpa,
          conversionRateRaw: conversionRate,
          conversionValueRaw: revenue, // Same as revenue for now
          // Trend data
          trend: row.trend || [],
          thumbnail_url: row.thumbnail_url,
          image_url: row.image_url,
          media_type: row.media_type,
          // Display formatted values (for collapsed row)
          display: {
            revenue: formatMetricValue(revenue, "currency"),
            spend: formatMetricValue(spend, "currency"),
            roas: roas != null ? `${roas.toFixed(2)}x` : "—",
            conversions: conversions?.toLocaleString() || "—",
            subtitle: row.last_updated_at
              ? `Updated ${formatRelativeTime(row.last_updated_at)}`
              : "—",
          },
        };
      });

      // Filter by search query (client-side for now)
      const filteredRows = searchQuery
        ? rows.filter((r) => r.name.toLowerCase().includes(searchQuery.toLowerCase()))
        : rows;

      if (append) {
        setCampaigns((prev) => [...prev, ...filteredRows]);
      } else {
        setCampaigns(filteredRows);
      }

      // Check if there are more results
      const totalFromMeta = result?.meta?.total || rows.length;
      setHasMore(pageNum * pageSize < totalFromMeta);
    } catch (err) {
      console.error("Failed to fetch campaigns:", err);
      setError("Failed to load campaigns. Please try again.");
      if (!append) setCampaigns([]);
    } finally {
      setDataLoading(false);
    }
  }, [workspaceId, dateRange, selectedStatus, selectedPlatform, searchQuery]);

  // Initial fetch when filters change
  useEffect(() => {
    setPage(1);
    setExpandedId(null);
    fetchCampaigns(1, false);
  }, [fetchCampaigns]);

  // Infinite scroll observer
  useEffect(() => {
    if (!sentinelRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !dataLoading) {
          const nextPage = page + 1;
          setPage(nextPage);
          fetchCampaigns(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinelRef.current);

    return () => observer.disconnect();
  }, [hasMore, dataLoading, page, fetchCampaigns]);

  // Handle campaign card toggle
  const handleToggle = (campaignId) => {
    setExpandedId((prev) => (prev === campaignId ? null : campaignId));
  };

  // Handle "View Full Details" click
  const handleViewDetails = (campaign) => {
    setSelectedCampaign(campaign);
    setModalOpen(true);
  };

  // Handle modal close
  const handleModalClose = () => {
    setModalOpen(false);
    setTimeout(() => setSelectedCampaign(null), 300);
  };

  // Loading state
  if (initialLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          <span className="text-neutral-500 text-sm">Loading campaigns...</span>
        </div>
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">
            You must be signed in.
          </h2>
          <a href="/sign-in" className="text-neutral-600 hover:text-neutral-900 underline">
            Go to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6 pb-16 md:pb-0">
      {/* Header */}
      <header className="flex flex-col gap-4 md:gap-8">
        {/* Title Row */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-neutral-900">Campaigns</h1>
            {dataLoading && campaigns.length > 0 && (
              <span className="text-xs text-neutral-400 mt-1">Syncing...</span>
            )}
          </div>
          
          {/* New Campaign button - commented out for now */}
          {/* 
          <button className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors shadow-sm shadow-neutral-900/10">
            <Plus className="w-4 h-4" />
            New Campaign
          </button>
          */}
        </div>

        {/* Filters Row */}
        <CampaignFilters
          platforms={platforms}
          selectedPlatform={selectedPlatform}
          onPlatformChange={setSelectedPlatform}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />
      </header>

      {/* Table */}
      <div className="space-y-3">
        {/* Table Headers */}
        <TableHeader />

        {/* Campaign Cards */}
        <div className="flex flex-col gap-3 pb-20">
          {/* Initial loading state */}
          {dataLoading && campaigns.length === 0 && (
            <div className="p-8 text-center text-neutral-500">
              <div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin mx-auto mb-3" />
              Loading campaigns...
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="p-8 text-center text-red-500">
              {error}
              <button
                onClick={() => fetchCampaigns(1, false)}
                className="ml-2 text-blue-600 hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty state */}
          {!dataLoading && !error && campaigns.length === 0 && (
            <div className="p-12 text-center">
              <Layers className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
              <p className="text-neutral-500">No campaigns found for the selected filters.</p>
              <p className="text-xs text-neutral-400 mt-1">
                Try adjusting your filters or connecting an ad platform.
              </p>
            </div>
          )}

          {/* Campaign cards */}
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              expanded={expandedId === campaign.id}
              onToggle={() => handleToggle(campaign.id)}
              onViewDetails={() => handleViewDetails(campaign)}
              workspaceId={workspaceId}
              dateRange={dateRange}
            />
          ))}

          {/* Infinite scroll sentinel */}
          {hasMore && campaigns.length > 0 && (
            <div ref={sentinelRef} className="py-4 flex justify-center">
              {dataLoading && (
                <div className="flex items-center gap-2 text-neutral-400 text-sm">
                  <div className="w-4 h-4 border-2 border-neutral-300 border-t-neutral-600 rounded-full animate-spin" />
                  Loading more...
                </div>
              )}
            </div>
          )}

          {/* End of list */}
          {!hasMore && campaigns.length > 0 && (
            <div className="py-4 text-center text-xs text-neutral-400">
              Showing all {campaigns.length} campaigns
            </div>
          )}
        </div>
      </div>

      {/* Campaign Detail Modal */}
      <CampaignDetailModal
        isOpen={modalOpen}
        onClose={handleModalClose}
        campaign={selectedCampaign}
        workspaceId={workspaceId}
        timeframe={dateRange?.from && dateRange?.to
          ? `${Math.ceil((dateRange.to - dateRange.from) / (1000 * 60 * 60 * 24)) + 1}d`
          : "7d"
        }
      />
    </div>
  );
}
