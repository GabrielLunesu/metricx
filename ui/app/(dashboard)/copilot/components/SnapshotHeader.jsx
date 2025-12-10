"use client";
import { useEffect, useState } from "react";
import { fetchWorkspaceKpis } from "../../../../lib/api";
import { currentUser } from "../../../../lib/workspace";

export default function SnapshotHeader() {
  const [workspaceId, setWorkspaceId] = useState(null);
  const [revenueToday, setRevenueToday] = useState(null);
  const [roasYesterday, setRoasYesterday] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    // Get workspace ID and fetch both KPIs
    currentUser()
      .then((user) => {
        if (!mounted || !user) return;
        setWorkspaceId(user.workspace_id);

        // Fetch both metrics in parallel (last 3 days)
        return Promise.all([
          // Revenue Last 3 Days vs Previous 3 Days
          fetchWorkspaceKpis({
            workspaceId: user.workspace_id,
            metrics: ['revenue'],
            lastNDays: 3,
            dayOffset: 0,
            compareToPrevious: true,
            sparkline: false
          }),
          // ROAS Last 3 Days vs Previous 3 Days
          fetchWorkspaceKpis({
            workspaceId: user.workspace_id,
            metrics: ['roas'],
            lastNDays: 3,
            dayOffset: 0,
            compareToPrevious: true,
            sparkline: false
          })
        ]);
      })
      .then(([revenueData, roasData]) => {
        if (!mounted) return;
        setRevenueToday(revenueData?.[0] || null);
        setRoasYesterday(roasData?.[0] || null);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch snapshot data:', err);
        if (mounted) setLoading(false);
      });

    return () => { mounted = false; };
  }, []);

  // Format delta percentage
  const formatDelta = (deltaPct) => {
    if (deltaPct === null || deltaPct === undefined) return null;
    const percentage = (deltaPct * 100).toFixed(1);
    const sign = deltaPct > 0 ? '+' : '';
    return `${sign}${percentage}%`;
  };

  // Determine color based on change
  const getDeltaColor = (deltaPct) => {
    if (deltaPct === null || deltaPct === undefined) return 'bg-neutral-50 text-neutral-600';
    return deltaPct >= 0 ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600';
  };

  return (
    <div className="mb-12 fade-up">
      <div className="flex items-start justify-between mb-8">
        <h2 className="text-5xl font-semibold tracking-tight text-neutral-900 leading-tight">
          Here's a quick snapshot<br/>of your performance.
        </h2>
        
        {/* Context Synced Indicator */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-cyan-400/30">
          <div className="w-2 h-2 rounded-full bg-cyan-400 pulse-dot"></div>
          <span className="text-sm font-medium text-neutral-700">Context synced</span>
        </div>
      </div>
      
      {/* Key Stats Row */}
      <div className="grid grid-cols-2 gap-6 mb-8 fade-up fade-up-delay-1">
        {/* Revenue Last 3 Days */}
        <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 cyan-glow-card relative overflow-hidden">
          <div className="glow-line"></div>
          <p className="text-sm font-medium text-neutral-500 mb-2 uppercase tracking-wide">Revenue - Last 3 Days</p>
          
          {loading ? (
            <>
              <div className="h-14 bg-neutral-200 rounded w-48 mb-2 animate-pulse"></div>
              <div className="h-7 bg-neutral-200 rounded w-32 animate-pulse"></div>
            </>
          ) : (
            <>
              <p className="text-5xl font-semibold text-neutral-900 mb-1">
                {revenueToday?.value !== null && revenueToday?.value !== undefined
                  ? `$${revenueToday.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  : '—'}
              </p>
              {revenueToday?.delta_pct !== null && revenueToday?.delta_pct !== undefined && (
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getDeltaColor(revenueToday.delta_pct)}`}>
                  {formatDelta(revenueToday.delta_pct)} vs previous 3 days
                </span>
              )}
            </>
          )}
          
          <div className="absolute -right-10 -bottom-10 w-32 h-32 bg-cyan-400 rounded-full blur-[60px] opacity-10 pulse-glow"></div>
        </div>
        
        {/* ROAS Last 3 Days */}
        <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 cyan-glow-card relative overflow-hidden">
          <div className="glow-line" style={{ animationDelay: '1s' }}></div>
          <p className="text-sm font-medium text-neutral-500 mb-2 uppercase tracking-wide">ROAS - Last 3 Days</p>
          
          {loading ? (
            <>
              <div className="h-14 bg-neutral-200 rounded w-40 mb-2 animate-pulse"></div>
              <div className="h-7 bg-neutral-200 rounded w-32 animate-pulse"></div>
            </>
          ) : (
            <>
              <p className="text-5xl font-semibold text-neutral-900 mb-1">
                {roasYesterday?.value !== null && roasYesterday?.value !== undefined
                  ? `${roasYesterday.value.toFixed(2)}x`
                  : '—'}
              </p>
              {roasYesterday?.delta_pct !== null && roasYesterday?.delta_pct !== undefined && (
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getDeltaColor(roasYesterday.delta_pct)}`}>
                  {formatDelta(roasYesterday.delta_pct)} improvement
                </span>
              )}
            </>
          )}
          
          <div className="absolute -right-10 -bottom-10 w-32 h-32 bg-cyan-400 rounded-full blur-[60px] opacity-10 pulse-glow" style={{ animationDelay: '1.5s' }}></div>
        </div>
      </div>
    </div>
  );
}


