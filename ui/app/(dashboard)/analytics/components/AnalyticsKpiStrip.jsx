"use client";
/**
 * AnalyticsKpiStrip Component
 * ============================
 *
 * WHAT: 4 KPI cards showing key metrics (Spend, Revenue, ROAS, Conversions)
 * WHY: Quick overview of key performance metrics at a glance
 *
 * DESIGN: Glassmorphic cards matching dashboard-module styling
 *
 * RELATED:
 *   - lib/utils.js (formatMetricValue, formatDelta)
 *   - dashboard/components/KpiCardsModule.jsx (styling reference)
 *
 * NOTE: Reduced from 7 metrics to 4 core metrics that match chart_data.
 * CPA, CPC, CTR, CVR not available in unified dashboard endpoint.
 */
import { TrendingUp, TrendingDown, Layers } from "lucide-react";
import { formatMetricValue, formatDelta } from "@/lib/utils";

/**
 * KPI metric definitions.
 * NOTE: Must match keys available in kpis array from dashboard API.
 */
const METRICS = [
    { key: 'spend', label: 'Spend', format: 'currency', inverse: true },
    { key: 'revenue', label: 'Revenue', format: 'currency', inverse: false },
    { key: 'roas', label: 'ROAS', format: 'multiplier', inverse: false, highlight: true },
    { key: 'conversions', label: 'Conversions', format: 'number', inverse: false },
];

export default function AnalyticsKpiStrip({ data, loading, dataSource = "Blended Data" }) {
    // Convert kpis array to map for O(1) lookups
    const kpis = {};
    data?.kpis?.forEach(item => {
        kpis[item.key] = item;
    });

    // Get currency from API response (defaults to USD)
    const currency = data?.currency || "USD";

    // Determine badge styling based on data source
    const isGoogle = dataSource?.toLowerCase().includes('google');
    const isMeta = dataSource?.toLowerCase().includes('meta');
    const badgeStyle = isGoogle
        ? 'bg-blue-50 text-blue-700 border-blue-200'
        : isMeta
        ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
        : 'bg-slate-100 text-slate-600 border-slate-200';

    if (loading) {
        return (
            <section className="space-y-3">
                <div className="flex items-center gap-2">
                    <div className="h-5 w-32 bg-slate-200 rounded animate-pulse"></div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
                    {METRICS.map((_, i) => (
                        <div key={i} className="dashboard-module h-28"></div>
                    ))}
                </div>
            </section>
        );
    }

    return (
        <section className="space-y-3 animate-slide-up">
            {/* Data Source Header */}
            <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Primary KPIs</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${badgeStyle}`}>
                    {dataSource}
                </span>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {METRICS.map((metric) => {
                const kpiData = kpis[metric.key] || {};
                const value = kpiData.value;
                const deltaInfo = formatDelta(kpiData.delta_pct, metric.inverse);
                const isPositive = deltaInfo?.isGood;

                return (
                    <div
                        key={metric.key}
                        className={`
                            dashboard-module transition-all duration-300 cursor-pointer group
                            ${metric.highlight ? 'ring-1 ring-cyan-200/50' : ''}
                        `}
                    >
                        {/* Label */}
                        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500 mb-1">
                            {metric.label}
                        </p>

                        {/* Value */}
                        <div className="text-2xl font-bold tracking-tight text-slate-900 mb-1">
                            {formatMetricValue(value, metric.format, { decimals: metric.decimals ?? 0, currency })}
                        </div>

                        {/* Delta */}
                        {deltaInfo ? (
                            <div className={`flex items-center gap-1 text-xs font-medium ${
                                isPositive ? 'text-emerald-600' : 'text-red-500'
                            }`}>
                                {isPositive ? (
                                    <TrendingUp className="w-3 h-3" />
                                ) : (
                                    <TrendingDown className="w-3 h-3" />
                                )}
                                <span>{deltaInfo.text}</span>
                                <span className="text-slate-400 font-normal">vs prev</span>
                            </div>
                        ) : (
                            <span className="text-xs text-slate-400">—</span>
                        )}
                    </div>
                );
            })}
            </div>
        </section>
    );
}
