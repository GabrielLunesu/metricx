"use client";

/**
 * AnalyticsCampaignTable - Campaign table with multi-select and nested ad sets
 * 
 * WHAT: Data table showing campaigns with metrics, expandable for Meta ad sets
 * WHY: Allow users to view and select campaigns to filter analytics data
 * 
 * FEATURES:
 *   - Multi-select campaigns (row click or checkbox)
 *   - Client-side search by campaign name
 *   - Expandable Meta campaigns → show nested Ad Sets
 *   - Platform icons (Meta ∞ / Google G)
 *   - Status indicators (Active, Learning, Paused)
 *   - Metrics: Spend, Revenue, ROAS, Conv., CPA
 *   - Pagination with Prev/Next
 *   - Export button
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - Backend: /entity-performance/list
 */

import { useState, useMemo } from "react";
import { Search, ChevronRight, ChevronDown, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Currency symbols
 */
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

/**
 * Format metric value
 */
function formatValue(value, format, currency = "USD") {
  if (value === null || value === undefined) return "—";

  const symbol = CURRENCY_SYMBOLS[currency] || "$";

  switch (format) {
    case "currency":
      return `${symbol}${new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value)}`;

    case "currency_compact":
      if (Math.abs(value) >= 1000) {
        return `${symbol}${(value / 1000).toFixed(2)}k`;
      }
      return `${symbol}${new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value)}`;

    case "multiplier":
      return `${Number(value).toFixed(2)}x`;

    case "number":
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value);

    default:
      return String(value);
  }
}

/**
 * Get ROAS color class
 * Good ROAS is >= 2x (green), below that is neutral
 */
function getRoasColor(roas) {
  if (roas === null || roas === undefined) return "text-neutral-500";
  if (roas >= 2) return "text-emerald-600";
  return "text-neutral-500";
}

/**
 * Get status display info
 */
function getStatusInfo(status) {
  const normalized = (status || "").toLowerCase();

  if (normalized === "active" || normalized === "enabled") {
    return { label: "Active", dotClass: "active" };
  }
  if (normalized === "learning" || normalized === "learning_limited") {
    return { label: "Learning", dotClass: "learning" };
  }
  if (normalized === "paused") {
    return { label: "Paused", dotClass: "paused" };
  }
  if (normalized === "removed" || normalized === "deleted") {
    return { label: "Removed", dotClass: "removed" };
  }

  return { label: status || "Unknown", dotClass: "paused" };
}

/**
 * Platform Icon Component
 */
function PlatformIcon({ platform }) {
  const normalized = (platform || "").toLowerCase();

  if (normalized === "meta" || normalized === "facebook") {
    return (
      <div className="platform-icon">
        <svg className="w-3 h-3 text-neutral-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z"/>
        </svg>
      </div>
    );
  }

  if (normalized === "google") {
    return (
      <div className="platform-icon">
        <svg className="w-3 h-3 text-neutral-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
      </div>
    );
  }

  return (
    <div className="platform-icon">
      <span className="text-xs text-neutral-400">?</span>
    </div>
  );
}

/**
 * Campaign Row Component
 */
