'use client';

/**
 * AiInsightsModule Component
 * ==========================
 *
 * WHAT: Glassmorphic card showing AI-generated insights from dashboard data
 * WHY: Users need actionable insights without making slow AI API calls
 *
 * FEATURES:
 *   - Data-driven insight generation (no external API)
 *   - Priority-sorted insights (critical first)
 *   - Animated insight cards with icons
 *   - Glassmorphic purple-tinted design
 *
 * INSIGHT TYPES:
 *   - Trend alerts (ROAS changes)
 *   - Wasted spend detection
 *   - Scale opportunities
 *   - Platform diversification
 *
 * PROPS:
 *   - data: Unified dashboard data
 *   - loading: Boolean for loading state
 *   - workspaceId: For potential future AI chat integration
 *
 * REFERENCES:
 *   - Original: AiInsightsPanel.jsx
 *   - Design: Apple glassmorphism
 */

import { useMemo } from "react";
import {
  Sparkles,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  DollarSign,
  Target,
  Flame,
  Zap,
} from "lucide-react";

/**
 * Generate insights from dashboard data.
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

  const roas = kpiMap.roas;
  const spend = kpiMap.spend;
  const revenue = kpiMap.revenue;
  const conversions = kpiMap.conversions;

  // ROAS dropping significantly
  if (roas?.delta_pct && roas.delta_pct < -0.10) {
    insights.push({
      type: 'warning',
      icon: TrendingDown,
      priority: 1,
      title: `ROAS dropped ${fmtPct(roas.delta_pct)}`,
      description: `Now at ${(roas.value || 0).toFixed(2)}x. Review underperforming campaigns.`,
    });
  }

  // ROAS improving significantly
  if (roas?.delta_pct && roas.delta_pct > 0.15) {
    insights.push({
      type: 'success',
      icon: TrendingUp,
      priority: 3,
      title: `ROAS up ${fmtPct(roas.delta_pct)}`,
      description: `Now at ${(roas.value || 0).toFixed(2)}x. Consider scaling budget.`,
    });
  }

  // Spend spike without revenue increase
  if (spend?.delta_pct && spend.delta_pct > 0.20 && (!revenue?.delta_pct || revenue.delta_pct < spend.delta_pct * 0.5)) {
    insights.push({
      type: 'warning',
      icon: AlertTriangle,
      priority: 1,
      title: `Spend up ${fmtPct(spend.delta_pct)} but revenue lagging`,
      description: `Increased spend isn't translating to proportional revenue.`,
    });
  }

  // Campaign performance
  // Handle both old format (array) and new format ({items, disclaimer})
  const topCampaignsData = data.top_campaigns || {};
  const campaigns = Array.isArray(topCampaignsData)
    ? topCampaignsData
    : topCampaignsData.items || [];
  if (campaigns.length >= 2) {
    const sortedByRoas = [...campaigns].sort((a, b) => (b.roas || 0) - (a.roas || 0));
    const best = sortedByRoas[0];
    const worst = sortedByRoas[sortedByRoas.length - 1];

    if (best && worst && best.roas > worst.roas * 1.5 && worst.spend > 10) {
      const suggestedShift = Math.min(worst.spend * 0.25, 100);
      insights.push({
        type: 'opportunity',
        icon: Flame,
        priority: 2,
        title: `Move ${fmt(suggestedShift)} to better performer`,
        description: `"${best.name?.slice(0, 25)}..." has ${best.roas.toFixed(1)}x vs ${worst.roas.toFixed(1)}x ROAS.`,
      });
    }

    // Wasted spend campaign
    const wastedSpend = campaigns.find(c => c.roas < 1.0 && c.spend > 50);
    if (wastedSpend) {
      insights.push({
        type: 'warning',
        icon: AlertTriangle,
        priority: 1,
        title: `Campaign losing money`,
        description: `${fmt(wastedSpend.spend)} spent with ${wastedSpend.roas.toFixed(2)}x ROAS. Consider pausing.`,
      });
    }
  }

  // Top performer scale opportunity
  const topCampaign = campaigns.find(c => c.roas > 2.0 && c.spend > 20);
  if (topCampaign) {
    insights.push({
      type: 'success',
      icon: Zap,
      priority: 2,
      title: `High performer ready to scale`,
      description: `"${topCampaign.name?.slice(0, 25)}..." at ${topCampaign.roas.toFixed(1)}x ROAS.`,
    });
  }

  // Profit intelligence
  if (roas?.value && roas.value < 1.0 && (spend?.value || 0) > 100) {
    const loss = (spend?.value || 0) - (revenue?.value || 0);
    insights.push({
      type: 'critical',
      icon: DollarSign,
      priority: 0,
      title: `Negative ROAS: ${roas.value.toFixed(2)}x`,
      description: `Estimated loss of ${fmt(loss)}. Pause low performers immediately.`,
    });
  } else if (roas?.value && roas.value > 3.0) {
    const profit = (revenue?.value || 0) - (spend?.value || 0);
    insights.push({
      type: 'success',
      icon: DollarSign,
      priority: 3,
      title: `Strong profitability`,
      description: `${roas.value.toFixed(2)}x ROAS with ~${fmt(profit)} gross profit.`,
    });
  }

  // Fallback summary
  if (insights.length === 0 && (spend?.value > 0 || revenue?.value > 0)) {
    if (roas?.value && roas.value >= 1.0) {
      insights.push({
        type: 'info',
        icon: Target,
        priority: 5,
        title: `Performance is stable`,
        description: `${roas.value.toFixed(2)}x ROAS. No critical issues detected.`,
      });
    }
    if (conversions?.value > 0) {
      const cpa = (spend?.value || 0) / conversions.value;
      insights.push({
        type: 'info',
        icon: Target,
        priority: 5,
        title: `${conversions.value.toFixed(0)} conversions`,
        description: `At ${fmt(cpa)} CPA across your campaigns.`,
      });
    }
  }

  return insights.sort((a, b) => a.priority - b.priority).slice(0, 4);
}

// Style mapping for insight types
const typeStyles = {
  critical: {
    bg: 'bg-red-500/10',
    iconBg: 'bg-red-500/20',
    iconColor: 'text-red-500',
    border: 'border-red-500/20'
  },
  warning: {
    bg: 'bg-amber-500/10',
    iconBg: 'bg-amber-500/20',
    iconColor: 'text-amber-600',
    border: 'border-amber-500/20'
  },
  opportunity: {
    bg: 'bg-blue-500/10',
    iconBg: 'bg-blue-500/20',
    iconColor: 'text-blue-500',
    border: 'border-blue-500/20'
  },
  success: {
    bg: 'bg-emerald-500/10',
    iconBg: 'bg-emerald-500/20',
    iconColor: 'text-emerald-500',
    border: 'border-emerald-500/20'
  },
  info: {
    bg: 'bg-slate-500/5',
    iconBg: 'bg-slate-500/10',
    iconColor: 'text-slate-500',
    border: 'border-slate-500/10'
  }
};

export default function AiInsightsModule({ data, loading }) {
  const insights = useMemo(() => generateInsights(data), [data]);

  // Loading state
  if (loading || !data) {
    return (
      <div className="dashboard-module dashboard-module-purple min-h-[380px] animate-pulse">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-full bg-purple-200/50"></div>
          <div className="h-5 w-24 bg-slate-200/50 rounded"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-slate-200/30 rounded-2xl"></div>
          ))}
        </div>
      </div>
    );
  }

  // No insights state
  if (insights.length === 0) {
    const hasData = data?.kpis?.some(k => k.value > 0);
    return (
      <div className="dashboard-module dashboard-module-purple min-h-[380px]">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-full bg-purple-100">
            <Sparkles className="w-4 h-4 text-purple-500" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">AI Insights</h2>
          <span className="text-[10px] px-2 py-0.5 bg-purple-100 text-purple-600 rounded-full font-medium">
            Live
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-400 text-sm text-center">
            {hasData
              ? "Your campaigns are performing within normal ranges."
              : "Connect ad accounts to generate insights."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-module dashboard-module-purple min-h-[380px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-full bg-purple-100">
            <Sparkles className="w-4 h-4 text-purple-500" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900">AI Insights</h2>
          <span className="text-[10px] px-2 py-0.5 bg-purple-100 text-purple-600 rounded-full font-medium">
            Live
          </span>
        </div>
        <span className="text-xs text-slate-400">{insights.length} found</span>
      </div>

      {/* Insights List */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        {insights.map((insight, index) => {
          const styles = typeStyles[insight.type] || typeStyles.info;
          const Icon = insight.icon;

          return (
            <div
              key={index}
              className={`
                p-3.5 rounded-2xl border transition-all duration-300
                hover:scale-[1.01] hover:shadow-md cursor-default
                ${styles.bg} ${styles.border}
              `}
              style={{
                animationDelay: `${index * 100}ms`,
              }}
            >
              <div className="flex gap-3">
                <div className={`${styles.iconBg} p-2 rounded-xl h-fit`}>
                  <Icon className={`w-4 h-4 ${styles.iconColor}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 leading-tight">
                    {insight.title}
                  </p>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {insight.description}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
