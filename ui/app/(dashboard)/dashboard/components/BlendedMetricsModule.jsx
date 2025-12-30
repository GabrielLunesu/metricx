'use client';

/**
 * BlendedMetricsModule Component - Metricx v3.0 Design
 * ====================================================
 *
 * WHAT: Main chart module showing selected metric over time with metric tabs
 * WHY: Users need a prominent chart to visualize metric trends
 *
 * CHANGES (2025-12-30):
 *   - New container styling: glass, rounded-[32px], neutral colors
 *   - Updated metric tabs: pill buttons with neutral-100 background
 *   - Cleaner header with "Performance Overview" title
 *   - Uses UnifiedGraphEngine for consistent chart rendering
 *
 * FEATURES:
 *   - Metric tabs: Revenue, ROAS, Ad Spend, Conversions
 *   - Timeframe-aware x-axis formatting
 *   - Glassmorphic card design
 */

import { useMemo } from "react";
import { RefreshCw } from "lucide-react";
import { formatDateOnlyLabel, formatTimestampLabel } from "@/lib/datetime";
import { UnifiedGraphEngine } from "@/components/charts/UnifiedGraphEngine";

// Metric configuration
const METRICS = [
  { key: 'revenue', label: 'Revenue', format: 'currency' },
  { key: 'spend', label: 'Spend', format: 'currency' },
  { key: 'roas', label: 'ROAS', format: 'multiplier' },
  { key: 'conversions', label: 'Orders', format: 'number' },
];

// Currency symbols mapping
const CURRENCY_SYMBOLS = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  CAD: 'C$',
  AUD: 'A$',
};

/**
 * Format value based on type
 */
function formatValue(val, format, currency = 'USD') {
  if (val === null || val === undefined) return '—';
  const symbol = CURRENCY_SYMBOLS[currency] || '$';

  switch (format) {
    case 'currency':
      if (val >= 1000) {
        return `${symbol}${(val / 1000).toFixed(1)}k`;
      }
      return `${symbol}${new Intl.NumberFormat('en-US', {
        maximumFractionDigits: 0
      }).format(val)}`;
    case 'multiplier':
      return `${Number(val).toFixed(2)}x`;
    case 'number':
      if (val >= 1000) {
        return `${(val / 1000).toFixed(1)}k`;
      }
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(val);
    default:
      return val;
  }
}

export default function BlendedMetricsModule({
  data,
  loading,
  timeframe = 'today',
  selectedMetric = 'revenue',
  onMetricChange
}) {
  // Get current metric config
  const currentMetric = METRICS.find(m => m.key === selectedMetric) || METRICS[0];

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
      <div className="bg-white/40 glass rounded-[32px] border border-white/60 p-10 animate-pulse">
        <div className="flex items-center justify-between mb-12">
          <div className="h-6 w-48 bg-neutral-200/50 rounded-lg"></div>
          <div className="flex gap-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-8 w-20 bg-neutral-200/50 rounded-lg"></div>
            ))}
          </div>
        </div>
        <div className="h-64 lg:h-80 bg-neutral-200/30 rounded-2xl"></div>
      </div>
    );
  }

  return (
    <div className="bg-white/40 glass rounded-[32px] border border-white/60 p-10">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-12">
        <div>
          <h2 className="text-lg font-medium text-neutral-900 tracking-tight">
            Performance Overview
          </h2>
        </div>

        {/* Metric Tabs */}
        <div className="flex items-center gap-2 bg-neutral-100/50 p-1 rounded-xl">
          {METRICS.map((metric) => (
            <button
              key={metric.key}
              onClick={() => onMetricChange?.(metric.key)}
              className={`
                px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200
                ${selectedMetric === metric.key
                  ? 'bg-white text-neutral-900 shadow-sm'
                  : 'text-neutral-400 hover:text-neutral-600'
                }
              `}
            >
              {metric.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-64 lg:h-80">
        {/* Intraday messaging */}
        {isSingleDay && !isIntraday && (
          <p className="text-[10px] text-neutral-400 mb-2">
            Hourly data starts after you connect your account and the first sync completes.
          </p>
        )}
        {isSingleDay && isIntraday && data?.intraday_available_from && (
          <p className="text-[10px] text-neutral-400 mb-2">
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
