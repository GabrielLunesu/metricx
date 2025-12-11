'use client';

/**
 * RevenueBarModule Component (v2.0 - Server-side data)
 * =====================================================
 *
 * WHAT: Vertical bar chart showing daily revenue
 * WHY: Users need a clear visual of revenue trends by day
 *
 * DESIGN:
 *   - Server-side data fetching via /analytics/daily-revenue
 *   - Frontend is dumb - just renders what backend sends
 *   - Week view: 7 individual bars (last 7 days)
 *   - Month view: 30 individual bars (last 30 days)
 *
 * FEATURES:
 *   - Pill-shaped vertical bars with gradient segments
 *   - Week/Month toggle (triggers server re-fetch)
 *   - Day labels with proper formatting
 *   - Value labels above bars
 *   - Highlight for highest day
 *   - Average per day stat
 *
 * REFERENCES:
 *   - backend/app/routers/analytics.py (GET /analytics/daily-revenue)
 *   - lib/api.js (fetchDailyRevenue)
 */

import { useState, useEffect, useCallback } from "react";
import { TrendingUp } from "lucide-react";
import { fetchDailyRevenue } from "@/lib/api";

// Format currency compactly
function formatCompact(val) {
  if (val === null || val === undefined) return '—';
  if (val >= 1000) {
    return `$${(val / 1000).toFixed(1)}k`;
  }
  return `$${Math.round(val)}`;
}

