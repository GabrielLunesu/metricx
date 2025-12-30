/**
 * AdSetRow Component
 * ==================
 *
 * WHAT: Simple nested row for ad sets within expanded campaign card
 * WHY: Shows ad set performance in a compact format
 *
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - ui/components/campaigns/CampaignCard.jsx (parent)
 */

import { Layers } from "lucide-react";
import { normalizeStatus } from "./StatusBadge";

/**
 * Format currency for display
 */
function formatCurrency(value) {
  if (value == null) return "—";
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}k`;
  }
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

/**
 * Format ROAS for display
 */
function formatRoas(value) {
  if (value == null) return "—";
  return `${value.toFixed(1)}x`;
}

/**
 * AdSetRow - Nested ad set row within expanded campaign.
 *
 * @param {Object} props
 * @param {Object} props.adset - Ad set data { id, name, spend, roas, status }
 * @param {Function} [props.onClick] - Optional click handler
 *
 * @example
 * <AdSetRow adset={{ id: "1", name: "US_Broad_18-65", spend: 4010, roas: 2.1, status: "active" }} />
 */
export default function AdSetRow({ adset, onClick }) {
  const { name, spend, roas, status } = adset;
  const normalizedStatus = normalizeStatus(status);
  const isPaused = normalizedStatus === "paused" || normalizedStatus === "archived";

  // Status dot color
  const statusDotColor = normalizedStatus === "active" 
    ? "bg-emerald-500" 
    : normalizedStatus === "learning"
    ? "bg-amber-500 animate-pulse"
    : "bg-neutral-300";

  return (
    <div
      onClick={onClick}
      className={`
        flex items-center justify-between p-3 rounded-lg
        border border-neutral-100 bg-neutral-50/30
        hover:bg-neutral-50 hover:border-neutral-200
        transition-all cursor-pointer
        ${isPaused ? "opacity-60" : ""}
      `}
    >
      {/* Left: Icon + Name */}
      <div className="flex items-center gap-3 min-w-0">
        <Layers className="w-4 h-4 text-neutral-400 flex-shrink-0" />
        <span className="text-sm font-medium text-neutral-700 truncate">
          {name}
        </span>
      </div>

      {/* Right: Metrics + Status */}
      <div className="flex items-center gap-6 text-sm text-neutral-600 tabular-nums flex-shrink-0">
        <span className="hidden sm:inline-block w-20 text-right">
          {formatCurrency(spend)}
        </span>
        <span className="hidden sm:inline-block w-16 text-right">
          {formatRoas(roas)}
        </span>
        <div className={`w-2 h-2 rounded-full ${statusDotColor}`} />
      </div>
    </div>
  );
}
