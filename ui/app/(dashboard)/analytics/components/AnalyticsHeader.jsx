"use client";
import { Sparkles, ArrowRight, Calendar, SlidersHorizontal, X, Filter, ChevronDown } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { fetchQA } from "@/lib/api";

export default function AnalyticsHeader({
    workspaceId,
    selectedProvider,
    onProviderChange,
    timeFilters,
    onTimeFilterChange,
    selectedCampaign,
    onFilterClick,
    onClearCampaign,
    providers = [] // New prop
}) {
    const [showDateMenu, setShowDateMenu] = useState(false);
    const [showCustomDate, setShowCustomDate] = useState(false);
    const [tempStart, setTempStart] = useState('');
    const [tempEnd, setTempEnd] = useState('');
    const [qaInput, setQaInput] = useState('');
    const [isQaSubmitting, setIsQaSubmitting] = useState(false);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const router = useRouter();

    const handleDateSelect = (option) => {
        if (option === 'custom') {
            setShowCustomDate(true);
        } else if (option === 'today') {
            const today = new Date().toISOString().split('T')[0];
            onTimeFilterChange({
                type: 'custom',
                preset: null,
                customStart: today,
                customEnd: today,
                rangeDays: 1
            });
            setShowDateMenu(false);
        } else if (option === 'yesterday') {
            const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
            onTimeFilterChange({
                type: 'custom',
                preset: null,
                customStart: yesterday,
                customEnd: yesterday,
                rangeDays: 1
            });
            setShowDateMenu(false);
        } else if (option === '7d') {
            onTimeFilterChange({
                type: 'preset',
                preset: '7d',
                customStart: null,
                customEnd: null,
                rangeDays: 7
            });
            setShowDateMenu(false);
        } else if (option === '30d') {
            onTimeFilterChange({
                type: 'preset',
                preset: '30d',
                customStart: null,
                customEnd: null,
                rangeDays: 30
            });
            setShowDateMenu(false);
        }
    };

    const applyCustomDate = () => {
        if (tempStart && tempEnd) {
            // Calculate days between dates
            const start = new Date(tempStart);
            const end = new Date(tempEnd);
            const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;

            onTimeFilterChange({
                type: 'custom',
                preset: null,
                customStart: tempStart,
                customEnd: tempEnd,
                rangeDays: days
            });
            setShowDateMenu(false);
            setShowCustomDate(false);
        }
    };

    const getDateLabel = () => {
        if (timeFilters.type === 'preset') {
            if (timeFilters.preset === '7d') return 'Last 7 Days';
            if (timeFilters.preset === '30d') return 'Last 30 Days';
        }
        if (timeFilters.type === 'custom') {
            if (timeFilters.customStart === timeFilters.customEnd) {
                // Single day
                const date = new Date(timeFilters.customStart);
                const today = new Date().toISOString().split('T')[0];
                const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];

                if (timeFilters.customStart === today) return 'Today';
                if (timeFilters.customStart === yesterday) return 'Yesterday';
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }
            return 'Custom Range';
        }
        return 'Date Range';
    };

    const handleQaSubmit = (e) => {
        e.preventDefault();
        if (!workspaceId || !qaInput.trim() || isQaSubmitting) return;

        const question = qaInput.trim();
        setIsQaSubmitting(true);

        // Fire and forget - log QA intent before transitioning to Copilot
        fetchQA({
            workspaceId,
            question,
            context: {
                source: 'analytics_header',
                provider: selectedProvider,
                campaignId: selectedCampaign?.id,
                campaignName: selectedCampaign?.name,
                timeframe: timeFilters.type === 'custom'
                    ? `${timeFilters.customStart || ''}:${timeFilters.customEnd || ''}`
                    : timeFilters.preset || `${timeFilters.rangeDays}d`
            }
        }).catch((err) => {
            console.error('QA request failed:', err);
        });

        setIsTransitioning(true);
        setTimeout(() => {
            const params = new URLSearchParams({ q: question, ws: workspaceId });
            router.push(`/copilot?${params.toString()}`);
        }, 300);
    };

    // Merge 'all' with fetched providers
    const displayProviders = ['all', ...providers];

    return (
        <header className="flex flex-col gap-6 animate-slide-up relative z-20">
            {/* Top Row: Title & Search */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Analytics</h1>
                    <p className="text-slate-500 text-sm mt-1">Deep insights into performance across all channels.</p>
                </div>

                {/* AI Search Bar */}
                <form onSubmit={handleQaSubmit} className="w-full md:w-auto flex-1 max-w-xl relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                    <div className={`relative flex items-center bg-white/80 backdrop-blur-xl border border-white/60 shadow-sm rounded-2xl px-4 py-3 transition-all focus-within:shadow-md focus-within:border-cyan-200 focus-within:bg-white ${isTransitioning ? 'chat-exit' : ''}`}>
                        <Sparkles className="w-5 h-5 text-cyan-500 mr-3 animate-pulse-slow" />
                        <input
                            type="text"
                            value={qaInput}
                            onChange={(e) => setQaInput(e.target.value)}
                            disabled={isQaSubmitting}
                            placeholder="Ask: Show ROAS last 14 days..."
                            className="flex-1 bg-transparent border-none outline-none text-slate-700 placeholder:text-slate-400 text-sm font-medium disabled:opacity-70"
                        />
                        <button
                            type="submit"
                            disabled={isQaSubmitting || !workspaceId}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-cyan-50 text-slate-400 hover:text-cyan-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <ArrowRight className={`w-4 h-4 ${isQaSubmitting ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </form>
            </div>

            {/* Bottom Row: Controls */}
            <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4">

                {/* Active Filters */}
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-2">Active Filters:</span>

                    {/* Campaign Chip */}
                    {selectedCampaign ? (
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-white border border-cyan-200 rounded-full shadow-sm group animate-fade-in">
                            <span className="text-xs font-medium text-slate-600">Campaign: <span className="text-cyan-700">{selectedCampaign.name}</span></span>
                            <button onClick={onClearCampaign} className="p-0.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-red-500 transition-colors">
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={onFilterClick}
                            className="flex items-center gap-2 px-3 py-1.5 bg-white border border-dashed border-slate-300 rounded-full hover:border-cyan-400 hover:text-cyan-600 text-slate-500 transition-all group"
                        >
                            <Filter className="w-3 h-3" />
                            <span className="text-xs font-medium">Filter Campaign</span>
                        </button>
                    )}

                    {/* Status Chip (Static for now) */}
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-full shadow-sm">
                        <span className="text-xs font-medium text-slate-600">Status: <span className="text-slate-900">Active</span></span>
                        <button className="p-0.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                            <X className="w-3 h-3" />
                        </button>
                    </div>
                </div>

                {/* Right Controls: Provider & Date */}
                <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">

                    {/* Provider Toggle */}
                    <div className="flex p-1 bg-slate-100/80 backdrop-blur-md rounded-xl border border-white/50 shadow-inner-light overflow-x-auto no-scrollbar max-w-[100vw]">
                        {displayProviders.map((p) => (
                            <button
                                key={p}
                                onClick={() => onProviderChange(p)}
                                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-300 ${selectedProvider === p
                                    ? 'bg-white text-slate-800 shadow-sm scale-105'
                                    : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
                                    }`}
                            >
                                {p.charAt(0).toUpperCase() + p.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Date Picker */}
                    <div className="relative z-50 w-full sm:w-auto">
                        <button
                            onClick={() => setShowDateMenu(!showDateMenu)}
                            className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-cyan-300 hover:shadow-md transition-all text-xs font-semibold text-slate-700 w-full sm:w-auto"
                        >
                            <Calendar className="w-4 h-4 text-slate-400" />
                            {getDateLabel()}
                            <ChevronDown className="w-3 h-3 text-slate-400 ml-1" />
                        </button>

                        {showDateMenu && (
                            <div className="absolute left-0 right-0 sm:left-auto sm:right-0 mt-2 w-full sm:w-64 bg-white rounded-2xl shadow-xl border border-slate-100 p-2 z-[100] animate-scale-up origin-top-right">
                                {!showCustomDate ? (
                                    <>
                                        <button onClick={() => handleDateSelect('today')} className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-slate-50 text-sm text-slate-700 font-medium transition-colors">Today</button>
                                        <button onClick={() => handleDateSelect('yesterday')} className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-slate-50 text-sm text-slate-700 font-medium transition-colors">Yesterday</button>
                                        <div className="h-px bg-slate-100 my-1"></div>
                                        <button onClick={() => handleDateSelect('7d')} className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-slate-50 text-sm text-slate-700 font-medium transition-colors">Last 7 Days</button>
                                        <button onClick={() => handleDateSelect('30d')} className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-slate-50 text-sm text-slate-700 font-medium transition-colors">Last 30 Days</button>
                                        <div className="h-px bg-slate-100 my-1"></div>
                                        <button onClick={() => setShowCustomDate(true)} className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-slate-50 text-sm text-cyan-600 font-semibold transition-colors">Custom Range...</button>
                                    </>
                                ) : (
                                    <div className="p-2">
                                        <div className="flex items-center justify-between mb-3">
                                            <h3 className="text-sm font-semibold text-slate-900">Custom Range</h3>
                                            <button onClick={() => setShowCustomDate(false)} className="text-slate-400 hover:text-slate-600">
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                        <div className="space-y-3">
                                            <div>
                                                <label className="block text-xs font-medium text-slate-600 mb-1">Start Date</label>
                                                <input
                                                    type="date"
                                                    value={tempStart}
                                                    onChange={(e) => setTempStart(e.target.value)}
                                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
                                                <input
                                                    type="date"
                                                    value={tempEnd}
                                                    onChange={(e) => setTempEnd(e.target.value)}
                                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                                                />
                                            </div>
                                            <button
                                                onClick={applyCustomDate}
                                                className="w-full px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-lg text-sm font-semibold hover:from-cyan-600 hover:to-blue-600 transition-all shadow-sm"
                                            >
                                                Apply
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Filter Button, for future use */}
                    {/* <button className="p-2 bg-white border border-slate-200 rounded-xl shadow-sm hover:bg-slate-50 text-slate-400 transition-colors">
                        <SlidersHorizontal className="w-4 h-4" />
                    </button> */}
                </div>
            </div>
        </header>
    );
}
