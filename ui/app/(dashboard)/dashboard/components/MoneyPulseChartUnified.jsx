'use client';

/**
 * MoneyPulseChartUnified Component
 *
 * WHAT: Displays revenue/spend chart using unified dashboard data
 * WHY: Uses pre-fetched chart_data instead of making its own API call
 *
 * REFERENCES:
 *   - docs/PERFORMANCE_INVESTIGATION.md
 */

import { MetricxChart } from "@/components/charts/MetricxChart";

export default function MoneyPulseChartUnified({ data, loading }) {
    if (loading || !data) {
        return (
            <div className="lg:col-span-2 glass-panel rounded-2xl p-4 animate-pulse h-72">
                <div className="h-full bg-slate-100 rounded"></div>
            </div>
        );
    }

    // Use chart_data from unified response
    const chartData = data.chart_data || [];

    if (chartData.length === 0) {
        return (
            <div className="lg:col-span-2 glass-panel rounded-2xl p-6">
                <p className="text-slate-500">No chart data available</p>
            </div>
        );
    }

    // Config for MetricxChart - object with series names as keys
    const chartConfig = {
        revenue: {
            label: "Revenue",
            color: "#22d3ee"
        },
        spend: {
            label: "Ad Spend",
            color: "#818cf8"
        }
    };

    return (
        <div className="lg:col-span-2">
            <MetricxChart
                data={chartData}
                config={chartConfig}
                type="area"
                xAxisKey="date"
                height="280px"
            />
        </div>
    );
}
