"use client";

/**
 * AnalyticsKpiGrid - 8 KPI cards in horizontal responsive grid
 * 
 * WHAT: Displays 8 key metrics in a horizontal card layout
 * WHY: Quick overview of performance metrics at a glance
 * 
 * KPIS (in order):
 *   1. Revenue - from API
 *   2. Spend - from API  
 *   3. CPC - from API
 *   4. ROAS - from API
 *   5. Conv. - from API
 *   6. Profit - calculated (revenue - spend)
 *   7. AOV - from API (Shopify) or "—"
 *   8. CPA - calculated (spend / conversions)
 * 
 * FEATURES:
 *   - Responsive grid: 2 cols → 4 cols → 8 cols
 *   - Delta indicators with colored arrows
 *   - Calculated metrics (Profit, CPA)
 *   - Loading skeleton state
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 */

import { ArrowUpRight, ArrowDownRight } from "lucide-react";

/**
 * KPI metric definitions
 * Includes both API-provided and calculated metrics
 */
const KPIS = [
  { key: "revenue", label: "Revenue", format: "currency" },
  { key: "spend", label: "Spend", format: "currency", inverse: true },
  { key: "cpc", label: "CPC", format: "currency_decimal" },
  { key: "roas", label: "ROAS", format: "multiplier" },
  { key: "conversions", label: "Conv.", format: "number" },
  { key: "profit", label: "Profit", format: "currency", calculated: true },
  { key: "aov", label: "AOV", format: "currency_decimal" },
  { key: "cpa", label: "CPA", format: "currency_decimal", calculated: true, inverse: true },
];

/**
 * Currency symbols for formatting
 */
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

/**
 * Format metric value based on type
 * @param {number|null} value - The value to format
 * @param {string} format - Format type
 * @param {string} currency - Currency code
 * @returns {string} Formatted value
 */
function formatValue(value, format, currency = "USD") {
  if (value === null || value === undefined) return "—";

  const symbol = CURRENCY_SYMBOLS[currency] || "$";

  switch (format) {
    case "currency":
      if (Math.abs(value) >= 10000) {
        return `${symbol}${(value / 1000).toFixed(1)}k`;
      }
      return `${symbol}${new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value)}`;

    case "currency_decimal":
      return `${symbol}${new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value)}`;

    case "multiplier":
      return `${Number(value).toFixed(2)}x`;

    case "number":
      if (value >= 10000) {
        return `${(value / 1000).toFixed(1)}k`;
      }
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value);

    case "percent":
      return `${Number(value).toFixed(2)}%`;

    default:
      return String(value);
  }
}

/**
 * Format delta percentage for display
 * @param {number|null} deltaPct - Delta as decimal (e.g., 0.125 = 12.5%)
 * @param {boolean} inverse - If true, negative is good (e.g., for spend, CPA)
 * @returns {object|null} { text, isGood }
 */
function formatDelta(deltaPct, inverse = false) {
  if (deltaPct === null || deltaPct === undefined) return null;

  const pct = (deltaPct * 100).toFixed(1);
  const isPositive = deltaPct >= 0;
  const isGood = inverse ? !isPositive : isPositive;

  return {
    text: `${isPositive ? "+" : ""}${pct}%`,
    isGood,
    isPositive,
  };
}

/**
 * Single KPI Card Component
 */
function KpiCard({ label, value, delta, format, currency, inverse, loading }) {
  const deltaInfo = formatDelta(delta, inverse);

  if (loading) {
    return (
      <div className="analytics-kpi-card animate-pulse">
        <div className="h-3 w-16 bg-neutral-200 rounded mb-2" />
        <div className="h-6 w-20 bg-neutral-200 rounded mb-2" />
        <div className="h-3 w-12 bg-neutral-200 rounded" />
      </div>
    );
  }

  return (
    <div className="analytics-kpi-card">
      {/* Label */}
      <div className="text-[11px] font-medium text-neutral-500 uppercase tracking-wider mb-1">
        {label}
      </div>

      {/* Value */}
      <div className="text-xl font-semibold text-neutral-900 tracking-tight tabular-nums">
        {formatValue(value, format, currency)}
      </div>

      {/* Delta */}
      <div className="flex items-center gap-1 mt-2">
        {deltaInfo ? (
          <>
            {deltaInfo.isPositive ? (
              <ArrowUpRight
                className={`w-3 h-3 ${
                  deltaInfo.isGood ? "text-emerald-600" : "text-rose-600"
                }`}
              />
            ) : (
              <ArrowDownRight
                className={`w-3 h-3 ${
                  deltaInfo.isGood ? "text-emerald-600" : "text-rose-600"
                }`}
              />
            )}
            <span
              className={`text-xs font-medium ${
                deltaInfo.isGood ? "text-emerald-600" : "text-rose-600"
              }`}
            >
              {deltaInfo.text}
            </span>
          </>
        ) : (
          <span className="text-xs text-neutral-400">—</span>
        )}
      </div>
    </div>
  );
}

/**
 * Main KPI Grid Component
 */
export default function AnalyticsKpiGrid({
  data,
  loading = false,
  currency = "USD",
}) {
  // Calculate derived metrics
  const metrics = {
    revenue: data?.revenue ?? null,
    spend: data?.spend ?? null,
    cpc: data?.cpc ?? null,
    roas: data?.roas ?? null,
    conversions: data?.conversions ?? null,
    aov: data?.aov ?? null,
    // Calculated metrics
    profit:
      data?.revenue != null && data?.spend != null
        ? data.revenue - data.spend
        : null,
    cpa:
      data?.conversions > 0 && data?.spend != null
        ? data.spend / data.conversions
        : null,
  };

  // Delta percentages (from API or calculated)
  const deltas = {
    revenue: data?.delta_revenue ?? data?.revenue_delta_pct ?? null,
    spend: data?.delta_spend ?? data?.spend_delta_pct ?? null,
    cpc: data?.delta_cpc ?? data?.cpc_delta_pct ?? null,
    roas: data?.delta_roas ?? data?.roas_delta_pct ?? null,
    conversions: data?.delta_conversions ?? data?.conversions_delta_pct ?? null,
    aov: data?.delta_aov ?? data?.aov_delta_pct ?? null,
    profit: data?.delta_profit ?? null, // Usually not provided, could calculate
    cpa: data?.delta_cpa ?? null, // Usually not provided, could calculate
  };

  return (
    <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-4">
      {KPIS.map((kpi) => (
        <KpiCard
          key={kpi.key}
          label={kpi.label}
          value={metrics[kpi.key]}
          delta={deltas[kpi.key]}
          format={kpi.format}
          currency={currency}
          inverse={kpi.inverse}
          loading={loading}
        />
      ))}
    </section>
  );
}
