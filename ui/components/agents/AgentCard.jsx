/**
 * AgentCard - Premium Glass Card Component
 * =========================================
 *
 * WHAT: Beautiful agent card with glass morphism design
 * WHY: Users need visually stunning, intuitive cards for agent management
 *
 * DESIGN PRINCIPLES:
 * - Glass morphism (backdrop blur, semi-transparent)
 * - Rounded corners (24px)
 * - Hover lift effect
 * - Smooth animations
 * - Premium color palette
 *
 * FEATURES:
 * - Animated status indicator (pulsing dot)
 * - Human-readable condition summary
 * - Action buttons with hover states
 * - Expandable details section
 * - State breakdown visualization
 *
 * REFERENCES:
 * - Metricx v3.0 design system
 * - components/dashboard/KpiCardsModule.jsx
 */

'use client';

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  Settings,
  Eye,
  Zap,
  Bell,
  Mail,
  Webhook,
  DollarSign,
  StopCircle,
  Activity,
  Clock,
  Target,
  CheckCircle2,
  AlertCircle,
  Timer,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';

// Map action types to icons and colors
const ACTION_CONFIG = {
  email: { icon: Mail, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  scale_budget: { icon: DollarSign, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  pause_campaign: { icon: StopCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
  webhook: { icon: Webhook, color: 'text-purple-500', bg: 'bg-purple-500/10' },
};

// State colors and icons
const STATE_CONFIG = {
  watching: { color: 'bg-blue-500', label: 'Watching', icon: Eye },
  accumulating: { color: 'bg-amber-500', label: 'Accumulating', icon: Timer },
  triggered: { color: 'bg-emerald-500', label: 'Triggered', icon: Zap },
  cooldown: { color: 'bg-purple-500', label: 'Cooldown', icon: Clock },
  error: { color: 'bg-red-500', label: 'Error', icon: AlertCircle },
};

// Status badge config
const STATUS_CONFIG = {
  active: { color: 'emerald', label: 'Active', dot: true },
  paused: { color: 'amber', label: 'Paused', dot: false },
  error: { color: 'red', label: 'Error', dot: false },
  draft: { color: 'neutral', label: 'Draft', dot: false },
};

/**
 * Convert condition to human-readable summary
 */
function conditionToSummary(condition) {
  if (!condition) return 'No condition configured';

  switch (condition.type) {
    case 'threshold': {
      const ops = { gt: '>', gte: '≥', lt: '<', lte: '≤', eq: '=', neq: '≠' };
      const metric = condition.metric?.replace(/_/g, ' ') || 'metric';
      return `When ${metric} ${ops[condition.operator] || '?'} ${condition.value}`;
    }
    case 'change': {
      const dir = condition.direction === 'increase' ? 'increases' : 'decreases';
      const metric = condition.metric?.replace(/_/g, ' ') || 'metric';
      return `When ${metric} ${dir} by ${condition.percent}%`;
    }
    case 'composite': {
      const op = condition.operator === 'and' ? ' AND ' : ' OR ';
      const summaries = condition.conditions?.map(c => conditionToSummary(c)) || [];
      return summaries.join(op);
    }
    case 'not':
      return `NOT (${conditionToSummary(condition.condition)})`;
    default:
      return 'Custom condition';
  }
}

function formatScheduleSummary(schedule, dateRange) {
  if (!schedule || schedule.type === 'realtime') {
    return 'Scheduled report';
  }

  const pad = (value) => value.toString().padStart(2, '0');
  const time = `${pad(schedule.hour ?? 0)}:${pad(schedule.minute ?? 0)}`;
  const tz = schedule.timezone || 'UTC';
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dateRangeLabels = {
    yesterday: 'Yesterday',
    today: 'Today',
    last_7_days: 'Last 7 days',
    last_30_days: 'Last 30 days',
  };

  let cadence = 'Daily';
  if (schedule.type === 'weekly') {
    const dayLabel = days[schedule.day_of_week ?? 0];
    cadence = `Weekly (${dayLabel})`;
  } else if (schedule.type === 'monthly') {
    cadence = `Monthly (${schedule.day_of_month ?? 1})`;
  }

  const rangeLabel = dateRangeLabels[dateRange?.type] ? ` · ${dateRangeLabels[dateRange.type]}` : '';
  return `Scheduled report · ${cadence} at ${time} ${tz}${rangeLabel}`;
}

/**
 * AgentCard - Premium glass card component
 */
export function AgentCard({
  agent,
  onView,
  onPause,
  onResume,
  onSettings,
  expanded = false,
  onToggleExpand,
}) {
  const [isHovered, setIsHovered] = useState(false);

  // Extract key data
  const {
    id,
    name,
    description,
    status,
    condition,
    actions,
    scope,
    accumulation,
    schedule,
    condition_required,
    date_range,
    entities_count = 0,
    last_evaluated_at,
    total_evaluations = 0,
    total_triggers = 0,
    last_triggered_at,
    current_states = [],
    error_message,
  } = agent;

  // Count entities in each state
  const stateBreakdown = current_states.reduce((acc, state) => {
    acc[state.state] = (acc[state.state] || 0) + 1;
    return acc;
  }, {});

  // Format times
  const lastEvaluatedText = last_evaluated_at
    ? formatDistanceToNow(new Date(last_evaluated_at), { addSuffix: true })
    : 'Never';

  const lastTriggeredText = last_triggered_at
    ? formatDistanceToNow(new Date(last_triggered_at), { addSuffix: true })
    : 'Never';

  // Get unique action types
  const actionTypes = [...new Set(actions?.map(a => a.type) || [])];

  // Status config
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const isReportAgent = condition_required === false;
  const summaryText = isReportAgent
    ? formatScheduleSummary(schedule, date_range)
    : conditionToSummary(condition);

  return (
    <div
      className={cn(
        'bg-white/40 glass rounded-2xl md:rounded-[24px] border border-white/60 overflow-hidden',
        'transition-all duration-300',
        'hover:bg-white/60 hover:-translate-y-0.5 hover:shadow-lg',
        expanded && 'ring-2 ring-neutral-200/50',
        status === 'error' && 'border-red-200/60'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Main row - always visible */}
      <div className="p-3 md:p-5">
        <div className="flex items-center gap-3 md:gap-4">
          {/* Status indicator */}
          <div className="flex-shrink-0">
            <div
              className={cn(
                'w-8 h-8 md:w-10 md:h-10 rounded-xl md:rounded-2xl flex items-center justify-center',
                statusConfig.color === 'emerald' && 'bg-emerald-500/10',
                statusConfig.color === 'amber' && 'bg-amber-500/10',
                statusConfig.color === 'red' && 'bg-red-500/10',
                statusConfig.color === 'neutral' && 'bg-neutral-500/10'
              )}
            >
              <div
                className={cn(
                  'w-2 h-2 md:w-2.5 md:h-2.5 rounded-full',
                  statusConfig.color === 'emerald' && 'bg-emerald-500',
                  statusConfig.color === 'amber' && 'bg-amber-500',
                  statusConfig.color === 'red' && 'bg-red-500',
                  statusConfig.color === 'neutral' && 'bg-neutral-400',
                  statusConfig.dot && 'animate-pulse'
                )}
              />
            </div>
          </div>

          {/* Name and condition */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-neutral-900 truncate text-sm md:text-base">{name}</h3>
              {total_triggers > 0 && (
                <span className="flex-shrink-0 flex items-center gap-1 text-[10px] md:text-xs font-semibold text-amber-600 bg-amber-500/10 px-1.5 md:px-2 py-0.5 md:py-1 rounded-md md:rounded-lg">
                  <Zap size={10} />
                  {total_triggers}
                </span>
              )}
              <span
                className={cn(
                  'flex-shrink-0 text-[9px] md:text-[10px] font-semibold uppercase tracking-wider px-1.5 md:px-2 py-0.5 rounded-md',
                  statusConfig.color === 'emerald' && 'text-emerald-700 bg-emerald-500/10',
                  statusConfig.color === 'amber' && 'text-amber-700 bg-amber-500/10',
                  statusConfig.color === 'red' && 'text-red-700 bg-red-500/10',
                  statusConfig.color === 'neutral' && 'text-neutral-500 bg-neutral-500/10'
                )}
              >
                {statusConfig.label}
              </span>
            </div>
            <p className="text-xs md:text-sm text-neutral-500 truncate mt-0.5 md:mt-1">
              {summaryText}
            </p>
            {/* Mobile: action type chips + trigger count below text */}
            <div className="flex md:hidden items-center gap-1.5 mt-2">
              {actionTypes.map(type => {
                const config = ACTION_CONFIG[type] || { icon: Bell, color: 'text-neutral-500', bg: 'bg-neutral-500/10' };
                const ActionIcon = config.icon;
                return (
                  <div
                    key={type}
                    className={cn('px-2 py-1 rounded-lg flex items-center gap-1', config.bg)}
                  >
                    <ActionIcon size={11} className={config.color} />
                    <span className="text-[10px] font-medium text-neutral-600 capitalize">{type.replace('_', ' ')}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stats - hidden on mobile */}
          <div className="hidden lg:flex items-center gap-8 text-sm">
            <div className="text-center">
              <div className="text-lg font-semibold text-neutral-900 number-display">{entities_count}</div>
              <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Entities</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-neutral-900">{lastEvaluatedText}</div>
              <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Last Check</div>
            </div>
            <div className="flex items-center gap-1.5">
              {actionTypes.map(type => {
                const config = ACTION_CONFIG[type] || { icon: Bell, color: 'text-neutral-500', bg: 'bg-neutral-500/10' };
                const ActionIcon = config.icon;
                return (
                  <div
                    key={type}
                    className={cn('p-2 rounded-xl', config.bg)}
                    title={type.replace('_', ' ')}
                  >
                    <ActionIcon size={14} className={config.color} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action buttons - minimal on mobile, full on desktop */}
          <div
            className={cn(
              'flex items-center gap-0.5 md:gap-1 flex-shrink-0',
              'transition-opacity duration-200',
              isHovered ? 'opacity-100' : 'opacity-60 lg:opacity-100'
            )}
          >
            {status === 'active' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onPause?.(id);
                }}
                className="w-8 h-8 md:w-9 md:h-9 p-0 rounded-xl text-neutral-500 hover:text-amber-600 hover:bg-amber-500/10"
              >
                <Pause size={15} />
              </Button>
            )}
            {status === 'paused' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onResume?.(id);
                }}
                className="w-8 h-8 md:w-9 md:h-9 p-0 rounded-xl text-neutral-500 hover:text-emerald-600 hover:bg-emerald-500/10"
              >
                <Play size={15} />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onView?.(id);
              }}
              className="hidden md:flex w-9 h-9 p-0 rounded-xl text-neutral-500 hover:text-neutral-900 hover:bg-neutral-500/10"
            >
              <Eye size={16} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSettings?.(id);
              }}
              className="hidden md:flex w-9 h-9 p-0 rounded-xl text-neutral-500 hover:text-neutral-900 hover:bg-neutral-500/10"
            >
              <Settings size={16} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggleExpand?.()}
              className="w-8 h-8 md:w-9 md:h-9 p-0 rounded-xl text-neutral-500 hover:text-neutral-900 hover:bg-neutral-500/10"
            >
              {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </Button>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-neutral-200/30 bg-white/30 px-3 py-3 md:px-5 md:py-4">
          {/* Error message */}
          {status === 'error' && error_message && (
            <div className="mb-4 p-3 bg-red-500/5 border border-red-200/60 rounded-xl text-sm text-red-700 flex items-start gap-3">
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
              <span>{error_message}</span>
            </div>
          )}

          {/* Description */}
          {description && (
            <p className="text-sm text-neutral-600 mb-4">{description}</p>
          )}

          {/* Details grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
            {/* Accumulation config */}
            <div className="bg-white/50 rounded-xl p-3">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Timer size={12} />
                Accumulation
              </div>
              <div className="font-semibold text-neutral-900">
                {accumulation?.required || 1} {accumulation?.unit || 'evaluations'}
              </div>
              {accumulation?.mode === 'consecutive' && (
                <div className="text-[10px] text-neutral-400 mt-0.5">Consecutive</div>
              )}
            </div>

            {/* Scope */}
            <div className="bg-white/50 rounded-xl p-3">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Target size={12} />
                Scope
              </div>
              <div className="font-semibold text-neutral-900 capitalize">
                {scope?.type === 'all'
                  ? 'All entities'
                  : scope?.type === 'specific'
                  ? `${scope.entity_ids?.length || 0} specific`
                  : scope?.type === 'filter'
                  ? 'Filtered'
                  : 'Unknown'}
              </div>
            </div>

            {/* Total evaluations */}
            <div className="bg-white/50 rounded-xl p-3">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Activity size={12} />
                Evaluations
              </div>
              <div className="font-semibold text-neutral-900 number-display">
                {total_evaluations.toLocaleString()}
              </div>
            </div>

            {/* Last triggered */}
            <div className="bg-white/50 rounded-xl p-3">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <Zap size={12} />
                Last Triggered
              </div>
              <div className="font-semibold text-neutral-900">{lastTriggeredText}</div>
            </div>
          </div>

          {/* Entity state breakdown */}
          {Object.keys(stateBreakdown).length > 0 && (
            <div className="mt-4 pt-4 border-t border-neutral-200/30">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-3">
                Entity States
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stateBreakdown).map(([state, count]) => {
                  const config = STATE_CONFIG[state] || STATE_CONFIG.watching;
                  const Icon = config.icon;
                  return (
                    <div
                      key={state}
                      className="flex items-center gap-2 px-3 py-1.5 bg-white/60 rounded-xl border border-neutral-200/30"
                    >
                      <div className={cn('w-2 h-2 rounded-full', config.color)} />
                      <span className="text-xs font-medium text-neutral-700 capitalize">
                        {config.label}
                      </span>
                      <span className="text-xs font-bold text-neutral-900">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Mobile stats + quick actions - shown only on mobile */}
          <div className="lg:hidden mt-4 pt-4 border-t border-neutral-200/30">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-white/50 rounded-xl p-3 text-center">
                <div className="text-xl font-semibold text-neutral-900 number-display">{entities_count}</div>
                <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Entities</div>
              </div>
              <div className="bg-white/50 rounded-xl p-3 text-center">
                <div className="text-sm font-semibold text-neutral-900">{lastEvaluatedText}</div>
                <div className="text-[10px] text-neutral-500 uppercase tracking-wider">Last Check</div>
              </div>
            </div>
            <div className="flex gap-2 mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onView?.(id);
                }}
                className="flex-1 h-9 rounded-xl text-xs font-medium border-neutral-200/60"
              >
                <Eye size={14} className="mr-1.5" />
                View Details
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onSettings?.(id);
                }}
                className="flex-1 h-9 rounded-xl text-xs font-medium border-neutral-200/60"
              >
                <Settings size={14} className="mr-1.5" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentCard;
