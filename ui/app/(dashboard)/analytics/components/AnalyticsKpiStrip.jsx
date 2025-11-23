"use client";
import { useEffect, useState } from "react";
import { fetchWorkspaceKpis } from "@/lib/api";
import { ArrowUpRight, ArrowDownRight, Minus, TrendingUp } from "lucide-react";

const METRICS_CONFIG = [
    { key: 'spend', label: 'Spend', format: 'currency', inverse: true },
    { key: 'revenue', label: 'Revenue', format: 'currency', inverse: false },
    { key: 'roas', label: 'ROAS', format: 'number', suffix: 'x', inverse: false },
    { key: 'cpa', label: 'CPA', format: 'currency', inverse: true },
    { key: 'ctr', label: 'CTR', format: 'percentage', inverse: false },
    { key: 'cpc', label: 'CPC', format: 'currency', inverse: true, decimals: 2 },
    { key: 'cvr', label: 'Conv. Rate', format: 'percentage', inverse: false },
];

export default function AnalyticsKpiStrip({
    workspaceId,
    selectedProvider,
    timeFilters,
    campaignId = null
}) {
    const [kpis, setKpis] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        let mounted = true;
        setLoading(true);

        // Build params based on timeFilters type
        const params = {
            workspaceId,
            metrics: METRICS_CONFIG.map(m => m.key),
            provider: selectedProvider === 'all' ? null : selectedProvider,
            compareToPrevious: true,
            campaignId: campaignId || undefined
        };

        // Add time range params
        if (timeFilters.type === 'custom' && timeFilters.customStart && timeFilters.customEnd) {
            // Custom date range - only pass custom dates
            params.customStartDate = timeFilters.customStart;
            params.customEndDate = timeFilters.customEnd;
            params.lastNDays = timeFilters.rangeDays; // for backend compatibility
        } else {
            // Preset range - only pass lastNDays
            params.lastNDays = timeFilters.rangeDays;
        }

        fetchWorkspaceKpis(params)
            .then((data) => {
                if (!mounted) return;
                // Convert array to object for easier access
                const kpiMap = {};
                data.forEach(item => {
                    kpiMap[item.key] = item;
                });
                setKpis(kpiMap);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Failed to fetch KPIs:', err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [workspaceId, selectedProvider, timeFilters.type, timeFilters.rangeDays, timeFilters.customStart, timeFilters.customEnd, campaignId]);

    const formatValue = (value, config) => {
        if (value === null || value === undefined) return "—";

        if (config.format === 'currency') {
            const decimals = config.decimals ?? 0;
            return `$${value.toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            })}`;
        }
        if (config.format === 'percentage') {
            return `${value.toFixed(2)}%`;
        }
        if (config.format === 'number') {
            return `${value.toFixed(2)}${config.suffix || ''}`;
        }
        return value;
    };

    const getTrendIcon = (delta, inverse) => {
        if (!delta) return <Minus className="w-3 h-3 text-slate-400" />;

        const isPositive = delta > 0;
        const isGood = inverse ? !isPositive : isPositive;

        if (isPositive) {
            return <ArrowUpRight className={`w-3 h-3 ${isGood ? 'text-emerald-500' : 'text-red-500'}`} />;
        } else {
            return <ArrowDownRight className={`w-3 h-3 ${isGood ? 'text-emerald-500' : 'text-red-500'}`} />;
        }
    };

    const getTrendColor = (delta, inverse) => {
        if (!delta) return 'text-slate-400';
        const isPositive = delta > 0;
        const isGood = inverse ? !isPositive : isPositive;
        return isGood ? 'text-emerald-600' : 'text-red-600';
    };

    const getBarColor = (metricKey) => {
        switch (metricKey) {
            case 'revenue': return 'bg-emerald-500';
            case 'spend': return 'bg-slate-800';
            case 'roas': return 'bg-cyan-400';
            case 'cpa': return 'bg-slate-400';
            case 'ctr': return 'bg-yellow-400';
            case 'cpc': return 'bg-red-400';
            case 'cvr': return 'bg-blue-400';
            default: return 'bg-slate-400';
        }
    };

    if (loading) {
        return (
            <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3 xl:gap-4 animate-pulse">
                {[...Array(7)].map((_, i) => (
                    <div key={i} className="glass-panel rounded-2xl p-4 h-24"></div>
                ))}
            </section>
        );
    }

    return (
        <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3 xl:gap-4 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            {METRICS_CONFIG.map((config) => {
                const data = kpis[config.key] || {};
                const value = data.value;
                const delta = data.delta_pct;

                return (
                    <div
                        key={config.key}
                        className="glass-panel rounded-2xl p-4 hover:-translate-y-1 transition-transform duration-300 cursor-pointer group relative overflow-hidden border-t border-white/80"
                    >
                        {/* Hover Gradient Line */}
                        <div className={`absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-cyan-400 to-blue-400 opacity-0 group-hover:opacity-100 transition-opacity`}></div>

                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">{config.label}</span>
                            {getTrendIcon(delta, config.inverse)}
                        </div>

                        <div className="text-lg xl:text-xl font-bold text-slate-800 tracking-tight">
                            {formatValue(value, config)}
                        </div>

                        <div className="flex items-center gap-1 mt-1">
                            {/* Simulated Progress Bar */}
                            <div className="w-12 h-1 bg-slate-100 rounded-full overflow-hidden">
                                <div className={`h-full ${getBarColor(config.key)}`} style={{ width: `${Math.random() * 40 + 40}%` }}></div>
                            </div>
                            <span className={`text-[10px] ${getTrendColor(delta, config.inverse)}`}>
                                {delta ? `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(1)}%` : '—'}
                            </span>
                        </div>
                    </div>
                );
            })}
        </section>
    );
}
