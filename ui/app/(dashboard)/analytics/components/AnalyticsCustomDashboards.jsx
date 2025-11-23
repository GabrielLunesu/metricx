"use client";
import { useEffect, useState } from "react";
import { fetchWorkspaceKpis } from "@/lib/api";
import { GripVertical, Plus } from "lucide-react";

export default function AnalyticsCustomDashboards({
    workspaceId,
    selectedProvider,
    rangeDays,
    customStartDate,
    customEndDate
}) {
    const [metrics, setMetrics] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;
        setLoading(true);

        const params = {
            workspaceId,
            metrics: ['profit', 'impressions', 'clicks', 'conversions'],
            lastNDays: rangeDays,
            provider: selectedProvider === 'all' ? null : selectedProvider,
            customStartDate: customStartDate || null,
            customEndDate: customEndDate || null
        };

        fetchWorkspaceKpis(params)
            .then((data) => {
                if (!mounted) return;
                const metricMap = {};
                data.forEach(item => {
                    metricMap[item.key] = item.value;
                });
                setMetrics(metricMap);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Failed to fetch dashboard metrics:', err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [workspaceId, selectedProvider, rangeDays, customStartDate, customEndDate]);

    // Calculate funnel percentages
    const impressions = metrics.impressions || 0;
    const clicks = metrics.clicks || 0;
    const conversions = metrics.conversions || 0;

    const clickRate = impressions > 0 ? (clicks / impressions) * 100 : 0;
    const convRate = clicks > 0 ? (conversions / clicks) * 100 : 0;

    // Normalize widths for visual funnel (impressions = 100%)
    // To make it look good, we'll just use relative widths but ensure they are visible
    const w1 = '100%';
    const w2 = '70%'; // Visual representation
    const w3 = '40%'; // Visual representation

    return (
        <section className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <div className="flex justify-between items-end mb-4">
                <h3 className="text-sm font-semibold text-slate-700">Custom View: <span className="text-slate-400 font-normal">Executive Summary</span></h3>
                <button className="text-[10px] text-cyan-600 font-medium flex items-center gap-1 hover:underline"><Plus className="w-3 h-3" /> Add Widget</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Widget 1: Profitability Gauge */}
                <div className="glass-panel p-4 rounded-2xl flex items-center gap-4 relative group">
                    <GripVertical className="absolute top-3 right-3 w-4 h-4 text-slate-300 opacity-0 group-hover:opacity-100 cursor-grab" />
                    <div className="relative w-16 h-16">
                        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                            <path className="text-slate-100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                            <path className="text-emerald-500 drop-shadow-md" strokeDasharray="75, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-slate-700">75%</div>
                    </div>
                    <div>
                        <div className="text-xs text-slate-500 uppercase font-medium">Profit Margin</div>
                        <div className="text-lg font-bold text-slate-800">
                            {loading ? '...' : `$${(metrics.profit || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                        </div>
                    </div>
                </div>

                {/* Widget 2: Funnel */}
                <div className="glass-panel p-4 rounded-2xl flex flex-col justify-center gap-2 relative group">
                    <GripVertical className="absolute top-3 right-3 w-4 h-4 text-slate-300 opacity-0 group-hover:opacity-100 cursor-grab" />
                    <div className="text-xs text-slate-500 uppercase font-medium mb-1">Conversion Funnel</div>

                    <div className="w-full h-1.5 bg-blue-50 rounded-full overflow-hidden flex relative group/bar">
                        <div className="h-full bg-blue-500 w-full"></div>
                        <span className="absolute -top-4 left-0 text-[9px] text-blue-500 opacity-0 group-hover/bar:opacity-100 transition-opacity">Imp: {impressions.toLocaleString()}</span>
                    </div>

                    <div className="w-[80%] h-1.5 bg-blue-50 rounded-full overflow-hidden flex relative group/bar">
                        <div className="h-full bg-blue-400 w-full"></div>
                        <span className="absolute -top-4 left-0 text-[9px] text-blue-400 opacity-0 group-hover/bar:opacity-100 transition-opacity">Clicks: {clicks.toLocaleString()}</span>
                    </div>

                    <div className="w-[40%] h-1.5 bg-blue-50 rounded-full overflow-hidden flex relative group/bar">
                        <div className="h-full bg-blue-300 w-full"></div>
                        <span className="absolute -top-4 left-0 text-[9px] text-blue-300 opacity-0 group-hover/bar:opacity-100 transition-opacity">Conv: {conversions.toLocaleString()}</span>
                    </div>
                </div>

                {/* Widget 3: Geo Map Placeholder */}
                <div className="glass-panel p-4 rounded-2xl flex flex-col justify-between relative group bg-[url('https://upload.wikimedia.org/wikipedia/commons/8/80/World_map_-_low_resolution.svg')] bg-no-repeat bg-center bg-contain bg-opacity-10">
                    <GripVertical className="absolute top-3 right-3 w-4 h-4 text-slate-300 opacity-0 group-hover:opacity-100 cursor-grab" />
                    <div className="text-xs text-slate-500 uppercase font-medium">Top Region</div>
                    <div className="text-lg font-bold text-slate-800 mt-auto">North America <span className="text-emerald-500 text-xs">+14%</span></div>
                </div>
            </div>
        </section>
    );
}
