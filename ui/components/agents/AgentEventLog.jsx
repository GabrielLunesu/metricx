/**
 * AgentEventLog - Comprehensive evaluation event log for agent detail page
 * ========================================================================
 *
 * WHAT: Detailed log view showing all agent evaluation events with full context
 * WHY: Users and AI copilot need to understand exactly what happened:
 *      - What condition was being checked
 *      - What actual data was fetched
 *      - Why the condition passed or failed
 *      - What actions were taken
 *      - State transitions and accumulation progress
 *
 * FEATURES:
 * - Expandable event cards with full details
 * - Filter by result type (all, triggered, errors, etc.)
 * - Shows condition definition vs actual values
 * - State machine visualization
 * - Action execution details with rollback status
 *
 * DESIGN:
 * - Premium glass morphism design
 * - Collapsible sections for complex data
 * - Color-coded by result type
 * - Monospace font for technical data
 *
 * REFERENCES:
 * - GET /v1/agents/{id}/events
 * - GET /v1/agents/{id}/actions
 * - backend/app/schemas.py (AgentEvaluationEventOut)
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Activity,
  ChevronDown,
  ChevronRight,
  Zap,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Timer,
  Clock,
  Eye,
  RefreshCw,
  ArrowRight,
  Database,
  Code,
  Mail,
  DollarSign,
  StopCircle,
  Webhook,
  Undo2,
  Filter,
  Bell,
  Loader2,
} from 'lucide-react';
import { fetchAgentEvents, fetchAgentActions } from '@/lib/api';

/** Number of events to load per page */
const PAGE_SIZE = 25;

/**
 * Result type configuration for styling and icons
 */
const RESULT_TYPE_CONFIG = {
  triggered: {
    label: 'Triggered',
    icon: Zap,
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-700',
    border: 'border-emerald-200/60',
    dot: 'bg-emerald-500',
  },
  condition_met: {
    label: 'Condition Met',
    icon: CheckCircle2,
    bg: 'bg-blue-500/10',
    text: 'text-blue-700',
    border: 'border-blue-200/60',
    dot: 'bg-blue-500',
  },
  condition_not_met: {
    label: 'Not Met',
    icon: XCircle,
    bg: 'bg-neutral-500/10',
    text: 'text-neutral-600',
    border: 'border-neutral-200/60',
    dot: 'bg-neutral-400',
  },
  cooldown: {
    label: 'Cooldown',
    icon: Timer,
    bg: 'bg-purple-500/10',
    text: 'text-purple-700',
    border: 'border-purple-200/60',
    dot: 'bg-purple-500',
  },
  error: {
    label: 'Error',
    icon: AlertTriangle,
    bg: 'bg-red-500/10',
    text: 'text-red-700',
    border: 'border-red-200/60',
    dot: 'bg-red-500',
  },
};

/**
 * Action type configuration
 */
