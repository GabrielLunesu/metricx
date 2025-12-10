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
 *   - Animated area chart with gradient fill
 *   - Glassmorphic card with blue primary accent
 *   - Timeframe-aware x-axis formatting
 */

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";

// Metric configuration - blue primary, each has inner accent color
const METRICS = [
  { key: 'revenue', label: 'Revenue', color: '#22d3ee', format: 'currency' },
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
function CustomTooltip({ active, payload, label, format, currency }) {
  if (!active || !payload?.length) return null;

  const value = payload[0]?.value;
  const date = new Date(label);
  const dateStr = !isNaN(date.getTime())
    ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : label;

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
        {METRICS.map((metric) => (
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
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ left: 0, right: 0, top: 10, bottom: 0 }}
            >
              <defs>
                <linearGradient id={`gradient-${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={currentMetric.color} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={currentMetric.color} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="#e2e8f0"
                opacity={0.5}
              />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  if (!isNaN(date.getTime())) {
                    if (isSingleDay) {
                      return date.toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                      });
                    }
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                  }
                  return value;
                }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={55}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(value) => formatValue(value, currentMetric.format, true, data?.currency)}
              />
              <Tooltip
                content={<CustomTooltip format={currentMetric.format} currency={data?.currency} />}
                cursor={{ stroke: currentMetric.color, strokeWidth: 1, strokeDasharray: '4 4' }}
              />
              <Area
                type="monotone"
                dataKey={selectedMetric}
                stroke={currentMetric.color}
                strokeWidth={2}
                fill={`url(#gradient-${selectedMetric})`}
                dot={false}
                activeDot={{ r: 4, fill: currentMetric.color, stroke: '#fff', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
              <RefreshCw className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-slate-600 font-medium text-sm">No data yet</p>
            <p className="text-slate-400 text-xs mt-1">
              Data will appear after the next sync
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
