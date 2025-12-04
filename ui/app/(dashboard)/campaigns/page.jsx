/**
 * Campaigns Page - Campaign management and performance view.
 *
 * WHAT: Lists all campaigns with performance metrics
 * WHY: Users need to see and manage their campaigns in one place
 *
 * NOTE: Attribution warnings have been moved to Settings > Attribution
 * per the "Ad Analytics First, Attribution Second" strategy.
 * See: .claude/CLAUDE.md
 *
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 */
"use client";
import { useState, useEffect, useMemo } from "react";
import { currentUser } from "@/lib/auth";
import { campaignsApiClient, campaignsAdapter } from "../../../lib";
import TopToolbar from "./components/TopToolbar";
import CampaignTableHeader from "./components/CampaignTableHeader";
import CampaignRow from "./components/CampaignRow";
import Card from "../../../components/Card";
import { useRouter } from "next/navigation";

export default function CampaignsPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [availableProviders, setAvailableProviders] = useState([]);

  const [campaignsData, setCampaignsData] = useState({
    meta: { title: "Campaigns", subtitle: "Loading...", level: "campaign", lastUpdatedAt: null },
    pagination: { total: 0, page: 1, pageSize: 8 },
    rows: [],
  });
  const [loading, setLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
    platform: null,
    status: "all",
    timeframe: "7d",
    sortBy: "roas",
    sortDir: "desc",
    page: 1,
    pageSize: 8,
  });

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
    return () => {
      mounted = false;
    };
  }, []);

  const fetchCampaigns = async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const apiResponse = await campaignsApiClient.fetchEntityPerformance({
        workspaceId,
        entityLevel: "campaign",
        platform: filters.platform === "all" ? null : filters.platform,
        status: filters.status,
        timeframe: filters.timeframe,
        sortBy: filters.sortBy,
        sortDir: filters.sortDir,
        page: filters.page,
        pageSize: filters.pageSize,
      });
      const adaptedData = campaignsAdapter.adaptEntityPerformance(apiResponse);
      setCampaignsData(adaptedData);
    } catch (err) {
      console.error("Failed to fetch campaigns:", err);
      setError("Failed to load campaigns. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (workspaceId) {
      fetchCampaigns();
    }
  }, [workspaceId, filters]);

  // Missing dependency warning fix - wrap fetchCampaigns in useCallback or disable eslint
  // eslint-disable-next-line react-hooks/exhaustive-deps

  const handlePlatformChange = (platform) => setFilters((prev) => ({ ...prev, platform, page: 1 }));
  const handleStatusChange = (status) => setFilters((prev) => ({ ...prev, status, page: 1 }));
  const handleSortChange = (sortBy, sortDir) => setFilters((prev) => ({ ...prev, sortBy, sortDir, page: 1 }));
  const handleTimeRangeChange = (timeframe) => setFilters((prev) => ({ ...prev, timeframe, page: 1 }));
  const handlePageChange = (newPage) => setFilters((prev) => ({ ...prev, page: newPage }));

  const handleCampaignClick = (campaignId) => {
    router.push(`/campaigns/${campaignId}`);
  };

  const { rows, meta, pagination } = campaignsData;

  const [selectedIds, setSelectedIds] = useState(new Set());

  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const summary = useMemo(() => {
    if (!rows || rows.length === 0) {
      return null;
    }
    const activeCount = rows.filter((r) => r.status === "active").length;
    const totalSpend = rows.reduce((sum, r) => sum + (r.spendRaw || 0), 0);
    const totalRevenue = rows.reduce(
      (sum, r) => sum + (r.revenueRaw || 0),
      0
    );
    const avgRoas = totalSpend > 0 ? totalRevenue / totalSpend : null;

    const totalSpendFormatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(totalSpend || 0);

    const avgRoasFormatted =
      avgRoas != null && !Number.isNaN(avgRoas)
        ? `${avgRoas.toFixed(1)}x`
        : "—";

    return { activeCount, totalSpendFormatted, avgRoasFormatted };
  }, [rows]);

  if (initialLoading) {
    return (
      <div className="p-12 text-center">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-neutral-600">Loading campaigns...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-12 text-center">
        <div className="glass-card rounded-3xl border border-neutral-200/60 p-6 max-w-md mx-auto">
          <h2 className="text-xl font-medium mb-2 text-neutral-900">You must be signed in.</h2>
          <a href="/login" className="text-cyan-600 hover:text-cyan-700 underline">Go to sign in</a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <TopToolbar
        meta={meta}
        filters={filters}
        workspaceId={workspaceId}
        availableProviders={availableProviders}
        setAvailableProviders={setAvailableProviders}
        onPlatformChange={handlePlatformChange}
        onStatusChange={handleStatusChange}
        onSortChange={handleSortChange}
        onTimeRangeChange={handleTimeRangeChange}
        loading={loading}
        summary={summary}
      />

      <div className="rounded-[24px] border border-slate-200 bg-white shadow-lg shadow-slate-200/50 overflow-hidden relative">
        <CampaignTableHeader />

        <div className="divide-y divide-slate-50">
          {loading && (
            <Card className="rounded-none border-0 p-8 text-center text-neutral-500">
              Loading campaigns...
            </Card>
          )}
          {error && (
            <Card className="rounded-none border-0 p-8 text-center text-red-500">
              {error}
              <button
                onClick={fetchCampaigns}
                className="ml-2 text-cyan-400 hover:underline"
              >
                Retry
              </button>
            </Card>
          )}
          {!loading && !error && rows.length === 0 && (
            <Card className="rounded-none border-0 p-8 text-center text-neutral-500">
              No campaigns found for the selected filters and date range.
            </Card>
          )}
          {!loading &&
            !error &&
            rows.map((row) => (
              <CampaignRow
                key={row.id}
                row={row}
                selected={selectedIds.has(row.id)}
                onRowClick={() => handleCampaignClick(row.id)}
                onSelectToggle={() => toggleSelected(row.id)}
              />
            ))}
        </div>

        {/* Pagination */}
        {!loading && !error && rows.length > 0 && (
          <div className="flex items-center justify-between px-6 py-3 text-[11px] text-slate-400 border-t border-slate-100 bg-white">
            <span>
              Showing{" "}
              {Math.min(
                (pagination.page - 1) * pagination.pageSize + 1,
                pagination.total
              )}{" "}
              -{" "}
              {Math.min(
                pagination.page * pagination.pageSize,
                pagination.total
              )}{" "}
              of {pagination.total} campaigns
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="px-3 py-1.5 rounded-full border border-slate-200 text-xs font-medium text-slate-500 hover:text-slate-700 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed bg-white"
              >
                Prev
              </button>
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={
                  pagination.page * pagination.pageSize >= pagination.total
                }
                className="px-3 py-1.5 rounded-full border border-slate-200 text-xs font-medium text-slate-500 hover:text-slate-700 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed bg-white"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Floating bulk actions */}
        {selectedIds.size > 0 && (
          <div className="pointer-events-none">
            <div className="fixed bottom-10 left-1/2 -translate-x-1/2 z-40 pointer-events-auto">
              <div className="flex items-center gap-4 px-6 py-3 bg-white text-white rounded-full shadow-xl shadow-slate-900/30 border border-slate-700/60">
                <span className="text-xs font-medium text-slate-300 border-r border-slate-700 pr-4">
                  {selectedIds.size} selected
                </span>
                <button className="flex items-center gap-2 text-xs font-medium text-slate-200 hover:text-white transition-colors">
                  Pause
                </button>
                <button className="flex items-center gap-2 text-xs font-medium text-slate-200 hover:text-white transition-colors">
                  Budget +20%
                </button>
                <button className="flex items-center gap-2 text-xs font-medium text-slate-200 hover:text-white transition-colors">
                  Export
                </button>
                <button
                  className="ml-2 p-1 rounded-full hover:bg-slate-800 transition-colors"
                  onClick={clearSelection}
                >
                  <span className="text-slate-400 text-xs">✕</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* <ActiveRulesPanel /> Not part of this task */}
    </div>
  );
}
