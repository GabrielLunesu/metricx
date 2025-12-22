"use client";
/**
 * AnalyticsFilterBar Component
 * ============================
 *
 * WHAT: Global filter bar for the entire analytics page
 * WHY: Users need one place to control all data filtering
 *
 * FEATURES:
 *   - Platform selector (All/Blended, Google, Meta)
 *   - Campaign multi-select (respects timeframe)
 *   - Clear data source indicator
 *   - Filters cascade to entire page
 *
 * RELATED:
 *   - analytics/page.jsx (parent)
 *   - DateRangePicker (sibling in header)
 */

import { useState, useMemo } from "react";
import { ChevronDown, X, LayoutGrid, Image } from "lucide-react";

const PLATFORM_OPTIONS = [
    { value: null, label: 'All Platforms', sublabel: 'Blended data' },
    { value: 'google', label: 'Google Ads', icon: '🔵' },
    { value: 'meta', label: 'Meta Ads', icon: '🟣' },
];

const PLATFORM_COLORS = {
    google: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', badge: 'bg-blue-500' },
    meta: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', badge: 'bg-indigo-500' },
};

const CURRENCY_SYMBOLS = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    CAD: 'C$',
    AUD: 'A$',
};

function formatCurrency(value, currency = 'USD') {
    if (value === null || value === undefined) return '—';
    const symbol = CURRENCY_SYMBOLS[currency] || currency;
    if (Math.abs(value) >= 1000) {
        return `${symbol}${(value / 1000).toFixed(1)}k`;
    }
    return `${symbol}${Math.round(value)}`;
}

