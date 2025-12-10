'use client';

/**
 * TopCreativeUnified Component
 *
 * WHAT: Shows top performing campaigns using unified dashboard data
 * WHY: Uses pre-fetched top_campaigns instead of making its own API call
 *
 * NOTE: top_campaigns is now wrapped in {items: [], disclaimer: string}
 */

import { Facebook, Youtube, Globe, Info } from "lucide-react";

const platformIcons = {
    meta: <Facebook className="w-4 h-4 text-blue-600" />,
    google: <Youtube className="w-4 h-4 text-red-500" />,
    unknown: <Globe className="w-4 h-4 text-slate-400" />
};

export default function TopCreativeUnified({ data, loading }) {
    if (loading || !data) {
        return (
            <div className="glass-panel rounded-2xl p-4 animate-pulse">
                <div className="h-6 bg-slate-200 rounded w-1/3 mb-4"></div>
                <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-14 bg-slate-100 rounded"></div>
                    ))}
                </div>
            </div>
        );
    }

    // Handle both old format (array) and new format ({items, disclaimer})
    const topCampaignsData = data.top_campaigns || {};
    const campaigns = Array.isArray(topCampaignsData)
        ? topCampaignsData
        : topCampaignsData.items || [];
    const disclaimer = topCampaignsData.disclaimer;

    if (campaigns.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-lg font-medium mb-4 text-slate-800">Top Campaigns</h3>
                <p className="text-slate-500">No campaign data available yet</p>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-medium mb-4 text-slate-800">Top Campaigns</h3>
            <div className="space-y-2">
                {campaigns.map((campaign, i) => (
                    <div key={campaign.id || i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                            {platformIcons[campaign.platform] || platformIcons.unknown}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{campaign.name}</p>
                            <p className="text-sm text-slate-500">
                                ${campaign.spend?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'} spend
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="font-semibold text-cyan-600">
                                {campaign.roas?.toFixed(2) || '0.00'}x
                            </p>
                            <p className="text-xs text-slate-500">ROAS</p>
                        </div>
                    </div>
                ))}
            </div>
            {disclaimer && (
                <div className="mt-4 flex items-start gap-2 text-xs text-slate-400">
                    <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    <p>{disclaimer}</p>
                </div>
            )}
        </div>
    );
}
