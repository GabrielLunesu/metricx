'use client';

import { useEffect, useState } from "react";
import { Facebook, Youtube, Instagram, Globe } from "lucide-react";
import { fetchEntityPerformance } from "@/lib/api";

export default function TopCreative({ workspaceId, timeframe }) {
    const [ads, setAds] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                let timeRange = { last_n_days: 7 };
                switch (timeframe) {
                    case 'today': timeRange = { last_n_days: 1 }; break; // API might need specific handling for today/yesterday if not supported by last_n_days, but assuming basic support
                    case 'yesterday': timeRange = { last_n_days: 1, offset_days: 1 }; break; // Need to check if API supports offset in time_range, assuming simplified for now or mapping to dates
                    case 'last_7_days': timeRange = { last_n_days: 7 }; break;
                    case 'last_30_days': timeRange = { last_n_days: 30 }; break;
                }

                // If specific dates are needed for today/yesterday, we might need to adjust. 
                // For now, using last_n_days as a proxy or assuming backend handles it.
                // Actually, let's use the same logic as KpiStrip if possible, but fetchEntityPerformance takes a time_range object.
                // Let's construct it properly.

                if (timeframe === 'today') {
                    const today = new Date().toISOString().split('T')[0];
                    timeRange = { start: today, end: today };
                } else if (timeframe === 'yesterday') {
                    const y = new Date();
                    y.setDate(y.getDate() - 1);
                    const yStr = y.toISOString().split('T')[0];
                    timeRange = { start: yStr, end: yStr };
                }

                const res = await fetchEntityPerformance({
                    workspaceId,
                    entityType: 'ad',
                    timeRange,
                    metrics: ['spend', 'revenue', 'roas', 'impressions'],
                    limit: 3,
                    sortBy: 'revenue',
                    sortDir: 'desc'
                });

                if (res && res.items) {
                    setAds(res.items.map(item => ({
                        id: item.id, // API returns 'id', not 'entity_id' in EntityPerformanceRow
                        name: item.name, // API returns 'name', not 'entity_name'
                        platform: item.platform || 'unknown',
                        roas: item.roas, // API returns top-level fields, not nested in 'metrics'
                        spend: item.spend,
                        revenue: item.revenue,
                        image: null // API doesn't provide thumbnail_url yet
                    })));
                }
            } catch (err) {
                console.error("Failed to fetch Top Creative:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [workspaceId, timeframe]);

    const getIcon = (platform) => {
        switch (platform?.toLowerCase()) {
            case 'facebook': case 'meta': return <Facebook className="w-3 h-3 text-blue-600 fill-current" />;
            case 'youtube': case 'google': return <Youtube className="w-3 h-3 text-red-600 fill-current" />;
            case 'instagram': return <Instagram className="w-3 h-3 text-pink-600" />;
            default: return <Globe className="w-3 h-3 text-slate-400" />;
        }
    };

    const fmt = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val || 0);

    if (loading) {
        return (
            <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight">Top Creative</h3>
                </div>
                {[1, 2, 3].map(i => (
                    <div key={i} className="glass-panel p-3 rounded-2xl h-20 animate-pulse"></div>
                ))}
            </div>
        );
    }

    if (ads.length === 0) {
        return (
            <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-medium text-slate-800 tracking-tight">Top Creative</h3>
                </div>
                <div className="glass-panel p-6 rounded-2xl text-center text-slate-400 text-sm">
                    No creative data available
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-slate-800 tracking-tight">Top Creative</h3>
                <button className="text-xs text-cyan-600 hover:text-cyan-700 font-medium">View All</button>
            </div>

            {ads.map((ad, index) => (
                <div key={ad.id} className="glass-panel p-3 rounded-2xl flex items-center gap-4 hover:bg-white/90 transition-all duration-300 hover:scale-[1.01] group border border-amber-100/50 shadow-[0_0_20px_rgba(251,191,36,0.1)]">
                    <div className="relative">
                        <div className="w-16 h-16 rounded-xl bg-slate-200 overflow-hidden shadow-inner flex items-center justify-center">
                            {ad.image ? (
                                <img src={ad.image} className="w-full h-full object-cover" alt={ad.name} />
                            ) : (
                                <span className="text-xs text-slate-400">No Img</span>
                            )}
                        </div>
                        <div className={`absolute -top-2 -left-2 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm transform group-hover:-rotate-6 transition-transform ${index === 0 ? 'bg-gradient-to-br from-amber-300 to-yellow-500' : 'bg-slate-200 text-slate-600'}`}>
                            #{index + 1}
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm text-slate-800 truncate" title={ad.name}>{ad.name}</span>
                            {getIcon(ad.platform)}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                            <span>ROAS: <span className="text-emerald-600 font-semibold">{ad.roas?.toFixed(1)}x</span></span>
                            <span>Spend: {fmt(ad.spend)}</span>
                        </div>
                    </div>
                    <div className="text-right pr-2">
                        <div className="text-sm font-bold text-slate-800">{fmt(ad.revenue)}</div>
                        <div className="text-[10px] text-slate-400">Revenue</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
