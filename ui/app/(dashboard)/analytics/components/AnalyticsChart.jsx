"use client";

/**
 * AnalyticsChart - Main chart section with metric tabs and compare legend
 * 
 * WHAT: Displays performance data as an area chart with metric selection
 * WHY: Visualize trends over time for key metrics
 * 
 * FEATURES:
 *   - Metric tabs: Revenue, Spend, ROAS, Orders
 *   - Current vs Previous period legend (when compare enabled)
 *   - Area chart with gradient fill
 *   - Dashed line for previous period
 *   - Responsive design
 *   - Loading skeleton
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - Uses Recharts for chart rendering
 */

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

/**
 * Metric tabs configuration
 */
const METRIC_TABS = [
  { key: "revenue", label: "Revenue", format: "currency" },
  { key: "spend", label: "Spend", format: "currency" },
  { key: "roas", label: "ROAS", format: "multiplier" },
  { key: "conversions", label: "Orders", format: "number" },
];

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
 * Format value for display
 */
function formatValue(value, format, currency = "USD", compact = false) {
  if (value === null || value === undefined) return "—";

  const symbol = CURRENCY_SYMBOLS[currency] || "$";

  switch (format) {
    case "currency":
      if (compact && Math.abs(value) >= 1000) {
        return `${symbol}${(value / 1000).toFixed(1)}k`;
      }
      return `${symbol}${new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value)}`;

    case "multiplier":
      return `${Number(value).toFixed(2)}x`;

    case "number":
      if (compact && value >= 1000) {
        return `${(value / 1000).toFixed(1)}k`;
      }
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0,
      }).format(value);

    default:
      return String(value);
  }
}

/**
 * Custom Tooltip Component
 */
function CustomTooltip({ active, payload, label, format, currency }) {
  if (!active || !payload || !payload.length) return null;

  const date = new Date(label);
  const dateStr = date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="bg-neutral-900 text-white px-3 py-2 rounded-lg shadow-xl text-xs">
      <div className="font-medium mb-1">{dateStr}</div>
      {payload.map((entry, index) => (
        <div key={index} className="flex justify-between gap-4 text-neutral-400">
          <span>{entry.name === "current" ? "Current:" : "Previous:"}</span>
          <span className="text-white font-medium">
            {formatValue(entry.value, format, currency)}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Main Chart Component
 */
export default function AnalyticsChart({
  data = [],
  compareData = null,
  selectedMetric = "revenue",
  onMetricChange,
  compareEnabled = false,
  loading = false,
  currency = "USD",
}) {
  // Get current metric config
  const currentMetric = useMemo(() => {
    return METRIC_TABS.find((m) => m.key === selectedMetric) || METRIC_TABS[0];
  }, [selectedMetric]);

  // Merge current and compare data for chart
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((d, index) => {
      const point = {
        date: d.date,
        current: d[selectedMetric] ?? 0,
      };

      // Add compare data if enabled and available
      if (compareEnabled && compareData && compareData[index]) {
        point.previous = compareData[index][selectedMetric] ?? 0;
      }

      return point;
    });
  }, [data, compareData, selectedMetric, compareEnabled]);

  // Check if we have data
  const hasData = chartData.length > 0 && chartData.some((d) => d.current > 0);

  // Loading skeleton
  if (loading) {
    return (
      <section className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div className="h-10 w-80 bg-neutral-100 rounded-lg animate-pulse" />
          <div className="h-4 w-40 bg-neutral-100 rounded animate-pulse" />
        </div>
        <div className="w-full h-80 bg-neutral-50 rounded-xl animate-pulse" />
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4 md:gap-6">
      {/* Header: Metric Tabs + Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Metric Tabs */}
        <div className="metric-tabs">
          {METRIC_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => onMetricChange(tab.key)}
              className={`metric-tab ${
                selectedMetric === tab.key ? "active" : ""
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="chart-legend">
          <div className="chart-legend-item">
            <span className="chart-legend-line" />
            <span className="text-[11px] md:text-xs font-medium text-neutral-600">Current</span>
          </div>
          {compareEnabled && (
            <div className="chart-legend-item">
              <span className="chart-legend-line dashed" />
              <span className="text-[11px] md:text-xs font-medium text-neutral-400">Previous</span>
            </div>
          )}
        </div>
      </div>

      {/* Chart Area */}
      <div className="w-full h-64 md:h-80 relative">
        {!hasData ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mb-3">
              <svg
                className="w-5 h-5 text-neutral-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <p className="text-neutral-600 font-medium text-sm">No data yet</p>
            <p className="text-neutral-400 text-xs mt-1">
              Data will appear after the next sync
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 0, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="currentGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#171717" stopOpacity={0.05} />
                  <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
                </linearGradient>
              </defs>

              {/* Grid lines */}
              <CartesianGrid
                horizontal={true}
                vertical={false}
                stroke="#f5f5f5"
                strokeDasharray="4 4"
              />

              {/* X Axis */}
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={{ stroke: "#f5f5f5" }}
                tickMargin={8}
                tick={{ fontSize: 10, fill: "#a3a3a3" }}
                interval="preserveStartEnd"
                minTickGap={30}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  });
                }}
              />

              {/* Y Axis */}
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={4}
                width={45}
                tick={{ fontSize: 10, fill: "#a3a3a3" }}
                tickFormatter={(value) =>
                  formatValue(value, currentMetric.format, currency, true)
                }
              />

              {/* Tooltip */}
              <Tooltip
                content={
                  <CustomTooltip
                    format={currentMetric.format}
                    currency={currency}
                  />
                }
                cursor={{ stroke: "#e5e5e5", strokeWidth: 1 }}
              />

              {/* Previous Period (dashed, behind current) */}
              {compareEnabled && (
                <Area
                  type="monotone"
                  dataKey="previous"
                  name="previous"
                  stroke="#d4d4d4"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  fill="transparent"
                  dot={false}
                  activeDot={false}
                />
              )}

              {/* Current Period (solid, on top) */}
              <Area
                type="monotone"
                dataKey="current"
                name="current"
                stroke="#171717"
                strokeWidth={2}
                fill="url(#currentGradient)"
                dot={false}
                activeDot={{
                  r: 4,
                  fill: "#171717",
                  stroke: "#fff",
                  strokeWidth: 2,
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
