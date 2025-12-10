'use client';

/**
 * KpiCardsModule Component
 * ========================
 *
 * WHAT: 4 clickable KPI cards that control the main chart's metric
 * WHY: Users can quickly see all key metrics and click to explore in detail
 *
 * FEATURES:
 *   - 4 metrics: Revenue, ROAS, Ad Spend, Conversions
 *   - Click to change main chart metric
 *   - Visual selection indicator (ring + glow)
 *   - Animated mini bar chart visualization
 *   - Delta percentage with trend indicator
 *   - Blue primary accent, each metric has inner color accent
 */

import { useMemo } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

// KPI configurations - blue primary, different inner accent colors
const KPIS = [
  {
    key: 'revenue',
    label: 'Revenue',
    format: 'currency',
    accentColor: '#22d3ee', // cyan
    bgSelected: 'bg-cyan-50/80',
    ringColor: 'ring-cyan-300',
    barColor: 'bg-cyan-400',
    textColor: 'text-cyan-600',
  },
  {
    key: 'roas',
    label: 'ROAS',
    format: 'multiplier',
    accentColor: '#a78bfa', // purple
    bgSelected: 'bg-purple-50/80',
    ringColor: 'ring-purple-300',
    barColor: 'bg-purple-400',
    textColor: 'text-purple-600',
  },
  {
    key: 'spend',
    label: 'Ad Spend',
    format: 'currency',
    inverse: true,
    accentColor: '#60a5fa', // blue
    bgSelected: 'bg-blue-50/80',
    ringColor: 'ring-blue-300',
    barColor: 'bg-blue-400',
    textColor: 'text-blue-600',
  },
  {
    key: 'conversions',
    label: 'Conversions',
    format: 'number',
    accentColor: '#f97316', // orange
    bgSelected: 'bg-orange-50/80',
    ringColor: 'ring-orange-300',
    barColor: 'bg-orange-400',
    textColor: 'text-orange-600',
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

// Format value based on type
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

// Mini bar chart component
function MiniBarChart({ data, color, maxBars = 7 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-end gap-1 h-10 mt-3">
        {Array.from({ length: maxBars }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-full bg-slate-200/50"
            style={{ height: '30%' }}
          />
        ))}
      </div>
    );
  }

  const chartData = data.slice(-maxBars);
  const maxVal = Math.max(...chartData.map(d => d.value || 0), 1);

  return (
    <div className="flex items-end gap-1 h-10 mt-3">
      {chartData.map((point, i) => {
        const height = Math.max(((point.value || 0) / maxVal) * 100, 8);
        const isLast = i === chartData.length - 1;

        return (
          <div
            key={i}
            className={`
              flex-1 rounded-full transition-all duration-500
              ${isLast ? color : 'bg-slate-300/40'}
            `}
            style={{ height: `${height}%` }}
          />
        );
      })}
    </div>
  );
}

export default function KpiCardsModule({
  data,
  loading,
  selectedMetric = 'revenue',
  onMetricClick
}) {
  // Convert kpis array to map
  const kpiMap = useMemo(() => {
    const map = {};
    data?.kpis?.forEach(item => {
      map[item.key] = item;
    });
    return map;
  }, [data?.kpis]);

  // Loading state
  if (loading || !data) {
    return (
      <div className="dashboard-module min-h-[200px]">
        <div className="grid grid-cols-2 gap-3 h-full">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-slate-200/30 rounded-2xl animate-pulse h-28"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-module min-h-[200px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
            Key Metrics
          </p>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900 mt-0.5">
            Performance Overview
          </h2>
        </div>
        <span className="text-xs text-slate-400">Click to explore</span>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 gap-3">
        {KPIS.map((kpi) => {
          const kpiData = kpiMap[kpi.key];
          const isSelected = selectedMetric === kpi.key;
          const deltaPct = kpiData?.delta_pct;
          const isPositive = kpi.inverse ? deltaPct <= 0 : deltaPct >= 0;

          return (
            <button
              key={kpi.key}
              onClick={() => onMetricClick?.(kpi.key)}
              className={`
                relative p-4 rounded-2xl text-left transition-all duration-300
                border hover:shadow-md
                ${isSelected
                  ? `ring-2 ${kpi.ringColor} ${kpi.bgSelected} border-white/80 shadow-lg`
                  : 'bg-white/50 border-white/60 hover:bg-white/70'
                }
              `}
            >
              {/* Label */}
              <p className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">
                {kpi.label}
              </p>

              {/* Value */}
              <p className={`text-xl font-bold mt-1 ${isSelected ? kpi.textColor : 'text-slate-900'}`}>
                {formatValue(kpiData?.value, kpi.format, data?.currency)}
              </p>

              {/* Delta */}
              {deltaPct !== null && deltaPct !== undefined && (
                <div className={`flex items-center gap-1 mt-1 text-[10px] font-medium ${
                  isPositive ? 'text-emerald-600' : 'text-red-500'
                }`}>
                  {isPositive ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  <span>
                    {deltaPct >= 0 ? '+' : ''}{(deltaPct * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {/* Mini bar chart */}
              <MiniBarChart
                data={kpiData?.sparkline}
                color={kpi.barColor}
              />

              {/* Selection indicator dot */}
              {isSelected && (
                <div className={`absolute top-3 right-3 w-2 h-2 rounded-full ${kpi.barColor}`} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
