/**
 * AnalyticsFunnel — Conversion funnel with liquid glass UI.
 *
 * WHAT: Renders a horizontal funnel visualization showing the drop-off between
 *       each stage (Impressions → Clicks → Page Views → Product Views → ATC →
 *       Checkout → Purchase). Below the bars, 3 highlight KPIs are shown.
 *
 * WHY: Users need to see where visitors drop off in the buying journey at a
 *       glance. This competes with Triple Whale's funnel view.
 *
 * DESIGN:
 *   - Liquid glass cards: uniform height, compact padding
 *   - Conversion rate badge floats on top-right corner OUTSIDE the card
 *   - Between stages, chevron connectors on desktop
 *   - Cards animate in left-to-right using framer-motion stagger
 *   - Below: 3 KPI highlight cards in matching glass style
 *   - Responsive: 2-col grid on mobile, full 7-col row on desktop
 *
 * PROPS:
 *   - stages: Array of { key, label, count, rate_from_previous, drop_off }
 *   - kpis: Array of { key, label, value, description }
 *   - loading: boolean
 *
 * REFERENCES:
 *   - backend/app/routers/funnel.py (data source)
 *   - ui/app/(dashboard)/analytics/page.jsx (parent page)
 *   - ui/app/(dashboard)/dashboard/components/KpiCardsModule.jsx (design reference)
 */

'use client';

import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

/**
 * Format large numbers in compact notation matching homepage style.
 */
function formatCompact(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 10_000) return `${(num / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(num);
}

/**
 * Get badge color based on conversion rate threshold.
 */
function getRateBadgeClass(rate) {
  if (rate >= 50) return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
  if (rate >= 20) return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
  return 'bg-red-500/10 text-red-600 border-red-500/20';
}

export default function AnalyticsFunnel({ stages = [], kpis = [], loading = false }) {
  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-4 w-36 bg-neutral-100 rounded animate-pulse" />
        <div className="flex items-stretch gap-2 md:gap-3 overflow-x-auto pb-1">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className="flex-1 min-w-[100px] bg-white/40 glass rounded-2xl px-3 py-3 md:px-4 md:py-4 border border-white/60 animate-pulse"
            >
              <div className="h-3 w-14 bg-neutral-200/50 rounded mb-3" />
              <div className="h-8 w-12 bg-neutral-200/50 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!stages || stages.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Section label */}
      <h3 className="text-xs md:text-sm font-medium text-neutral-400 tracking-wide">
        Conversion Funnel
      </h3>

      {/* Funnel stage cards — single row with chevrons */}
      <div className="flex items-stretch gap-0 overflow-x-auto pb-1">
        {stages.map((stage, idx) => {
          const hasRate = stage.rate_from_previous !== null && stage.rate_from_previous !== undefined;

          return (
            <div key={stage.key} className="flex items-stretch flex-1 min-w-0">
              {/* Card wrapper with top-right badge */}
              <motion.div
                className="relative flex-1 min-w-0 pt-3"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
              >
                {/* Conversion rate badge — floating on top-right corner */}
                {hasRate && (
                  <div className="absolute -top-0 right-1 z-10">
                    <span
                      className={`inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5
                                  rounded-md border backdrop-blur-sm
                                  ${getRateBadgeClass(stage.rate_from_previous)}`}
                    >
                      {stage.rate_from_previous}%
                    </span>
                  </div>
                )}

                {/* Glass card — compact, uniform height */}
                <div
                  className="bg-white/40 glass rounded-2xl px-3 py-3 md:px-4 md:py-4
                             border border-white/60
                             hover:bg-white/60 hover:-translate-y-0.5
                             transition-all duration-300 h-full
                             flex flex-col justify-between gap-1"
                >
                  {/* Label */}
                  <span className="text-[11px] font-medium text-neutral-500 tracking-wide leading-tight">
                    {stage.label}
                  </span>

                  {/* Count */}
                  <div className="text-2xl md:text-3xl font-medium text-neutral-900 number-display tracking-tighter">
                    {formatCompact(stage.count)}
                  </div>
                </div>
              </motion.div>

              {/* Chevron connector */}
              {idx < stages.length - 1 && (
                <div className="hidden md:flex items-center px-1 flex-shrink-0">
                  <ChevronRight className="w-3.5 h-3.5 text-neutral-300/80" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* KPI highlight cards */}
      {kpis.length > 0 && (
        <div className="grid grid-cols-3 gap-2 md:gap-3">
          {kpis.map((kpi, idx) => (
            <motion.div
              key={kpi.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + idx * 0.05, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="bg-white/40 glass rounded-2xl px-3 py-3 md:px-4 md:py-4 border border-white/60
                         hover:bg-white/60 hover:-translate-y-0.5
                         transition-all duration-300"
            >
              <span className="text-[11px] font-medium text-neutral-500 tracking-wide">
                {kpi.label}
              </span>
              <div className="text-xl md:text-2xl font-medium text-neutral-900 number-display tracking-tighter mt-0.5">
                {kpi.value}
              </div>
              <p className="text-[10px] text-neutral-400 mt-0.5 leading-tight">
                {kpi.description}
              </p>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
