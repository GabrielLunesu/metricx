'use client';

/**
 * KpiStrip Component
 *
 * WHAT: Displays key performance indicators on the dashboard
 * WHY: Give merchants a quick overview of their business performance
 *
 * DATA SOURCE (via /dashboard/kpis endpoint):
 * - If Shopify connected: Revenue from Shopify orders (source of truth)
 * - If no Shopify: Revenue from ad platform metrics (fallback)
 * - Spend: Always from ad platforms
 * - ROAS: Computed from revenue/spend
 * - Conversions: Attributed orders (Shopify) or platform conversions (fallback)
 */

import { useEffect, useState } from 'react';
import KpiCard from "./KPICard";
import { fetchDashboardKpis } from "@/lib/api";

export default function KpiStrip({ workspaceId, timeframe }) {
    const [data, setData] = useState(null);
    const [dataSource, setDataSource] = useState(null);
    const [connectedPlatforms, setConnectedPlatforms] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                // New endpoint handles timeframe mapping internally
                const res = await fetchDashboardKpis({
                    workspaceId,
                    timeframe: timeframe || 'last_7_days'
                });

                // Transform kpis array to object for easier access
                const kpiMap = {};
                res.kpis.forEach(item => {
                    kpiMap[item.key] = item;
                });
                setData(kpiMap);
                setDataSource(res.data_source); // 'shopify' or 'platform'
                setConnectedPlatforms(res.connected_platforms || []); // ['meta', 'google', etc.]
            } catch (err) {
                console.error("Failed to fetch dashboard KPIs:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [workspaceId, timeframe]);

    // Helper to format currency/numbers
    const fmt = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val || 0);
    const fmtNum = (val) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(val || 0);
    const fmtPct = (val) => new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 }).format(val || 0);

    if (loading || !data) {
        return (
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="h-32 glass-panel rounded-2xl animate-pulse"></div>
                ))}
            </section>
        );
    }

    return (
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 snap-x snap-mandatory overflow-x-auto md:overflow-visible pb-4 md:pb-0 no-scrollbar">

            {/* Revenue: From Shopify orders if connected, otherwise from ad platforms */}
            <KpiCard
                title="Total Revenue"
                value={fmt(data.revenue?.value)}
                change={data.revenue?.delta_pct ? `${data.revenue.delta_pct > 0 ? '+' : ''}${fmtPct(data.revenue.delta_pct)}` : '0%'}
                trend={data.revenue?.delta_pct >= 0 ? "up" : "down"}
                color="cyan"
                sparklineData={data.revenue?.sparkline?.map(p => p.value) || []}
                source={dataSource}
                platforms={connectedPlatforms}
            />

            {/* ROAS: Always computed from revenue/spend */}
            <KpiCard
                title="ROAS"
                value={`${fmtNum(data.roas?.value)}x`}
                change={data.roas?.delta_pct ? `${data.roas.delta_pct > 0 ? '+' : ''}${fmtPct(data.roas.delta_pct)}` : '0%'}
                trend={data.roas?.delta_pct >= 0 ? "up" : "down"}
                color="purple"
                sparklineData={data.roas?.sparkline?.map(p => p.value) || []}
                source="computed"
            />

            {/* Ad Spend: Always from ad platforms */}
            <KpiCard
                title="Ad Spend"
                value={fmt(data.spend?.value)}
                change={data.spend?.delta_pct ? `${data.spend.delta_pct > 0 ? '+' : ''}${fmtPct(data.spend.delta_pct)}` : '0%'}
                trend={data.spend?.delta_pct <= 0 ? "up" : "down"}
                color="blue"
                sparklineData={data.spend?.sparkline?.map(p => p.value) || []}
                source="platform"
                platforms={connectedPlatforms}
            />

            {/* Conversions: Attributed orders (Shopify) or platform conversions */}
            <KpiCard
                title="Conversions"
                value={fmtNum(data.conversions?.value)}
                change={data.conversions?.delta_pct ? `${data.conversions.delta_pct > 0 ? '+' : ''}${fmtPct(data.conversions.delta_pct)}` : '0%'}
                trend={data.conversions?.delta_pct >= 0 ? "up" : "down"}
                color="orange"
                sparklineData={data.conversions?.sparkline?.map(p => p.value) || []}
                source={dataSource}
                platforms={connectedPlatforms}
            />

        </section>
    );
}
