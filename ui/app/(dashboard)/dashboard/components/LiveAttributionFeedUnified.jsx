'use client';

/**
 * LiveAttributionFeedUnified Component
 *
 * WHAT: Shows recent attribution events using unified dashboard data
 * WHY: Uses pre-fetched attribution_feed instead of separate API call
 */

import { Facebook, Youtube, Globe } from "lucide-react";

const platformIcons = {
    meta: <Facebook className="w-4 h-4 text-blue-600" />,
    google: <Youtube className="w-4 h-4 text-red-500" />,
    unknown: <Globe className="w-4 h-4 text-slate-400" />
};

export default function LiveAttributionFeedUnified({ data, loading }) {
    if (loading || !data) {
        return (
            <div className="glass-panel rounded-2xl p-4 animate-pulse h-48">
                <div className="h-full bg-slate-100 rounded"></div>
            </div>
        );
    }

    const feed = data.attribution_feed || [];

    if (feed.length === 0) {
        return (
            <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-lg font-medium mb-4 text-slate-800">Live Attribution</h3>
                <p className="text-slate-500">No recent attributions</p>
            </div>
        );
    }

    const formatTime = (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-medium mb-4 text-slate-800">Live Attribution Feed</h3>
            <div className="space-y-3 max-h-64 overflow-y-auto">
                {feed.map((item, i) => (
                    <div key={item.order_id || i} className="flex items-center gap-3 p-2 bg-slate-50 rounded-lg">
                        <div className="flex-shrink-0">
                            {platformIcons[item.provider] || platformIcons.unknown}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-800 truncate">
                                {item.campaign_name || 'Direct/Unknown'}
                            </p>
                            <p className="text-xs text-slate-500">
                                {formatTime(item.attributed_at)}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm font-semibold text-green-600">
                                +${item.revenue?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
