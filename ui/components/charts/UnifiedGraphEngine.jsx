"use client";

/**
 * UnifiedGraphEngine - Single chart component for all Metricx visualizations
 * ==========================================================================
 *
 * WHAT: Unified chart component that powers all analytics visualizations
 * WHY: Replaces 3 duplicate charting implementations with one clean abstraction
 *
 * Supports:
 *   - Chart types: area, line, bar, composed
 *   - Dual Y-axis for mixed metric scales (currency + percentage)
 *   - Multi-series with platform colors
 *   - Loading, error, and empty states
 *   - Smart metric formatting
 *
 * Used by: Dashboard, Analytics, Finance, Campaigns pages
 *
 * @module components/charts/UnifiedGraphEngine
 */

import * as React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, BarChart3, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  METRIC_CONFIG,
  PLATFORM_COLORS,
  formatCurrency,
  formatNumber,
  formatPercentage,
  formatMultiplier,
  formatDateForAxis,
  shouldUseRightAxis,
  getMetricFormatter,
} from "@/lib/chartFormatting";

// =============================================================================
// TYPES & DEFAULTS
// =============================================================================

const CHART_TYPES = {
  area: AreaChart,
  line: LineChart,
  bar: BarChart,
  composed: ComposedChart,
};

const DEFAULT_HEIGHT = "400px";

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Builds chart config from series data for ChartContainer
 */
function buildChartConfig(series, metrics) {
  const config = {};

  if (series && series.length > 0) {
    series.forEach((s) => {
      config[s.key] = {
        label: s.label || s.key,
        color: s.color || PLATFORM_COLORS[s.key] || "#6B7280",
      };
    });
  } else if (metrics && metrics.length > 0) {
    metrics.forEach((metric) => {
      const metricConfig = METRIC_CONFIG[metric];
      config[metric] = {
        label: metricConfig?.label || metric,
        color: metricConfig?.color || "#6B7280",
      };
    });
  }

  return config;
}

/**
 * Gets the Y-axis formatter based on metric type
 */
function getYAxisFormatter(metrics = [], isRightAxis = false) {
  // If right axis, typically for percentages/multipliers
  if (isRightAxis) {
    const rightMetrics = metrics.filter((m) =>
      ["percentage", "multiplier"].includes(METRIC_CONFIG[m]?.format)
    );
    if (rightMetrics.length > 0) {
      const format = METRIC_CONFIG[rightMetrics[0]]?.format;
      if (format === "percentage") return (v) => `${v.toFixed(0)}%`;
      if (format === "multiplier") return (v) => `${v.toFixed(1)}x`;
    }
    return (v) => v.toFixed(1);
  }

  // Left axis - detect primary format
  const currencyMetrics = metrics.filter(
    (m) => METRIC_CONFIG[m]?.format === "currency"
  );
  const compactMetrics = metrics.filter(
    (m) => METRIC_CONFIG[m]?.format === "compact"
  );

  if (currencyMetrics.length > 0) {
    return (value) => {
      if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
      if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
      return `$${value}`;
    };
  }

  if (compactMetrics.length > 0) {
    return (value) => {
      if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
      if (value >= 1000) return `${(value / 1000).toFixed(0)}k`;
      return value.toString();
    };
  }

  return (v) => v.toFixed(0);
}

/**
 * Formats tooltip values based on metric type
 */
function formatTooltipValue(value, metricKey) {
  const formatter = getMetricFormatter(metricKey);
  return formatter(value);
}

// =============================================================================
// LOADING STATE
// =============================================================================

function ChartLoadingSkeleton({ height }) {
  return (
    <div style={{ height }} className="w-full flex flex-col gap-4 p-4">
      <div className="flex justify-between items-center">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="flex-1 flex items-end gap-2">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${30 + Math.random() * 60}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between">
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}

// =============================================================================
// ERROR STATE
// =============================================================================

function ChartErrorState({ height, error, onRetry }) {
  return (
    <div
      style={{ height }}
      className="w-full flex flex-col items-center justify-center gap-4 p-8 text-center"
    >
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
        <AlertCircle className="w-6 h-6 text-red-600" />
      </div>
      <div>
        <p className="font-medium text-gray-900">Failed to load chart</p>
        <p className="text-sm text-gray-500 mt-1">
          {error || "Something went wrong. Please try again."}
        </p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      )}
    </div>
  );
}

