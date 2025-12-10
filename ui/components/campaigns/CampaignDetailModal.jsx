/**
 * CampaignDetailModal Component
 * =============================
 *
 * WHAT: Full-screen modal showing campaign details with KPIs, chart, adsets, and creatives
 * WHY: Replaces separate /campaigns/[id] pages - all detail in one modal
 *
 * SECTIONS:
 *   1. Header: Platform icon, title, status, ID, date range
 *   2. KPI Strip: Spend, ROAS, Conversions, CTR with vs prev period
 *   3. Performance Chart: Revenue/spend over time
 *   4. Ad Set Selector: Dropdown to filter by adset (Meta + Google hierarchy)
 *   5. Creatives Section: Meta only - thumbnail grid with KPIs
 *
 * DATA FLOW:
 *   - Parent passes campaign row data on open
 *   - Modal fetches children (adsets/ads) and creatives via API
 *   - All calculations done server-side, UI is dumb
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/analytics/page.jsx (pattern to follow)
 *   - ui/lib/api.js (fetchEntityPerformance for children)
 *   - backend/app/routers/entity_performance.py (data source)
 */

"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { X, Calendar, TrendingUp, TrendingDown, DollarSign, BarChart2, ShoppingBag, MousePointerClick, Image, Video, Layers, Play, ExternalLink, ChevronDown } from "lucide-react";
import { Dialog, Transition } from "@headlessui/react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip
} from "recharts";
import StatusBadge from "./StatusBadge";
import PlatformBadge from "./PlatformBadge";
import TrendSparkline from "./TrendSparkline";
import { fetchEntityPerformance } from "@/lib/api";
import { formatMetricValue, formatDelta } from "@/lib/utils";

/**
 * KPI metric definitions for the modal strip.
 */
const MODAL_KPIS = [
  { key: "spend", label: "Spend", format: "currency", icon: DollarSign, inverse: true },
  { key: "roas", label: "ROAS", format: "multiplier", icon: BarChart2, inverse: false, highlight: true },
  { key: "conversions", label: "Conversions", format: "number", icon: ShoppingBag, inverse: false },
  { key: "ctr_pct", label: "CTR", format: "percent", icon: MousePointerClick, inverse: false },
];

/**
 * KpiCard - Single metric card for the modal.
 */
