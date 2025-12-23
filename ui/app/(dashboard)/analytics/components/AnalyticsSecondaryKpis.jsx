"use client";
/**
 * AnalyticsSecondaryKpis Component
 * ================================
 *
 * WHAT: Second row of KPIs showing derived metrics (Profit, AOV, CPC, CTR)
 * WHY: Users want to see efficiency metrics beyond basic spend/revenue
 *
 * METRICS:
 *   - Profit: Revenue - Spend (simple, clear)
 *   - AOV: Average Order Value = Revenue / Conversions
 *   - CPC: Cost Per Click (averaged from campaigns)
 *   - CTR: Click Through Rate (averaged from campaigns)
 *
 * RELATED:
 *   - AnalyticsKpiStrip.jsx (primary KPIs)
 *   - analytics/page.jsx (parent)
 */

import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, MousePointer, Target, BarChart3 } from "lucide-react";

const CURRENCY_SYMBOLS = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    CAD: 'C$',
    AUD: 'A$',
};

/**
 * Format currency values with appropriate symbols and decimals
 * Shows 2 decimal places for values under $10 (e.g., CPC, CPM)
 */
function formatCurrency(value, currency = 'USD', compact = false) {
    if (value === null || value === undefined) return '—';
    const symbol = CURRENCY_SYMBOLS[currency] || '$';
    const absValue = Math.abs(value);

    if (compact && absValue >= 1000) {
        return `${value < 0 ? '-' : ''}${symbol}${(absValue / 1000).toFixed(1)}k`;
    }

    // Show 2 decimals for small values (under $10) like CPC
    const decimals = absValue < 10 ? 2 : 0;

    return `${value < 0 ? '-' : ''}${symbol}${new Intl.NumberFormat('en-US', {
        maximumFractionDigits: decimals,
        minimumFractionDigits: decimals
    }).format(absValue)}`;
}

/**
 * Format percentage values
 */
function formatPercent(value) {
    if (value === null || value === undefined) return '—';
    return `${value.toFixed(2)}%`;
}

export default function AnalyticsSecondaryKpis({
    data,
    campaigns = [],
    loading,
    currency = 'USD',
    dataSource = "Blended Data"
}) {
    // Get KPIs from API response
    const kpis = {};
    data?.kpis?.forEach(item => {
        kpis[item.key] = item;
    });

    const revenue = kpis.revenue?.value || 0;
    const spend = kpis.spend?.value || 0;
    const conversions = kpis.conversions?.value || 0;

    // Previous period values for deltas
    const prevRevenue = kpis.revenue?.prev || 0;
    const prevSpend = kpis.spend?.prev || 0;
    const prevConversions = kpis.conversions?.prev || 0;

    // Calculate profit (derived)
    const profit = revenue - spend;
    const aov = conversions > 0 ? revenue / conversions : 0;

    // Calculate previous metrics for comparison
    const prevProfit = prevRevenue - prevSpend;
    const prevAov = prevConversions > 0 ? prevRevenue / prevConversions : 0;

    // Calculate deltas
    const profitDelta = prevProfit !== 0 ? ((profit - prevProfit) / Math.abs(prevProfit)) : null;
    const aovDelta = prevAov !== 0 ? ((aov - prevAov) / prevAov) : null;

    // Get CPC and CTR from API KPIs (calculated from aggregated clicks/impressions)
    const cpc = kpis.cpc?.value || 0;
    const ctr = kpis.ctr?.value || 0;
    const cpcDelta = kpis.cpc?.delta_pct || null;
    const ctrDelta = kpis.ctr?.delta_pct || null;

    // Define secondary metrics
    const metrics = [
        {
            key: 'profit',
            label: 'Profit',
            value: profit,
            delta: profitDelta,
            format: 'currency',
            icon: DollarSign,
            highlight: profit > 0,
            inverse: false
        },
        {
            key: 'aov',
            label: 'Avg Order Value',
            value: aov,
            delta: aovDelta,
            format: 'currency',
            icon: ShoppingCart,
            inverse: false
        },
        {
            key: 'cpc',
            label: 'CPC',
            value: cpc,
            delta: cpcDelta,
            format: 'currency',
            icon: MousePointer,
            inverse: true // Lower is better
        },
        {
            key: 'ctr',
            label: 'CTR',
            value: ctr,
            delta: ctrDelta,
            format: 'percent',
            icon: Target,
            inverse: false
        }
    ];

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
                    {metrics.map((_, i) => (
                        <div key={i} className="dashboard-module h-24"></div>
                    ))}
                </div>
            </section>
        );
    }

    return (
        <section className="space-y-3 animate-slide-up">
            {/* Data Source Header */}
            <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Efficiency KPIs</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${badgeStyle}`}>
                    {dataSource}
                </span>
            </div>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metrics.map((metric) => {
                const Icon = metric.icon;
                const isPositive = metric.delta !== null
                    ? (metric.inverse ? metric.delta < 0 : metric.delta >= 0)
                    : null;

                // Format the value
                let formattedValue = '—';
                if (metric.format === 'currency') {
                    formattedValue = formatCurrency(metric.value, currency);
                } else if (metric.format === 'percent') {
                    formattedValue = formatPercent(metric.value);
                }

                // Profit color indicator
                const isProfitPositive = metric.key === 'profit' && profit > 0;
                const isProfitNegative = metric.key === 'profit' && profit < 0;

                return (
                    <div
                        key={metric.key}
                        className={`
                            dashboard-module transition-all duration-300 cursor-pointer group
                            ${isProfitPositive ? 'ring-1 ring-emerald-200/50' : ''}
                            ${isProfitNegative ? 'ring-1 ring-red-200/50' : ''}
                        `}
                    >
                        {/* Header */}
                        <div className="flex items-center gap-2 mb-1">
                            <Icon className="w-3.5 h-3.5 text-slate-400" />
                            <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-slate-500">
                                {metric.label}
                            </p>
                        </div>

                        {/* Value */}
                        <div className={`text-xl font-bold tracking-tight mb-1 ${
                            isProfitPositive ? 'text-emerald-600' :
                            isProfitNegative ? 'text-red-500' :
                            'text-slate-900'
                        }`}>
                            {formattedValue}
                        </div>

                        {/* Delta */}
                        {metric.delta !== null && metric.delta !== undefined ? (
                            <div className={`flex items-center gap-1 text-xs font-medium ${
                                isPositive ? 'text-emerald-600' : 'text-red-500'
                            }`}>
                                {isPositive ? (
                                    <TrendingUp className="w-3 h-3" />
                                ) : (
                                    <TrendingDown className="w-3 h-3" />
                                )}
                                <span>
                                    {metric.delta >= 0 ? '+' : ''}
                                    {(metric.delta * 100).toFixed(1)}%
                                </span>
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
