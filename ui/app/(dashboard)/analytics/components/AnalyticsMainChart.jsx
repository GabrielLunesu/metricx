"use client";
/**
 * AnalyticsMainChart Component
 * =============================
 *
 * WHAT: Large interactive chart with metric selection - uses unified dashboard data
 * WHY: Users need a big chart with the ability to toggle metrics on/off
 *
 * DATA SOURCE: Uses unified dashboard data (chart_data from the response)
 *
 * FEATURES:
 *   - Multiple metrics toggleable (Revenue, Spend)
 *   - Chart type toggle (Area/Bar/Line)
 *   - Entity selection dropdown for drill-down
 *   - Glass-panel styling
 *
 * REFERENCES:
 *   - Original AnalyticsGraphEngine.jsx styling
 *   - dashboard/components/MoneyPulseChartUnified.jsx
 */

import { useState, useEffect } from "react";
import { fetchEntityPerformance } from "@/lib/api";
import {
    Area,
    AreaChart,
    Bar,
    BarChart,
    Line,
    LineChart,
    CartesianGrid,
    XAxis,
    YAxis,
    ResponsiveContainer,
    Tooltip
} from "recharts";
import {
    ChevronDown,
    Check,
    Target,
    Layers,
    Image,
    Search
} from "lucide-react";

// Available metrics from unified dashboard
const METRICS = [
    { key: 'revenue', label: 'Revenue', color: '#22d3ee', format: 'currency' },
    { key: 'spend', label: 'Spend', color: '#818cf8', format: 'currency' },
];