// =============================================================================
// EMPTY STATE
// =============================================================================

function ChartEmptyState({ height, emptyState }) {
  const Icon = emptyState?.icon || BarChart3;
  return (
    <div
      style={{ height }}
      className="w-full flex flex-col items-center justify-center gap-4 p-8 text-center"
    >
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
        <Icon className="w-6 h-6 text-gray-400" />
      </div>
      <div>
        <p className="font-medium text-gray-900">
          {emptyState?.title || "No data available"}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {emptyState?.description ||
            "Connect your ad accounts to start seeing performance data."}
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// CUSTOM TOOLTIP
// =============================================================================

function CustomTooltip({ active, payload, label, metrics, isSingleDay }) {
  if (!active || !payload || !payload.length) return null;

  const dateLabel = (() => {
    const date = new Date(label);
    if (isNaN(date.getTime())) return label;
    if (isSingleDay) {
      return date.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }
    return date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  })();

  return (
    <div className="bg-white border border-slate-200 shadow-lg rounded-lg p-3 min-w-[180px]">
      <p className="text-sm font-medium text-gray-900 mb-2">{dateLabel}</p>
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const metricKey = entry.dataKey;
          const value = formatTooltipValue(entry.value, metricKey);
          const config = METRIC_CONFIG[metricKey];
          return (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm text-gray-600">
                  {config?.label || entry.name}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-900">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * UnifiedGraphEngine - The primary chart component for Metricx
 *
 * @param {Object} props
 * @param {Array} props.data - Chart data array [{date, revenue, spend, ...}]
 * @param {Array} props.series - Series definitions [{key, label, color, type}]
 * @param {string} props.type - Chart type: "area" | "line" | "bar" | "composed"
 * @param {Array} props.metrics - Metric keys to display: ["revenue", "spend", "roas"]
 * @param {string} props.xAxisKey - Key for x-axis (default: "date")
 * @param {string} props.height - Chart height (default: "400px")
 * @param {boolean} props.showLegend - Show legend (default: true for multi-series)
 * @param {boolean} props.showTooltip - Show tooltip (default: true)
 * @param {boolean} props.showGrid - Show grid lines (default: true)
 * @param {boolean} props.loading - Show loading state
 * @param {string} props.error - Error message to display
 * @param {function} props.onRetry - Retry callback for error state
 * @param {Object} props.emptyState - {icon, title, description} for no data
 * @param {boolean} props.isSingleDay - Enable hourly formatting for single day
 * @param {string} props.className - Additional CSS classes
 */
export function UnifiedGraphEngine({
  data = [],
  series = [],
  type = "area",
  metrics = [],
  xAxisKey = "date",
  height = DEFAULT_HEIGHT,
  showLegend,
  showTooltip = true,
  showGrid = true,
  loading = false,
  error = null,
  onRetry,
  emptyState,
  isSingleDay = false,
  className,
}) {
  // Handle loading state
  if (loading) {
    return <ChartLoadingSkeleton height={height} />;
  }

  // Handle error state
  if (error) {
    return <ChartErrorState height={height} error={error} onRetry={onRetry} />;
  }

  // Handle empty state
  if (!data || data.length === 0) {
    return <ChartEmptyState height={height} emptyState={emptyState} />;
  }

  // Determine what to render
  const effectiveMetrics =
    metrics.length > 0 ? metrics : series.map((s) => s.key);
  const chartConfig = buildChartConfig(series, metrics);

  // Auto-detect if legend should show
  const shouldShowLegend =
    showLegend !== undefined
      ? showLegend
      : effectiveMetrics.length > 1 || series.length > 1;

  // Determine if we need dual Y-axis
  const needsRightAxis = effectiveMetrics.some((m) =>
    shouldUseRightAxis(m, effectiveMetrics)
  );

  // Get chart component
  const ChartComponent = CHART_TYPES[type] || AreaChart;

  // Determine which metrics go on which axis
  const leftAxisMetrics = effectiveMetrics.filter(
    (m) => !shouldUseRightAxis(m, effectiveMetrics)
  );
  const rightAxisMetrics = effectiveMetrics.filter((m) =>
    shouldUseRightAxis(m, effectiveMetrics)
  );

  // Render series elements based on type
  const renderSeriesElements = () => {
    return effectiveMetrics.map((metricKey) => {
      const config = METRIC_CONFIG[metricKey] || {};
      const color = config.color || chartConfig[metricKey]?.color || "#6B7280";
      const isRightAxis = shouldUseRightAxis(metricKey, effectiveMetrics);

      const commonProps = {
        dataKey: metricKey,
        name: config.label || metricKey,
        yAxisId: isRightAxis ? "right" : "left",
      };

      // For composed charts, check series definition for type override
      const seriesType =
        series.find((s) => s.key === metricKey)?.type || type;

      if (type === "composed") {
        // In composed mode, we can mix types per series
        if (seriesType === "bar") {
          return (
            <Bar
              key={metricKey}
              {...commonProps}
              fill={color}
              radius={[4, 4, 0, 0]}
              maxBarSize={50}
            />
          );
        } else if (seriesType === "line") {
          return (
            <Line
              key={metricKey}
              {...commonProps}
              type="monotone"
              stroke={color}
              strokeWidth={2}
              dot={false}
            />
          );
        } else {
          return (
            <Area
              key={metricKey}
              {...commonProps}
              type="monotone"
              fill={`url(#fill-${metricKey})`}
              fillOpacity={0.4}
              stroke={color}
              strokeWidth={2}
            />
          );
        }
      }

      // Single type charts
      if (type === "bar") {
        return (
          <Bar
            key={metricKey}
            {...commonProps}
            fill={color}
            radius={[4, 4, 0, 0]}
            maxBarSize={50}
          />
        );
      } else if (type === "line") {
        return (
          <Line
            key={metricKey}
            {...commonProps}
            type="monotone"
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        );
      } else {
        // area (default)
        return (
          <Area
            key={metricKey}
            {...commonProps}
            type="monotone"
            fill={`url(#fill-${metricKey})`}
            fillOpacity={0.4}
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        );
      }
    });
  };

  return (
    <div style={{ height, width: "100%" }} className={className}>
      <ChartContainer config={chartConfig} className="h-full w-full aspect-auto">
        <ChartComponent
          data={data}
          margin={{
            left: 0,
            right: needsRightAxis ? 0 : 0,
            top: 10,
            bottom: 0,
          }}
        >
          {/* Gradient definitions for area charts */}
          <defs>
            {effectiveMetrics.map((metricKey) => {
              const config = METRIC_CONFIG[metricKey] || {};
              const color =
                config.color || chartConfig[metricKey]?.color || "#6B7280";
              return (
                <linearGradient
                  key={`gradient-${metricKey}`}
                  id={`fill-${metricKey}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.1} />
                </linearGradient>
              );
            })}
          </defs>

          {/* Grid */}
          {showGrid && (
            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.4}
            />
          )}

          {/* Left Y-Axis */}
          <YAxis
            yAxisId="left"
            domain={[0, "auto"]}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            width={60}
            tickFormatter={getYAxisFormatter(leftAxisMetrics, false)}
          />

          {/* Right Y-Axis (if needed) */}
          {needsRightAxis && (
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, "auto"]}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              width={50}
              tickFormatter={getYAxisFormatter(rightAxisMetrics, true)}
            />
          )}

          {/* X-Axis */}
          <XAxis
            dataKey={xAxisKey}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={isSingleDay ? 20 : 32}
            tickFormatter={(value) => {
              const date = new Date(value);
              if (!isNaN(date.getTime())) {
                if (isSingleDay) {
                  return date.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  });
                }
                return date.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                });
              }
              return value;
            }}
          />

          {/* Tooltip */}
          {showTooltip && (
            <Tooltip
              content={
                <CustomTooltip
                  metrics={effectiveMetrics}
                  isSingleDay={isSingleDay}
                />
              }
              cursor={{ strokeDasharray: "3 3" }}
            />
          )}

          {/* Legend */}
          {shouldShowLegend && (
            <Legend
              content={({ payload }) => (
                <div className="flex flex-wrap justify-center gap-4 pt-4">
                  {payload?.map((entry, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                      />
                      <span className="text-sm text-gray-600">
                        {entry.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            />
          )}

          {/* Render series */}
          {renderSeriesElements()}
        </ChartComponent>
      </ChartContainer>
    </div>
  );
}

// =============================================================================
// EXPORTS
// =============================================================================

export default UnifiedGraphEngine;
