"use client";
/**
 * AnalyticsProfitWidget Component
 * ================================
 *
 * WHAT: Net Profit card showing calculated profit from revenue - spend
 * WHY: Quick profitability indicator for merchants at a glance
 *
 * NOTE: Uses unified dashboard data which is aggregated across all platforms.
 * Per-platform breakdown requires separate API calls (not yet implemented).
 *
 * RELATED: lib/utils.js (formatCurrency, formatDelta)
 */
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { formatCurrency, formatDelta } from "@/lib/utils";

export default function AnalyticsProfitWidget({ data, loading }) {
    // Build KPI lookup from array
    const kpis = {};
    data?.kpis?.forEach(item => {
        kpis[item.key] = item;
    });

    // Get currency from API response (defaults to USD)
    const currency = data?.currency || "USD";

    // Calculate net profit from revenue and spend
    const revenue = kpis['revenue']?.value ?? 0;
    const spend = kpis['spend']?.value ?? 0;
    const netProfit = revenue - spend;
    const margin = revenue > 0 ? ((netProfit / revenue) * 100) : 0;

    // Calculate period-over-period change
    // Using revenue delta as proxy since we don't have direct profit comparison
    const revenueDelta = kpis['revenue']?.delta_pct;
    const deltaInfo = formatDelta(revenueDelta, false);

    if (loading) {
        return (
            <div className="dashboard-module border-l-4 border-l-emerald-400 animate-pulse">
                <div className="h-4 bg-slate-200/50 rounded w-1/3 mb-3"></div>
                <div className="h-8 bg-slate-200/50 rounded w-2/3 mb-2"></div>
                <div className="h-3 bg-slate-200/50 rounded w-1/2"></div>
            </div>
        );
    }

    const isPositive = netProfit >= 0;
    const TrendIcon = isPositive ? TrendingUp : (netProfit < 0 ? TrendingDown : Minus);

    return (
        <div className="dashboard-module border-l-4 border-l-emerald-400 relative overflow-hidden group">

            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Gross Profit
                </h3>
                {deltaInfo && (
                    <div className={`
                        flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold
                        ${deltaInfo.isGood ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}
                    `}>
                        <TrendIcon className="w-2.5 h-2.5" />
                        {deltaInfo.text} vs prev
                    </div>
                )}
            </div>

            {/* Main Value */}
            <div className={`text-3xl font-bold tracking-tight ${isPositive ? 'text-slate-800' : 'text-red-600'}`}>
                {formatCurrency(netProfit, { currency })}
            </div>

            {/* Margin */}
            <div className="text-xs text-slate-500 mt-1">
                Margin:{' '}
                <span className={`font-semibold ${margin >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {margin.toFixed(0)}%
                </span>
            </div>

            {/* Revenue/Spend breakdown */}
            <div className="flex gap-4 mt-4 pt-3 border-t border-slate-100 text-xs">
                <div>
                    <span className="text-slate-400">Revenue:</span>{' '}
                    <span className="font-medium text-slate-700">{formatCurrency(revenue, { currency })}</span>
                </div>
                <div>
                    <span className="text-slate-400">Spend:</span>{' '}
                    <span className="font-medium text-slate-700">{formatCurrency(spend, { currency })}</span>
                </div>
            </div>
        </div>
    );
}
