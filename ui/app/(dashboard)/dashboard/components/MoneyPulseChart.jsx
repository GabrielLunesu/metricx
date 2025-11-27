'use client';

import { useEffect, useState } from "react";
import { fetchWorkspaceKpis } from "@/lib/api";
import { metricxChart } from "@/components/charts/metricxChart";

export default function MoneyPulseChart({ workspaceId, timeframe }) {
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState('overview'); // 'overview' | 'breakdown'
    const [chartData, setChartData] = useState([]);

    // Fetch Data
    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                // Map timeframe to API params
                let lastNDays = 7;
                let dayOffset = 0;

                switch (timeframe) {
                    case 'today':
                        lastNDays = 1;
                        dayOffset = 0;
                        break;
                    case 'yesterday':
                        lastNDays = 1;
                        dayOffset = 1;
                        break;
                    case 'last_7_days':
                        lastNDays = 7;
                        dayOffset = 0;
                        break;
                    case 'last_30_days':
                        lastNDays = 30;
                        dayOffset = 0;
                        break;
                    default:
                        lastNDays = 7;
                }

                const metrics = ["revenue", "spend"];
                const res = await fetchWorkspaceKpis({
                    workspaceId,
                    metrics,
                    lastNDays,
                    dayOffset,
                    sparkline: true
                });

                // Transform data for metricxChart (Recharts format)
                const revenueData = res.find(d => d.key === 'revenue')?.sparkline || [];
                const spendData = res.find(d => d.key === 'spend')?.sparkline || [];

                const mergedData = revenueData.map((item, index) => ({
                    date: item.date,
                    revenue: item.value,
                    spend: spendData[index]?.value || 0
                }));

                setChartData(mergedData);

            } catch (err) {
                console.error("Failed to fetch Money Pulse data:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [workspaceId, timeframe]);

    const chartConfig = {
        revenue: {
            label: "Revenue",
            color: "#06b6d4", // Cyan 500
        },
        spend: {
            label: "Spend",
            color: "#f43f5e", // Rose 500
        },
    };

    const isSingleDay = timeframe === 'today' || timeframe === 'yesterday';

    return (
        <div className="lg:col-span-2 glass-panel rounded-[32px] p-6 md:p-8 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div>
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight">Money Pulse</h3>
                    <p className="text-xs text-slate-500">Real-time revenue & spend velocity</p>
                </div>
                {/* Toggle Pill */}
                <div className="flex bg-slate-100/50 p-1 rounded-full border border-white/60 backdrop-blur-sm">
                    <button
                        onClick={() => setViewMode('overview')}
                        className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'overview' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setViewMode('breakdown')}
                        className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'breakdown' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Breakdown
                    </button>
                </div>
            </div>

            <div className="relative w-full h-[280px]">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-20 backdrop-blur-sm">
                        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <metricxChart
                        data={chartData}
                        config={chartConfig}
                        type={viewMode === 'overview' ? 'area' : 'bar'}
                        height="280px"
                        isSingleDay={isSingleDay}
                    />
                )}
            </div>
        </div>
    );
}
