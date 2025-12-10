'use client';

/**
 * AI Insights Panel (v2 - Data-Driven)
 * ====================================
 *
 * WHAT: Generates actionable insights from dashboard data.
 *
 * WHY: Instead of making slow AI calls for generic questions, this panel
 *      computes specific insights from the data that's already loaded.
 *      This is faster, more reliable, and always has data to show.
 *
 * INSIGHT TYPES:
 *   1. 🔥 Actionable Spend Shifts - Budget reallocation suggestions
 *   2. 🚨 Wasted Spend Detection - Low-performing campaigns
 *   3. 📈 Creative Performance - Top performers to scale
 *   4. 🧭 Trend Alerts - Significant metric changes
 *   5. 🧠 Profit Intelligence - ROAS-based decisions
 *
 * PROPS:
 *   - data: Unified dashboard data (kpis, top_campaigns, spend_mix, chart_data)
 *   - loading: Boolean for loading state
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/dashboard/page.jsx (parent)
 *   - backend/app/routers/dashboard.py (data source)
 */

import { useState, useMemo } from "react";
// import { useRouter } from "next/navigation";  // TODO: Re-enable for Ask AI
import {
    Sparkles,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    DollarSign,
    Target,
    ChevronDown,
    ChevronUp,
    Flame,
    Zap,
    // MessageSquare  // TODO: Re-enable for Ask AI
} from "lucide-react";

// =============================================================================
// INSIGHT GENERATORS
// =============================================================================

/**
 * Generate all insights from dashboard data.
 * Returns prioritized array of insight objects.
 */
