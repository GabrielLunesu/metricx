/**
 * Financial Summary Cards
 * 
 * WHAT: Display P&L summary KPIs (read-only cards)
 * WHY: Top-level metrics at a glance
 * REFERENCES: lib/pnlAdapter.js:adaptPnLStatement
 */

import { TrendingUp, TrendingDown, CheckCircle, Wallet, CreditCard, Coins, BarChart4, ArrowUpRight, Minus } from "lucide-react";

export default function FinancialSummaryCards({ summary, showComparison }) {
  if (!summary) return null;

  const cards = [
    {
      data: summary.totalRevenue,
      label: "Total Revenue",
      icon: Wallet,
      badgeColor: "bg-emerald-50 text-emerald-600 border-emerald-100",
      badgeIcon: ArrowUpRight,
      progressColor: 'from-cyan-400 to-cyan-600',
      delay: '0ms',
    },
    {
      data: summary.totalSpend,
      label: "Total Spend",
      icon: CreditCard,
      badgeColor: "bg-red-50 text-red-600 border-red-100",
      badgeIcon: ArrowUpRight,
      progressColor: 'from-neutral-400 to-neutral-600',
      delay: '100ms',
    },
    {
      data: summary.grossProfit,
      label: "Gross Profit",
      icon: Coins,
      badgeColor: "bg-emerald-50 text-emerald-600 border-emerald-100",
      badgeIcon: ArrowUpRight,
      progressColor: 'from-green-400 to-green-600',
      delay: '200ms',
    },
    {
      data: summary.netRoas,
      label: "Net ROAS",
      icon: BarChart4,
      badgeColor: "bg-slate-100 text-slate-600 border-slate-200",
      badgeIcon: Minus,
      valueColor: 'text-cyan-600',
      delay: '300ms',
      showCheck: true,
    },
  ];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => {
        const hasDelta = showComparison && card.data.delta;
        const isPositive = hasDelta && !card.data.delta.startsWith('-');
        const TrendIcon = card.showCheck ? CheckCircle : (isPositive ? TrendingUp : TrendingDown);
        const trendColor = card.showCheck 
          ? 'bg-green-50 text-green-600 border-green-200' 
          : (isPositive ? 'bg-green-50 text-green-600 border-green-200' : 'bg-red-50 text-red-600 border-red-200');
        const LeadingIcon = card.icon;
        const BadgeIcon = card.badgeIcon;
        
        return (
          <div
            key={idx}
            className="glass-card rounded-xl p-5 relative overflow-hidden group hover:shadow-float transition-all border border-slate-200/80 bg-white"
            style={{ animationDelay: card.delay }}
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-slate-200 to-slate-100 group-hover:from-blue-400 group-hover:to-blue-300 transition-all" />
            <div className="flex justify-between items-start mb-4 relative z-10">
              <div className="p-2 rounded-lg bg-slate-50 text-slate-400">
                {LeadingIcon && <LeadingIcon className="w-4 h-4" />}
              </div>
              {hasDelta && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${card.badgeColor}`}>
                  {BadgeIcon && <BadgeIcon className="w-3 h-3" />}
                  {card.data.delta}
                </span>
              )}
            </div>
            <div className="space-y-1 relative z-10">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {card.label || card.data.label}
              </p>
              <h3
                className={`text-2xl font-bold text-slate-900 tracking-tight truncate ${card.valueColor || ''}`}
                title={card.data.value}
              >
                {card.data.value}
              </h3>
            </div>
          </div>
        );
      })}
    </div>
  );
}
