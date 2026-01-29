/**
 * NotificationItem - Individual notification in the agent feed
 * =============================================================
 *
 * WHAT: Displays a single agent evaluation event with rollback capability
 * WHY: Users need to see what agents are doing and undo actions if needed
 *
 * FEATURES:
 * - Result type icon (trigger, error, etc.)
 * - Agent name as link to detail page
 * - Headline and relative time
 * - Rollback button for reversible actions
 * - Expandable detail panel
 *
 * DESIGN:
 * - Glass morphism style
 * - Fade-in animation via framer-motion
 * - Consistent with other agent components
 *
 * REFERENCES:
 * - ui/components/agents/NotificationFeed.jsx
 * - GET /v1/agents/events endpoint
 * - POST /v1/agents/actions/{id}/rollback endpoint
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Zap,
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Bot,
  DollarSign,
  StopCircle,
  Mail,
  Webhook,
} from 'lucide-react';

// Result type configuration
const RESULT_CONFIG = {
  triggered: {
    icon: Zap,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    label: 'Triggered',
  },
  condition_met: {
    icon: CheckCircle2,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    label: 'Condition Met',
  },
  condition_not_met: {
    icon: Eye,
    color: 'text-neutral-400',
    bg: 'bg-neutral-100',
    label: 'Watching',
  },
  cooldown: {
    icon: Clock,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    label: 'Cooldown',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    label: 'Error',
  },
};

// Action type icons
const ACTION_ICONS = {
  scale_budget: DollarSign,
  pause_campaign: StopCircle,
  email: Mail,
  webhook: Webhook,
};

/**
 * NotificationItem component
 *
 * @param {Object} props
 * @param {Object} props.event - Event object from API
 * @param {Function} props.onViewDetails - Callback when View is clicked
 * @param {Function} props.onRollback - Callback when Rollback is clicked
 * @param {boolean} props.isRollingBack - True if rollback is in progress
 */
