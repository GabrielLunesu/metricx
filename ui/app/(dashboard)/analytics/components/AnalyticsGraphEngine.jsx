"use client";
/**
 * AnalyticsGraphEngine Component (v2.0 - Server-side filtering)
 * =============================================================
 *
 * WHAT: Multi-line chart that renders server-provided series data
 * WHY: Frontend is dumb - just renders what backend sends
 *
 * DESIGN:
 *   - Receives pre-computed series from /analytics/chart endpoint
 *   - Each series has {key, label, color, data: [...]}
 *   - No client-side filtering logic - all filtering happens server-side
 *   - Metric tabs trigger parent to re-fetch with new metric
 *
 * PROPS:
 *   - series: Array of {key, label, color, data} from API
 *   - totals: {revenue, spend, roas, ...} totals for period
 *   - metadata: {granularity, platforms_available, ...}
 *   - loading: Boolean loading state
 *   - selectedMetric: Current metric tab ('revenue', 'spend', etc.)
 *   - onMetricChange: Callback when metric tab clicked
 *
 * RELATED:
 *   - backend/app/routers/analytics.py (data source)
 *   - lib/api.js (fetchAnalyticsChart)
 */
import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Legend } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Info } from "lucide-react";

/**
 * Metric tabs configuration.
 * When user clicks a tab, parent component re-fetches with that metric.
 */
const METRIC_TABS = [
    { key: 'revenue', label: 'Revenue', format: 'currency' },
    { key: 'spend', label: 'Spend', format: 'currency' },
    { key: 'roas', label: 'ROAS', format: 'multiplier' },
    { key: 'conversions', label: 'Conversions', format: 'number' },
];

// Currency symbols for formatting
const CURRENCY_SYMBOLS = {
    USD: "$",
    EUR: "€",
    GBP: "£",
    CAD: "C$",
    AUD: "A$",
};

