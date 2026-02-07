/**
 * Agents Dashboard Page - Metricx v3.0 Design
 * ===========================================
 *
 * WHAT: Dashboard-style agent management with stats and notification feed
 * WHY: Users need quick overview and real-time visibility into agent activity
 *
 * LAYOUT:
 * - Top row: Stats card (left) + Notification feed (right)
 * - Bottom row: Full-width Agents grid
 *
 * FEATURES:
 * - Real-time stats (active agents, triggers, evaluations, errors)
 * - Notification feed with infinite scroll
 * - Fullscreen notification modal
 * - Agent cards with pause/resume actions
 * - Rollback capability for reversible actions
 *
 * REFERENCES:
 * - GET /v1/agents/stats endpoint
 * - GET /v1/agents/events endpoint
 * - components/agents/* components
 */

'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { currentUser } from '@/lib/workspace';
import { fetchAgents, fetchAgentStats, pauseAgent, resumeAgent } from '@/lib/api';
import {
  AgentCard,
  AgentStatsGrid,
  AgentEmptyState,
  NotificationFeed,
  NotificationFeedFullscreen,
} from '@/components/agents';
import {
  Plus,
  RefreshCw,
  Maximize2,
  Search,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';

/**
 * AgentsPage - Dashboard-style agent management
 */
export default function AgentsPage() {
  const router = useRouter();

  // State
  const [workspaceId, setWorkspaceId] = useState(null);
  const [agents, setAgents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  // Fullscreen notification modal
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Pagination
  const [hasMore, setHasMore] = useState(false);

  // Get current user/workspace
  useEffect(() => {
    currentUser()
      .then(user => {
        if (user?.workspace_id) {
          setWorkspaceId(user.workspace_id);
        } else {
          setError('No workspace found. Please complete onboarding.');
        }
      })
      .catch(err => {
        console.error('Failed to get current user:', err);
        setError('Failed to load user context');
      });
  }, []);

  // Fetch agents
  const loadAgents = useCallback(async () => {
    if (!workspaceId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await fetchAgents({
        workspaceId,
        status: statusFilter,
        limit: 50,
        offset: 0
      });

      setAgents(result.items || []);
      setHasMore((result.meta?.offset || 0) + (result.items?.length || 0) < (result.meta?.total || 0));
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError(err.message || 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, statusFilter]);

  // Fetch stats
  const loadStats = useCallback(async () => {
    if (!workspaceId) return;

    setStatsLoading(true);

    try {
      const result = await fetchAgentStats({ workspaceId });
      setStats(result);
    } catch (err) {
      console.error('Failed to fetch agent stats:', err);
      // Don't set error for stats, just show 0s
      setStats({
        active_agents: 0,
        triggers_today: 0,
        evaluations_this_hour: 0,
        errors_today: 0,
      });
    } finally {
      setStatsLoading(false);
    }
  }, [workspaceId]);

  // Load data when workspace changes
  useEffect(() => {
    loadAgents();
    loadStats();
  }, [loadAgents, loadStats]);

  // Filter agents by search query (client-side for instant feedback)
  const filteredAgents = useMemo(() => {
    if (!searchQuery) return agents;

    const query = searchQuery.toLowerCase();
    return agents.filter(agent =>
      agent.name.toLowerCase().includes(query) ||
      agent.description?.toLowerCase().includes(query)
    );
  }, [agents, searchQuery]);

  // Handlers
  const handlePause = async (agentId) => {
    try {
      await pauseAgent({ workspaceId, agentId });
      toast.success('Agent paused');
      loadAgents();
      loadStats();
    } catch (err) {
      toast.error('Failed to pause agent: ' + err.message);
    }
  };

  const handleResume = async (agentId) => {
    try {
      await resumeAgent({ workspaceId, agentId });
      toast.success('Agent resumed');
      loadAgents();
      loadStats();
    } catch (err) {
      toast.error('Failed to resume agent: ' + err.message);
    }
  };

  const handleView = (agentId) => {
    router.push(`/agents/${agentId}`);
  };

  const handleSettings = (agentId) => {
    router.push(`/agents/${agentId}?tab=settings`);
  };

  const handleClearFilters = () => {
    setStatusFilter(null);
    setSearchQuery('');
  };

  const handleRefresh = () => {
    loadAgents();
    loadStats();
  };

  const hasActiveFilters = statusFilter !== null || searchQuery.length > 0;

  // Calculate local stats for filter counts
  const localStats = useMemo(() => ({
    total: agents.length,
    active: agents.filter(a => a.status === 'active').length,
    paused: agents.filter(a => a.status === 'paused').length,
    error: agents.filter(a => a.status === 'error').length,
  }), [agents]);

  // Loading state with premium spinner
  if (loading && agents.length === 0 && !workspaceId) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-2 border-neutral-200 rounded-full" />
            <div className="absolute inset-0 w-16 h-16 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          </div>
          <span className="text-neutral-500 text-sm font-medium">Loading agents...</span>
        </div>
      </div>
    );
  }

  // Error state with premium design
  if (error && agents.length === 0) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="bg-white/40 glass rounded-[32px] p-12 max-w-md text-center border border-white/60">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-red-100 to-red-50 flex items-center justify-center">
            <Shield className="w-10 h-10 text-red-500" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900 mb-3">
            Unable to load agents
          </h3>
          <p className="text-neutral-500 mb-8">{error}</p>
          <Button
            onClick={handleRefresh}
            className="bg-neutral-900 text-white rounded-xl px-6 py-3 hover:bg-neutral-800 transition-all"
          >
            <RefreshCw size={16} className="mr-2" />
            Try again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-16 md:pb-12 p-4 sm:p-6">
      {/* Header with Create button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-semibold text-neutral-900">Agents</h1>
          <p className="text-xs md:text-sm text-neutral-500 mt-0.5">
            Autonomous monitoring that watches, learns, and acts on your behalf
          </p>
        </div>
        <div className="flex items-center gap-2 md:gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={loading || statsLoading}
            className="rounded-xl border-neutral-200/60 hover:bg-white/60"
          >
            <RefreshCw size={16} className={(loading || statsLoading) ? 'animate-spin' : ''} />
          </Button>
          <Link href="/agents/new">
            <Button className="gap-2 bg-neutral-900 text-white rounded-xl px-4 py-2 hover:bg-neutral-800 transition-all">
              <Plus size={16} />
              Create Agent
            </Button>
          </Link>
        </div>
      </div>

      {/* Top Row: Stats + Notifications side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 mb-4 md:mb-6">
        {/* Stats Card */}
        <Card className="bg-white/60 backdrop-blur-sm border-neutral-200/40 shadow-sm">
          <CardHeader className="pb-2 pt-3 md:pt-4 px-3 md:px-5">
            <CardTitle className="text-xs md:text-sm font-semibold text-neutral-900">
              Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 md:px-5 pb-3 md:pb-5 pt-0">
            <AgentStatsGrid stats={stats} isLoading={statsLoading} />
          </CardContent>
        </Card>

        {/* Notifications Card */}
        <Card className="bg-white/60 backdrop-blur-sm border-neutral-200/40 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2 pt-3 md:pt-4 px-3 md:px-5">
            <CardTitle className="text-xs md:text-sm font-semibold text-neutral-900">
              Activity Feed
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setFullscreenOpen(true)}
              className="h-7 w-7 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100/80 rounded-lg"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="px-3 md:px-5 pb-3 md:pb-5 pt-0">
            {workspaceId && (
              <NotificationFeed
                workspaceId={workspaceId}
                maxHeight={160}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row: Agents - Full Width */}
      <Card className="bg-white/40 glass border-white/60">
        <CardHeader className="flex flex-row items-center justify-between pb-2 md:pb-3 px-3 md:px-6 pt-3 md:pt-5">
          <CardTitle className="text-sm md:text-base font-semibold text-neutral-900">
            Agents
          </CardTitle>
          <span className="text-xs text-neutral-500">
            {filteredAgents.length} {filteredAgents.length === 1 ? 'agent' : 'agents'}
          </span>
        </CardHeader>
        <CardContent className="px-2 md:px-6 pb-3 md:pb-6">
          {/* Search & Filters */}
          {(agents.length > 0 || hasActiveFilters) && (
            <div className="mb-4 md:mb-6">
              {/* Search Input */}
              <div className="relative mb-3">
                <div className="absolute left-3 md:left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                  <Search className="w-4 h-4 text-neutral-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search agents..."
                  className="w-full pl-10 md:pl-11 pr-4 py-2 md:py-2.5 bg-white/70 hover:bg-white/90 focus:bg-white rounded-xl border border-neutral-200/60 hover:border-neutral-300/60 focus:border-neutral-300 text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all duration-200"
                />
              </div>

              {/* Status Filters - scrollable on mobile */}
              <div className="flex items-center gap-1.5 md:gap-2 overflow-x-auto no-scrollbar">
                {['all', 'active', 'paused', 'error'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status === 'all' ? null : status)}
                    className={`px-2.5 md:px-3 py-1 md:py-1.5 rounded-lg text-xs md:text-sm font-medium transition-all duration-150 flex-shrink-0 ${(status === 'all' && statusFilter === null) || statusFilter === status
                      ? 'bg-neutral-900 text-white shadow-sm'
                      : 'bg-white/60 text-neutral-600 active:bg-neutral-100 border border-neutral-200/60'
                      }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                    {status !== 'all' && (
                      <span className="ml-1 md:ml-1.5 opacity-60">
                        {localStats[status] || 0}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Agent list */}
          {filteredAgents.length === 0 ? (
            <AgentEmptyState
              hasFilters={hasActiveFilters}
              onClearFilters={handleClearFilters}
            />
          ) : (
            <div className="space-y-2 md:space-y-4">
              {filteredAgents.map((agent, index) => (
                <div
                  key={agent.id}
                  className="animate-slide-up"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <AgentCard
                    agent={agent}
                    expanded={expandedId === agent.id}
                    onToggleExpand={() => setExpandedId(expandedId === agent.id ? null : agent.id)}
                    onPause={handlePause}
                    onResume={handleResume}
                    onView={handleView}
                    onSettings={handleSettings}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center mt-6">
              <Button
                variant="outline"
                onClick={() => {/* TODO: Load more */}}
                className="rounded-xl border-neutral-200/60 hover:bg-white/60"
              >
                Load more agents
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Fullscreen notification modal */}
      {workspaceId && (
        <NotificationFeedFullscreen
          open={fullscreenOpen}
          onClose={() => setFullscreenOpen(false)}
          workspaceId={workspaceId}
        />
      )}
    </div>
  );
}