export function NotificationItem({
  event,
  onViewDetails,
  onRollback,
  isRollingBack = false,
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const {
    id,
    agent_id,
    agent_name,
    entity_name,
    entity_provider,
    result_type,
    headline,
    evaluated_at,
    actions_executed = [],
  } = event;

  // Get result type config
  const resultConfig = RESULT_CONFIG[result_type] || RESULT_CONFIG.condition_not_met;
  const ResultIcon = resultConfig.icon;

  // Format relative time
  const timeAgo = formatDistanceToNow(new Date(evaluated_at), { addSuffix: true });

  // Check if any action can be rolled back
  const rollbackableActions = actions_executed.filter(
    (action) =>
      action.rollback_possible &&
      !action.rollback_executed_at &&
      (action.action_type === 'scale_budget' || action.action_type === 'pause_campaign')
  );
  const canRollback = rollbackableActions.length > 0;

  // Get unique action types
  const actionTypes = [...new Set(actions_executed.map((a) => a.action_type))];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'rounded-xl border border-neutral-200/50',
        'bg-white/60 backdrop-blur-sm',
        'transition-all duration-200',
        'hover:bg-white/80 hover:border-neutral-200/70',
        isExpanded && 'ring-1 ring-neutral-200/50'
      )}
    >
      {/* Main content */}
      <div className="flex items-start gap-3 p-3">
        {/* Result type icon */}
        <div
          className={cn(
            'flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg',
            resultConfig.bg
          )}
        >
          <ResultIcon className={cn('h-4 w-4', resultConfig.color)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Agent name and headline */}
          <div className="flex items-center gap-2 flex-wrap">
            <Link
              href={`/agents/${agent_id}`}
              className="font-medium text-sm text-neutral-900 hover:text-blue-600 transition-colors"
            >
              {agent_name}
            </Link>
            <span className="text-xs text-neutral-400">•</span>
            <span className="text-xs text-neutral-500 capitalize">
              {entity_provider}
            </span>
          </div>

          {/* Headline */}
          <p className="text-sm text-neutral-600 mt-0.5 line-clamp-2">
            {headline}
          </p>

          {/* Action badges (if any) */}
          {actionTypes.length > 0 && (
            <div className="flex items-center gap-1.5 mt-2">
              {actionTypes.map((type) => {
                const ActionIcon = ACTION_ICONS[type] || Bot;
                return (
                  <div
                    key={type}
                    className={cn(
                      'flex items-center gap-1 px-2 py-0.5 rounded-md text-xs',
                      'bg-neutral-100 text-neutral-600'
                    )}
                  >
                    <ActionIcon className="h-3 w-3" />
                    <span className="capitalize">{type.replace('_', ' ')}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Time and actions */}
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-neutral-400">{timeAgo}</span>

            <div className="flex items-center gap-1">
              {/* View details button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onViewDetails?.(event)}
                className="h-7 px-2 text-xs text-neutral-500 hover:text-neutral-900"
              >
                <Eye className="h-3 w-3 mr-1" />
                View
              </Button>

              {/* Rollback button (only for reversible actions) */}
              {canRollback && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRollback?.(rollbackableActions[0])}
                  disabled={isRollingBack}
                  className={cn(
                    'h-7 px-2 text-xs',
                    'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
                  )}
                >
                  <RotateCcw
                    className={cn('h-3 w-3 mr-1', isRollingBack && 'animate-spin')}
                  />
                  Rollback
                </Button>
              )}

              {/* Expand button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-7 w-7 p-0 text-neutral-400 hover:text-neutral-600"
              >
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="border-t border-neutral-200/50 px-3 pb-3 pt-2"
        >
          {/* Entity info */}
          <div className="text-xs space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-neutral-500">Entity:</span>
              <span className="font-medium text-neutral-700">{entity_name}</span>
            </div>
          </div>

          {/* Actions executed */}
          {actions_executed.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">
                Actions Executed
              </p>
              <div className="space-y-2">
                {actions_executed.map((action) => {
                  const ActionIcon = ACTION_ICONS[action.action_type] || Bot;
                  const isRolledBack = !!action.rollback_executed_at;

                  return (
                    <div
                      key={action.id}
                      className={cn(
                        'flex items-center gap-2 p-2 rounded-lg text-xs',
                        'bg-neutral-50 border border-neutral-100',
                        isRolledBack && 'opacity-60'
                      )}
                    >
                      <ActionIcon className="h-3.5 w-3.5 text-neutral-500" />
                      <span className="flex-1 text-neutral-700">
                        {action.description}
                      </span>
                      {action.success ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                      ) : (
                        <AlertCircle className="h-3.5 w-3.5 text-red-500" />
                      )}
                      {isRolledBack && (
                        <span className="text-amber-600 font-medium">
                          Rolled back
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* State changes (for budget scaling) */}
          {actions_executed.some((a) => a.state_before && a.state_after) && (
            <div className="mt-3">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">
                State Changes
              </p>
              {actions_executed
                .filter((a) => a.state_before && a.state_after)
                .map((action) => (
                  <div
                    key={action.id}
                    className="flex items-center gap-2 text-xs text-neutral-600"
                  >
                    {action.action_type === 'scale_budget' && (
                      <>
                        <span>Budget:</span>
                        <span className="font-mono">
                          ${action.state_before?.budget?.toFixed(2) || 'N/A'}
                        </span>
                        <span>→</span>
                        <span className="font-mono font-medium">
                          ${action.state_after?.budget?.toFixed(2) || 'N/A'}
                        </span>
                      </>
                    )}
                    {action.action_type === 'pause_campaign' && (
                      <>
                        <span>Status:</span>
                        <span className="font-mono">
                          {action.state_before?.status || 'N/A'}
                        </span>
                        <span>→</span>
                        <span className="font-mono font-medium">
                          {action.state_after?.status || 'PAUSED'}
                        </span>
                      </>
                    )}
                  </div>
                ))}
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}

export default NotificationItem;