export default function AnalyticsFilterBar({
    connectedPlatforms = [],
    campaigns = [],
    selectedPlatform,
    onPlatformChange,
    selectedCampaigns = [],
    onCampaignsChange,
    // Meta drill-down (campaign → ad set → ad/creative)
    adSets = [],
    ads = [],
    selectedAdSetId = null,
    onAdSetChange = () => { },
    selectedAdId = null,
    onAdChange = () => { },
    adLoading = false,
    loading = false,
    currency = 'EUR',
}) {
    const [campaignOpen, setCampaignOpen] = useState(false);
    const [adSetOpen, setAdSetOpen] = useState(false);
    const [adOpen, setAdOpen] = useState(false);

    // Filter platforms to only show connected ones
    const availablePlatforms = useMemo(() => {
        return PLATFORM_OPTIONS.filter(opt =>
            opt.value === null || connectedPlatforms.includes(opt.value)
        );
    }, [connectedPlatforms]);

    // Filter campaigns by selected platform and exclude zero-spend campaigns
    const filteredCampaigns = useMemo(() => {
        let filtered = campaigns.filter(c => (c.spend || 0) > 0);
        if (selectedPlatform) {
            filtered = filtered.filter(c =>
                (c.platform || c.provider)?.toLowerCase() === selectedPlatform
            );
        }
        return filtered;
    }, [campaigns, selectedPlatform]);

    const platformStyle = selectedPlatform ? PLATFORM_COLORS[selectedPlatform] : null;

    const handlePlatformSelect = (value) => {
        onPlatformChange(value);
        // Clear campaign selection when platform changes
        onCampaignsChange([]);
        onAdSetChange(null);
        onAdChange(null);
    };

    const handleCampaignToggle = (campaignId) => {
        if (selectedCampaigns.includes(campaignId)) {
            onCampaignsChange(selectedCampaigns.filter(id => id !== campaignId));
        } else {
            onCampaignsChange([...selectedCampaigns, campaignId]);
        }
    };

    const clearCampaigns = () => {
        onCampaignsChange([]);
        onAdSetChange(null);
        onAdChange(null);
    };

    const clearAllFilters = () => {
        onPlatformChange(null);
        onCampaignsChange([]);
        onAdSetChange(null);
        onAdChange(null);
    };

    const hasFilters = selectedPlatform || selectedCampaigns.length > 0 || selectedAdSetId || selectedAdId;

    return (
        <div className="flex flex-wrap items-center gap-3">
            {/* Sources */}
            <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">Sources</span>
                <div className="flex items-center gap-1 bg-slate-100/50 p-1 rounded-xl border border-white/60">
                    {availablePlatforms.map((opt) => {
                        const isActive = selectedPlatform === opt.value;
                        const dotColor =
                            opt.value === "meta" ? "bg-cyan-500" : opt.value === "google" ? "bg-violet-500" : "bg-slate-400";
                        return (
                            <button
                                key={opt.value || "all"}
                                type="button"
                                onClick={() => handlePlatformSelect(opt.value)}
                                disabled={loading}
                                className={`
                                    px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2
                                    ${isActive
                                        ? "bg-slate-900 text-white shadow-sm"
                                        : "text-slate-600 hover:text-slate-800 hover:bg-white/60"
                                    }
                                    ${loading ? "opacity-60 cursor-not-allowed" : ""}
                                `}
                            >
                                <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
                                {opt.value === null ? "Blended" : opt.value === "meta" ? "Meta" : "Google"}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Campaign Selector - only show when platform selected or campaigns exist */}
            {filteredCampaigns.length > 0 && (
                <div className="relative">
                    <button
                        onClick={() => setCampaignOpen(!campaignOpen)}
                        className={`
                            flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                            transition-all border
                            ${selectedCampaigns.length > 0
                                ? 'bg-cyan-50 text-cyan-700 border-cyan-200'
                                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                            }
                        `}
                    >
                        <span>
                            {selectedCampaigns.length > 0
                                ? `${selectedCampaigns.length} Campaign${selectedCampaigns.length > 1 ? 's' : ''}`
                                : 'All Campaigns'
                            }
                        </span>
                        <ChevronDown className={`w-4 h-4 transition-transform ${campaignOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {campaignOpen && (
                        <>
                            <div
                                className="fixed inset-0 z-[9999]"
                                onClick={() => setCampaignOpen(false)}
                            />
                            <div className="absolute top-full left-0 mt-1 w-72 max-h-64 overflow-y-auto bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-[9999]">
                                {selectedCampaigns.length > 0 && (
                                    <button
                                        onClick={clearCampaigns}
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-600 hover:bg-red-50 border-b border-slate-100"
                                    >
                                        <X className="w-3 h-3" />
                                        Clear selection
                                    </button>
                                )}
                                {filteredCampaigns.map(campaign => (
                                    <button
                                        key={campaign.id}
                                        onClick={() => handleCampaignToggle(campaign.id)}
                                        className={`
                                            w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                                            hover:bg-slate-50 transition-colors
                                            ${selectedCampaigns.includes(campaign.id) ? 'bg-cyan-50' : ''}
                                        `}
                                    >
                                        <div className={`
                                            w-4 h-4 rounded border flex items-center justify-center
                                            ${selectedCampaigns.includes(campaign.id)
                                                ? 'bg-cyan-500 border-cyan-500 text-white'
                                                : 'border-slate-300'
                                            }
                                        `}>
                                            {selectedCampaigns.includes(campaign.id) && (
                                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                </svg>
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-slate-900 truncate">{campaign.name}</p>
                                            <p className="text-[10px] text-slate-500">
                                                {campaign.platform || campaign.provider} · {formatCurrency(campaign.spend, currency)} spend
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Meta drill-down selectors (Ad Set / Ad) */}
            {adSets.length > 0 && (
                <div className="relative">
                    <button
                        onClick={() => setAdSetOpen(!adSetOpen)}
                        className={`
                            flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                            transition-all border
                            ${selectedAdSetId
                                ? 'bg-violet-50 text-violet-700 border-violet-200'
                                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                            }
                        `}
                        disabled={adLoading}
                    >
                        <LayoutGrid className="w-4 h-4" />
                        <span className="max-w-[160px] truncate">
                            {selectedAdSetId ? (adSets.find(a => a.id === selectedAdSetId)?.name || "Ad set") : "All Ad Sets"}
                        </span>
                        <ChevronDown className={`w-4 h-4 transition-transform ${adSetOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {adSetOpen && (
                        <>
                            <div className="fixed inset-0 z-[9998]" onClick={() => setAdSetOpen(false)} />
                            <div className="absolute top-full left-0 mt-1 w-72 max-h-64 overflow-y-auto bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-[9999]">
                                {selectedAdSetId && (
                                    <button
                                        onClick={() => {
                                            onAdSetChange(null);
                                            onAdChange(null);
                                            setAdSetOpen(false);
                                        }}
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-600 hover:bg-red-50 border-b border-slate-100"
                                    >
                                        <X className="w-3 h-3" />
                                        Clear selection
                                    </button>
                                )}
                                {adSets.map((adset) => (
                                    <button
                                        key={adset.id}
                                        onClick={() => {
                                            onAdSetChange(adset.id);
                                            onAdChange(null);
                                            setAdSetOpen(false);
                                        }}
                                        className={`
                                            w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                                            hover:bg-slate-50 transition-colors
                                            ${selectedAdSetId === adset.id ? 'bg-violet-50' : ''}
                                        `}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-slate-900 truncate">{adset.name}</p>
                                            <p className="text-[10px] text-slate-500">
                                                {formatCurrency(adset.spend, currency)} spend · {(adset.roas ?? 0).toFixed(2)}x
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {ads.length > 0 && (
                <div className="relative">
                    <button
                        onClick={() => setAdOpen(!adOpen)}
                        className={`
                            flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                            transition-all border
                            ${selectedAdId
                                ? 'bg-cyan-50 text-cyan-700 border-cyan-200'
                                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                            }
                        `}
                        disabled={adLoading}
                    >
                        <Image className="w-4 h-4" />
                        <span className="max-w-[180px] truncate">
                            {selectedAdId ? (ads.find(a => a.id === selectedAdId)?.name || "Ad") : "All Ads"}
                        </span>
                        <ChevronDown className={`w-4 h-4 transition-transform ${adOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {adOpen && (
                        <>
                            <div className="fixed inset-0 z-[9998]" onClick={() => setAdOpen(false)} />
                            <div className="absolute top-full left-0 mt-1 w-80 max-h-64 overflow-y-auto bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-[9999]">
                                {selectedAdId && (
                                    <button
                                        onClick={() => {
                                            onAdChange(null);
                                            setAdOpen(false);
                                        }}
                                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-600 hover:bg-red-50 border-b border-slate-100"
                                    >
                                        <X className="w-3 h-3" />
                                        Clear selection
                                    </button>
                                )}
                                {ads.map((ad) => (
                                    <button
                                        key={ad.id}
                                        onClick={() => {
                                            onAdChange(ad.id);
                                            setAdOpen(false);
                                        }}
                                        className={`
                                            w-full flex items-center gap-2 px-3 py-2 text-sm text-left
                                            hover:bg-slate-50 transition-colors
                                            ${selectedAdId === ad.id ? 'bg-cyan-50' : ''}
                                        `}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-slate-900 truncate">{ad.name}</p>
                                            <p className="text-[10px] text-slate-500">
                                                {formatCurrency(ad.spend, currency)} spend · {(ad.roas ?? 0).toFixed(2)}x
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Clear All Filters */}
            {hasFilters && (
                <button
                    onClick={clearAllFilters}
                    className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                >
                    <X className="w-3 h-3" />
                    Clear filters
                </button>
            )}

            {/* Current Data Source Indicator */}
            <div className="ml-auto flex items-center gap-2">
                {selectedPlatform && (
                    <div className={`px-2.5 py-1 rounded-full text-xs font-medium ${platformStyle?.bg} ${platformStyle?.text}`}>
                        {selectedPlatform === "google" ? "Google Ads" : "Meta Ads"}
                    </div>
                )}
                {selectedCampaigns.length > 0 && (
                    <div className="px-2.5 py-1 rounded-full text-xs font-medium bg-cyan-50 text-cyan-700">
                        {selectedCampaigns.length} campaign{selectedCampaigns.length > 1 ? 's' : ''} selected
                    </div>
                )}
                {selectedAdSetId && (
                    <div className="px-2.5 py-1 rounded-full text-xs font-medium bg-violet-50 text-violet-700">
                        Ad set selected
                    </div>
                )}
                {selectedAdId && (
                    <div className="px-2.5 py-1 rounded-full text-xs font-medium bg-cyan-50 text-cyan-700">
                        Ad selected
                    </div>
                )}
                {!hasFilters && (
                    <div className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                        Blended Data (All Platforms)
                    </div>
                )}
            </div>
        </div>
    );
}
