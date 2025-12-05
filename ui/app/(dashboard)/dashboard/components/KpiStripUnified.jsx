'use client';

/**
 * KpiStripUnified Component
 *
 * WHAT: Displays key performance indicators using unified dashboard data
 * WHY: Uses pre-fetched data instead of making its own API call
 *
 * PROPS:
 *   - data: Unified dashboard response
 *   - loading: Boolean for loading state
 *
 * REFERENCES:
 *   - docs/PERFORMANCE_INVESTIGATION.md
 */

import KpiCard from "./KPICard";

export default function KpiStripUnified({ data, loading }) {
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

    // Convert kpis array to map for easier access
    const kpiMap = {};
    data.kpis?.forEach(item => {
        kpiMap[item.key] = item;
    });

    return (
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 snap-x snap-mandatory overflow-x-auto md:overflow-visible pb-4 md:pb-0 no-scrollbar">

            {/* Revenue */}
            <KpiCard
                title="Total Revenue"
                value={fmt(kpiMap.revenue?.value)}
                change={kpiMap.revenue?.delta_pct ? `${kpiMap.revenue.delta_pct > 0 ? '+' : ''}${fmtPct(kpiMap.revenue.delta_pct)}` : '0%'}
                trend={kpiMap.revenue?.delta_pct >= 0 ? "up" : "down"}
                color="cyan"
                sparklineData={kpiMap.revenue?.sparkline?.map(p => p.value) || []}
                source={data.data_source}
                platforms={data.connected_platforms}
            />

            {/* ROAS */}
            <KpiCard
                title="ROAS"
                value={`${fmtNum(kpiMap.roas?.value)}x`}
                change={kpiMap.roas?.delta_pct ? `${kpiMap.roas.delta_pct > 0 ? '+' : ''}${fmtPct(kpiMap.roas.delta_pct)}` : '0%'}
                trend={kpiMap.roas?.delta_pct >= 0 ? "up" : "down"}
                color="purple"
                sparklineData={kpiMap.roas?.sparkline?.map(p => p.value) || []}
                source="computed"
            />

            {/* Ad Spend */}
            <KpiCard
                title="Ad Spend"
                value={fmt(kpiMap.spend?.value)}
                change={kpiMap.spend?.delta_pct ? `${kpiMap.spend.delta_pct > 0 ? '+' : ''}${fmtPct(kpiMap.spend.delta_pct)}` : '0%'}
                trend={kpiMap.spend?.delta_pct <= 0 ? "up" : "down"}
                color="blue"
                sparklineData={kpiMap.spend?.sparkline?.map(p => p.value) || []}
                source="platform"
                platforms={data.connected_platforms}
            />

            {/* Conversions */}
            <KpiCard
                title="Conversions"
                value={fmtNum(kpiMap.conversions?.value)}
                change={kpiMap.conversions?.delta_pct ? `${kpiMap.conversions.delta_pct > 0 ? '+' : ''}${fmtPct(kpiMap.conversions.delta_pct)}` : '0%'}
                trend={kpiMap.conversions?.delta_pct >= 0 ? "up" : "down"}
                color="orange"
                sparklineData={kpiMap.conversions?.sparkline?.map(p => p.value) || []}
                source={data.data_source}
                platforms={data.connected_platforms}
            />

        </section>
    );
}