const ACTION_CONFIG = {
  email: { icon: Mail, color: 'text-blue-500', bg: 'bg-blue-500/10', label: 'Email' },
  scale_budget: { icon: DollarSign, color: 'text-emerald-500', bg: 'bg-emerald-500/10', label: 'Scale Budget' },
  pause_campaign: { icon: StopCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Pause Campaign' },
  webhook: { icon: Webhook, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Webhook' },
};

/**
 * Filter options for the event log
 */
const FILTER_OPTIONS = [
  { id: 'all', label: 'All Events', icon: Activity },
  { id: 'triggered', label: 'Triggered', icon: Zap },
  { id: 'condition_met', label: 'Condition Met', icon: CheckCircle2 },
  { id: 'condition_not_met', label: 'Not Met', icon: XCircle },
  { id: 'error', label: 'Errors', icon: AlertTriangle },
];

/**
 * AgentEventLog - Main component
 *
 * @param {Object} props
 * @param {string} props.workspaceId - Workspace UUID
 * @param {string} props.agentId - Agent UUID
 * @param {Object} props.agent - Agent data for condition reference
 */
export function AgentEventLog({ workspaceId, agentId, agent }) {
  const scrollRef = useRef(null);

  // Events state with pagination
  const [events, setEvents] = useState([]);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [expandedEvents, setExpandedEvents] = useState(new Set());

  // Pagination state
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  /**
   * Fetch initial events and actions from API
   */
  const loadData = useCallback(async () => {
    if (!workspaceId || !agentId) return;

    setLoading(true);
    setError(null);
    setOffset(0);

    try {
      // Fetch first page of events
      const eventsResult = await fetchAgentEvents({
        workspaceId,
        agentId,
        result_type: filter === 'all' ? null : filter,
        limit: PAGE_SIZE,
        offset: 0,
      });

      const eventsList = eventsResult.events || eventsResult.items || [];
      const totalCount = eventsResult.total || eventsList.length;

      setEvents(eventsList);
      setTotal(totalCount);
      setHasMore(eventsList.length >= PAGE_SIZE && eventsList.length < totalCount);
      setOffset(eventsList.length);

      // Fetch all actions to map to events (actions are typically fewer)
      const actionsResult = await fetchAgentActions({
        workspaceId,
        agentId,
        limit: 500,
      });
      setActions(actionsResult.items || []);
    } catch (err) {
      console.error('Failed to fetch agent data:', err);
      setError(err.message || 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, agentId, filter]);

  /**
   * Load more events (pagination)
   */
  const loadMore = useCallback(async () => {
    if (!workspaceId || !agentId || loadingMore || !hasMore) return;

    setLoadingMore(true);

    try {
      const eventsResult = await fetchAgentEvents({
        workspaceId,
        agentId,
        result_type: filter === 'all' ? null : filter,
        limit: PAGE_SIZE,
        offset: offset,
      });

      const newEvents = eventsResult.events || eventsResult.items || [];
      const totalCount = eventsResult.total || (offset + newEvents.length);

      setEvents(prev => [...prev, ...newEvents]);
      setTotal(totalCount);
      setOffset(prev => prev + newEvents.length);
      setHasMore(newEvents.length >= PAGE_SIZE && (offset + newEvents.length) < totalCount);
    } catch (err) {
      console.error('Failed to load more events:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [workspaceId, agentId, filter, offset, loadingMore, hasMore]);

  /**
   * Handle scroll for infinite loading
   */
  const handleScroll = useCallback((e) => {
    if (!hasMore || loadingMore) return;

    const target = e.target;
    const scrollBottom = target.scrollHeight - target.scrollTop - target.clientHeight;

    // Load more when within 100px of bottom
    if (scrollBottom < 100) {
      loadMore();
    }
  }, [hasMore, loadingMore, loadMore]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /**
   * Toggle event expansion
   */
  const toggleExpanded = (eventId) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  /**
   * Get actions for a specific event
   */
  const getActionsForEvent = (eventId) => {
    return actions.filter(a => a.evaluation_event_id === eventId);
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="bg-white/40 rounded-[20px] border border-white/60 p-5"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-neutral-100" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-1/3 bg-neutral-100 rounded" />
                <div className="h-3 w-2/3 bg-neutral-100/70 rounded" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="h-10 w-10 text-red-400 mb-3" />
        <p className="text-sm text-neutral-600 mb-4">{error}</p>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full animate-fade-in-up">
      {/* Filter tabs */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-1 p-1 bg-white/40 glass rounded-xl border border-white/60">
          {FILTER_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isActive = filter === option.id;
            // Show total count for active filter, loaded count for others
            const displayCount = isActive && option.id === 'all'
              ? total
              : (option.id === 'all' ? events.length : events.filter(e => e.result_type === option.id).length);

            return (
              <button
                key={option.id}
                onClick={() => setFilter(option.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all',
                  isActive
                    ? 'bg-neutral-900 text-white'
                    : 'text-neutral-600 hover:bg-white/60 hover:text-neutral-900'
                )}
              >
                <Icon size={14} />
                {option.label}
                {displayCount > 0 && (
                  <span className={cn(
                    'px-1.5 py-0.5 rounded text-[10px]',
                    isActive ? 'bg-white/20' : 'bg-neutral-100'
                  )}>
                    {displayCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          {/* Show loaded/total count */}
          {total > 0 && (
            <span className="text-xs text-neutral-400">
              {events.length} of {total} loaded
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            className="rounded-xl border-neutral-200/60 hover:bg-white/60"
          >
            <RefreshCw size={14} className="mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Events list with infinite scroll */}
      {events.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-20 h-20 rounded-[24px] bg-white/40 glass border border-white/60 flex items-center justify-center mb-6">
            <Activity size={32} className="text-neutral-400" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900 mb-3">
            No {filter === 'all' ? '' : filter.replace('_', ' ')} events yet
          </h3>
          <p className="text-neutral-500 max-w-md">
            Events will appear here after the agent runs evaluations.
            Use the Test button to trigger a manual evaluation.
          </p>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
          style={{ maxHeight: 'calc(100vh - 400px)' }}
          onScroll={handleScroll}
        >
          <div className="space-y-3 pr-2">
            {events.map((event, idx) => (
              <EventCard
                key={event.id}
                event={event}
                actions={getActionsForEvent(event.id)}
                isExpanded={expandedEvents.has(event.id)}
                onToggle={() => toggleExpanded(event.id)}
                agent={agent}
                index={idx}
              />
            ))}

            {/* Loading more indicator */}
            {loadingMore && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-neutral-400 mr-2" />
                <span className="text-sm text-neutral-500">Loading more events...</span>
              </div>
            )}

            {/* End of list */}
            {!hasMore && events.length > 0 && (
              <div className="text-center py-6 border-t border-neutral-100 mt-4">
                <p className="text-xs text-neutral-400">
                  All {total} events loaded
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * EventCard - Individual event with expandable details
 */
function EventCard({ event, actions, isExpanded, onToggle, agent, index }) {
  const config = RESULT_TYPE_CONFIG[event.result_type] || RESULT_TYPE_CONFIG.condition_not_met;
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'bg-white/40 glass rounded-[20px] border overflow-hidden transition-all duration-200',
        isExpanded ? 'border-neutral-300/60' : 'border-white/60 hover:border-neutral-200/60'
      )}
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      {/* Header - always visible */}
      <button
        onClick={onToggle}
        className="w-full p-5 flex items-start justify-between gap-4 text-left hover:bg-white/30 transition-colors"
      >
        <div className="flex items-start gap-4 flex-1 min-w-0">
          {/* Icon */}
          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', config.bg)}>
            <Icon size={18} className={config.text} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={cn(
                'px-2.5 py-0.5 text-xs font-semibold rounded-lg',
                config.bg, config.text
              )}>
                {config.label}
              </span>
              <span className="text-xs text-neutral-400">
                {format(new Date(event.evaluated_at), 'MMM d, HH:mm:ss')}
              </span>
              <span className="text-xs text-neutral-300">
                ({formatDistanceToNow(new Date(event.evaluated_at), { addSuffix: true })})
              </span>
            </div>
            <div className="font-medium text-neutral-900 mb-1">{event.headline}</div>
            <div className="text-sm text-neutral-500">
              {event.entity_name}
              <span className="mx-1.5 text-neutral-300">•</span>
              <span className="capitalize">{event.entity_provider}</span>
              {actions.length > 0 && (
                <>
                  <span className="mx-1.5 text-neutral-300">•</span>
                  <span className="text-emerald-600 font-medium">{actions.length} action(s)</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Expand indicator */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-xs text-neutral-400 bg-neutral-100/50 px-2 py-1 rounded-lg">
            {event.evaluation_duration_ms}ms
          </div>
          {isExpanded ? (
            <ChevronDown size={18} className="text-neutral-400" />
          ) : (
            <ChevronRight size={18} className="text-neutral-400" />
          )}
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="border-t border-neutral-200/30 p-5 space-y-5 bg-white/20">
          {/* Summary */}
          {event.summary && (
            <div className="p-4 bg-neutral-900/5 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Bell size={12} />
                Summary
              </div>
              <p className="text-sm text-neutral-700">{event.summary}</p>
            </div>
          )}

          {/* Condition Evaluation */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Condition Definition */}
            <div className="p-4 bg-white/50 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Eye size={12} />
                Condition Checked
              </div>
              <div className="bg-neutral-900/5 rounded-lg p-3 overflow-auto max-h-32">
                <pre className="text-xs text-neutral-600 font-mono whitespace-pre-wrap">
                  {JSON.stringify(event.condition_definition, null, 2)}
                </pre>
              </div>
            </div>

            {/* Actual Values */}
            <div className="p-4 bg-white/50 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Database size={12} />
                Actual Values
              </div>
              <div className="bg-neutral-900/5 rounded-lg p-3 overflow-auto max-h-32">
                <pre className="text-xs text-neutral-600 font-mono whitespace-pre-wrap">
                  {JSON.stringify(event.condition_inputs, null, 2)}
                </pre>
              </div>
            </div>
          </div>

          {/* Condition Result */}
          <div className="p-4 bg-white/50 rounded-xl">
            <div className="text-xs text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Code size={12} />
              Condition Result
            </div>
            <div className="flex items-center gap-3">
              <span className={cn(
                'px-3 py-1 rounded-lg text-sm font-semibold',
                event.condition_result
                  ? 'bg-emerald-500/10 text-emerald-700'
                  : 'bg-neutral-500/10 text-neutral-600'
              )}>
                {event.condition_result ? 'TRUE' : 'FALSE'}
              </span>
              {event.condition_explanation && (
                <span className="text-sm text-neutral-600">{event.condition_explanation}</span>
              )}
            </div>
          </div>

          {/* State Transition */}
          {(event.state_before || event.state_after) && (
            <div className="p-4 bg-white/50 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Activity size={12} />
                State Transition
              </div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 bg-neutral-100 rounded-lg text-sm font-medium text-neutral-700 capitalize">
                  {event.state_before || 'unknown'}
                </span>
                <ArrowRight size={16} className="text-neutral-400" />
                <span className={cn(
                  'px-3 py-1 rounded-lg text-sm font-medium capitalize',
                  event.state_after === 'triggered' && 'bg-emerald-500/10 text-emerald-700',
                  event.state_after === 'accumulating' && 'bg-amber-500/10 text-amber-700',
                  event.state_after === 'watching' && 'bg-blue-500/10 text-blue-700',
                  event.state_after === 'cooldown' && 'bg-purple-500/10 text-purple-700',
                  event.state_after === 'error' && 'bg-red-500/10 text-red-700',
                  !['triggered', 'accumulating', 'watching', 'cooldown', 'error'].includes(event.state_after) && 'bg-neutral-100 text-neutral-700'
                )}>
                  {event.state_after || 'unknown'}
                </span>
              </div>
              {event.state_transition_reason && (
                <p className="text-sm text-neutral-500 mt-2">{event.state_transition_reason}</p>
              )}
            </div>
          )}

          {/* Accumulation */}
          {(event.accumulation_before || event.accumulation_after) && (
            <div className="p-4 bg-white/50 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Timer size={12} />
                Accumulation Progress
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-neutral-400 mb-1">Before</div>
                  <div className="bg-neutral-900/5 rounded-lg p-2 overflow-auto">
                    <pre className="text-xs text-neutral-600 font-mono">
                      {JSON.stringify(event.accumulation_before, null, 2)}
                    </pre>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-neutral-400 mb-1">After</div>
                  <div className="bg-neutral-900/5 rounded-lg p-2 overflow-auto">
                    <pre className="text-xs text-neutral-600 font-mono">
                      {JSON.stringify(event.accumulation_after, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
              {event.accumulation_explanation && (
                <p className="text-sm text-neutral-500 mt-2">{event.accumulation_explanation}</p>
              )}
            </div>
          )}

          {/* Trigger Decision */}
          {event.trigger_explanation && (
            <div className="p-4 bg-white/50 rounded-xl">
              <div className="text-xs text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Zap size={12} />
                Trigger Decision
              </div>
              <div className="flex items-center gap-3">
                <span className={cn(
                  'px-3 py-1 rounded-lg text-sm font-semibold',
                  event.should_trigger
                    ? 'bg-emerald-500/10 text-emerald-700'
                    : 'bg-neutral-500/10 text-neutral-600'
                )}>
                  {event.should_trigger ? 'TRIGGERED' : 'NOT TRIGGERED'}
                </span>
                <span className="text-sm text-neutral-600">{event.trigger_explanation}</span>
              </div>
            </div>
          )}

          {/* Actions Executed */}
          {actions.length > 0 && (
            <div className="p-4 bg-emerald-500/5 rounded-xl border border-emerald-200/40">
              <div className="text-xs text-emerald-700 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Zap size={12} />
                Actions Executed ({actions.length})
              </div>
              <div className="space-y-2">
                {actions.map((action) => {
                  const actionConfig = ACTION_CONFIG[action.action_type] || ACTION_CONFIG.webhook;
                  const ActionIcon = actionConfig.icon;
                  return (
                    <div
                      key={action.id}
                      className="flex items-center justify-between p-3 bg-white/60 rounded-xl"
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', actionConfig.bg)}>
                          <ActionIcon size={14} className={actionConfig.color} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-neutral-900 text-sm">
                              {actionConfig.label}
                            </span>
                            <span className={cn(
                              'px-2 py-0.5 text-xs font-semibold rounded',
                              action.success
                                ? 'bg-emerald-500/10 text-emerald-700'
                                : 'bg-red-500/10 text-red-700'
                            )}>
                              {action.success ? 'Success' : 'Failed'}
                            </span>
                            {action.rollback_executed_at && (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-700 flex items-center gap-1">
                                <Undo2 size={10} />
                                Rolled Back
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-neutral-500 mt-0.5">{action.description}</p>
                        </div>
                      </div>
                      <div className="text-xs text-neutral-400">
                        {action.duration_ms}ms
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Raw Entity Data (collapsible) */}
          {event.entity_snapshot && Object.keys(event.entity_snapshot).length > 0 && (
            <details className="p-4 bg-white/50 rounded-xl">
              <summary className="text-xs text-neutral-500 uppercase tracking-wider cursor-pointer hover:text-neutral-700 flex items-center gap-1.5">
                <Database size={12} />
                Full Entity Snapshot (click to expand)
              </summary>
              <div className="mt-3 bg-neutral-900/5 rounded-lg p-3 overflow-auto max-h-64">
                <pre className="text-xs text-neutral-600 font-mono whitespace-pre-wrap">
                  {JSON.stringify(event.entity_snapshot, null, 2)}
                </pre>
              </div>
            </details>
          )}

          {/* Observations */}
          {event.observations && Object.keys(event.observations).length > 0 && (
            <details className="p-4 bg-white/50 rounded-xl">
              <summary className="text-xs text-neutral-500 uppercase tracking-wider cursor-pointer hover:text-neutral-700 flex items-center gap-1.5">
                <Eye size={12} />
                Observations (click to expand)
              </summary>
              <div className="mt-3 bg-neutral-900/5 rounded-lg p-3 overflow-auto max-h-64">
                <pre className="text-xs text-neutral-600 font-mono whitespace-pre-wrap">
                  {JSON.stringify(event.observations, null, 2)}
                </pre>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

export default AgentEventLog;
