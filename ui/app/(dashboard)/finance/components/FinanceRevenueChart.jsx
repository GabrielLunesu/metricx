"use client";

/**
 * FinanceRevenueChart - Bar chart for daily revenue
 * 
 * WHAT: Displays revenue over time as a bar chart
 * WHY: Visual trend of revenue performance
 * 
 * REFERENCES:
 *   - Metricx v3.0 design system
 *   - Uses Recharts for chart rendering
 */

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { ChevronDown } from "lucide-react";

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
 * Format currency value for display
 */
function formatValue(value, currency = "EUR", compact = false) {
  if (value === null || value === undefined) return "—";
  const symbol = CURRENCY_SYMBOLS[currency] || "€";

  if (compact && Math.abs(value) >= 1000) {
    return `${symbol}${(value / 1000).toFixed(1)}k`;
  }
  return `${symbol}${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value)}`;
}

/**
 * Custom Tooltip
 */
function CustomTooltip({ active, payload, label, currency }) {
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
      <div className="flex justify-between gap-4 text-neutral-400">
        <span>Revenue:</span>
        <span className="text-white font-medium">
          {formatValue(payload[0]?.value, currency)}
        </span>
      </div>
    </div>
  );
}

export default function FinanceRevenueChart({
  timeseries = [],
  loading = false,
  currency = "EUR",
}) {
  // Prepare chart data
  const chartData = useMemo(() => {
    if (!timeseries || timeseries.length === 0) return [];
    
    return timeseries.map((d) => ({
      date: d.date,
      revenue: d.revenue || 0,
    }));
  }, [timeseries]);

  // Check if we have data
  const hasData = chartData.length > 0 && chartData.some((d) => d.revenue > 0);

  if (loading) {
    return (
      <div className="p-6 border border-neutral-200 bg-white rounded-xl h-full">
        <div className="flex items-center justify-between mb-8">
          <div className="h-5 w-40 bg-neutral-100 rounded animate-pulse" />
          <div className="h-4 w-16 bg-neutral-100 rounded animate-pulse" />
        </div>
        <div className="h-64 bg-neutral-50 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="p-6 border border-neutral-200 bg-white rounded-xl shadow-[0_1px_2px_rgba(0,0,0,0.02)] h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h3 className="text-base font-semibold text-neutral-900 tracking-tight">
          Revenue Over Time
        </h3>
        <button
          disabled
          className="text-xs font-medium text-neutral-500 flex items-center gap-1 cursor-not-allowed"
        >
          Daily <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* Chart */}
      <div className="h-64 w-full">
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
            <p className="text-neutral-600 font-medium text-sm">No revenue data</p>
            <p className="text-neutral-400 text-xs mt-1">
              Data will appear after syncing
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 0, left: 0, bottom: 0 }}
            >
              {/* Grid */}
              <CartesianGrid
                horizontal={true}
                vertical={false}
                stroke="#f5f5f5"
                strokeDasharray="0"
              />

              {/* X Axis */}
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={{ stroke: "#f5f5f5" }}
                tickMargin={12}
                tick={{ fontSize: 10, fill: "#a3a3a3" }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  });
                }}
                interval="preserveStartEnd"
              />

              {/* Y Axis */}
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={55}
                tick={{ fontSize: 10, fill: "#a3a3a3" }}
                tickFormatter={(value) => formatValue(value, currency, true)}
              />

              {/* Tooltip */}
              <Tooltip
                content={<CustomTooltip currency={currency} />}
                cursor={{ fill: "rgba(0,0,0,0.02)" }}
              />

              {/* Bars */}
              <Bar
                dataKey="revenue"
                fill="#171717"
                radius={[2, 2, 0, 0]}
                maxBarSize={30}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
