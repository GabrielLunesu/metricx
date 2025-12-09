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

export default function MoneyPulseChartUnified({ data, loading, timeframe = 'last_7_days' }) {
    // Show hourly x-axis for today/yesterday views
    const isSingleDay = timeframe === 'today' || timeframe === 'yesterday';
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

    // Check how many slots actually have data (non-null)
    const slotsWithData = chartData.filter(d => d.spend !== null).length;

    // Show message only if NO data points at all
    if (slotsWithData === 0 && isSingleDay) {
        return (
            <div className="lg:col-span-2 glass-panel rounded-2xl p-6">
                <div className="flex flex-col items-center justify-center h-64 text-center">
                    <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                        <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <p className="text-slate-600 font-medium mb-1">No sync data yet</p>
                    <p className="text-slate-400 text-sm max-w-xs">
                        Chart will populate as syncs complete (every 15 min).
                    </p>
                </div>
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
                isSingleDay={isSingleDay}
            />
        </div>
    );
}
