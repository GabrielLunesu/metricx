"use client";
import { useState, useEffect } from "react";
import { ArrowDownUp } from "lucide-react";
import { fetchWorkspaceProviders } from "@/lib/api";

export default function TopToolbar({
  meta,
  filters,
  onPlatformChange,
  onStatusChange,
  onSortChange,
  onTimeRangeChange,
  loading,
  workspaceId,
  availableProviders,
  setAvailableProviders,
  summary,
}) {
  const [providersLoading, setProvidersLoading] = useState(true);

  // Use filters from parent, with defaults
  // Note: platform is null for "all", so we need to convert it
  const selectedPlatform = filters?.platform === null || filters?.platform === 'all' ? 'all' : filters.platform;
  const selectedStatus = filters?.status || 'all';
  const selectedSort = filters?.sortBy || 'roas';
  const selectedTime = filters?.timeframe || '7d';

  // Fetch available providers on mount
  useEffect(() => {
    if (!workspaceId) return;

    let mounted = true;
    setProvidersLoading(true);

    fetchWorkspaceProviders({ workspaceId })
      .then((data) => {
        if (!mounted) return;
        if (setAvailableProviders) {
          setAvailableProviders(data.providers || []);
        }
        setProvidersLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch providers:', err);
        if (mounted) setProvidersLoading(false);
      });

    return () => { mounted = false; };
  }, [workspaceId, setAvailableProviders]);

  const timeRanges = [
    { id: 'today', label: 'Today' },
    { id: 'yesterday', label: 'Yesterday' },
    { id: '7d', label: '7d' },
    { id: '30d', label: '30d' },
  ];

  const statusOptions = ['all', 'active', 'paused'];

  const handleTimeChange = (id) => {
    onTimeRangeChange?.(id);
  };

  const handleStatusClick = (status) => {
    onStatusChange?.(status);
  };

  const handlePlatformClick = (platform) => {
    // Convert 'all' to null for parent component
    onPlatformChange?.(platform === 'all' ? null : platform);
  };

  return (
    <header className="pt-2 pb-2">
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
        {/* Title & subtitle */}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
              {meta?.title || "Campaigns"}
            </h1>
            {loading && (
              <span className="text-[11px] text-cyan-500">Syncing…</span>
            )}
          </div>
          <p className="text-sm text-slate-900 mt-1 font-normal">
            {meta?.subtitle
              ? `All paid campaigns • updated ${meta.subtitle}`
              : "All paid campaigns across Meta & Google in one view."}
          </p>
        </div>

        {/* Time range + sort */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Time range pills */}
          <div className="flex bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
            {timeRanges.map((range) => (
              <button
                key={range.id}
                onClick={() => handleTimeChange(range.id)}
                className={`px-3 py-1.5 text-xs font-black font-medium rounded-md transition-colors ${selectedTime === range.id
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
              value={selectedSort}
              onChange={(e) =>
                onSortChange?.(e.target.value, filters?.sortDir || "desc")
              }
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
        {/* Platform + status pills */}
        <div className="flex items-center gap-3 overflow-x-auto no-scrollbar pb-1 md:pb-0">
          {/* Platform filter */}
          <div className="flex items-center p-1 bg-white/70 border border-slate-200 rounded-full backdrop-blur-sm">
            {providersLoading ? (
              <div className="flex gap-2">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-14 h-7 bg-slate-100 animate-pulse rounded-full"
                  />
                ))}
              </div>
            ) : (
              <>
                <button
                  onClick={() => handlePlatformClick("all")}
                  className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${selectedPlatform === "all"
                    ? "bg-slate-850 text-black shadow-sm"
                    : "text-slate-600 hover:text-black"
                    }`}
                >
                  All
                </button>
                {availableProviders?.map((provider) => (
                  <button
                    key={provider}
                    onClick={() => handlePlatformClick(provider)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-full capitalize transition-all ${selectedPlatform === provider
                      ? "bg-slate-850 text-black shadow-sm"
                      : "text-slate-600 hover:text-black"
                      }`}
                  >
                    {provider}
                  </button>
                ))}
              </>
            )}
          </div>

          <div className="w-px h-6 bg-slate-200 mx-1" />

          {/* Status filter */}
          <div className="flex items-center gap-2">
            {statusOptions.map((status) => (
              <button
                key={status}
                onClick={() => handleStatusClick(status)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all capitalize ${selectedStatus === status
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

        {/* Summary strip */}
        {summary && (
          <div className="flex items-center gap-6 text-xs px-4 py-2 bg-white/60 border border-white/70 rounded-full backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Active</span>
              <span className="font-semibold text-slate-700">
                {summary.activeCount}
              </span>
            </div>
            <div className="w-px h-3 bg-slate-300" />
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Spend</span>
              <span className="font-semibold text-slate-700">
                {summary.totalSpendFormatted}
              </span>
            </div>
            <div className="w-px h-3 bg-slate-300" />
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Avg ROAS</span>
              <span className="font-semibold text-emerald-600">
                {summary.avgRoasFormatted}
              </span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