export default function AnalyticsMainChart({
    workspaceId,
    selectedProvider,
    timeFilters,
    dashboardData,
    loading: parentLoading = false
}) {
    // Chart state
    const [activeMetrics, setActiveMetrics] = useState(['revenue', 'spend']);
    const [chartType, setChartType] = useState('area');

    // Entity selector state
    const [entitySelectorOpen, setEntitySelectorOpen] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const [entities, setEntities] = useState([]);
    const [entityLevel, setEntityLevel] = useState('campaign');
    const [entitySearch, setEntitySearch] = useState('');
    const [loadingEntities, setLoadingEntities] = useState(false);

    // Build time range helper
    const buildTimeRange = () => {
        if (timeFilters.type === 'custom' && timeFilters.customStart && timeFilters.customEnd) {
            return { start: timeFilters.customStart, end: timeFilters.customEnd };
        }
        return { last_n_days: timeFilters.rangeDays };
    };

    // Fetch entities when selector opens
    useEffect(() => {
        if (!entitySelectorOpen || !workspaceId) return;

        setLoadingEntities(true);
        fetchEntityPerformance({
            workspaceId,
            entityType: entityLevel,
            timeRange: buildTimeRange(),
            provider: selectedProvider === 'all' ? null : selectedProvider,
            limit: 50,
            sortBy: 'spend',
            sortDir: 'desc',
            status: 'all'
        })
            .then(res => setEntities(res?.items || []))
            .catch(err => console.error('Failed to fetch entities:', err))
            .finally(() => setLoadingEntities(false));
    }, [entitySelectorOpen, workspaceId, selectedProvider, entityLevel, timeFilters.rangeDays]);

    // Toggle metric
    const toggleMetric = (key) => {
        setActiveMetrics(prev => {
            if (prev.includes(key)) {
                if (prev.length === 1) return prev;
                return prev.filter(k => k !== key);
            }
            return [...prev, key];
        });
    };

    // Format value for tooltip
    const formatValue = (value, format) => {
        if (value === null || value === undefined) return '—';
        switch (format) {
            case 'currency':
                return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
            case 'multiplier':
                return `${value.toFixed(2)}x`;
            case 'percentage':
                return `${value.toFixed(2)}%`;
            case 'number':
                return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
            default:
                return value;
        }
    };

    // Custom tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload || !payload.length) return null;

        const date = new Date(label);
        const formattedDate = date.toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric'
        });

        return (
            <div className="glass-panel rounded-xl p-3 min-w-[180px] shadow-xl border border-white/50">
                <div className="text-xs font-semibold text-slate-800 mb-2">{formattedDate}</div>
                <div className="space-y-1.5">
                    {payload.map((entry) => {
                        const metric = METRICS.find(m => m.key === entry.dataKey);
                        if (!metric) return null;
                        return (
                            <div key={entry.dataKey} className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: metric.color }} />
                                    <span className="text-[10px] text-slate-600">{metric.label}</span>
                                </div>
                                <span className="text-xs font-semibold text-slate-800">
                                    {formatValue(entry.value, metric.format)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    const isSingleDay = timeFilters.rangeDays === 1 ||
        (timeFilters.type === 'custom' && timeFilters.customStart === timeFilters.customEnd);

    // Filter entities by search
    const filteredEntities = entities.filter(e =>
        e.name?.toLowerCase().includes(entitySearch.toLowerCase())
    );

    // Use chart_data from unified dashboard
    const chartData = dashboardData?.chart_data || [];

    return (
        <div className="glass-panel rounded-[24px] p-4 md:p-6 flex flex-col relative overflow-hidden min-h-[500px]">
            {/* Header */}
            <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
                <div>
                    <h2 className="text-lg font-semibold text-slate-800">
                        Performance Analytics
                        {isSingleDay && <span className="text-sm font-normal text-slate-500 ml-2">(24 Hours)</span>}
                    </h2>
                    {selectedEntity && (
                        <p className="text-sm text-cyan-600 mt-1">
                            {entityLevel.charAt(0).toUpperCase() + entityLevel.slice(1)}: {selectedEntity.name}
                        </p>
                    )}
                </div>

                {/* Chart Type Toggle */}
                <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
                    <button
                        onClick={() => setChartType('area')}
                        className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${chartType === 'area' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Area
                    </button>
                    <button
                        onClick={() => setChartType('bar')}
                        className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${chartType === 'bar' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Bar
                    </button>
                    <button
                        onClick={() => setChartType('line')}
                        className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${chartType === 'line' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Line
                    </button>
                </div>
            </div>

            {/* Metric Toggles + Entity Selector Row */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
                {/* Metric toggles */}
                <div className="flex flex-wrap gap-2">
                    {METRICS.map((metric) => {
                        const isActive = activeMetrics.includes(metric.key);
                        return (
                            <button
                                key={metric.key}
                                onClick={() => toggleMetric(metric.key)}
                                className={`
                                    flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                                    ${isActive
                                        ? 'bg-white shadow-sm border-2'
                                        : 'bg-slate-50 text-slate-500 hover:bg-slate-100 border-2 border-transparent'
                                    }
                                `}
                                style={{
                                    borderColor: isActive ? metric.color : 'transparent',
                                    color: isActive ? metric.color : undefined
                                }}
                            >
                                <div
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: isActive ? metric.color : '#94a3b8' }}
                                />
                                {metric.label}
                            </button>
                        );
                    })}
                </div>

                {/* Divider */}
                <div className="h-6 w-px bg-slate-200 hidden md:block" />

                {/* Entity Selector Dropdown */}
                <div className="relative">
                    <button
                        onClick={() => setEntitySelectorOpen(!entitySelectorOpen)}
                        className={`
                            flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                            ${selectedEntity
                                ? 'bg-cyan-50 border border-cyan-200 text-cyan-700'
                                : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
                            }
                        `}
                    >
                        {entityLevel === 'campaign' && <Target className="w-3.5 h-3.5" />}
                        {entityLevel === 'adset' && <Layers className="w-3.5 h-3.5" />}
                        {entityLevel === 'ad' && <Image className="w-3.5 h-3.5" />}
                        {selectedEntity ? selectedEntity.name : 'All Data'}
                        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${entitySelectorOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {entitySelectorOpen && (
                        <div className="absolute top-full left-0 mt-2 w-[320px] bg-white rounded-xl shadow-2xl border border-slate-100 z-50 overflow-hidden">
                            {/* Level tabs */}
                            <div className="flex border-b border-slate-100">
                                {['campaign', 'adset', 'ad'].map(level => (
                                    <button
                                        key={level}
                                        onClick={() => { setEntityLevel(level); setSelectedEntity(null); }}
                                        className={`flex-1 py-2 text-xs font-medium transition-colors ${entityLevel === level ? 'bg-slate-50 text-cyan-600 border-b-2 border-cyan-500' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        {level === 'campaign' ? 'Campaigns' : level === 'adset' ? 'Ad Sets' : 'Ads'}
                                    </button>
                                ))}
                            </div>

                            {/* Search */}
                            <div className="p-2 border-b border-slate-100">
                                <div className="relative">
                                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                                    <input
                                        type="text"
                                        value={entitySearch}
                                        onChange={(e) => setEntitySearch(e.target.value)}
                                        placeholder="Search..."
                                        className="w-full pl-8 pr-3 py-1.5 bg-slate-50 rounded-lg text-xs border-none outline-none focus:ring-2 focus:ring-cyan-500/20"
                                    />
                                </div>
                            </div>

                            {/* "All" option */}
                            <button
                                onClick={() => { setSelectedEntity(null); setEntitySelectorOpen(false); }}
                                className={`w-full text-left px-3 py-2 text-xs font-medium transition-colors ${!selectedEntity ? 'bg-cyan-50 text-cyan-700' : 'text-slate-600 hover:bg-slate-50'}`}
                            >
                                All {entityLevel === 'campaign' ? 'Campaigns' : entityLevel === 'adset' ? 'Ad Sets' : 'Ads'}
                            </button>

                            {/* Entity list */}
                            <div className="max-h-[200px] overflow-y-auto">
                                {loadingEntities ? (
                                    <div className="p-4 text-center text-xs text-slate-500">Loading...</div>
                                ) : filteredEntities.length === 0 ? (
                                    <div className="p-4 text-center text-xs text-slate-500">No {entityLevel}s found</div>
                                ) : (
                                    filteredEntities.map(entity => (
                                        <button
                                            key={entity.id}
                                            onClick={() => { setSelectedEntity(entity); setEntitySelectorOpen(false); }}
                                            className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between ${selectedEntity?.id === entity.id ? 'bg-cyan-50 text-cyan-700' : 'text-slate-600 hover:bg-slate-50'}`}
                                        >
                                            <span className="truncate flex-1">{entity.name}</span>
                                            <span className="text-slate-400 ml-2">${(entity.spend || 0).toLocaleString()}</span>
                                            {selectedEntity?.id === entity.id && <Check className="w-3.5 h-3.5 text-cyan-600 ml-2" />}
                                        </button>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Clear selection */}
                {selectedEntity && (
                    <button
                        onClick={() => setSelectedEntity(null)}
                        className="text-xs text-red-500 hover:text-red-600 font-medium"
                    >
                        Clear
                    </button>
                )}
            </div>

            {/* Chart */}
            <div className="flex-1 min-h-[350px]">
                {parentLoading ? (
                    <div className="h-full flex items-center justify-center">
                        <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : chartData.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-slate-400">
                        No data available for selected period
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        {chartType === 'area' ? (
                            <AreaChart data={chartData} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
                                <defs>
                                    {activeMetrics.map(key => {
                                        const metric = METRICS.find(m => m.key === key);
                                        return (
                                            <linearGradient key={key} id={`gradient-${key}`} x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor={metric.color} stopOpacity={0.3} />
                                                <stop offset="95%" stopColor={metric.color} stopOpacity={0} />
                                            </linearGradient>
                                        );
                                    })}
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={10}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    minTickGap={isSingleDay ? 20 : 40}
                                    tickFormatter={(value) => {
                                        const date = new Date(value);
                                        if (isSingleDay) {
                                            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                                        }
                                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                    }}
                                />
                                <YAxis
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={8}
                                    width={60}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    tickFormatter={(value) => {
                                        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                                        if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                                        return `$${value}`;
                                    }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                {activeMetrics.map(key => {
                                    const metric = METRICS.find(m => m.key === key);
                                    return (
                                        <Area
                                            key={key}
                                            type="monotone"
                                            dataKey={key}
                                            stroke={metric.color}
                                            fill={`url(#gradient-${key})`}
                                            strokeWidth={2}
                                            connectNulls
                                            dot={false}
                                            activeDot={{ r: 4, strokeWidth: 2 }}
                                        />
                                    );
                                })}
                            </AreaChart>
                        ) : chartType === 'bar' ? (
                            <BarChart data={chartData} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={10}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    minTickGap={isSingleDay ? 20 : 40}
                                    tickFormatter={(value) => {
                                        const date = new Date(value);
                                        if (isSingleDay) {
                                            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                                        }
                                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                    }}
                                />
                                <YAxis
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={8}
                                    width={60}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    tickFormatter={(value) => {
                                        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                                        if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                                        return `$${value}`;
                                    }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                {activeMetrics.map(key => {
                                    const metric = METRICS.find(m => m.key === key);
                                    return (
                                        <Bar
                                            key={key}
                                            dataKey={key}
                                            fill={metric.color}
                                            radius={[4, 4, 0, 0]}
                                            maxBarSize={40}
                                        />
                                    );
                                })}
                            </BarChart>
                        ) : (
                            <LineChart data={chartData} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={10}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    minTickGap={isSingleDay ? 20 : 40}
                                    tickFormatter={(value) => {
                                        const date = new Date(value);
                                        if (isSingleDay) {
                                            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                                        }
                                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                    }}
                                />
                                <YAxis
                                    tickLine={false}
                                    axisLine={false}
                                    tickMargin={8}
                                    width={60}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    tickFormatter={(value) => {
                                        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                                        if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                                        return `$${value}`;
                                    }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                {activeMetrics.map(key => {
                                    const metric = METRICS.find(m => m.key === key);
                                    return (
                                        <Line
                                            key={key}
                                            type="monotone"
                                            dataKey={key}
                                            stroke={metric.color}
                                            strokeWidth={2.5}
                                            dot={false}
                                            activeDot={{ r: 5, strokeWidth: 2 }}
                                            connectNulls
                                        />
                                    );
                                })}
                            </LineChart>
                        )}
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}
