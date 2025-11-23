'use client';

import { useEffect, useState } from 'react';
import KpiCard from "./KPICard";
import { fetchWorkspaceKpis } from "@/lib/api";

export default function KpiStrip({ workspaceId, timeframe }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!workspaceId) return;

        const loadData = async () => {
            setLoading(true);
            try {
                // Map timeframe to API params
                let lastNDays = 7;
                let dayOffset = 0;

                switch (timeframe) {
                    case 'today':
                        lastNDays = 1;
                        dayOffset = 0;
                        break;
                    case 'yesterday':
                        lastNDays = 1;
                        dayOffset = 1;
                        break;
                    case 'last_7_days':
                        lastNDays = 7;
                        dayOffset = 0;
                        break;
                    case 'last_30_days':
                        lastNDays = 30;
                        dayOffset = 0;
                        break;
                    default:
                        lastNDays = 7;
                }

                const metrics = ["revenue", "roas", "spend", "conversions"];
                const res = await fetchWorkspaceKpis({
                    workspaceId,
                    metrics,
                    lastNDays,
                    dayOffset,
                    sparkline: true
                });

                // Transform array to object for easier access
                const kpiMap = {};
                res.forEach(item => {
                    kpiMap[item.key] = item;
                });
                setData(kpiMap);
            } catch (err) {
                console.error("Failed to fetch KPIs:", err);
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

            <KpiCard
                title="Total Revenue"
                value={fmt(data.revenue?.value)}
                change={data.revenue?.delta_pct ? `${data.revenue.delta_pct > 0 ? '+' : ''}${fmtPct(data.revenue.delta_pct)}` : '0%'}
                trend={data.revenue?.delta_pct >= 0 ? "up" : "down"}
                color="cyan"
                sparklineData={data.revenue?.sparkline?.map(p => p.value) || []}
            />

            <KpiCard
                title="ROAS"
                value={`${fmtNum(data.roas?.value)}x`}
                change={data.roas?.delta_pct ? `${data.roas.delta_pct > 0 ? '+' : ''}${fmtPct(data.roas.delta_pct)}` : '0%'}
                trend={data.roas?.delta_pct >= 0 ? "up" : "down"}
                color="purple"
                sparklineData={data.roas?.sparkline?.map(p => p.value) || []}
            />

            <KpiCard
                title="Ad Spend"
                value={fmt(data.spend?.value)}
                change={data.spend?.delta_pct ? `${data.spend.delta_pct > 0 ? '+' : ''}${fmtPct(data.spend.delta_pct)}` : '0%'}
                trend={data.spend?.delta_pct <= 0 ? "up" : "down"} // Lower spend increase is usually better? Or maybe not. Let's stick to standard up=green for now or neutral.
                color="blue"
                sparklineData={data.spend?.sparkline?.map(p => p.value) || []}
            />

            <KpiCard
                title="Conversions"
                value={fmtNum(data.conversions?.value)}
                change={data.conversions?.delta_pct ? `${data.conversions.delta_pct > 0 ? '+' : ''}${fmtPct(data.conversions.delta_pct)}` : '0%'}
                trend={data.conversions?.delta_pct >= 0 ? "up" : "down"}
                color="orange"
                sparklineData={data.conversions?.sparkline?.map(p => p.value) || []}
            />

        </section>
    );
}
