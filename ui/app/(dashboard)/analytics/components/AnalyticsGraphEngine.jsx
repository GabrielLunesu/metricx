"use client";
import { useEffect, useRef, useState } from "react";
import { fetchWorkspaceKpis } from "@/lib/api";
import { metricxChart } from "@/components/charts/metricxChart";

export default function AnalyticsGraphEngine({
    workspaceId,
    selectedProvider,
    timeFilters,
    campaignId
}) {
    const [loading, setLoading] = useState(true);
    const [chartData, setChartData] = useState([]);
    const [viewMode, setViewMode] = useState('overview'); // 'overview' | 'breakdown'

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;
        setLoading(true);

        // Build params based on timeFilters type
        const params = {
            workspaceId,
            metrics: ['revenue', 'spend', 'roas'],
            provider: selectedProvider === 'all' ? null : selectedProvider,
            sparkline: true,
            campaignId: campaignId || null
        };

        // Add time range params based on filter type
        if (timeFilters.type === 'custom' && timeFilters.customStart && timeFilters.customEnd) {
            params.customStartDate = timeFilters.customStart;
            params.customEndDate = timeFilters.customEnd;
            params.lastNDays = timeFilters.rangeDays;
        } else {
            params.lastNDays = timeFilters.rangeDays;
        }

        fetchWorkspaceKpis(params)
            .then((data) => {
                if (!mounted) return;

                // Transform data for Recharts: Array of objects with date and all metrics
                // Assuming all sparklines have the same dates
                const revenueData = data.find(d => d.key === 'revenue')?.sparkline || [];
                const spendData = data.find(d => d.key === 'spend')?.sparkline || [];
                const roasData = data.find(d => d.key === 'roas')?.sparkline || [];

                const mergedData = revenueData.map((item, index) => ({
                    date: item.date,
                    revenue: item.value,
                    spend: spendData[index]?.value || 0,
                    roas: roasData[index]?.value || 0
                }));

                setChartData(mergedData);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Failed to fetch chart data:', err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [workspaceId, selectedProvider, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd, campaignId]);

    const chartConfig = {
        revenue: {
            label: "Revenue",
            color: "#2563eb", // Blue 600
        },
        spend: {
            label: "Spend",
            color: "#93c5fd", // Blue 300
        },
        // ROAS is typically on a different axis/scale, which is tricky in a simple AreaChart.
        // For now, we might exclude it or accept it shares the scale (which is bad for ROAS vs Revenue).
        // The user asked to "only show line" and "remove data points".
        // Let's stick to Revenue and Spend for the main visual as they are currency.
        // If ROAS is needed, we'd need a composed chart with dual axis, but metricxChart is simple Area/Bar.
        // Let's hide ROAS for now to keep it clean as requested "readability... on mobile".
    };

    return (
        <div className="xl:col-span-2 bg-white border border-slate-200 shadow-sm rounded-[24px] p-4 md:p-6 flex flex-col relative overflow-hidden h-full min-h-[400px]">
            {/* Graph Header */}
            <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-semibold text-slate-800">
                        Performance Velocity
                        {(timeFilters.rangeDays === 1 ||
                            (timeFilters.type === 'custom' && timeFilters.customStart === timeFilters.customEnd)) ? (
                            <span className="text-sm font-normal text-slate-500 ml-2">(24 Hours)</span>
                        ) : null}
                    </h2>
                    <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
                        <button
                            onClick={() => setViewMode('overview')}
                            className={`px-3 py-1 rounded-md text-[10px] font-semibold transition-all ${viewMode === 'overview' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Overview
                        </button>
                        <button
                            onClick={() => setViewMode('breakdown')}
                            className={`px-3 py-1 rounded-md text-[10px] font-medium transition-all ${viewMode === 'breakdown' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Breakdown
                        </button>
                    </div>
                </div>
                <div className="flex gap-4 items-center">
                    <div className="flex items-center gap-2 text-[10px]">
                        <span className="w-2 h-2 rounded-full bg-blue-600"></span> Revenue
                        <span className="w-2 h-2 rounded-full bg-blue-300 ml-2"></span> Spend
                    </div>
                </div>
            </div>

            {/* Canvas Area */}
            <div className="relative w-full flex-1">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <metricxChart
                        data={chartData}
                        config={chartConfig}
                        type={viewMode === 'overview' ? 'area' : 'bar'}
                        height="300px"
                        isSingleDay={timeFilters.rangeDays === 1 || (timeFilters.type === 'custom' && timeFilters.customStart === timeFilters.customEnd)}
                    />
                )}
            </div>
        </div>
    );
}
