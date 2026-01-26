/**
 * Agents List Page - Metricx v3.0 Design
 * ======================================
 *
 * WHAT: Premium agent list with glass morphism and award-winning design
 * WHY: Users need a beautiful, intuitive interface for managing their agents
 *
 * DESIGN PRINCIPLES:
 * - Glass morphism with backdrop blur
 * - Soft rounded cards (32px radius)
 * - Subtle animations and hover effects
 * - Centered hero layout
 * - Premium color palette
 *
 * FEATURES:
 * - Hero header with agent stats visualization
 * - Glass filter bar with search
 * - Beautiful agent cards with status badges
 * - Staggered entrance animations
 *
 * REFERENCES:
 * - Metricx v3.0 design system
 * - components/dashboard/KpiCardsModule.jsx
 */

'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { currentUser } from '@/lib/workspace';
import { fetchAgents, pauseAgent, resumeAgent } from '@/lib/api';
import {
  AgentCard,
  AgentFilters,
  AgentEmptyState,
} from '@/components/agents';
import {
  Plus,
  RefreshCw,
  Bot,
  Zap,
  Search,
  Activity,
  Sparkles,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';

/**
 * AgentsPage - Premium agent list page
 */
export default function AgentsPage() {
  const router = useRouter();

  // State
  const [workspaceId, setWorkspaceId] = useState(null);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

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

  // Fetch agents when workspace or filters change
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

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

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
    } catch (err) {
      toast.error('Failed to pause agent: ' + err.message);
    }
  };

  const handleResume = async (agentId) => {
    try {
      await resumeAgent({ workspaceId, agentId });
      toast.success('Agent resumed');
      loadAgents();
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

  const hasActiveFilters = statusFilter !== null || searchQuery.length > 0;

  // Calculate stats
  const stats = useMemo(() => {
    const totalTriggers = agents.reduce((sum, a) => sum + (a.total_triggers || 0), 0);
    const totalEvaluations = agents.reduce((sum, a) => sum + (a.total_evaluations || 0), 0);
    return {
      total: agents.length,
      active: agents.filter(a => a.status === 'active').length,
      paused: agents.filter(a => a.status === 'paused').length,
      error: agents.filter(a => a.status === 'error').length,
      totalTriggers,
      totalEvaluations,
    };
  }, [agents]);

  // Loading state with premium spinner
  if (loading && agents.length === 0) {
    return (
      <div className=" min-h-[80vh] flex items-center justify-center">
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
            onClick={loadAgents}
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
    <div className=" min-h-screen pb-12">
      {/* Hero Header */}
      <header className="flex flex-col items-center justify-center pt-8 pb-4 max-w-4xl mx-auto text-center px-4">
        {/* Live Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/50 border border-neutral-200/60 mb-6 backdrop-blur-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">
            {stats.active} Active Agents
          </span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium text-neutral-900 tracking-tighter mb-4 text-glow">
          Your AI Agents
        </h1>

        {/* Subtitle */}
        <p className="text-lg sm:text-xl text-neutral-400 font-light tracking-tight max-w-xl">
          Autonomous monitoring that watches, learns, and acts on your behalf.
        </p>

        {/* Create Agent CTA */}
        <div className="mt-8 flex items-center gap-4">
          <Button
            variant="outline"
            onClick={loadAgents}
            disabled={loading}
            className="rounded-xl border-neutral-200/60 hover:bg-white/60"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </Button>
          <Link href="/agents/new">
            <Button className="gap-2 bg-neutral-900 text-white rounded-xl px-6 py-3 hover:bg-neutral-800 hover:scale-105 transition-all duration-300 shadow-lg hover:shadow-xl">
              <Sparkles size={16} />
              Create Agent
            </Button>
          </Link>
        </div>
      </header>

      {/* Stats Cards - Premium KPI Grid */}
      {agents.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 max-w-5xl mx-auto px-4 mb-8">
          {/* Total Agents */}
          <div className="bg-white/40 glass rounded-[24px] sm:rounded-[32px] p-4 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300 cursor-default">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Total Agents</span>
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-neutral-100/80">
                <Bot size={14} className="text-neutral-600 sm:w-4 sm:h-4" />
              </div>
            </div>
            <div className="text-3xl sm:text-4xl lg:text-5xl font-medium text-neutral-900 number-display tracking-tighter">
              {stats.total}
            </div>
          </div>

          {/* Active */}
          <div className="bg-white/40 glass rounded-[24px] sm:rounded-[32px] p-4 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300 cursor-default">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Active</span>
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-emerald-500/10">
                <Activity size={14} className="text-emerald-600 sm:w-4 sm:h-4" />
              </div>
            </div>
            <div className="text-3xl sm:text-4xl lg:text-5xl font-medium text-emerald-600 number-display tracking-tighter">
              {stats.active}
            </div>
          </div>

          {/* Triggers */}
          <div className="bg-white/40 glass rounded-[24px] sm:rounded-[32px] p-4 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300 cursor-default">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Total Triggers</span>
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-amber-500/10">
                <Zap size={14} className="text-amber-600 sm:w-4 sm:h-4" />
              </div>
            </div>
            <div className="text-3xl sm:text-4xl lg:text-5xl font-medium text-amber-600 number-display tracking-tighter">
              {stats.totalTriggers.toLocaleString()}
            </div>
          </div>

          {/* Evaluations */}
          <div className="bg-white/40 glass rounded-[24px] sm:rounded-[32px] p-4 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300 cursor-default">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Evaluations</span>
              <div className="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-violet-500/10">
                <Activity size={14} className="text-violet-600 sm:w-4 sm:h-4" />
              </div>
            </div>
            <div className="text-3xl sm:text-4xl lg:text-5xl font-medium text-violet-600 number-display tracking-tighter">
              {stats.totalEvaluations >= 1000
                ? `${(stats.totalEvaluations / 1000).toFixed(1)}K`
                : stats.totalEvaluations.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Search & Filters - Glass Panel */}
      {(agents.length > 0 || hasActiveFilters) && (
        <div className="max-w-5xl mx-auto px-4 mb-8">
          <div className="bg-white/40 glass rounded-2xl border border-white/60 p-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
              {/* Search Input */}
              <div className="relative flex-1">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                  <Search className="w-4 h-4 text-neutral-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search agents..."
                  className="w-full pl-11 pr-4 py-3 bg-white/70 hover:bg-white/90 focus:bg-white rounded-xl border border-neutral-200/60 hover:border-neutral-300/60 focus:border-neutral-300 text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all duration-200"
                />
              </div>

              {/* Status Filters */}
              <div className="flex items-center gap-2 flex-wrap">
                {['all', 'active', 'paused', 'error'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status === 'all' ? null : status)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${(status === 'all' && statusFilter === null) || statusFilter === status
                      ? 'bg-neutral-900 text-white shadow-md'
                      : 'bg-white/60 text-neutral-600 hover:bg-white/80 border border-neutral-200/60'
                      }`}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                    {status !== 'all' && (
                      <span className="ml-1.5 opacity-60">
                        {stats[status] || 0}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Agent list */}
      <div className="max-w-5xl mx-auto px-4">
        {filteredAgents.length === 0 ? (
          <AgentEmptyState
            hasFilters={hasActiveFilters}
            onClearFilters={handleClearFilters}
          />
        ) : (
          <div className="space-y-4">
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
      </div>

      {/* Load more */}
      {hasMore && (
        <div className="flex justify-center mt-8">
          <Button
            variant="outline"
            onClick={() => {/* TODO: Load more */ }}
            className="rounded-xl border-neutral-200/60 hover:bg-white/60"
          >
            Load more agents
          </Button>
        </div>
      )}
    </div>
  );
}
