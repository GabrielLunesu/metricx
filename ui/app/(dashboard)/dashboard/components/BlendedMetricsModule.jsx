'use client';

/**
 * BlendedMetricsModule Component
 * ==============================
 *
 * WHAT: Main chart module showing selected metric over time with metric tabs
 * WHY: Users need a prominent chart to visualize metric trends
 *
 * FEATURES:
 *   - Metric tabs: Revenue, ROAS, Ad Spend, Conversions
 *   - Uses UnifiedGraphEngine for consistent chart rendering
 *   - Glassmorphic card with blue primary accent
 *   - Timeframe-aware x-axis formatting
 *
 * UPDATED: Now uses UnifiedGraphEngine and chartFormatting for consistency
 */

import { useMemo } from "react";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";
import { formatDateOnlyLabel, formatTimestampLabel } from "@/lib/datetime";
import { UnifiedGraphEngine } from "@/components/charts/UnifiedGraphEngine";
import { formatCurrency, formatMultiplier, formatNumber } from "@/lib/chartFormatting";

// Metric configuration - blue primary, each has inner accent color
const METRICS = [
  { key: 'revenue', label: 'Revenue', color: '#22d3ee', format: 'currency' },
  { key: 'conversion_value', label: 'Conv. value', color: '#0891b2', format: 'currency' },
  { key: 'roas', label: 'ROAS', color: '#a78bfa', format: 'multiplier' },
  { key: 'spend', label: 'Ad Spend', color: '#60a5fa', format: 'currency' },
  { key: 'conversions', label: 'Conversions', color: '#f97316', format: 'number' },
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
function formatValue(val, format, compact = false, currency = 'USD') {
  if (val === null || val === undefined) return '—';
  const symbol = CURRENCY_SYMBOLS[currency] || '$';

  switch (format) {
    case 'currency':
      if (compact && val >= 1000) {
        return `${symbol}${(val / 1000).toFixed(1)}k`;
      }
      return `${symbol}${new Intl.NumberFormat('en-US', {
        maximumFractionDigits: 0
      }).format(val)}`;
    case 'multiplier':
      return `${Number(val).toFixed(2)}x`;
    case 'number':
      if (compact && val >= 1000) {
        return `${(val / 1000).toFixed(1)}k`;
      }
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(val);
    default:
      return val;
  }
}

// Custom tooltip
function CustomTooltip({ active, payload, label, format, currency, timeZone, granularity }) {
  if (!active || !payload?.length) return null;

  const value = payload[0]?.value;
  const dateStr = granularity === "intraday_15m"
    ? formatTimestampLabel(label, {
        timeZone,
        options: { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }
      })
    : formatDateOnlyLabel(label, {
        timeZone,
        options: { month: "short", day: "numeric", year: "numeric" }
      });

  return (
    <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-xl px-3 py-2 shadow-lg">
      <p className="text-[10px] text-slate-500 mb-1">{dateStr}</p>
      <p className="text-sm font-semibold text-slate-900">
        {formatValue(value, format, false, currency)}
      </p>
    </div>
  );
}

export default function BlendedMetricsModule({
  data,
  loading,
  timeframe = 'last_7_days',
  selectedMetric = 'revenue',
  onMetricChange
}) {
  // Get current metric config
  const availableMetrics = data?.has_shopify ? METRICS : METRICS.filter(m => m.key !== 'conversion_value');
  const currentMetric = availableMetrics.find(m => m.key === selectedMetric) || availableMetrics[0];

  // Get KPI data for the selected metric
  const kpiMap = useMemo(() => {
    const map = {};
    data?.kpis?.forEach(item => {
      map[item.key] = item;
    });
    return map;
  }, [data?.kpis]);

  const metricData = kpiMap[selectedMetric];
  const isSingleDay = timeframe === 'today' || timeframe === 'yesterday';
  const chartTimeZone = data?.chart_timezone || 'UTC';
  const chartGranularity = data?.chart_granularity || (isSingleDay ? 'intraday_15m' : 'daily');
  const isIntraday = chartGranularity === 'intraday_15m';

  // Process chart data - ensure we have valid numbers
  const chartData = useMemo(() => {
    if (!data?.chart_data) return [];
    return data.chart_data.map(d => ({
      ...d,
      [selectedMetric]: d[selectedMetric] ?? 0
    }));
  }, [data?.chart_data, selectedMetric]);

  // Loading state
  if (loading || !data) {
    return (
      <div className="dashboard-module min-h-[380px] animate-pulse">
        <div className="flex items-center justify-between mb-6">
          <div className="h-6 w-32 bg-slate-200/50 rounded-lg"></div>
          <div className="flex gap-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-8 w-20 bg-slate-200/50 rounded-full"></div>
            ))}
          </div>
        </div>
        <div className="h-64 bg-slate-200/30 rounded-2xl"></div>
      </div>
    );
  }

  // Check if we have data
  const hasData = chartData.length > 0 && chartData.some(d => d[selectedMetric] > 0);

  return (
    <div className="dashboard-module min-h-[380px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
            Blended Metrics
          </p>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900 mt-0.5">
            {currentMetric.label}
          </h2>
        </div>

        {/* Metric value + change */}
        {metricData && (
          <div className="text-right">
            <p className="text-2xl font-bold text-slate-900">
              {formatValue(metricData.value, currentMetric.format, false, data?.currency)}
            </p>
            {metricData.delta_pct !== null && metricData.delta_pct !== undefined && (
              <div className={`flex items-center justify-end gap-1 text-xs font-medium ${
                metricData.delta_pct >= 0 ? 'text-emerald-600' : 'text-red-500'
              }`}>
                {metricData.delta_pct >= 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                <span>{metricData.delta_pct >= 0 ? '+' : ''}{(metricData.delta_pct * 100).toFixed(1)}%</span>
                <span className="text-slate-400 font-normal">vs prev</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Metric Tabs */}
      <div className="flex items-center gap-1.5 mb-4 p-1 bg-slate-900/5 rounded-full w-fit">
        {availableMetrics.map((metric) => (
          <button
            key={metric.key}
            onClick={() => onMetricChange?.(metric.key)}
            className={`
              px-4 py-1.5 rounded-full text-[11px] font-medium transition-all duration-200
              ${selectedMetric === metric.key
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }
            `}
          >
            {metric.label}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="flex-1 min-h-[220px]">
        {/* Intraday messaging */}
        {isSingleDay && !isIntraday && (
          <p className="text-[10px] text-slate-400 mb-2">
            Hourly data starts after you connect your account and the first sync completes.
          </p>
        )}
        {isSingleDay && isIntraday && data?.intraday_available_from && (
          <p className="text-[10px] text-slate-400 mb-2">
            Hourly data since{" "}
            {formatTimestampLabel(data.intraday_available_from, {
              timeZone: chartTimeZone,
              options: { hour: "2-digit", minute: "2-digit", hour12: false }
            })}{" "}
            ({chartTimeZone})
          </p>
        )}
        <UnifiedGraphEngine
          data={chartData}
          metrics={[selectedMetric]}
          type="area"
          height="100%"
          showLegend={false}
          showGrid={true}
          isSingleDay={isIntraday}
          emptyState={{
            icon: RefreshCw,
            title: "No data yet",
            description: "Data will appear after the next sync"
          }}
        />
      </div>
    </div>
  );
}