export default function RevenueBarModule({ workspaceId, loading: parentLoading }) {
  const [viewMode, setViewMode] = useState('week'); // 'week' | 'month'
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch data from server
  const fetchData = useCallback(async () => {
    if (!workspaceId) return;

    setLoading(true);
    setError(null);

    try {
      const days = viewMode === 'week' ? 7 : 30;
      const result = await fetchDailyRevenue({ workspaceId, days });
      setData(result);
    } catch (err) {
      console.error('Failed to fetch daily revenue:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, viewMode]);

  // Fetch on mount and when viewMode changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Calculate stats from server data
  const bars = data?.bars || [];
  const maxRevenue = Math.max(...bars.map(b => b.revenue), 1);
  const highestDay = data?.highest_day;

  // Combined loading state
  const isLoading = loading || parentLoading;

  // Loading state
  if (isLoading || !data) {
    return (
      <div className="dashboard-module min-h-[200px] animate-pulse">
        <div className="flex items-center justify-between mb-6">
          <div className="h-6 w-32 bg-slate-200/50 rounded"></div>
          <div className="h-8 w-24 bg-slate-200/50 rounded-full"></div>
        </div>
        <div className="flex items-end justify-between gap-1 h-40">
          {Array.from({ length: viewMode === 'week' ? 7 : 15 }).map((_, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-2">
              <div className="w-full max-w-[36px] rounded-full bg-slate-200/50" style={{ height: `${30 + Math.random() * 50}%` }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="dashboard-module min-h-[200px] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Daily Revenue</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-red-500 text-sm">Failed to load: {error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (bars.length === 0) {
    return (
      <div className="dashboard-module min-h-[200px] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Daily Revenue</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-400 text-sm">No revenue data yet</p>
        </div>
      </div>
    );
  }

  // For month view with 30 bars, show abbreviated labels (every 5th day or date numbers)
  const getBarLabel = (bar, index) => {
    if (viewMode === 'week') {
      return bar.day_name;
    }
    // Month view: show day of month for every ~5th bar or use compact format
    const date = new Date(bar.date);
    const dayOfMonth = date.getDate();
    // Show label for 1st, 8th, 15th, 22nd, 29th, or today
    if (bar.is_today || dayOfMonth === 1 || dayOfMonth === 8 || dayOfMonth === 15 || dayOfMonth === 22 || dayOfMonth === 29) {
      return dayOfMonth.toString();
    }
    return '';
  };

  return (
    <div className="dashboard-module min-h-[200px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Daily Revenue
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {viewMode === 'week' ? 'Last 7 days performance' : 'Last 30 days performance'}
          </p>
        </div>

        {/* Week/Month toggle */}
        <div className="inline-flex items-center gap-1 bg-slate-100 rounded-full p-1">
          <button
            onClick={() => setViewMode('week')}
            className={`
              px-3 py-1.5 rounded-full text-[11px] font-medium transition-all duration-200
              ${viewMode === 'week'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
              }
            `}
          >
            Week
          </button>
          <button
            onClick={() => setViewMode('month')}
            className={`
              px-3 py-1.5 rounded-full text-[11px] font-medium transition-all duration-200
              ${viewMode === 'month'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
              }
            `}
          >
            Month
          </button>
        </div>
      </div>

      {/* Bar Chart */}
      <div className={`flex-1 flex items-end justify-between mt-4 min-h-[160px] ${viewMode === 'month' ? 'gap-[2px]' : 'gap-2 sm:gap-3'}`}>
        {bars.map((bar, index) => {
          const heightPct = Math.max((bar.revenue / maxRevenue) * 100, 5);
          const isHighest = bar.date === highestDay && bar.revenue > 0;
          const label = getBarLabel(bar, index);

          return (
            <div key={bar.date} className="flex flex-col items-center gap-2 flex-1" style={{ minWidth: viewMode === 'month' ? '8px' : 'auto' }}>
              {/* Value label - only show for week view or highest in month view */}
              {(viewMode === 'week' || isHighest) && (
                <div className={`
                  text-[10px] font-medium  transition-all whitespace-nowrap
                  ${isHighest ? 'text-slate-900' : 'text-slate-500'}
                  ${viewMode === 'month' && !isHighest ? 'hidden' : ''}
                `}>
                  {bar.revenue > 0 ? formatCompact(bar.revenue) : '—'}
                </div>
              )}

              {/* Bar container */}
              <div className={`relative w-full h-32 flex items-end ${viewMode === 'month' ? 'max-w-[12px]' : 'max-w-[40px]'}`}>
                <div
                  className={`
                    w-full rounded-full overflow-hidden transition-all duration-500
                    ${isHighest
                      ? 'bg-white shadow-md ring-1 ring-emerald-200'
                      : 'bg-slate-900/10'
                    }
                  `}
                  style={{
                    height: `${heightPct}%`,
                    minHeight: '4px'
                  }}
                >
                  {/* Gradient segments inside the bar */}
                  {bar.revenue > 0 && (
                    <div className="w-full h-full flex flex-col justify-end overflow-hidden rounded-full">
                      {/* Top segment (brightest) */}
                      <div
                        className={`w-full ${isHighest ? 'bg-emerald-400' : 'bg-emerald-400/60'}`}
                        style={{ height: '35%' }}
                      />
                      {/* Middle segment */}
                      <div
                        className={`w-full ${isHighest ? 'bg-emerald-300/80' : 'bg-emerald-300/40'}`}
                        style={{ height: '35%' }}
                      />
                      {/* Bottom segment (darkest) */}
                      <div
                        className={`w-full ${isHighest ? 'bg-emerald-200/60' : 'bg-emerald-200/30'}`}
                        style={{ height: '30%' }}
                      />
                    </div>
                  )}
                </div>

                {/* Highlight badge for highest */}
                {isHighest && bar.revenue > 0 && (
                  <div className="absolute -top-14 left-1/2 -translate-x-1/2">
                    <div className="flex items-center gap-0.5 bg-slate-900 text-emerald-400 text-[9px] font-medium px-1.5 py-0.5 rounded-full">
                      <TrendingUp className="w-2.5 h-2.5" />
                    </div>
                  </div>
                )}
              </div>

              {/* Day label */}
              {label && (
                <span className={`
                  text-[10px] font-medium whitespace-nowrap
                  ${bar.is_today ? 'text-slate-900' : 'text-slate-500'}
                `}>
                  {label}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer stats */}
      <div className="mt-4 pt-3 border-t border-slate-200/50 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2 text-slate-500">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 border border-slate-900/10"></span>
          <span>Daily revenue</span>
        </div>
        <p className="font-medium text-slate-700">
          Average per day: <span className="text-slate-900 font-semibold">{formatCompact(data.average_revenue)}</span>
        </p>
      </div>
    </div>
  );
}