function CampaignRow({
  campaign,
  isSelected,
  isExpanded,
  onToggleSelect,
  onToggleExpand,
  canExpand,
  currency,
}) {
  const statusInfo = getStatusInfo(campaign.status);
  const cpa = campaign.conversions > 0 ? campaign.spend / campaign.conversions : null;
  const isPaused = statusInfo.dotClass === "paused" || statusInfo.dotClass === "removed";

  return (
    <tr
      className={`
        group border-b border-neutral-100 cursor-pointer transition-colors
        ${isSelected ? "selected bg-neutral-50" : "hover:bg-neutral-50"}
        ${isPaused ? "opacity-60 hover:opacity-100" : ""}
      `}
      onClick={onToggleSelect}
    >
      {/* Expand Chevron */}
      <td className="py-3 px-4 text-neutral-400 w-8">
        {canExpand ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="p-1 hover:text-neutral-600 transition-transform"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        ) : (
          <ChevronRight className="w-4 h-4 opacity-0" />
        )}
      </td>

      {/* Campaign Name + Platform */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <PlatformIcon platform={campaign.platform || campaign.provider} />
          <span className="font-medium text-neutral-900 truncate max-w-[250px]">
            {campaign.name}
          </span>
        </div>
      </td>

      {/* Status */}
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${statusInfo.dotClass}`} />
          <span className="text-neutral-600 text-xs">{statusInfo.label}</span>
        </div>
      </td>

      {/* Spend */}
      <td className="py-3 px-4 text-right font-medium text-neutral-900 tabular-nums tracking-tight">
        {formatValue(campaign.spend, "currency_compact", currency)}
      </td>

      {/* Revenue */}
      <td className="py-3 px-4 text-right font-medium text-neutral-900 tabular-nums tracking-tight">
        {formatValue(campaign.revenue, "currency_compact", currency)}
      </td>

      {/* ROAS */}
      <td className={`py-3 px-4 text-right font-medium tabular-nums tracking-tight ${getRoasColor(campaign.roas)}`}>
        {formatValue(campaign.roas, "multiplier")}
      </td>

      {/* Conversions */}
      <td className="py-3 px-4 text-right text-neutral-600 tabular-nums tracking-tight">
        {formatValue(campaign.conversions, "number")}
      </td>

      {/* CPA */}
      <td className="py-3 px-4 text-right text-neutral-600 tabular-nums tracking-tight">
        {formatValue(cpa, "currency", currency)}
      </td>
    </tr>
  );
}

/**
 * Ad Set Row Component (nested under campaign)
 */
function AdSetRow({ adSet, currency }) {
  const statusInfo = getStatusInfo(adSet.status);
  const cpa = adSet.conversions > 0 ? adSet.spend / adSet.conversions : null;

  return (
    <tr className="nested border-b border-neutral-100 bg-neutral-50/50">
      {/* Indent */}
      <td className="py-2.5 px-4" />

      {/* Name */}
      <td className="py-2.5 px-4">
        <div className="flex items-center gap-3 pl-6">
          <span className="w-1 h-1 rounded-full bg-neutral-300" />
          <span className="text-sm text-neutral-700 truncate max-w-[220px]">
            {adSet.name}
          </span>
        </div>
      </td>

      {/* Status */}
      <td className="py-2.5 px-4">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${statusInfo.dotClass}`} />
          <span className="text-neutral-500 text-xs">{statusInfo.label}</span>
        </div>
      </td>

      {/* Spend */}
      <td className="py-2.5 px-4 text-right text-sm text-neutral-600 tabular-nums">
        {formatValue(adSet.spend, "currency_compact", currency)}
      </td>

      {/* Revenue */}
      <td className="py-2.5 px-4 text-right text-sm text-neutral-600 tabular-nums">
        {formatValue(adSet.revenue, "currency_compact", currency)}
      </td>

      {/* ROAS */}
      <td className={`py-2.5 px-4 text-right text-sm tabular-nums ${getRoasColor(adSet.roas)}`}>
        {formatValue(adSet.roas, "multiplier")}
      </td>

      {/* Conversions */}
      <td className="py-2.5 px-4 text-right text-sm text-neutral-500 tabular-nums">
        {formatValue(adSet.conversions, "number")}
      </td>

      {/* CPA */}
      <td className="py-2.5 px-4 text-right text-sm text-neutral-500 tabular-nums">
        {formatValue(cpa, "currency", currency)}
      </td>
    </tr>
  );
}

/**
 * Main Campaign Table Component
 */
