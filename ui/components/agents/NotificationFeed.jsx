/**
 * NotificationFeed - Agent activity feed with infinite scroll
 * ===========================================================
 *
 * WHAT: Displays actionable agent events (triggers + errors) across workspace
 * WHY: Users need real-time visibility into what agents are doing, without noise
 *
 * FEATURES:
 * - Infinite scroll with cursor-based pagination
 * - Filter tabs: All (triggers+errors) | Triggers | Errors
 * - Real-time updates (when mounted)
 * - Rollback capability for reversible actions
 *
 * DESIGN:
 * - "All" tab shows only actionable events (triggered + error), NOT condition_not_met logs
 * - Condition evaluation logs belong in the individual agent's detail page Events tab
 * - ScrollArea from shadcn for smooth scrolling
 * - AnimatePresence for fade-in animations
 * - Loading skeleton states
 *
 * REFERENCES:
 * - GET /v1/agents/events endpoint
 * - ui/components/agents/NotificationItem.jsx
 * - ui/app/(dashboard)/agents/page.jsx
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Loader2, Bell, Zap, AlertCircle, RefreshCw } from 'lucide-react';
import { NotificationItem } from './NotificationItem';
import { fetchWorkspaceAgentEvents, rollbackAgentAction } from '@/lib/api';

/**
 * Filter options for the activity feed
 *
 * NOTE: 'all' now maps to 'triggered' on the backend because:
 * - "Condition not met" logs are debug-level noise for the workspace feed
 * - Users care about actionable events: triggers (actions executed) and errors
 * - Detailed evaluation logs are available on individual agent detail pages
 */
const FILTER_OPTIONS = [
  { id: 'all', label: 'All', icon: Bell },
  { id: 'triggered', label: 'Triggers', icon: Zap },
  { id: 'error', label: 'Errors', icon: AlertCircle },
];

/**
 * NotificationFeed component
 *
 * @param {Object} props
 * @param {string} props.workspaceId - Workspace UUID
 * @param {number} props.maxHeight - Max height of the scroll area (default 400)
 * @param {Function} props.onEventClick - Callback when an event is clicked
 */
export function NotificationFeed({
  workspaceId,
  maxHeight = 400,
  onEventClick,
}) {
  const router = useRouter();
  const scrollRef = useRef(null);

  // State
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [rollingBackId, setRollingBackId] = useState(null);

  /**
   * Fetch events from API
   */
  const fetchEvents = useCallback(async (cursor = null, append = false) => {
    try {
      if (cursor) {
        setIsLoadingMore(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      // 'all' now fetches 'triggered' events only (actionable events)
      // This filters out "condition_not_met" noise from the workspace feed
      // Users can view all evaluation logs on individual agent detail pages
      const result = await fetchWorkspaceAgentEvents({
        workspaceId,
        resultType: filter === 'all' ? 'triggered' : filter,
        limit: 20,
        cursor,
      });

      if (append) {
        setEvents((prev) => [...prev, ...result.events]);
      } else {
        setEvents(result.events);
      }

      setNextCursor(result.next_cursor);
      setHasMore(!!result.next_cursor);
    } catch (err) {
      console.error('Failed to fetch agent events:', err);
      setError(err.message || 'Failed to load notifications');
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [workspaceId, filter]);

  // Initial fetch and filter changes
  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  /**
   * Handle scroll for infinite loading
   */
  const handleScroll = useCallback((e) => {
    if (!hasMore || isLoadingMore) return;

    const target = e.target;
    const scrollBottom = target.scrollHeight - target.scrollTop - target.clientHeight;

    // Load more when within 100px of bottom
    if (scrollBottom < 100) {
      fetchEvents(nextCursor, true);
    }
  }, [hasMore, isLoadingMore, nextCursor, fetchEvents]);

  /**
   * Handle rollback action
   */
  const handleRollback = async (action) => {
    if (!action || rollingBackId) return;

    try {
      setRollingBackId(action.id);
      await rollbackAgentAction({ workspaceId, actionId: action.id });

      // Refresh events to show rollback status
      await fetchEvents();
    } catch (err) {
      console.error('Failed to rollback action:', err);
      // Could show a toast here
    } finally {
      setRollingBackId(null);
    }
  };

  /**
   * Handle view details
   */
  const handleViewDetails = (event) => {
    if (onEventClick) {
      onEventClick(event);
    } else {
      // Navigate to agent detail page
      router.push(`/agents/${event.agent_id}`);
    }
  };

  /**
   * Refresh events
   */
  const handleRefresh = () => {
    fetchEvents();
  };

  // Loading skeleton with shimmer effect
  if (isLoading) {
    return (
      <div className="space-y-3">
        {/* Filter tabs skeleton */}
        <div className="flex items-center gap-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-8 w-20 rounded-lg bg-neutral-50 border border-neutral-100 animate-pulse"
            />
          ))}
        </div>

        {/* Items skeleton with more realistic shapes */}
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="p-3 rounded-xl bg-neutral-50/80 border border-neutral-100/60 animate-pulse"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-neutral-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-1/3 rounded bg-neutral-100" />
                  <div className="h-3 w-2/3 rounded bg-neutral-100/70" />
                </div>
                <div className="h-6 w-16 rounded bg-neutral-100" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <AlertCircle className="h-10 w-10 text-red-400 mb-3" />
        <p className="text-sm text-neutral-600 mb-4">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter tabs */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1">
          {FILTER_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isActive = filter === option.id;

            return (
              <Button
                key={option.id}
                variant={isActive ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setFilter(option.id)}
                className={cn(
                  'h-8 px-3 text-xs',
                  isActive
                    ? 'bg-neutral-900 text-white hover:bg-neutral-800'
                    : 'text-neutral-600 hover:text-neutral-900'
                )}
              >
                <Icon className="h-3 w-3 mr-1.5" />
                {option.label}
              </Button>
            );
          })}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          className="h-8 w-8 p-0 text-neutral-400 hover:text-neutral-600"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Events list */}
      {events.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Bell className="h-10 w-10 text-neutral-300 mb-3" />
          <p className="text-sm text-neutral-500">
            {filter === 'all'
              ? 'No triggered events yet'
              : `No ${filter === 'triggered' ? 'triggers' : 'errors'} found`}
          </p>
          {filter === 'all' && (
            <p className="text-xs text-neutral-400 mt-1">
              Agents are running — triggers will appear here when conditions are met
            </p>
          )}
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
          style={{ maxHeight }}
          onScroll={handleScroll}
        >
          <div className="space-y-2 pr-2">
            <AnimatePresence mode="popLayout">
              {events.map((event) => (
                <NotificationItem
                  key={event.id}
                  event={event}
                  onViewDetails={handleViewDetails}
                  onRollback={handleRollback}
                  isRollingBack={rollingBackId === event.actions_executed?.[0]?.id}
                />
              ))}
            </AnimatePresence>

            {/* Load more indicator */}
            {isLoadingMore && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
              </div>
            )}

            {/* End of list */}
            {!hasMore && events.length > 0 && (
              <div className="text-center py-4">
                <p className="text-xs text-neutral-400">No more notifications</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationFeed;