function KpiCard({ label, value, format, delta, inverse, Icon, highlight }) {
  const deltaInfo = delta != null ? formatDelta(delta, inverse) : null;
  const isPositive = deltaInfo?.isGood;

  return (
    <div className={`bg-white p-5 rounded-xl border border-slate-100 shadow-sm ${highlight ? "ring-1 ring-cyan-200/50" : ""}`}>
      <div className="flex justify-between items-start mb-2">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
        {Icon && <Icon className="w-4 h-4 text-slate-300" />}
      </div>
      <p className={`text-2xl font-semibold tracking-tight ${highlight ? "text-emerald-600" : "text-slate-900"}`}>
        {formatMetricValue(value, format)}
      </p>
      {deltaInfo ? (
        <div className={`flex items-center gap-1 mt-1 text-[11px] font-medium ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{deltaInfo.text} vs prev</span>
        </div>
      ) : (
        <span className="text-xs text-slate-400 mt-1 block">—</span>
      )}
    </div>
  );
}

/**
 * AdSetSelector - Dropdown to filter by adset.
 */
function AdSetSelector({ adsets, selectedId, onSelect, loading }) {
  if (!adsets || adsets.length === 0) return null;

  return (
    <div className="relative">
      <label className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2 block">
        Filter by Ad Set
      </label>
      <div className="relative">
        <select
          value={selectedId || "all"}
          onChange={(e) => onSelect(e.target.value === "all" ? null : e.target.value)}
          disabled={loading}
          className="w-full px-4 py-2.5 pr-10 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 appearance-none cursor-pointer hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50"
        >
          <option value="all">All Ad Sets ({adsets.length})</option>
          {adsets.map((adset) => (
            <option key={adset.id} value={adset.id}>
              {adset.name} • {formatMetricValue(adset.roas, "multiplier")} ROAS
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
      </div>
    </div>
  );
}

/**
 * CreativeCard - Single creative with thumbnail and KPIs.
 */
function CreativeCard({ creative }) {
  const { name, thumbnail_url, image_url, media_type, spend, roas, ctr_pct } = creative;

  // Media type icon and label
  const mediaConfig = {
    image: { Icon: Image, label: "Static Image" },
    video: { Icon: Video, label: "Video" },
    carousel: { Icon: Layers, label: "Carousel" },
    unknown: { Icon: Image, label: "Creative" },
  };
  const { Icon: MediaIcon, label: mediaLabel } = mediaConfig[media_type] || mediaConfig.unknown;

  // ROAS color coding
  const roasColor = roas >= 3 ? "bg-emerald-500" : roas >= 1.5 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="group bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-lg transition-all duration-300">
      {/* Thumbnail */}
      <div className="relative h-48 bg-slate-100 overflow-hidden">
        {thumbnail_url || image_url ? (
          <img
            src={thumbnail_url || image_url}
            alt={name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <MediaIcon className="w-12 h-12 text-slate-300" />
          </div>
        )}

        {/* Media type badge */}
        <div className="absolute top-3 left-3 bg-white/90 backdrop-blur px-2 py-1 rounded text-[10px] font-bold text-slate-700 uppercase tracking-wide border border-white/50">
          {mediaLabel}
        </div>

        {/* Video play overlay */}
        {media_type === "video" && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 bg-white/30 backdrop-blur rounded-full flex items-center justify-center border border-white/50">
            <Play className="w-5 h-5 text-white drop-shadow-md fill-white" />
          </div>
        )}

        {/* ROAS badge */}
        {roas != null && (
          <div className={`absolute bottom-3 right-3 ${roasColor} text-white px-2 py-1 rounded shadow-lg text-[10px] font-bold`}>
            ROAS {formatMetricValue(roas, "multiplier")}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-slate-900 truncate">{name || "Untitled Creative"}</h4>
          </div>
          <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0 ml-2">
            <ExternalLink className="w-3 h-3 text-slate-500" />
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-2 py-3 border-t border-slate-50">
          <div>
            <p className="text-[10px] text-slate-400 uppercase">Spend</p>
            <p className="text-sm font-medium text-slate-700">{formatMetricValue(spend, "currency")}</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-400 uppercase">CTR</p>
            <p className={`text-sm font-medium ${ctr_pct >= 1.5 ? "text-emerald-600" : "text-slate-600"}`}>
              {formatMetricValue(ctr_pct, "percent")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * CreativesSection - Grid of creative cards (Meta only).
 */
function CreativesSection({ creatives, loading }) {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-6 w-48 bg-slate-200 rounded mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-64 bg-slate-200 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!creatives || creatives.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-slate-900">Top Performing Creatives</h3>
        {creatives.length > 3 && (
          <button className="text-xs font-medium text-cyan-600 hover:text-cyan-700">
            View All ({creatives.length})
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {creatives.slice(0, 6).map((creative) => (
          <CreativeCard key={creative.id} creative={creative} />
        ))}
      </div>
    </div>
  );
}

/**
 * PerformanceChart - Recharts-based performance chart for campaign modal.
 *
 * WHAT: Renders an area chart with revenue data over time
 * WHY: Uses Recharts for consistent chart behavior across the app
 *
 * @param {Array} trend - Array of trend data points with date and value
 */
function PerformanceChart({ trend }) {
  if (!trend || trend.length === 0) return null;

  // Transform trend data for recharts (expects {date, revenue} format)
  const chartData = trend.map((point) => ({
    date: point.date || point.label,
    revenue: point.value ?? point.revenue ?? 0,
  }));

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;

    const date = new Date(label);
    const formattedDate = date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });

    return (
      <div className="bg-white rounded-xl p-3 min-w-[150px] shadow-xl border border-slate-100">
        <div className="text-xs font-semibold text-slate-800 mb-2">{formattedDate}</div>
        <div className="space-y-1.5">
          {payload.map((entry) => (
            <div key={entry.dataKey} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-[10px] text-slate-600">Revenue</span>
              </div>
              <span className="text-xs font-semibold text-slate-800">
                ${entry.value?.toLocaleString() ?? "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm mb-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-semibold text-slate-800">Performance Over Time</h3>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-500" />
            Revenue
          </span>
        </div>
      </div>
      <div className="w-full h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              tick={{ fill: "#64748b", fontSize: 11 }}
              minTickGap={40}
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
              }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              width={50}
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickFormatter={(value) => {
                if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                return `$${value}`;
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#22d3ee"
              fill="url(#revenueGradient)"
              strokeWidth={2}
              connectNulls
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: "#22d3ee" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/**
 * CampaignDetailModal - Main modal component.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Modal visibility
 * @param {Function} props.onClose - Close handler
 * @param {Object} props.campaign - Campaign row data from parent
 * @param {string} props.workspaceId - Current workspace ID
 * @param {string} props.timeframe - Current timeframe filter
 *
 * @example
 * <CampaignDetailModal
 *   isOpen={modalOpen}
 *   onClose={() => setModalOpen(false)}
 *   campaign={selectedCampaign}
 *   workspaceId={workspaceId}
 *   timeframe="7d"
 * />
 */
export default function CampaignDetailModal({
  isOpen,
  onClose,
  campaign,
  workspaceId,
  timeframe = "7d",
}) {
  const [adsets, setAdsets] = useState([]);
  const [creatives, setCreatives] = useState([]);
  const [selectedAdsetId, setSelectedAdsetId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creativesLoading, setCreativesLoading] = useState(false);

  // Determine if this is a Meta campaign (show creatives)
  const isMeta = campaign?.platform?.toLowerCase() === "meta";

  // Fetch adsets when modal opens
  const fetchAdsets = useCallback(async () => {
    if (!campaign?.id || !workspaceId) return;

    setLoading(true);
    try {
      const days = timeframe === "30d" ? 30 : 7;
      const result = await fetchEntityPerformance({
        workspaceId,
        entityType: "adset",
        timeRange: { last_n_days: days },
        limit: 50,
        sortBy: "roas",
        sortDir: "desc",
        status: "all",
        campaignId: campaign.id, // This maps to parent_id in the API
      });
      // Map items to include required fields
      const items = (result?.items || []).map((item) => ({
        ...item,
        roas: item.roas ?? (item.spend > 0 ? item.revenue / item.spend : null),
      }));
      setAdsets(items);
    } catch (err) {
      console.error("Failed to fetch adsets:", err);
      setAdsets([]);
    } finally {
      setLoading(false);
    }
  }, [campaign?.id, workspaceId, timeframe]);

  // Fetch creatives (Meta only)
  const fetchCreatives = useCallback(async () => {
    if (!campaign?.id || !workspaceId || !isMeta) return;

    setCreativesLoading(true);
    try {
      const days = timeframe === "30d" ? 30 : 7;
      // Fetch ads/creatives under this campaign
      const result = await fetchEntityPerformance({
        workspaceId,
        entityType: "ad",
        timeRange: { last_n_days: days },
        limit: 20,
        sortBy: "roas",
        sortDir: "desc",
        status: "all",
        campaignId: campaign.id, // This maps to parent_id in the API
      });
      // Map items to include required fields for creative cards
      const items = (result?.items || []).map((item) => ({
        ...item,
        roas: item.roas ?? (item.spend > 0 ? item.revenue / item.spend : null),
        ctr_pct: item.ctr_pct ?? (item.impressions > 0 ? (item.clicks / item.impressions) * 100 : null),
      }));
      setCreatives(items);
    } catch (err) {
      console.error("Failed to fetch creatives:", err);
      setCreatives([]);
    } finally {
      setCreativesLoading(false);
    }
  }, [campaign?.id, workspaceId, timeframe, isMeta]);

  // Fetch data when modal opens
  useEffect(() => {
    if (isOpen && campaign?.id) {
      fetchAdsets();
      if (isMeta) {
        fetchCreatives();
      }
    }
  }, [isOpen, campaign?.id, fetchAdsets, fetchCreatives, isMeta]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setAdsets([]);
      setCreatives([]);
      setSelectedAdsetId(null);
    }
  }, [isOpen]);

  if (!campaign) return null;

  // Build KPI data from campaign row
  const kpiData = {
    spend: campaign.spendRaw ?? campaign.spend ?? 0,
    roas: campaign.roasRaw ?? campaign.roas ?? null,
    conversions: campaign.conversionsRaw ?? campaign.conversions ?? 0,
    ctr_pct: campaign.ctr_pctRaw ?? campaign.ctr_pct ?? null,
  };

  // Format campaign ID for display
  const displayId = campaign.external_id || campaign.id?.slice(0, 8);

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="fixed inset-0 z-[100]" onClose={onClose}>
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm" />
        </Transition.Child>

        {/* Modal */}
        <div className="fixed inset-0 flex items-center justify-center p-4 md:p-8">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95 translate-y-4"
            enterTo="opacity-100 scale-100 translate-y-0"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100 translate-y-0"
            leaveTo="opacity-0 scale-95 translate-y-4"
          >
            <Dialog.Panel className="bg-white w-full max-w-5xl h-[90vh] md:h-[85vh] rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-white/40 ring-1 ring-slate-900/5">
              {/* Header */}
              <div className="flex items-start justify-between p-6 md:p-8 border-b border-slate-100 bg-white/80 backdrop-blur z-10">
                <div className="flex items-start gap-5">
                  <PlatformBadge platform={campaign.platform} size="lg" />
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <Dialog.Title className="text-xl md:text-2xl font-semibold tracking-tight text-slate-900">
                        {campaign.name}
                      </Dialog.Title>
                      <StatusBadge status={campaign.status} size="md" />
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 text-sm">
                      <span>ID: {displayId}</span>
                      <span className="w-1 h-1 bg-slate-300 rounded-full" />
                      <span>{timeframe === "30d" ? "Last 30 Days" : "Last 7 Days"}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button className="hidden md:flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition-all">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    {timeframe === "30d" ? "Last 30 Days" : "Last 7 Days"}
                  </button>
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {/* Body (Scrollable) */}
              <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-50/50">
                {/* KPI Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  {MODAL_KPIS.map((kpi) => (
                    <KpiCard
                      key={kpi.key}
                      label={kpi.label}
                      value={kpiData[kpi.key]}
                      format={kpi.format}
                      delta={campaign[`${kpi.key}_delta`]}
                      inverse={kpi.inverse}
                      Icon={kpi.icon}
                      highlight={kpi.highlight}
                    />
                  ))}
                </div>

                {/* Performance Chart */}
                {campaign.trend && campaign.trend.length > 0 && (
                  <PerformanceChart trend={campaign.trend} />
                )}

                {/* Ad Set Selector */}
                {adsets.length > 0 && (
                  <div className="mb-8">
                    <AdSetSelector
                      adsets={adsets}
                      selectedId={selectedAdsetId}
                      onSelect={setSelectedAdsetId}
                      loading={loading}
                    />
                  </div>
                )}

                {/* Creatives Section (Meta only) */}
                {isMeta && (
                  <CreativesSection creatives={creatives} loading={creativesLoading} />
                )}

                {/* Empty state for Google without adsets */}
                {!isMeta && adsets.length === 0 && !loading && (
                  <div className="text-center py-12 text-slate-500">
                    <BarChart2 className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                    <p className="text-sm">No ad sets found for this campaign.</p>
                    <p className="text-xs text-slate-400 mt-1">This campaign may use a different structure.</p>
                  </div>
                )}
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