export default function AnalyticsCampaignTable({
  campaigns = [],
  selectedIds = [],
  onSelectionChange,
  loading = false,
  currency = "USD",
  // Pagination
  page = 1,
  pageSize = 25,
  total = 0,
  onPageChange,
  // Ad Sets
  adSetsMap = {},
  onExpandCampaign,
  expandedCampaignId = null,
  adSetsLoading = false,
  // Export
  onExport,
}) {
  // Local search state
  const [searchQuery, setSearchQuery] = useState("");

  // Filter campaigns by search query (client-side)
  const filteredCampaigns = useMemo(() => {
    if (!searchQuery.trim()) return campaigns;

    const query = searchQuery.toLowerCase();
    return campaigns.filter((c) =>
      c.name?.toLowerCase().includes(query)
    );
  }, [campaigns, searchQuery]);

  // Toggle campaign selection
  const toggleSelect = (campaignId) => {
    if (selectedIds.includes(campaignId)) {
      onSelectionChange(selectedIds.filter((id) => id !== campaignId));
    } else {
      onSelectionChange([...selectedIds, campaignId]);
    }
  };

  // Toggle campaign expansion (for Meta campaigns)
  const toggleExpand = (campaignId) => {
    if (expandedCampaignId === campaignId) {
      onExpandCampaign(null);
    } else {
      onExpandCampaign(campaignId);
    }
  };

  // Check if campaign can expand (Meta only)
  const canExpand = (campaign) => {
    const platform = (campaign.platform || campaign.provider || "").toLowerCase();
    return platform === "meta" || platform === "facebook";
  };

  // Pagination info
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);
  const hasNextPage = endItem < total;
  const hasPrevPage = page > 1;

  // Loading skeleton
  if (loading && campaigns.length === 0) {
    return (
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="h-10 w-72 bg-neutral-100 rounded-lg animate-pulse" />
          <div className="flex gap-2">
            <div className="h-8 w-20 bg-neutral-100 rounded animate-pulse" />
            <div className="h-8 w-20 bg-neutral-100 rounded animate-pulse" />
          </div>
        </div>
        <div className="analytics-table">
          <table className="w-full">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200">
                <th className="py-3 px-4 w-8" />
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase">Campaign</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase">Status</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase">Spend</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase">Revenue</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase">ROAS</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase">Conv.</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase">CPA</th>
              </tr>
            </thead>
            <tbody>
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i} className="border-b border-neutral-100">
                  <td className="py-3 px-4"><div className="w-4 h-4 bg-neutral-100 rounded animate-pulse" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-48 bg-neutral-100 rounded animate-pulse" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-16 bg-neutral-100 rounded animate-pulse" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-20 bg-neutral-100 rounded animate-pulse ml-auto" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-20 bg-neutral-100 rounded animate-pulse ml-auto" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-12 bg-neutral-100 rounded animate-pulse ml-auto" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-12 bg-neutral-100 rounded animate-pulse ml-auto" /></td>
                  <td className="py-3 px-4"><div className="h-4 w-16 bg-neutral-100 rounded animate-pulse ml-auto" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="analytics-search"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="btn-sm"
            disabled
          >
            Columns
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="btn-sm"
            onClick={onExport}
          >
            Export
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="analytics-table overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[800px]">
          <thead>
            <tr className="bg-neutral-50 border-b border-neutral-200">
              <th className="py-3 px-4 w-8" />
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide">
                Campaign
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide">
                Status
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide text-right">
                Spend
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide text-right">
                Revenue
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide text-right">
                ROAS
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide text-right">
                Conv.
              </th>
              <th className="py-3 px-4 text-xs font-medium text-neutral-500 uppercase tracking-wide text-right">
                CPA
              </th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {filteredCampaigns.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-neutral-500">
                  {searchQuery
                    ? "No campaigns match your search"
                    : "No campaigns found"}
                </td>
              </tr>
            ) : (
              filteredCampaigns.map((campaign) => (
                <>
                  <CampaignRow
                    key={campaign.id}
                    campaign={campaign}
                    isSelected={selectedIds.includes(campaign.id)}
                    isExpanded={expandedCampaignId === campaign.id}
                    onToggleSelect={() => toggleSelect(campaign.id)}
                    onToggleExpand={() => toggleExpand(campaign.id)}
                    canExpand={canExpand(campaign)}
                    currency={currency}
                  />
                  {/* Nested Ad Sets */}
                  {expandedCampaignId === campaign.id && (
                    <>
                      {adSetsLoading ? (
                        <tr className="nested bg-neutral-50/50">
                          <td colSpan={8} className="py-4 text-center text-neutral-500 text-sm">
                            Loading ad sets...
                          </td>
                        </tr>
                      ) : adSetsMap[campaign.id]?.length > 0 ? (
                        adSetsMap[campaign.id].map((adSet) => (
                          <AdSetRow
                            key={adSet.id}
                            adSet={adSet}
                            currency={currency}
                          />
                        ))
                      ) : (
                        <tr className="nested bg-neutral-50/50">
                          <td colSpan={8} className="py-4 text-center text-neutral-500 text-sm">
                            No ad sets found
                          </td>
                        </tr>
                      )}
                    </>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-2">
        <span className="text-xs text-neutral-400">
          Showing {startItem}-{endItem} of {total} campaigns
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="btn-sm"
            disabled={!hasPrevPage}
            onClick={() => onPageChange(page - 1)}
          >
            Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="btn-sm"
            disabled={!hasNextPage}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </section>
  );
}
