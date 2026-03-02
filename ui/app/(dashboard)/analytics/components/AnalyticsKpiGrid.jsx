"use client";

/**
 * AnalyticsKpiGrid - 8 KPI cards matching homepage glass design
 *
 * WHAT: Displays 8 key metrics in glass cards with large numbers
 * WHY: Quick overview of performance metrics at a glance
 *
 * DESIGN:
 *   - Matches homepage KpiCardsModule: glass cards, large numbers, delta badges
 *   - Responsive grid: 2 cols → 4 cols → 8 cols
 *   - Hover lift animation
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/dashboard/components/KpiCardsModule.jsx (design ref)
 */

import { motion } from "framer-motion";

/**
 * KPI metric definitions
 */
const KPIS = [
  { key: "revenue", label: "Revenue", format: "currency", deltaColor: "emerald" },
  { key: "spend", label: "Ad Spend", format: "currency", inverse: true, deltaColor: "amber" },
  { key: "cpc", label: "CPC", format: "currency_decimal", inverse: true, deltaColor: "amber" },
  { key: "roas", label: "ROAS", format: "multiplier", deltaColor: "violet" },
  { key: "conversions", label: "Orders", format: "number", deltaColor: "blue" },
  { key: "profit", label: "Profit", format: "currency", calculated: true, deltaColor: "emerald" },
  { key: "aov", label: "AOV", format: "currency_decimal", deltaColor: "blue" },
  { key: "cpa", label: "CPA", format: "currency_decimal", calculated: true, inverse: true, deltaColor: "amber" },
];

const CURRENCY_SYMBOLS = { USD: "$", EUR: "€", GBP: "£", CAD: "C$", AUD: "A$" };

/** Delta badge color classes — matches homepage */
const DELTA_COLORS = {
  emerald: {
    positive: "bg-emerald-500/5 border-emerald-500/10 text-emerald-600",
    negative: "bg-red-500/5 border-red-500/10 text-red-600",
  },
  amber: {
    positive: "bg-red-500/5 border-red-500/10 text-red-600",
    negative: "bg-emerald-500/5 border-emerald-500/10 text-emerald-600",
  },
  violet: {
    positive: "bg-violet-500/5 border-violet-500/10 text-violet-600",
    negative: "bg-red-500/5 border-red-500/10 text-red-600",
  },
  blue: {
    positive: "bg-blue-500/5 border-blue-500/10 text-blue-600",
    negative: "bg-red-500/5 border-red-500/10 text-red-600",
  },
};

function formatValue(value, format, currency = "USD") {
  if (value === null || value === undefined) return "—";
  const symbol = CURRENCY_SYMBOLS[currency] || "$";

  switch (format) {
    case "currency":
      if (Math.abs(value) >= 10000) return `${symbol}${(value / 1000).toFixed(1)}K`;
      return `${symbol}${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)}`;
    case "currency_decimal":
      return `${symbol}${new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}`;
    case "multiplier":
      return `${Number(value).toFixed(2)}x`;
    case "number":
      if (value >= 10000) return `${(value / 1000).toFixed(1)}K`;
      return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
    default:
      return String(value);
  }
}

function getDeltaBadge(deltaPct, colorScheme, inverse = false) {
  if (deltaPct === null || deltaPct === undefined) return null;
  const isPositive = inverse ? deltaPct <= 0 : deltaPct >= 0;
  const cls = DELTA_COLORS[colorScheme]?.[isPositive ? "positive" : "negative"] || DELTA_COLORS.emerald.positive;
  const text = `${deltaPct >= 0 ? "+" : ""}${(deltaPct * 100).toFixed(1)}%`;
  return { cls, text };
}

export default function AnalyticsKpiGrid({ data, loading = false, currency = "USD" }) {
  const metrics = {
    revenue: data?.revenue ?? null,
    spend: data?.spend ?? null,
    cpc: data?.cpc ?? null,
    roas: data?.roas ?? null,
    conversions: data?.conversions ?? null,
    aov: data?.aov ?? null,
    profit: data?.revenue != null && data?.spend != null ? data.revenue - data.spend : null,
    cpa: data?.conversions > 0 && data?.spend != null ? data.spend / data.conversions : null,
  };

  const deltas = {
    revenue: data?.delta_revenue ?? data?.revenue_delta_pct ?? null,
    spend: data?.delta_spend ?? data?.spend_delta_pct ?? null,
    cpc: data?.delta_cpc ?? data?.cpc_delta_pct ?? null,
    roas: data?.delta_roas ?? data?.roas_delta_pct ?? null,
    conversions: data?.delta_conversions ?? data?.conversions_delta_pct ?? null,
    aov: data?.delta_aov ?? data?.aov_delta_pct ?? null,
    profit: data?.delta_profit ?? null,
    cpa: data?.delta_cpa ?? null,
  };

  if (loading || !data) {
    return (
      <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2 md:gap-3">
        {KPIS.map((kpi) => (
          <div
            key={kpi.key}
            className="bg-white/40 glass rounded-2xl p-4 md:p-5 border border-white/60 animate-pulse"
          >
            <div className="h-3 w-14 bg-neutral-200/50 rounded mb-3" />
            <div className="h-7 w-16 bg-neutral-200/50 rounded" />
          </div>
        ))}
      </section>
    );
  }

  return (
    <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2 md:gap-3">
      {KPIS.map((kpi, idx) => {
        const badge = getDeltaBadge(deltas[kpi.key], kpi.deltaColor, kpi.inverse);

        return (
          <motion.div
            key={kpi.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="bg-white/40 glass rounded-2xl p-4 md:p-5 border border-white/60
                       hover:bg-white/60 hover:-translate-y-0.5
                       transition-all duration-300"
          >
            {/* Header: Label + Delta */}
            <div className="flex items-start justify-between gap-1 mb-1">
              <span className="text-xs font-medium text-neutral-500 tracking-wide">
                {kpi.label}
              </span>
              {badge && (
                <div className={`px-1.5 py-0.5 rounded-md border text-[10px] font-semibold whitespace-nowrap ${badge.cls}`}>
                  {badge.text}
                </div>
              )}
            </div>

            {/* Value */}
            <div className="text-xl md:text-2xl font-medium text-neutral-900 number-display tracking-tighter">
              {formatValue(metrics[kpi.key], kpi.format, currency)}
            </div>
          </motion.div>
        );
      })}
    </section>
  );
}
