'use client';

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchEntityPerformance } from "@/lib/api";

export default function UnitEconomicsTable({ workspaceId, timeframe }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                let timeRange = { last_n_days: 7 };
                // Simple mapping for now, similar to other components
                if (timeframe === 'today') {
                    const today = new Date().toISOString().split('T')[0];
                    timeRange = { start: today, end: today };
                } else if (timeframe === 'yesterday') {
                    const y = new Date();
                    y.setDate(y.getDate() - 1);
                    const yStr = y.toISOString().split('T')[0];
                    timeRange = { start: yStr, end: yStr };
                } else if (timeframe === 'last_30_days') {
                    timeRange = { last_n_days: 30 };
                }

                // Fetch campaigns as proxy for products
                const res = await fetchEntityPerformance({
                    workspaceId,
                    entityType: 'campaign',
                    timeRange,
                    metrics: ['spend', 'revenue', 'conversions'],
                    limit: 5,
                    sortBy: 'revenue',
                    sortDir: 'desc'
                });

                if (res && res.items) {
                    setItems(res.items
                        .filter(item => item && item.metrics) // Filter out items without metrics
                        .map(item => {
                            const spend = item.metrics?.spend || 0;
                            const revenue = item.metrics?.revenue || 0;
                            const conversions = item.metrics?.conversions || 0;

                            // Calculate proxy metrics
                            // Price -> CPA (Cost per Acquisition) = Spend / Conversions
                            const cpa = conversions > 0 ? spend / conversions : 0;

                            // Margin % = (Revenue - Spend) / Revenue
                            const margin = revenue > 0 ? ((revenue - spend) / revenue) : 0;

                            return {
                                id: item.entity_id,
                                name: item.entity_name || 'Unknown',
                                price: cpa,
                                margin: margin
                            };
                        })
                    );
                }
            } catch (err) {
                console.error("Failed to fetch Unit Economics:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [workspaceId, timeframe]);

    const fmtCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(val || 0);
    const fmtPct = (val) => new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 }).format(val || 0);

    if (loading) {
        return (
            <div className="glass-panel rounded-3xl overflow-hidden h-[200px] animate-pulse">
                <div className="p-4 border-b border-white/50 h-12 bg-slate-100/50"></div>
                <div className="p-4 space-y-4">
                    <div className="h-4 bg-slate-100/50 rounded w-3/4"></div>
                    <div className="h-4 bg-slate-100/50 rounded w-1/2"></div>
                    <div className="h-4 bg-slate-100/50 rounded w-2/3"></div>
                </div>
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="glass-panel rounded-3xl overflow-hidden h-[200px] flex flex-col">
                <div className="p-4 flex justify-between items-center border-b border-white/50">
                    <h4 className="text-sm font-medium text-slate-700">Unit Economics</h4>
                </div>
                <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
                    No data available
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel rounded-3xl overflow-hidden">
            <div className="p-4 flex justify-between items-center border-b border-white/50">
                <h4 className="text-sm font-medium text-slate-700">Unit Economics</h4>
                <button className="flex items-center gap-1 text-[10px] bg-white/60 hover:bg-white px-2 py-1 rounded-full border border-slate-200 transition-colors">
                    <RefreshCw className="w-3 h-3" /> Sync Shopify
                </button>
            </div>
            <table className="w-full text-left text-sm">
                <thead className="bg-slate-50/50 text-xs text-slate-400 uppercase tracking-wider font-medium">
                    <tr>
                        <th className="px-4 py-3 font-medium">Campaign (Product)</th>
                        <th className="px-4 py-3 font-medium text-right">CPA</th>
                        <th className="px-4 py-3 font-medium text-right">Margin</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                    {items.map((item) => (
                        <tr key={item.id} className="hover:bg-cyan-50/30 transition-colors">
                            <td className="px-4 py-3 font-medium text-slate-700 truncate max-w-[150px]" title={item.name}>{item.name}</td>
                            <td className="px-4 py-3 text-right text-slate-500">{fmtCurrency(item.price)}</td>
                            <td className={`px-4 py-3 text-right font-medium ${item.margin >= 0.5 ? 'text-emerald-600' : item.margin >= 0.2 ? 'text-amber-500' : 'text-red-500'}`}>
                                {fmtPct(item.margin)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
