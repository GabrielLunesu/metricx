"use client";
/**
 * ProfitTrendChart Component
 * ==========================
 *
 * WHAT: Shows daily profit (Revenue - Spend) as a bar chart
 * WHY: Users want to visualize profitability at a glance
 *
 * FEATURES:
 *   - Bar chart with daily profit
 *   - Green bars for positive profit
 *   - Red bars for negative profit
 *   - Shows total profit for period
 *
 * RELATED:
 *   - analytics/page.jsx (parent)
 *   - AnalyticsGraphEngine.jsx (similar patterns)
 */

import { useMemo } from "react";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ReferenceLine,
    CartesianGrid,
    Cell
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign } from "lucide-react";

const CURRENCY_SYMBOLS = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    CAD: 'C$',
    AUD: 'A$',
};

function formatCurrency(value, currency = 'USD') {
    if (value === null || value === undefined) return '—';
    const symbol = CURRENCY_SYMBOLS[currency] || '$';
    const isNegative = value < 0;
    const absValue = Math.abs(value);

    if (absValue >= 1000000) {
        return `${isNegative ? '-' : ''}${symbol}${(absValue / 1000000).toFixed(1)}M`;
    }
    if (absValue >= 1000) {
        return `${isNegative ? '-' : ''}${symbol}${(absValue / 1000).toFixed(1)}k`;
    }
    return `${isNegative ? '-' : ''}${symbol}${Math.round(absValue)}`;
}

function formatDateLabel(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return dateStr;
    }
}

function CustomTooltip({ active, payload, label, currency }) {
    if (!active || !payload?.length) return null;

    const profit = payload[0]?.value || 0;
    const isPositive = profit >= 0;

    return (
        <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-xl px-3 py-2 shadow-lg">
            <p className="text-[10px] text-slate-500 mb-1">{formatDateLabel(label)}</p>
            <p className={`text-sm font-bold ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
                {formatCurrency(profit, currency)} profit
            </p>
        </div>
    );
}

export default function ProfitTrendChart({
    chartData = [],
    loading,
    currency = 'USD'
}) {
    // Calculate profit for each data point
    const profitData = useMemo(() => {
        return chartData.map(d => ({
            date: d.date,
            profit: (d.revenue || 0) - (d.spend || 0),
            revenue: d.revenue || 0,
            spend: d.spend || 0
        }));
    }, [chartData]);

    // Calculate totals
    const totals = useMemo(() => {
        let totalProfit = 0;
        let totalRevenue = 0;
        let totalSpend = 0;
        let profitableDays = 0;

        profitData.forEach(d => {
            totalProfit += d.profit;
            totalRevenue += d.revenue;
            totalSpend += d.spend;
            if (d.profit > 0) profitableDays++;
        });

        return {
            profit: totalProfit,
            revenue: totalRevenue,
            spend: totalSpend,
            profitableDays,
            totalDays: profitData.length,
            margin: totalRevenue > 0 ? ((totalProfit / totalRevenue) * 100) : 0
        };
    }, [profitData]);


    if (loading) {
        return (
            <div className="dashboard-module animate-pulse">
                <div className="flex items-center gap-2 mb-4">
                    <div className="h-5 w-5 bg-slate-200/50 rounded"></div>
                    <div className="h-5 w-32 bg-slate-200/50 rounded"></div>
                </div>
                <div className="h-[180px] bg-slate-100/50 rounded-xl"></div>
            </div>
        );
    }

    if (!profitData.length) {
        return (
            <div className="dashboard-module">
                <div className="flex items-center gap-2 mb-4">
                    <DollarSign className="w-4 h-4 text-emerald-500" />
                    <h3 className="text-sm font-semibold text-slate-900">Daily Profit</h3>
                </div>
                <div className="h-[180px] flex items-center justify-center">
                    <p className="text-sm text-slate-500">No data available</p>
                </div>
            </div>
        );
    }

    const isPositiveTotal = totals.profit >= 0;

    return (
        <div className="dashboard-module">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <DollarSign className={`w-4 h-4 ${isPositiveTotal ? 'text-emerald-500' : 'text-red-500'}`} />
                    <h3 className="text-sm font-semibold text-slate-900">Daily Profit</h3>
                </div>
                <div className="text-right">
                    <p className={`text-lg font-bold ${isPositiveTotal ? 'text-emerald-600' : 'text-red-500'}`}>
                        {formatCurrency(totals.profit, currency)}
                    </p>
                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                        {isPositiveTotal ? (
                            <TrendingUp className="w-3 h-3 text-emerald-500" />
                        ) : (
                            <TrendingDown className="w-3 h-3 text-red-500" />
                        )}
                        <span>{totals.margin.toFixed(1)}% margin</span>
                    </div>
                </div>
            </div>

            {/* Chart */}
            <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={profitData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                        <XAxis
                            dataKey="date"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fontSize: 9, fill: '#94a3b8' }}
                            tickFormatter={formatDateLabel}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            axisLine={false}
                            tickLine={false}
                            tick={{ fontSize: 9, fill: '#94a3b8' }}
                            tickFormatter={(val) => formatCurrency(val, currency)}
                            width={50}
                        />
                        <Tooltip content={<CustomTooltip currency={currency} />} />
                        {/* Zero reference line */}
                        <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
                        {/* Profit bars with conditional coloring */}
                        <Bar dataKey="profit" radius={[3, 3, 0, 0]}>
                            {profitData.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.profit >= 0 ? '#10b981' : '#ef4444'}
                                    fillOpacity={0.85}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Footer stats */}
            <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-3 gap-4 text-center">
                <div>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wide">Revenue</p>
                    <p className="text-sm font-semibold text-slate-900">{formatCurrency(totals.revenue, currency)}</p>
                </div>
                <div>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wide">Ad Spend</p>
                    <p className="text-sm font-semibold text-slate-900">{formatCurrency(totals.spend, currency)}</p>
                </div>
                <div>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wide">Profitable Days</p>
                    <p className="text-sm font-semibold text-slate-900">{totals.profitableDays}/{totals.totalDays}</p>
                </div>
            </div>
        </div>
    );
}
