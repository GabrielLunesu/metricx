/**
 * CampaignCard Component
 * ======================
 *
 * WHAT: Expandable campaign card with metrics and nested ad sets
 * WHY: Clean, animated card that expands to show performance details
 *
 * STATES:
 *   - Collapsed: Single row with platform icon, name, status, metrics
 *   - Expanded: Shows performance chart + ad sets list + "View Full Details"
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - ui/components/campaigns/AdSetRow.jsx
 *   - ui/components/campaigns/TrendSparkline.jsx
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { ChevronUp, ChevronDown, Loader2 } from "lucide-react";
import PlatformBadge from "./PlatformBadge";
import StatusBadge, { normalizeStatus } from "./StatusBadge";
import AdSetRow from "./AdSetRow";
import { UnifiedGraphEngine } from "@/components/charts/UnifiedGraphEngine";
import { fetchEntityPerformance } from "@/lib/api";

// =============================================================================
// FORMATTING FUNCTIONS
// =============================================================================

/**
 * Format large currency values (with k/M suffixes)
 */
function formatCurrency(value) {
  if (value == null) return "—";
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}k`;
  }
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Format small currency values (CPC, CPM, CPA - typically < $100)
 */
function formatSmallCurrency(value) {
  if (value == null) return "—";
  return `$${value.toFixed(2)}`;
}

/**
 * Format ROAS for display
 */
function formatRoas(value) {
  if (value == null) return "—";
  return `${value.toFixed(2)}x`;
}

/**
 * Format percentage values
 */
function formatPercent(value) {
  if (value == null) return "—";
  return `${value.toFixed(2)}%`;
}

/**
 * Format generic numbers with optional decimals
 */
function formatNumber(value, decimals = 0) {
  if (value == null) return "—";
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  });
}

/**
 * Format conversions/integers for display
 */
function formatConversions(value) {
  if (value == null) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

/**
 * Get ROAS color class based on value
 * >= 2x = green, >= 1x = amber, < 1x = red
 */
function getRoasColorClass(roas) {
  if (roas == null) return "text-neutral-500";
  if (roas >= 2) return "text-emerald-600";
  if (roas >= 1) return "text-amber-600";
  return "text-red-600";
}

// =============================================================================
// METRIC CARD COMPONENT
// =============================================================================

/**
 * MetricCard - Small KPI card for the expanded metrics grid
 */
function MetricCard({ label, value, colorClass = "text-neutral-900" }) {
  return (
    <div className="bg-neutral-50 rounded-lg p-3">
      <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
        {label}
      </span>
      <p className={`text-base font-semibold tabular-nums mt-0.5 ${colorClass}`}>
        {value}
      </p>
    </div>
  );
}

/**
 * Format a timeframe label (e.g., "7D", "30D")
 * Calculates inclusive day count from date range
 */
function getTimeframeLabel(dateRange) {
  if (!dateRange?.from || !dateRange?.to) return "7D";
  // Round the difference to handle endOfDay/startOfDay edge cases
  // No +1 needed because endOfDay already makes it inclusive
  const days = Math.round((dateRange.to - dateRange.from) / (1000 * 60 * 60 * 24));
  // Ensure at least 1 day
  return `${Math.max(1, days)}D`;
}

/**
 * CampaignCard - Expandable campaign card component.
 *
 * @param {Object} props
 * @param {Object} props.campaign - Campaign data
 * @param {boolean} props.expanded - Whether card is expanded
 * @param {Function} props.onToggle - Toggle expand/collapse
 * @param {Function} props.onViewDetails - Open full details modal
 * @param {string} props.workspaceId - Workspace ID for fetching adsets
 * @param {Object} props.dateRange - { from: Date, to: Date }
 */
export default function CampaignCard({
  campaign,
  expanded,
  onToggle,
  onViewDetails,
  workspaceId,
  dateRange,
}) {
  const [adsets, setAdsets] = useState([]);
  const [adsetsLoading, setAdsetsLoading] = useState(false);
  const [showAllAdsets, setShowAllAdsets] = useState(false);

  const { id, name, platform, status, trend, display } = campaign;
  const normalizedStatus = normalizeStatus(status);
  const isPaused = normalizedStatus === "paused" || normalizedStatus === "archived";
  const timeframeLabel = getTimeframeLabel(dateRange);

  // Fetch adsets when expanded
  const fetchAdsets = useCallback(async () => {
    if (!expanded || !workspaceId || !id) return;

    setAdsetsLoading(true);
    try {
      // Calculate days from date range
      const days = dateRange?.from && dateRange?.to
        ? Math.ceil((dateRange.to - dateRange.from) / (1000 * 60 * 60 * 24)) + 1
        : 7;

      const result = await fetchEntityPerformance({
        workspaceId,
        entityType: "adset",
        timeRange: { last_n_days: days },
        limit: 20,
        sortBy: "roas",
        sortDir: "desc",
        status: "all",
        campaignId: id,
      });

      const items = (result?.items || []).map((item) => ({
        ...item,
        roas: item.roas ?? (item.spend > 0 ? item.revenue / item.spend : null),
      }));
      setAdsets(items);
    } catch (err) {
      console.error("Failed to fetch adsets:", err);
      setAdsets([]);
    } finally {
      setAdsetsLoading(false);
    }
  }, [expanded, workspaceId, id, dateRange]);

  // Fetch adsets when card expands
  useEffect(() => {
    if (expanded) {
      fetchAdsets();
    } else {
      setAdsets([]);
      setShowAllAdsets(false);
    }
  }, [expanded, fetchAdsets]);

  // Visible adsets (show 3 by default, all if showAllAdsets)
  const visibleAdsets = showAllAdsets ? adsets : adsets.slice(0, 3);
  const hasMoreAdsets = adsets.length > 3;

  return (
    <div
      className={`
        relative bg-white border rounded-xl overflow-hidden
        transition-all duration-300
        ${expanded
          ? "border-neutral-300 shadow-[0_8px_30px_rgba(0,0,0,0.04)]"
          : "border-neutral-200 hover:shadow-[0_4px_12px_rgba(0,0,0,0.03)] hover:-translate-y-[2px] hover:border-neutral-300 cursor-pointer"
        }
        ${isPaused && !expanded ? "opacity-75 hover:opacity-100" : ""}
      `}
    >
      {/* Main Row (always visible) */}
      <div
        onClick={onToggle}
        className={`
          flex flex-col md:flex-row md:items-center p-4 cursor-pointer
          ${expanded ? "bg-neutral-50/50 border-b border-neutral-200/60" : ""}
        `}
      >
        {/* Campaign Info */}
        <div className="flex-1 flex items-center gap-4 min-w-0">
          <PlatformBadge platform={platform} size="md" />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className={`text-sm font-semibold truncate ${isPaused ? "text-neutral-700" : "text-neutral-900"}`}>
                {name}
              </h3>
              {expanded && (
                <ChevronUp className="w-4 h-4 text-neutral-400" />
              )}
            </div>
            <p className="text-[11px] text-neutral-400 mt-0.5 font-medium truncate">
              {expanded ? `ID: ${id?.slice(0, 8)} • ${platform}` : display?.subtitle || "—"}
            </p>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:flex md:items-center gap-y-4 gap-x-8 md:gap-0 mt-4 md:mt-0 w-full md:w-auto">
          {/* Status */}
          <div className="md:w-24 flex items-center md:justify-center">
            <StatusBadge status={status} showDot showIcon={false} />
          </div>

          {/* Spend */}
          <div className="md:w-28 flex flex-col items-start md:items-end">
            <span className="text-[10px] font-medium text-neutral-400 uppercase md:hidden">Spend</span>
            <span className={`text-sm font-medium tabular-nums ${isPaused ? "text-neutral-500" : "text-neutral-900"}`}>
              {formatCurrency(campaign.spendRaw)}
            </span>
          </div>

          {/* Revenue */}
          <div className="md:w-28 flex flex-col items-start md:items-end">
            <span className="text-[10px] font-medium text-neutral-400 uppercase md:hidden">Revenue</span>
            <span className={`text-sm font-medium tabular-nums ${isPaused ? "text-neutral-500" : "text-neutral-900"}`}>
              {formatCurrency(campaign.revenueRaw)}
            </span>
          </div>

          {/* ROAS */}
          <div className="md:w-24 flex flex-col items-start md:items-end">
            <span className="text-[10px] font-medium text-neutral-400 uppercase md:hidden">ROAS</span>
            <span className={`text-sm font-medium tabular-nums ${getRoasColorClass(campaign.roasRaw)}`}>
              {formatRoas(campaign.roasRaw)}
            </span>
          </div>

          {/* Conversions */}
          <div className="md:w-24 flex flex-col items-start md:items-end pr-2">
            <span className="text-[10px] font-medium text-neutral-400 uppercase md:hidden">Conv.</span>
            <span className={`text-sm font-medium tabular-nums ${isPaused ? "text-neutral-500" : "text-neutral-900"}`}>
              {formatConversions(campaign.conversionsRaw)}
            </span>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-6 animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Performance Trend Chart */}
          {trend && trend.length > 0 && (
            <div className="mb-8">
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-4">
                Performance Trend ({timeframeLabel})
              </h4>
              <div className="bg-neutral-50/50 rounded-lg p-4">
                <UnifiedGraphEngine
                  data={trend
                    // Filter out future dates (shouldn't happen but backend might return them)
                    .filter((p) => {
                      const date = new Date(p.date || p.label);
                      return date <= new Date();
                    })
                    .map((p) => ({
                      date: p.date || p.label,
                      revenue: p.value,
                    }))}
                  metrics={["revenue"]}
                  type="area"
                  height="180px"
                  showLegend={false}
                  showGrid={true}
                />
              </div>
            </div>
          )}

          {/* Show KPI grid when no ad sets (PMAX campaigns or campaigns without ad sets) */}
          {!adsetsLoading && adsets.length === 0 && (
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-4">
                Performance Metrics ({timeframeLabel})
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {/* Row 1: Core spend/revenue metrics */}
                <MetricCard label="Spend" value={formatCurrency(campaign.spendRaw)} />
                <MetricCard label="Revenue" value={formatCurrency(campaign.revenueRaw)} />
                <MetricCard 
                  label="ROAS" 
                  value={formatRoas(campaign.roasRaw)} 
                  colorClass={getRoasColorClass(campaign.roasRaw)}
                />
                {/* Row 2: Traffic metrics */}
                <MetricCard label="Impressions" value={formatConversions(campaign.impressionsRaw)} />
                <MetricCard label="Clicks" value={formatConversions(campaign.clicksRaw)} />
                <MetricCard label="CTR" value={formatPercent(campaign.ctrRaw)} />
                {/* Row 3: Cost efficiency metrics */}
                <MetricCard label="CPC" value={formatSmallCurrency(campaign.cpcRaw)} />
                <MetricCard label="CPM" value={formatSmallCurrency(campaign.cpmRaw)} />
                <MetricCard label="CPA" value={formatSmallCurrency(campaign.cpaRaw)} />
                {/* Row 4: Conversion metrics */}
                <MetricCard label="Conversions" value={formatConversions(campaign.conversionsRaw)} />
                <MetricCard label="Conv. Rate" value={formatPercent(campaign.conversionRateRaw)} />
                <MetricCard label="Conv. Value" value={formatCurrency(campaign.conversionValueRaw)} />
              </div>
            </div>
          )}

          {/* Ad Sets Section - only show when there are ad sets or loading */}
          {(adsetsLoading || adsets.length > 0) && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                Ad Sets {adsets.length > 0 && `(${adsets.length})`}
              </h4>

              {adsetsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 text-neutral-400 animate-spin" />
                  <span className="ml-2 text-sm text-neutral-500">Loading ad sets...</span>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    {visibleAdsets.map((adset) => (
                      <AdSetRow key={adset.id} adset={adset} />
                    ))}
                  </div>

                  {/* Show more button */}
                  {hasMoreAdsets && !showAllAdsets && (
                    <div className="mt-4 flex items-center justify-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowAllAdsets(true);
                        }}
                        className="text-xs font-medium text-neutral-400 hover:text-neutral-900 transition-colors flex items-center gap-1"
                      >
                        Show all ad sets
                        <ChevronDown className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* View Full Details button - commented out for now, dropdown is enough */}
          {/*
          <div className="mt-6 flex items-center justify-center">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewDetails?.();
              }}
              className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors flex items-center gap-1"
            >
              View Full Details
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
          */}
        </div>
      )}
    </div>
  );
}