export default function AnalyticsGraphEngine({
    series = [],
    totals = {},
    metadata = {},
    loading,
    selectedMetric,
    onMetricChange,
    currency = "USD",
}) {
    // Get current metric config for formatting
    const currentMetric = useMemo(() => {
        return METRIC_TABS.find(m => m.key === selectedMetric) || METRIC_TABS[0];
    }, [selectedMetric]);

    // Granularity from metadata (or default to 'day')
    const granularity = metadata?.granularity || 'day';

    // Check if we have data to show
    const hasData = useMemo(() => {
        if (!series || series.length === 0) return false;
        return series.some(s => s.data && s.data.length > 0 && s.data.some(d => (d[selectedMetric] ?? 0) > 0));
    }, [series, selectedMetric]);

    // Transform series data for chart - pick the selected metric as the Y value
    const chartData = useMemo(() => {
        if (!series || series.length === 0) return [];

        // If single series, just return its data with metric value
        if (series.length === 1) {
            return series[0].data.map(d => ({
                date: d.date,
                [series[0].key]: d[selectedMetric] ?? 0
            }));
        }

        // Multiple series: merge by date
        const dateMap = new Map();

        series.forEach(s => {
            (s.data || []).forEach(d => {
                if (!dateMap.has(d.date)) {
                    dateMap.set(d.date, { date: d.date });
                }
                dateMap.get(d.date)[s.key] = d[selectedMetric] ?? 0;
            });
        });

        return Array.from(dateMap.values()).sort((a, b) =>
            new Date(a.date) - new Date(b.date)
        );
    }, [series, selectedMetric]);

    // Build chart config from series
    const chartConfig = useMemo(() => {
        const config = {};
        series.forEach(s => {
            config[s.key] = { label: s.label, color: s.color };
        });
        return config;
    }, [series]);

    /**
     * Format value for Y axis and tooltip.
     */
    const formatValue = (value, format, compact = false) => {
        if (value === null || value === undefined) return '—';

        const symbol = CURRENCY_SYMBOLS[currency] || currency;

        switch (format) {
            case 'currency':
                if (compact && value >= 1000) return `${symbol}${(value / 1000).toFixed(1)}k`;
                return `${symbol}${value.toFixed(0)}`;
            case 'multiplier':
                return `${value.toFixed(2)}x`;
            case 'number':
                if (compact && value >= 1000) return `${(value / 1000).toFixed(1)}k`;
                return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
            default:
                return value.toLocaleString();
        }
    };

    if (loading) {
        return (
            <div className="flex-[3] dashboard-module min-h-[450px] animate-pulse">
                <div className="flex items-center justify-between mb-6">
                    <div className="h-6 w-32 bg-slate-200/50 rounded-lg"></div>
                    <div className="flex gap-2">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="h-8 w-20 bg-slate-200/50 rounded-full"></div>
                        ))}
                    </div>
                </div>
                <div className="h-80 bg-slate-200/30 rounded-2xl"></div>
            </div>
        );
    }

    return (
        <div className="flex-[3] dashboard-module min-h-[450px] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500">
                        Performance Analytics
                    </p>
                    <div className="flex items-center gap-3 mt-0.5">
                        <h2 className="text-xl font-semibold tracking-tight text-slate-900">
                            {currentMetric.label}
                        </h2>
                        {/* Selection indicator - shows what's being displayed */}
                        <div className="flex items-center gap-1.5">
                            {series.length === 1 && series[0].key === 'total' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-[10px] font-medium text-slate-600">
                                    All Platforms
                                </span>
                            ) : (
                                series.map(s => (
                                    <span
                                        key={s.key}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium text-white"
                                        style={{ backgroundColor: s.color }}
                                    >
                                        {s.label}
                                    </span>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Metric Tabs */}
            <div className="flex items-center gap-1.5 mb-4 p-1 bg-slate-900/5 rounded-full w-fit">
                {METRIC_TABS.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => onMetricChange(tab.key)}
                        className={`
                            px-4 py-1.5 rounded-full text-[11px] font-medium transition-all duration-200
                            ${selectedMetric === tab.key
                                ? 'bg-slate-900 text-white shadow-sm'
                                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
                            }
                        `}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Chart Canvas */}
            <div className="flex-1 min-h-[320px]">
                {!hasData ? (
                    <div className="h-full flex flex-col items-center justify-center text-center">
                        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                            <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <p className="text-slate-600 font-medium text-sm">No data yet</p>
                        <p className="text-slate-400 text-xs mt-1">
                            Data will appear after the next sync
                        </p>
                    </div>
                ) : (
                    <ChartContainer config={chartConfig} className="h-full w-full">
                        <AreaChart data={chartData} margin={{ left: 0, right: 0, top: 10, bottom: 0 }}>
                            <defs>
                                {series.map(s => (
                                    <linearGradient key={`gradient-${s.key}`} id={`gradient-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={s.color} stopOpacity={0.3} />
                                        <stop offset="95%" stopColor={s.color} stopOpacity={0.05} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <CartesianGrid
                                vertical={false}
                                strokeDasharray="3 3"
                                stroke="#e2e8f0"
                                opacity={0.5}
                            />
                            <XAxis
                                dataKey="date"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={8}
                                tick={{ fontSize: 11, fill: '#64748b' }}
                                tickFormatter={(value) => {
                                    const date = new Date(value);
                                    if (!isNaN(date.getTime())) {
                                        if (granularity === 'hour') {
                                            return date.toLocaleTimeString('en-US', {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                hour12: false
                                            });
                                        }
                                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                    }
                                    return value;
                                }}
                            />
                            <YAxis
                                tickLine={false}
                                axisLine={false}
                                tickMargin={8}
                                width={55}
                                tick={{ fontSize: 11, fill: '#64748b' }}
                                tickFormatter={(value) => formatValue(value, currentMetric.format, true)}
                            />
                            <ChartTooltip
                                content={
                                    <ChartTooltipContent
                                        formatter={(value, name) => {
                                            const config = chartConfig[name];
                                            const label = config?.label || currentMetric.label;
                                            return (
                                                <div className="flex items-center justify-between gap-3 w-full">
                                                    <span className="text-slate-600">{label}</span>
                                                    <span className="font-semibold text-slate-900">
                                                        {formatValue(value, currentMetric.format)}
                                                    </span>
                                                </div>
                                            );
                                        }}
                                        labelFormatter={(label) => {
                                            const date = new Date(label);
                                            if (granularity === 'hour') {
                                                return date.toLocaleString('en-US', {
                                                    month: 'short',
                                                    day: 'numeric',
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                });
                                            }
                                            return date.toLocaleDateString('en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                                year: 'numeric'
                                            });
                                        }}
                                    />
                                }
                                cursor={{ stroke: '#64748b', strokeWidth: 1, strokeDasharray: '4 4' }}
                            />
                            {/* Render an Area for each series */}
                            {series.map(s => (
                                <Area
                                    key={s.key}
                                    type="monotone"
                                    dataKey={s.key}
                                    name={s.key}
                                    stroke={s.color}
                                    strokeWidth={2}
                                    fill={`url(#gradient-${s.key})`}
                                    dot={false}
                                    activeDot={{ r: 4, fill: s.color, stroke: '#fff', strokeWidth: 2 }}
                                />
                            ))}
                            {/* Legend for multiple series */}
                            {series.length > 1 && (
                                <Legend
                                    verticalAlign="top"
                                    align="right"
                                    iconType="circle"
                                    iconSize={8}
                                    wrapperStyle={{ paddingBottom: 10 }}
                                    formatter={(value) => {
                                        const config = chartConfig[value];
                                        return <span className="text-xs text-slate-600">{config?.label || value}</span>;
                                    }}
                                />
                            )}
                        </AreaChart>
                    </ChartContainer>
                )}
            </div>

            {/* Disclaimer for campaign-level breakdowns */}
            {metadata?.disclaimer && (
                <div className="mt-3 flex items-start gap-2 text-xs text-slate-400">
                    <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    <p>{metadata.disclaimer}</p>
                </div>
            )}
        </div>
    );
}
