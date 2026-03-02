/**
 * AnalyticsFunnel — Conversion funnel with liquid glass UI.
 *
 * WHAT: Renders a funnel visualization showing the drop-off between each stage
 *       (Impressions → Clicks → Page Views → Product Views → ATC → Checkout →
 *       Purchase). Below the funnel, 3 highlight KPIs are shown.
 *
 * WHY: Users need to see where visitors drop off in the buying journey at a
 *       glance. This competes with Triple Whale's funnel view.
 *
 * DESIGN:
 *   - Desktop: single horizontal row with chevron connectors
 *   - Mobile: snake/zigzag pattern — 2 columns going down, alternating
 *     left-to-right then right-to-left with connecting arrows
 *   - Liquid glass cards with floating rate badges on top-right
 *   - Cards animate in staggered with framer-motion
 *   - Below: 3 KPI highlight cards in matching glass style
 *
 * PROPS:
 *   - stages: Array of { key, label, count, rate_from_previous, drop_off }
 *   - kpis: Array of { key, label, value, description }
 *   - loading: boolean
 *
 * REFERENCES:
 *   - backend/app/routers/funnel.py (data source)
 *   - ui/app/(dashboard)/analytics/page.jsx (parent page)
 */

'use client';

import { motion } from 'framer-motion';
import { ChevronRight, ChevronDown } from 'lucide-react';

function formatCompact(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 10_000) return `${(num / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(num);
}

function getRateBadgeClass(rate) {
  if (rate >= 50) return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
  if (rate >= 20) return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
  return 'bg-red-500/10 text-red-600 border-red-500/20';
}

/**
 * Single funnel stage card — reused in both mobile and desktop layouts.
 */
function StageCard({ stage, idx }) {
  const hasRate = stage.rate_from_previous !== null && stage.rate_from_previous !== undefined;

  return (
    <motion.div
      className="relative pt-3 h-full"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Floating rate badge on top-right */}
      {hasRate && (
        <div className="absolute top-0 right-1 z-10">
          <span
            className={`inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5
                        rounded-md border backdrop-blur-sm
                        ${getRateBadgeClass(stage.rate_from_previous)}`}
          >
            {stage.rate_from_previous}%
          </span>
        </div>
      )}

      {/* Glass card */}
      <div
        className="bg-white/40 glass rounded-2xl px-3 py-3 md:px-4 md:py-4
                   border border-white/60
                   hover:bg-white/60 hover:-translate-y-0.5
                   transition-all duration-300 h-full
                   flex flex-col justify-between gap-1"
      >
        <span className="text-[11px] font-medium text-neutral-500 tracking-wide leading-tight">
          {stage.label}
        </span>
        <div className="text-2xl md:text-3xl font-medium text-neutral-900 number-display tracking-tighter">
          {formatCompact(stage.count)}
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Mobile snake layout — 2 columns, alternating row direction.
 * Row 0: [0] → [1]    (left to right)
 * Row 1: [3] ← [2]    (right to left)
 * Row 2: [4] → [5]    (left to right)
 * Row 3: [6]           (left to right, single)
 *
 * With connecting arrows between rows.
 */
function MobileSnakeLayout({ stages }) {
  // Group stages into pairs (rows of 2)
  const rows = [];
  for (let i = 0; i < stages.length; i += 2) {
    rows.push(stages.slice(i, i + 2));
  }

  return (
    <div className="flex flex-col gap-1">
      {rows.map((row, rowIdx) => {
        // Even rows: left-to-right. Odd rows: right-to-left.
        const isReversed = rowIdx % 2 === 1;
        const displayRow = isReversed ? [...row].reverse() : row;

        return (
          <div key={rowIdx}>
            {/* Row connector arrow — between rows */}
            {rowIdx > 0 && (
              <div className="flex justify-center py-0.5">
                <ChevronDown className="w-4 h-4 text-neutral-300/80" />
              </div>
            )}

            {/* Stage cards in this row */}
            <div className="flex items-stretch gap-0">
              {displayRow.map((stage, colIdx) => {
                const globalIdx = rowIdx * 2 + (isReversed ? (row.length - 1 - colIdx) : colIdx);
                const isLast = colIdx === displayRow.length - 1;

                return (
                  <div key={stage.key} className="flex items-stretch flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <StageCard stage={stage} idx={globalIdx} />
                    </div>

                    {/* Horizontal chevron between cards in same row */}
                    {!isLast && (
                      <div className="flex items-center px-0.5 flex-shrink-0 pt-3">
                        <ChevronRight className="w-3.5 h-3.5 text-neutral-300/80" />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* If odd row has only 1 item, add empty spacer for alignment */}
              {displayRow.length === 1 && (
                <div className="flex-1 min-w-0" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Desktop layout — single horizontal row with chevrons.
 */
function DesktopRowLayout({ stages }) {
  return (
    <div className="flex items-stretch gap-0">
      {stages.map((stage, idx) => (
        <div key={stage.key} className="flex items-stretch flex-1 min-w-0">
          <div className="flex-1 min-w-0">
            <StageCard stage={stage} idx={idx} />
          </div>

          {idx < stages.length - 1 && (
            <div className="flex items-center px-1 flex-shrink-0 pt-3">
              <ChevronRight className="w-3.5 h-3.5 text-neutral-300/80" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsFunnel({ stages = [], kpis = [], loading = false }) {
  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-4 w-36 bg-neutral-100 rounded animate-pulse" />
        {/* Desktop skeleton */}
        <div className="hidden md:flex items-stretch gap-2">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className="flex-1 bg-white/40 glass rounded-2xl px-3 py-3 border border-white/60 animate-pulse"
            >
              <div className="h-3 w-14 bg-neutral-200/50 rounded mb-3" />
              <div className="h-8 w-12 bg-neutral-200/50 rounded" />
            </div>
          ))}
        </div>
        {/* Mobile skeleton */}
        <div className="md:hidden grid grid-cols-2 gap-2">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className="bg-white/40 glass rounded-2xl px-3 py-3 border border-white/60 animate-pulse"
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
      <h3 className="text-xs md:text-sm font-medium text-neutral-400 tracking-wide">
        Conversion Funnel
      </h3>

      {/* Mobile: snake pattern */}
      <div className="md:hidden">
        <MobileSnakeLayout stages={stages} />
      </div>

      {/* Desktop: single row */}
      <div className="hidden md:block">
        <DesktopRowLayout stages={stages} />
      </div>

      {/* KPI highlight cards */}
      {kpis.length > 0 && (
        <div className="grid grid-cols-3 gap-2 md:gap-3 mt-1">
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
