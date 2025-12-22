"use client";
/**
 * EntityTrendChart
 * =================
 *
 * WHAT: Lightweight timeseries chart for a single entity (ad set / ad / creative).
 * WHY: Entity-performance endpoints currently only provide a single-metric trend series.
 *
 * DATA:
 *   - trend: [{ date: "YYYY-MM-DD", value: number|null }]
 *   - trendMetric: "revenue" | "roas"
 */

import { useMemo } from "react";
import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { Info } from "lucide-react";

const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

function formatDateLabel(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatValue(value, trendMetric, currency) {
  if (value === null || value === undefined) return "—";
  if (trendMetric === "roas") return `${Number(value).toFixed(2)}x`;
  const symbol = CURRENCY_SYMBOLS[currency] || "$";
  const n = Number(value) || 0;
  return `${symbol}${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function CustomTooltip({ active, payload, label, trendMetric, currency }) {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  return (
    <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-xl px-3 py-2 shadow-lg">
      <p className="text-[10px] text-slate-500 mb-1">{formatDateLabel(label)}</p>
      <p className="text-sm font-semibold text-slate-900">{formatValue(v, trendMetric, currency)}</p>
    </div>
  );
}

export default function EntityTrendChart({
  title = "Entity trend",
  subtitle = "Daily trend (single metric)",
  trend = [],
  trendMetric = "revenue",
  currency = "USD",
  loading = false,
  disclaimer,
}) {
  const data = useMemo(
    () =>
      (trend || []).map((p) => ({
        date: p.date,
        value: p.value ?? 0,
      })),
    [trend]
  );

  if (loading) {
    return (
      <div className="dashboard-module min-h-[450px] animate-pulse">
        <div className="h-6 w-40 bg-slate-200/50 rounded-lg mb-4" />
        <div className="h-80 bg-slate-200/30 rounded-2xl" />
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="dashboard-module min-h-[450px] flex flex-col justify-center items-center text-center">
        <p className="text-slate-700 font-medium">No trend available</p>
        <p className="text-xs text-slate-400 mt-1">Try a wider date range or a different entity.</p>
      </div>
    );
  }

  const symbol = CURRENCY_SYMBOLS[currency] || "$";

  return (
    <div className="dashboard-module min-h-[450px] flex flex-col">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">{subtitle}</p>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
        </div>
        <div className="px-2.5 py-1 rounded-full text-[10px] font-medium bg-slate-900/5 text-slate-600">
          {trendMetric === "roas" ? "ROAS" : `Revenue (${symbol})`}
        </div>
      </div>

      <div className="flex-1 min-h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="entityTrendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.28} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickFormatter={formatDateLabel}
              interval="preserveStartEnd"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              width={64}
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickFormatter={(v) => (trendMetric === "roas" ? `${Number(v).toFixed(1)}x` : `${symbol}${Math.round(Number(v) || 0)}`)}
            />
            <Tooltip content={<CustomTooltip trendMetric={trendMetric} currency={currency} />} />
            <Area type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} fill="url(#entityTrendFill)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {(disclaimer || trendMetric) && (
        <div className="mt-3 flex items-start gap-2 text-xs text-slate-400">
          <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
          <p>{disclaimer || "This trend comes from entity-performance snapshots and currently supports a single metric."}</p>
        </div>
      )}
    </div>
  );
}

