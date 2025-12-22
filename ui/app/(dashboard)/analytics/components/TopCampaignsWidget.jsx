"use client";
/**
 * TopCampaignsWidget Component
 * ============================
 *
 * WHAT: Shows top 5 best performing campaigns ranked by ROAS
 * WHY: Users want quick visibility into which campaigns are working
 *
 * FEATURES:
 *   - Sorted by ROAS (highest first)
 *   - Shows platform badge (Google/Meta)
 *   - Quick metrics: ROAS, Spend, Revenue
 *   - Click to see more details (future)
 *
 * RELATED:
 *   - analytics/page.jsx (parent)
 *   - fetchEntityPerformance (data source)
 */

import { Trophy, TrendingUp, ChevronRight } from "lucide-react";

const CURRENCY_SYMBOLS = {
    USD: '$',
    EUR: '€',
    GBP: '£',
    CAD: 'C$',
    AUD: 'A$',
};

const PLATFORM_COLORS = {
    google: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    meta: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
    default: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' }
};

function formatCompact(value, currency = 'USD') {
    if (value === null || value === undefined) return '—';
    const symbol = CURRENCY_SYMBOLS[currency] || '$';

    if (value >= 1000000) {
        return `${symbol}${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `${symbol}${(value / 1000).toFixed(1)}k`;
    }
    return `${symbol}${Math.round(value)}`;
}

function getRankBadge(rank) {
    if (rank === 1) return { emoji: '🥇', color: 'text-amber-500' };
    if (rank === 2) return { emoji: '🥈', color: 'text-slate-400' };
    if (rank === 3) return { emoji: '🥉', color: 'text-amber-700' };
    return { emoji: `#${rank}`, color: 'text-slate-500' };
}

export default function TopCampaignsWidget({
    campaigns = [],
    loading,
    currency = 'USD',
    limit = 5
}) {
    // Sort by ROAS (highest first), filter out zero spend, and take top N
    const sortedCampaigns = [...campaigns]
        .filter(c => c.roas !== null && c.roas !== undefined && c.spend > 0 && c.revenue > 0)
        .sort((a, b) => (b.roas || 0) - (a.roas || 0))
        .slice(0, limit);

    if (loading) {
        return (
            <div className="dashboard-module animate-pulse">
                <div className="flex items-center gap-2 mb-4">
                    <div className="h-5 w-5 bg-slate-200/50 rounded"></div>
                    <div className="h-5 w-32 bg-slate-200/50 rounded"></div>
                </div>
                <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-14 bg-slate-100/50 rounded-lg"></div>
                    ))}
                </div>
            </div>
        );
    }

    if (sortedCampaigns.length === 0) {
        return (
            <div className="dashboard-module">
                <div className="flex items-center gap-2 mb-4">
                    <Trophy className="w-4 h-4 text-amber-500" />
                    <h3 className="text-sm font-semibold text-slate-900">Top Campaigns</h3>
                </div>
                <div className="py-8 text-center">
                    <p className="text-sm text-slate-500">No campaign data yet</p>
                    <p className="text-xs text-slate-400 mt-1">Connect your ad accounts to see rankings</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-module">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-amber-500" />
                    <h3 className="text-sm font-semibold text-slate-900">Top Campaigns by ROAS</h3>
                </div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wide">
                    {sortedCampaigns.length} of {campaigns.length}
                </span>
            </div>

            {/* Campaign List */}
            <div className="space-y-2">
                {sortedCampaigns.map((campaign, index) => {
                    const rank = index + 1;
                    const badge = getRankBadge(rank);
                    const platform = campaign.platform || campaign.provider || 'unknown';
                    const platformStyle = PLATFORM_COLORS[platform] || PLATFORM_COLORS.default;

                    return (
                        <div
                            key={campaign.id}
                            className="group flex items-center gap-3 p-3 rounded-xl bg-slate-50/50 hover:bg-slate-100/70 transition-all cursor-pointer"
                        >
                            {/* Rank */}
                            <div className={`text-lg font-bold ${badge.color} w-6 text-center`}>
                                {badge.emoji}
                            </div>

                            {/* Campaign Info */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <p className="text-sm font-medium text-slate-900 truncate">
                                        {campaign.name}
                                    </p>
                                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${platformStyle.bg} ${platformStyle.text} border ${platformStyle.border}`}>
                                        {platform === 'google' ? 'Google' : platform === 'meta' ? 'Meta' : platform}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3 mt-0.5">
                                    <span className="text-xs text-slate-500">
                                        Spend: {formatCompact(campaign.spend, currency)}
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        Rev: {formatCompact(campaign.revenue, currency)}
                                    </span>
                                </div>
                            </div>

                            {/* ROAS Badge */}
                            <div className="flex items-center gap-1.5">
                                <div className={`px-2.5 py-1 rounded-lg font-bold text-sm ${
                                    campaign.roas >= 3 ? 'bg-emerald-100 text-emerald-700' :
                                    campaign.roas >= 2 ? 'bg-cyan-100 text-cyan-700' :
                                    campaign.roas >= 1 ? 'bg-amber-100 text-amber-700' :
                                    'bg-red-100 text-red-600'
                                }`}>
                                    {campaign.roas?.toFixed(2)}x
                                </div>
                                <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Footer hint */}
            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                    <TrendingUp className="w-3 h-3" />
                    <span>Sorted by Return on Ad Spend</span>
                </div>
            </div>
        </div>
    );
}
