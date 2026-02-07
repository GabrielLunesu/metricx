"use client";

/**
 * FinanceKpiCards - 4 KPI cards for finance overview
 * 
 * WHAT: Displays Total Revenue, Total Spend, Gross Profit, Net ROAS
 * WHY: Quick overview of financial performance at a glance
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 */

import { ArrowUpRight, ArrowDownRight } from "lucide-react";

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
 * Format currency value
 */
function formatCurrency(value, currency = "EUR") {
  if (value === null || value === undefined) return "—";
  const symbol = CURRENCY_SYMBOLS[currency] || "€";
  
  if (Math.abs(value) >= 1000000) {
    return `${symbol}${(value / 1000000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `${symbol}${(value / 1000).toFixed(1)}k`;
  }
  return `${symbol}${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)}`;
}

/**
 * Format delta percentage
 */
function formatDelta(deltaPct) {
  if (deltaPct === null || deltaPct === undefined) return null;
  const pct = (deltaPct * 100).toFixed(1);
  return `${deltaPct >= 0 ? "+" : ""}${pct}%`;
}

/**
 * Single KPI Card
 */
function KpiCard({ label, value, delta, isGoodWhenUp = true, loading }) {
  const deltaValue = formatDelta(delta);
  const isPositive = delta >= 0;
  const isGood = isGoodWhenUp ? isPositive : !isPositive;

  if (loading) {
    return (
      <div className="p-3 md:p-5 border border-neutral-200 bg-white rounded-xl">
        <div className="h-3 w-16 md:w-24 bg-neutral-100 rounded animate-pulse mb-2 md:mb-3" />
        <div className="h-6 md:h-7 w-24 md:w-32 bg-neutral-100 rounded animate-pulse mb-2 md:mb-3" />
        <div className="h-3 w-16 md:w-20 bg-neutral-100 rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="p-3 md:p-5 border border-neutral-200 bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-shadow hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)]">
      <div className="flex items-center justify-between mb-1 md:mb-2">
        <span className="text-[10px] md:text-xs font-medium text-neutral-500 uppercase tracking-wider">
          {label}
        </span>
      </div>
      <div className="text-lg md:text-2xl font-semibold text-neutral-900 tracking-tight">
        {value}
      </div>
      {deltaValue && (
        <div className="flex items-center gap-1 mt-3">
          {isPositive ? (
            <ArrowUpRight className={`w-3 h-3 ${isGood ? "text-emerald-600" : "text-neutral-500"}`} />
          ) : (
            <ArrowDownRight className={`w-3 h-3 ${isGood ? "text-emerald-600" : "text-neutral-500"}`} />
          )}
          <span className={`text-xs font-medium ${isGood ? "text-emerald-600" : "text-neutral-500"}`}>
            {deltaValue}
          </span>
          <span className="text-xs text-neutral-400 ml-1">vs last month</span>
        </div>
      )}
    </div>
  );
}

/**
 * Main Finance KPI Cards Component
 */
export default function FinanceKpiCards({
  summary,
  loading = false,
  currency = "EUR",
}) {
  // Extract values from summary
  const totalRevenue = summary?.totalRevenue?.rawValue ?? 0;
  const totalSpend = summary?.totalSpend?.rawValue ?? 0;
  const grossProfit = summary?.grossProfit?.rawValue ?? (totalRevenue - totalSpend);
  const netRoas = summary?.netRoas?.rawValue ?? (totalSpend > 0 ? totalRevenue / totalSpend : 0);

  // Extract deltas (convert from formatted string if needed)
  const revenueDelta = summary?.totalRevenue?.delta 
    ? parseFloat(summary.totalRevenue.delta) / 100 
    : null;
  const spendDelta = summary?.totalSpend?.delta 
    ? parseFloat(summary.totalSpend.delta) / 100 
    : null;
  const profitDelta = summary?.grossProfit?.delta 
    ? parseFloat(summary.grossProfit.delta) / 100 
    : null;
  const roasDelta = summary?.netRoas?.delta 
    ? parseFloat(summary.netRoas.delta) 
    : null;

  return (
    <section className="grid grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
      <KpiCard
        label="Total Revenue"
        value={formatCurrency(totalRevenue, currency)}
        delta={revenueDelta}
        isGoodWhenUp={true}
        loading={loading}
      />
      <KpiCard
        label="Total Spend"
        value={formatCurrency(totalSpend, currency)}
        delta={spendDelta}
        isGoodWhenUp={false}
        loading={loading}
      />
      <KpiCard
        label="Gross Profit"
        value={formatCurrency(grossProfit, currency)}
        delta={profitDelta}
        isGoodWhenUp={true}
        loading={loading}
      />
      <KpiCard
        label="Net ROAS"
        value={netRoas > 0 ? `${netRoas.toFixed(2)}x` : "—"}
        delta={roasDelta}
        isGoodWhenUp={true}
        loading={loading}
      />
    </section>
  );
}