function generateInsights(data) {
    if (!data) return [];

    const insights = [];
    const kpiMap = {};
    data.kpis?.forEach(item => { kpiMap[item.key] = item; });

    // Format helpers
    const fmt = (val) => new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
    }).format(val || 0);

    const fmtPct = (val) => {
        const pct = Math.abs(val || 0) * 100;
        return `${pct.toFixed(1)}%`;
    };

    // =========================================================================
    // 1. TREND ALERTS - Significant metric changes
    // =========================================================================
    const roas = kpiMap.roas;
    const spend = kpiMap.spend;
    const revenue = kpiMap.revenue;
    const conversions = kpiMap.conversions;

    // ROAS dropping significantly
    if (roas?.delta_pct && roas.delta_pct < -0.10) {
        insights.push({
            type: 'warning',
            category: 'Trend Alert',
            icon: TrendingDown,
            priority: 1,
            title: `ROAS dropped ${fmtPct(roas.delta_pct)}`,
            description: `From ${(roas.prev || 0).toFixed(2)}x to ${(roas.value || 0).toFixed(2)}x. Review underperforming campaigns.`,
            action: 'Review campaigns'
        });
    }

    // ROAS improving significantly
    if (roas?.delta_pct && roas.delta_pct > 0.15) {
        insights.push({
            type: 'success',
            category: 'Growth Signal',
            icon: TrendingUp,
            priority: 3,
            title: `ROAS up ${fmtPct(roas.delta_pct)}`,
            description: `Now at ${(roas.value || 0).toFixed(2)}x. Consider scaling budget.`,
            action: 'Scale winners'
        });
    }

    // Spend spike without revenue increase
    if (spend?.delta_pct && spend.delta_pct > 0.20 && (!revenue?.delta_pct || revenue.delta_pct < spend.delta_pct * 0.5)) {
        insights.push({
            type: 'warning',
            category: 'Wasted Spend',
            icon: AlertTriangle,
            priority: 1,
            title: `Spend up ${fmtPct(spend.delta_pct)} but revenue lagging`,
            description: `Increased spend isn't translating to proportional revenue.`,
            action: 'Optimize spend'
        });
    }

    // =========================================================================
    // 2. SPEND SHIFTS - Budget reallocation based on campaign performance
    // =========================================================================
    const campaigns = data.top_campaigns || [];

    if (campaigns.length >= 2) {
        // Sort by ROAS to find best and worst
        const sortedByRoas = [...campaigns].sort((a, b) => (b.roas || 0) - (a.roas || 0));
        const best = sortedByRoas[0];
        const worst = sortedByRoas[sortedByRoas.length - 1];

        // Only suggest if there's a meaningful ROAS difference
        if (best && worst && best.roas > worst.roas * 1.5 && worst.spend > 10) {
            const suggestedShift = Math.min(worst.spend * 0.25, 100);
            const potentialGain = (best.roas - worst.roas) * suggestedShift;

            insights.push({
                type: 'opportunity',
                category: 'Spend Shift',
                icon: Flame,
                priority: 2,
                title: `Move ${fmt(suggestedShift)} to better performing campaign`,
                campaignFrom: worst.name,
                campaignTo: best.name,
                description: `"${best.name}" has ${best.roas.toFixed(1)}x ROAS vs ${worst.roas.toFixed(1)}x for "${worst.name}". Potential +${fmt(potentialGain)} revenue.`,
                action: 'Reallocate'
            });
        }

        // Find campaign with high spend but low ROAS (wasted spend)
        const wastedSpendCampaign = campaigns.find(c =>
            c.roas < 1.0 && c.spend > 50
        );

        if (wastedSpendCampaign) {
            insights.push({
                type: 'warning',
                category: 'Wasted Spend',
                icon: AlertTriangle,
                priority: 1,
                title: `Campaign losing money`,
                campaignName: wastedSpendCampaign.name,
                description: `${fmt(wastedSpendCampaign.spend)} spent with only ${wastedSpendCampaign.roas.toFixed(2)}x ROAS. Consider pausing.`,
                action: 'Pause or fix'
            });
        }
    }

    // =========================================================================
    // 3. TOP PERFORMER - Scale opportunity
    // =========================================================================
    const topCampaign = campaigns.find(c => c.roas > 2.0 && c.spend > 20);

    if (topCampaign) {
        const scaleAmount = topCampaign.spend * 0.25;
        const expectedRevenue = scaleAmount * topCampaign.roas;

        insights.push({
            type: 'success',
            category: 'Scale Opportunity',
            icon: Zap,
            priority: 2,
            title: `High performer ready to scale`,
            campaignName: topCampaign.name,
            description: `${topCampaign.roas.toFixed(1)}x ROAS. Add ${fmt(scaleAmount)}/day for ~${fmt(expectedRevenue)} more revenue.`,
            action: 'Increase budget'
        });
    }

    // =========================================================================
    // 4. PLATFORM MIX - Concentration warnings
    // =========================================================================
    const spendMix = data.spend_mix || [];

    if (spendMix.length > 0) {
        const dominant = spendMix.find(p => p.pct > 85);
        if (dominant) {
            insights.push({
                type: 'info',
                category: 'Diversification',
                icon: Target,
                priority: 4,
                title: `${dominant.pct.toFixed(0)}% spend on ${dominant.provider}`,
                description: `High concentration. Consider testing other platforms to reduce risk.`,
                action: 'Diversify'
            });
        }
    }

    // =========================================================================
    // 5. PROFIT INTELLIGENCE - Break-even analysis
    // =========================================================================
    if (roas?.value && roas.value < 1.0 && (spend?.value || 0) > 100) {
        const loss = (spend?.value || 0) - (revenue?.value || 0);
        insights.push({
            type: 'critical',
            category: 'Profit Alert',
            icon: DollarSign,
            priority: 0,
            title: `Negative ROAS: ${roas.value.toFixed(2)}x`,
            description: `Estimated loss of ${fmt(loss)} this period. Pause low performers immediately.`,
            action: 'Take action'
        });
    } else if (roas?.value && roas.value > 3.0) {
        const profit = (revenue?.value || 0) - (spend?.value || 0);
        insights.push({
            type: 'success',
            category: 'Profit Alert',
            icon: DollarSign,
            priority: 3,
            title: `Strong profitability: ${roas.value.toFixed(2)}x ROAS`,
            description: `Gross profit ~${fmt(profit)}. Room to scale if CPA holds.`,
            action: 'Scale carefully'
        });
    }

    // =========================================================================
    // 6. FALLBACK - When there's data but no specific alerts
    // =========================================================================
    if (insights.length === 0 && (spend?.value > 0 || revenue?.value > 0)) {
        // Summary insight when no issues detected
        if (roas?.value && roas.value >= 1.0 && roas.value <= 3.0) {
            insights.push({
                type: 'info',
                category: 'Summary',
                icon: Target,
                priority: 5,
                title: `Performance is stable at ${roas.value.toFixed(2)}x ROAS`,
                description: `${fmt(spend?.value || 0)} spent → ${fmt(revenue?.value || 0)} revenue. No critical issues detected.`,
                action: 'View details'
            });
        }

        // Conversion summary
        if (conversions?.value > 0) {
            const cpa = (spend?.value || 0) / conversions.value;
            insights.push({
                type: 'info',
                category: 'Performance',
                icon: Target,
                priority: 5,
                title: `${conversions.value.toFixed(0)} conversions at ${fmt(cpa)} CPA`,
                description: conversions.delta_pct
                    ? `${conversions.delta_pct > 0 ? 'Up' : 'Down'} ${fmtPct(conversions.delta_pct)} from previous period.`
                    : 'Tracking performance across your campaigns.',
                action: 'Analyze'
            });
        }
    }

    // Sort by priority (lower = more urgent)
    return insights.sort((a, b) => a.priority - b.priority).slice(0, 4);
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function AiInsightsPanel({ data, loading, workspaceId }) {
    const [expanded, setExpanded] = useState(false);
    // const router = useRouter();

    const insights = useMemo(() => generateInsights(data), [data]);

    // TODO: Re-enable Ask AI functionality later
    // /**
    //  * Generate a QA prompt from an insight and navigate to copilot page
    //  */
    // const handleInsightClick = (insight) => {
    //     if (!workspaceId) return;
    //
    //     let prompt = '';
    //
    //     if (insight.campaignName) {
    //         prompt = `Tell me more about the campaign "${insight.campaignName}". ${insight.description} What should I do?`;
    //     } else if (insight.campaignFrom && insight.campaignTo) {
    //         prompt = `Should I move budget from "${insight.campaignFrom}" to "${insight.campaignTo}"? Explain the reasoning and potential impact.`;
    //     } else {
    //         prompt = `${insight.title}. ${insight.description} Can you explain this in more detail and suggest what actions I should take?`;
    //     }
    //
    //     // Navigate to Copilot page with the prompt (same pattern as HeroHeader)
    //     const params = new URLSearchParams({
    //         q: prompt,
    //         ws: workspaceId
    //     });
    //     router.push(`/copilot?${params.toString()}`);
    // };

    // Show first 2 by default, all 4 when expanded
    const visibleInsights = expanded ? insights : insights.slice(0, 2);

    if (loading || !data) {
        return (
            <div className="lg:col-span-1 flex flex-col gap-3">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded-full font-medium ml-1">AI</span>
                </div>
                <div className="glass-panel p-4 rounded-2xl h-24 animate-pulse bg-slate-100/50"></div>
                <div className="glass-panel p-4 rounded-2xl h-24 animate-pulse bg-slate-100/50"></div>
            </div>
        );
    }

    if (insights.length === 0) {
        // Determine why there are no insights
        const hasData = data?.kpis?.some(k => k.value > 0) || data?.top_campaigns?.length > 0;
        const message = hasData
            ? "Your campaigns are performing within normal ranges. No alerts at this time."
            : "Sync your ad accounts to generate insights.";

        return (
            <div className="lg:col-span-1 flex flex-col gap-3">
                <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                    <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded-full font-medium ml-1">Live</span>
                </div>
                <div className="glass-panel p-4 rounded-2xl text-slate-400 text-sm text-center">
                    {message}
                </div>
            </div>
        );
    }

    // Color mapping for insight types
    const typeStyles = {
        critical: {
            border: 'border-l-red-500',
            bg: 'bg-red-50',
            iconBg: 'bg-red-100',
            iconColor: 'text-red-600'
        },
        warning: {
            border: 'border-l-amber-400',
            bg: 'bg-amber-50/50',
            iconBg: 'bg-amber-100',
            iconColor: 'text-amber-600'
        },
        opportunity: {
            border: 'border-l-blue-400',
            bg: 'bg-blue-50/50',
            iconBg: 'bg-blue-100',
            iconColor: 'text-blue-600'
        },
        success: {
            border: 'border-l-emerald-400',
            bg: 'bg-emerald-50/50',
            iconBg: 'bg-emerald-100',
            iconColor: 'text-emerald-600'
        },
        info: {
            border: 'border-l-slate-300',
            bg: 'bg-slate-50/50',
            iconBg: 'bg-slate-100',
            iconColor: 'text-slate-600'
        }
    };

    return (
        <div className="lg:col-span-1 flex flex-col gap-3">
            <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <h3 className="text-sm font-medium text-slate-700">Insights</h3>
                <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded-full font-medium ml-1">Live</span>
                <span className="text-[10px] text-slate-400 ml-auto">{insights.length} found</span>
            </div>

            {visibleInsights.map((insight, index) => {
                const styles = typeStyles[insight.type] || typeStyles.info;
                const Icon = insight.icon;

                return (
                    <div
                        key={index}
                        className={`glass-panel p-4 rounded-xl border-l-[3px] ${styles.border} ${styles.bg}`}
                    >
                        <div className="flex gap-3">
                            {/* Icon */}
                            <div className={`${styles.iconBg} p-2 rounded-lg h-fit shrink-0`}>
                                <Icon className={`w-4 h-4 ${styles.iconColor}`} />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                {/* Category tag */}
                                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
                                    {insight.category}
                                </span>

                                {/* Campaign name if present */}
                                {insight.campaignName && (
                                    <p className="text-sm font-semibold text-slate-800 mt-1 truncate" title={insight.campaignName}>
                                        {insight.campaignName}
                                    </p>
                                )}

                                {/* Title (only if no campaign name, or as subtitle) */}
                                <p className={`text-sm ${insight.campaignName ? 'text-slate-600 mt-0.5' : 'font-medium text-slate-800 mt-1'}`}>
                                    {insight.title}
                                </p>

                                {/* Description */}
                                <p className="text-xs text-slate-500 leading-relaxed mt-1.5">
                                    {insight.description}
                                </p>
                            </div>
                        </div>
                    </div>
                );
            })}

            {/* Show more/less toggle */}
            {insights.length > 2 && (
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center justify-center gap-1 text-xs text-slate-500 hover:text-slate-700 py-1.5 transition-colors"
                >
                    {expanded ? (
                        <>
                            <ChevronUp className="w-3.5 h-3.5" />
                            Show less
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-3.5 h-3.5" />
                            Show {insights.length - 2} more
                        </>
                    )}
                </button>
            )}
        </div>
    );
}
