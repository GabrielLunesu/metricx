'use client';

/**
 * TopCreativeUnified Component
 *
 * WHAT: Shows top performing ads using unified dashboard data
 * WHY: Uses pre-fetched top_creatives instead of making its own API call
 */

import { Facebook, Youtube, Globe } from "lucide-react";

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
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-16 bg-slate-100 rounded"></div>
                    ))}
                </div>
            </div>
        );
    }

    const ads = data.top_creatives || [];

    if (ads.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-lg font-medium mb-4 text-slate-800">Top Ads</h3>
                <p className="text-slate-500">No ad data available yet</p>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-medium mb-4 text-slate-800">Top Performing Ads</h3>
            <div className="space-y-3">
                {ads.map((ad, i) => (
                    <div key={ad.id || i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                            {platformIcons[ad.platform] || platformIcons.unknown}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{ad.name}</p>
                            <p className="text-sm text-slate-500">
                                ${ad.spend?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'} spend
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="font-semibold text-cyan-600">
                                {ad.roas?.toFixed(2) || '0.00'}x
                            </p>
                            <p className="text-xs text-slate-500">ROAS</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
