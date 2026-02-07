/**
 * AgentStatsGrid - Dashboard stats cards for agent system
 * ========================================================
 *
 * WHAT: 2x2 grid of stat cards showing agent system health
 * WHY: Users need quick overview of agent activity at a glance
 *
 * STATS DISPLAYED:
 * - Active Agents: Count of ACTIVE agents
 * - Triggers Today: Count of triggers in last 24 hours
 * - Evals This Hour: Count of evaluations in last hour
 * - Errors: Count of ERROR status agents or failed evaluations
 *
 * DESIGN:
 * - Clean card style with subtle gradients
 * - Icons from Lucide with colored backgrounds
 * - Error stat uses red color for visual warning
 * - Fills parent container height
 *
 * REFERENCES:
 * - GET /v1/agents/stats endpoint
 * - ui/app/(dashboard)/agents/page.jsx
 */

'use client';

import { cn } from '@/lib/utils';
import { Bot, Zap, Activity, AlertCircle } from 'lucide-react';

/**
 * Individual stat item within the grid.
 *
 * @param {Object} props
 * @param {React.ElementType} props.icon - Lucide icon component
 * @param {string} props.label - Stat label
 * @param {number} props.value - Stat value
 * @param {string} props.variant - 'default', 'primary', 'warning', or 'error'
 * @param {string} props.iconBg - Background color class for icon
 * @param {string} props.iconColor - Icon color class
 */
function StatItem({ icon: Icon, label, value, variant = 'default', iconBg, iconColor }) {
  const variants = {
    default: {
      bg: 'bg-neutral-100',
      icon: 'text-neutral-600',
    },
    primary: {
      bg: 'bg-blue-50',
      icon: 'text-blue-600',
    },
    warning: {
      bg: 'bg-amber-50',
      icon: 'text-amber-600',
    },
    success: {
      bg: 'bg-emerald-50',
      icon: 'text-emerald-600',
    },
    error: {
      bg: 'bg-red-50',
      icon: 'text-red-500',
    },
  };

  const styles = variants[variant] || variants.default;

  return (
    <div
      className={cn(
        'flex flex-col justify-center p-3 md:p-4 rounded-xl h-full',
        'bg-gradient-to-br from-white to-neutral-50/80',
        'border border-neutral-200/40',
        'transition-all duration-200',
        'hover:shadow-sm hover:border-neutral-200/60'
      )}
    >
      <div className="flex items-center gap-2.5 md:gap-3">
        <div
          className={cn(
            'flex items-center justify-center w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl flex-shrink-0',
            iconBg || styles.bg
          )}
        >
          <Icon className={cn('h-4 w-4 md:h-5 md:w-5', iconColor || styles.icon)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] md:text-[11px] text-neutral-500 uppercase tracking-wide font-medium leading-tight">
            {label}
          </p>
          <p
            className={cn(
              'text-xl md:text-2xl font-bold tabular-nums',
              variant === 'error' && value > 0 ? 'text-red-600' : 'text-neutral-900'
            )}
          >
            {value.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * AgentStatsGrid - 2x2 grid of agent stats
 *
 * @param {Object} props
 * @param {Object} props.stats - Stats object from API
 * @param {number} props.stats.active_agents - Count of active agents
 * @param {number} props.stats.triggers_today - Count of triggers today
 * @param {number} props.stats.evaluations_this_hour - Count of evaluations this hour
 * @param {number} props.stats.errors_today - Count of errors today
 * @param {boolean} props.isLoading - Loading state
 */
export function AgentStatsGrid({ stats, isLoading = false }) {
  // Default values while loading
  const {
    active_agents = 0,
    triggers_today = 0,
    evaluations_this_hour = 0,
    errors_today = 0,
  } = stats || {};

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 h-full">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="rounded-xl bg-gradient-to-br from-neutral-50 to-neutral-100/50 border border-neutral-100 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 h-full">
      <StatItem
        icon={Bot}
        label="Active Agents"
        value={active_agents}
        variant="primary"
      />
      <StatItem
        icon={Zap}
        label="Triggers Today"
        value={triggers_today}
        variant="warning"
      />
      <StatItem
        icon={Activity}
        label="Evals This Hour"
        value={evaluations_this_hour}
        variant="success"
      />
      <StatItem
        icon={AlertCircle}
        label="Errors"
        value={errors_today}
        variant={errors_today > 0 ? 'error' : 'default'}
      />
    </div>
  );
}

export default AgentStatsGrid;
