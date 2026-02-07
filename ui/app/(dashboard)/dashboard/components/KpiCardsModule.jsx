'use client';

/**
 * KpiCardsModule Component - Metricx v3.0 Design
 * ==============================================
 *
 * WHAT: 4 KPI cards displaying key metrics in a responsive grid
 * WHY: Users need at-a-glance view of their most important metrics
 *
 * CHANGES (2025-12-30):
 *   - New design: card-soft styling with rounded-[32px]
 *   - 4-column grid on large screens (1/2/4 responsive)
 *   - Large numbers with number-display font feature
 *   - Colored delta badges (emerald for positive, amber for spend, etc.)
 *   - Removed mini bar charts for cleaner design
 *   - Click to select metric for main chart
 *
 * FEATURES:
 *   - 4 metrics: Revenue, Ad Spend, ROAS, Orders/Conversions
 *   - Hover lift animation
 *   - Delta percentage with colored badge
 */

import { useMemo } from "react";

// KPI configurations with delta badge colors
const KPIS = [
  {
    key: 'revenue',
    label: 'Revenue',
    format: 'currency',
    deltaColor: 'emerald', // green for revenue up
  },
  {
    key: 'spend',
    label: 'Ad Spend',
    format: 'currency',
    inverse: true, // lower is better
    deltaColor: 'amber', // amber for spend
  },
  {
    key: 'roas',
    label: 'ROAS',
    format: 'multiplier',
    deltaColor: 'violet', // purple for ROAS
  },
  {
    key: 'conversions',
    label: 'Orders',
    format: 'number',
    deltaColor: 'blue', // blue for orders
  },
];

// Currency symbols mapping
const CURRENCY_SYMBOLS = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  CAD: 'C$',
  AUD: 'A$',
};

// Delta badge color classes
const DELTA_COLORS = {
  emerald: {
    positive: 'bg-emerald-500/5 border-emerald-500/10 text-emerald-600',
    negative: 'bg-red-500/5 border-red-500/10 text-red-600',
  },
  amber: {
    positive: 'bg-red-500/5 border-red-500/10 text-red-600', // for spend, up is bad
    negative: 'bg-emerald-500/5 border-emerald-500/10 text-emerald-600', // down is good
  },
  violet: {
    positive: 'bg-violet-500/5 border-violet-500/10 text-violet-600',
    negative: 'bg-red-500/5 border-red-500/10 text-red-600',
  },
  blue: {
    positive: 'bg-blue-500/5 border-blue-500/10 text-blue-600',
    negative: 'bg-red-500/5 border-red-500/10 text-red-600',
  },
};

/**
 * Format value based on type
 * @param {number} val - The value to format
 * @param {string} format - Format type: 'currency', 'multiplier', 'number'
 * @param {string} currency - Currency code (USD, EUR, etc.)
 * @returns {string} Formatted value
 */
function formatValue(val, format, currency = 'USD') {
  if (val === null || val === undefined) return '—';
  const symbol = CURRENCY_SYMBOLS[currency] || '$';

  switch (format) {
    case 'currency':
      if (val >= 10000) {
        return `${symbol}${(val / 1000).toFixed(1)}K`;
      }
      return `${symbol}${new Intl.NumberFormat('en-US', {
        maximumFractionDigits: 0,
      }).format(val)}`;
    case 'multiplier':
      return `${Number(val).toFixed(2)}x`;
    case 'number':
      if (val >= 10000) {
        return `${(val / 1000).toFixed(1)}K`;
      }
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(val);
    default:
      return val;
  }
}

/**
 * Get delta badge class based on value and color scheme
 */
function getDeltaBadgeClass(deltaPct, colorScheme, inverse = false) {
  const isPositive = inverse ? deltaPct <= 0 : deltaPct >= 0;
  return DELTA_COLORS[colorScheme]?.[isPositive ? 'positive' : 'negative'] || DELTA_COLORS.emerald.positive;
}

export default function KpiCardsModule({
  data,
  loading,
  selectedMetric = 'revenue',
  onMetricClick
}) {
  // Convert kpis array to map for easy lookup
  const kpiMap = useMemo(() => {
    const map = {};
    data?.kpis?.forEach(item => {
      map[item.key] = item;
    });
    return map;
  }, [data?.kpis]);

  // Loading skeleton
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6 mb-8 md:mb-12">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white/40 glass rounded-2xl md:rounded-[32px] p-4 md:p-8 border border-white/60 animate-pulse">
            <div className="flex flex-col h-full justify-between gap-2 md:gap-4">
              <div className="flex items-start justify-between">
                <div className="h-3 md:h-4 w-16 md:w-20 bg-neutral-200/50 rounded"></div>
                <div className="h-5 md:h-6 w-14 md:w-16 bg-neutral-200/50 rounded-lg"></div>
              </div>
              <div className="h-8 md:h-12 w-24 md:w-32 bg-neutral-200/50 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6 mb-8 md:mb-12">
      {KPIS.map((kpi) => {
        const kpiData = kpiMap[kpi.key];
        const isSelected = selectedMetric === kpi.key;
        const deltaPct = kpiData?.delta_pct;
        const hasDelta = deltaPct !== null && deltaPct !== undefined;

        // Get display label (use Shopify revenue if available)
        const label = (kpi.key === "revenue" && data?.has_shopify) ? "Revenue" : kpi.label;

        return (
          <button
            key={kpi.key}
            onClick={() => onMetricClick?.(kpi.key)}
            className={`
              bg-white/40 glass rounded-2xl md:rounded-[32px] p-4 md:p-8 text-left transition-all duration-300 cursor-pointer
              border border-white/60 hover:bg-white/60 hover:-translate-y-0.5
            `}
          >
            <div className="flex flex-col h-full justify-between gap-1.5 md:gap-2">
              {/* Header: Label + Delta Badge */}
              <div className="flex items-start justify-between gap-1">
                <span className="text-xs md:text-sm font-medium text-neutral-500 tracking-wide">
                  {label}
                </span>
                {hasDelta && (
                  <div className={`px-1.5 md:px-2 py-0.5 md:py-1 rounded-md md:rounded-lg border ${getDeltaBadgeClass(deltaPct, kpi.deltaColor, kpi.inverse)}`}>
                    <span className="text-[10px] md:text-xs font-semibold whitespace-nowrap">
                      {deltaPct >= 0 ? '+' : ''}{(deltaPct * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>

              {/* Value */}
              <div>
                <div className="text-2xl md:text-5xl font-medium text-neutral-900 number-display tracking-tighter">
                  {formatValue(kpiData?.value, kpi.format, data?.currency)}
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
