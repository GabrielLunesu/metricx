/**
 * Agent Detail Page - Metricx v3.0 Premium Design
 * ================================================
 *
 * WHAT: Premium agent detail view with glass morphism design
 * WHY: Users need a beautiful, intuitive interface to monitor agent performance
 *
 * DESIGN PRINCIPLES:
 * - Glass morphism with backdrop blur
 * - Soft rounded cards (24px-32px radius)
 * - Subtle animations and hover effects
 * - Premium color palette
 * - Award-winning visual quality
 *
 * TABS:
 * - Overview: Status, stats, current entity states
 * - Events: Evaluation event log with filtering
 * - Actions: Action execution history
 * - Settings: Agent configuration (edit)
 *
 * REFERENCES:
 * - Metricx v3.0 design system
 * - backend/app/routers/agents.py
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams, useParams } from 'next/navigation';
import Link from 'next/link';
import { formatDistanceToNow, format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { currentUser } from '@/lib/workspace';
import {
  fetchAgent,
  fetchAgentEvents,
  fetchAgentActions,
  pauseAgent,
  resumeAgent,
  testAgent,
  deleteAgent
} from '@/lib/api';
import {
  ArrowLeft,
  Play,
  Pause,
  Trash2,
  Settings,
  RefreshCw,
  Zap,
  Activity,
  Clock,
  Eye,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Bot,
  TestTube,
  Target,
  Timer,
  Sparkles,
  Shield,
  ChevronRight,
  TrendingUp,
  Mail,
  Webhook,
  DollarSign,
  StopCircle,
  Bell,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';

// Tab definitions
const TABS = [
  { id: 'overview', label: 'Overview', icon: Eye },
  { id: 'events', label: 'Events', icon: Activity },
  { id: 'actions', label: 'Actions', icon: Zap },
  { id: 'settings', label: 'Settings', icon: Settings },
];

// Result type config with premium styling
const RESULT_TYPE_CONFIG = {
  triggered: {
    label: 'Triggered',
    color: 'emerald',
    icon: Zap,
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-700',
    border: 'border-emerald-200/60',
  },
  condition_met: {
    label: 'Condition Met',
    color: 'blue',
    icon: CheckCircle2,
    bg: 'bg-blue-500/10',
    text: 'text-blue-700',
    border: 'border-blue-200/60',
  },
  condition_not_met: {
    label: 'Not Met',
    color: 'neutral',
    icon: XCircle,
    bg: 'bg-neutral-500/10',
    text: 'text-neutral-600',
    border: 'border-neutral-200/60',
  },
  cooldown: {
    label: 'Cooldown',
    color: 'purple',
    icon: Timer,
    bg: 'bg-purple-500/10',
    text: 'text-purple-700',
    border: 'border-purple-200/60',
  },
  error: {
    label: 'Error',
    color: 'red',
    icon: AlertTriangle,
    bg: 'bg-red-500/10',
    text: 'text-red-700',
    border: 'border-red-200/60',
  },
};

// State config for entity states
const STATE_CONFIG = {
  watching: { color: 'bg-blue-500', label: 'Watching', icon: Eye },
  accumulating: { color: 'bg-amber-500', label: 'Accumulating', icon: Timer },
  triggered: { color: 'bg-emerald-500', label: 'Triggered', icon: Zap },
  cooldown: { color: 'bg-purple-500', label: 'Cooldown', icon: Clock },
  error: { color: 'bg-red-500', label: 'Error', icon: AlertTriangle },
};

// Action type config
const ACTION_CONFIG = {
  email: { icon: Mail, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  scale_budget: { icon: DollarSign, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  pause_campaign: { icon: StopCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
  webhook: { icon: Webhook, color: 'text-purple-500', bg: 'bg-purple-500/10' },
};

// Status config
const STATUS_CONFIG = {
  active: { color: 'emerald', label: 'Active', dot: true },
  paused: { color: 'amber', label: 'Paused', dot: false },
  error: { color: 'red', label: 'Error', dot: false },
  draft: { color: 'neutral', label: 'Draft', dot: false },
};

/**
 * AgentDetailPage - Premium agent detail view
 */
export default function AgentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params.id;

  // State
  const [workspaceId, setWorkspaceId] = useState(null);
  const [agent, setAgent] = useState(null);
  const [events, setEvents] = useState([]);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Active tab from URL
  const activeTab = searchParams.get('tab') || 'overview';

  // Get current user/workspace
  useEffect(() => {
    currentUser()
      .then(user => {
        if (user?.workspace_id) {
          setWorkspaceId(user.workspace_id);
        } else {
          setError('No workspace found');
        }
      })
      .catch(err => {
        console.error('Failed to get current user:', err);
        setError('Failed to load user context');
      });
  }, []);

  // Fetch agent details
  const loadAgent = useCallback(async () => {
    if (!workspaceId || !agentId) return;

    setLoading(true);
    setError(null);

    try {
      const agentData = await fetchAgent({ workspaceId, agentId });
      setAgent(agentData);
    } catch (err) {
      console.error('Failed to fetch agent:', err);
      setError(err.message || 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, agentId]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  // Fetch events when Events tab is active
  useEffect(() => {
    if (activeTab === 'events' && workspaceId && agentId) {
      fetchAgentEvents({ workspaceId, agentId, limit: 50 })
        .then(result => setEvents(result.items || []))
        .catch(err => console.error('Failed to fetch events:', err));
    }
  }, [activeTab, workspaceId, agentId]);

  // Fetch actions when Actions tab is active
  useEffect(() => {
    if (activeTab === 'actions' && workspaceId && agentId) {
      fetchAgentActions({ workspaceId, agentId, limit: 50 })
        .then(result => setActions(result.items || []))
        .catch(err => console.error('Failed to fetch actions:', err));
    }
  }, [activeTab, workspaceId, agentId]);

  // Handlers
  const handlePause = async () => {
    try {
      await pauseAgent({ workspaceId, agentId });
      toast.success('Agent paused');
      loadAgent();
    } catch (err) {
      toast.error('Failed to pause agent: ' + err.message);
    }
  };

  const handleResume = async () => {
    try {
      await resumeAgent({ workspaceId, agentId });
      toast.success('Agent resumed');
      loadAgent();
    } catch (err) {
      toast.error('Failed to resume agent: ' + err.message);
    }
  };

  const handleTest = async () => {
    try {
      toast.info('Running test evaluation...');
      const result = await testAgent({ workspaceId, agentId });

      // Test is a dry run - results are returned in the response, not stored as events
      if (result.results && result.results.length > 0) {
        const metCount = result.results.filter(r => r.condition_result).length;
        const wouldTriggerCount = result.results.filter(r => r.would_trigger).length;
        toast.success(
          `Test complete: ${metCount}/${result.results.length} entities met condition, ${wouldTriggerCount} would trigger`,
          { duration: 5000 }
        );
      } else {
        toast.success('Test complete: No entities found to evaluate');
      }
    } catch (err) {
      toast.error('Test failed: ' + err.message);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this agent? This cannot be undone.')) {
      return;
    }

    try {
      await deleteAgent({ workspaceId, agentId });
      toast.success('Agent deleted');
      router.push('/agents');
    } catch (err) {
      toast.error('Failed to delete agent: ' + err.message);
    }
  };

  const setActiveTab = (tab) => {
    router.push(`/agents/${agentId}?tab=${tab}`);
  };

  // Loading state with premium spinner
  if (loading) {
    return (
      <div className=" min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-2 border-neutral-200 rounded-full" />
            <div className="absolute inset-0 w-16 h-16 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
          </div>
          <span className="text-neutral-500 text-sm font-medium">Loading agent...</span>
        </div>
      </div>
    );
  }

  // Error state with premium design
  if (error || !agent) {
    return (
      <div className=" min-h-[80vh] flex items-center justify-center px-4">
        <div className="bg-white/40 glass rounded-[32px] p-12 max-w-md text-center border border-white/60">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-red-100 to-red-50 flex items-center justify-center">
            <AlertTriangle className="w-10 h-10 text-red-500" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900 mb-3">
            {error || 'Agent not found'}
          </h3>
          <p className="text-neutral-500 mb-8">
            The agent you're looking for doesn't exist or you don't have access to it.
          </p>
          <Link href="/agents">
            <Button className="bg-neutral-900 text-white rounded-xl px-6 py-3 hover:bg-neutral-800 transition-all">
              <ArrowLeft size={16} className="mr-2" />
              Back to Agents
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[agent.status] || STATUS_CONFIG.draft;

  return (
    <div className=" min-h-screen pb-12">
      {/* Back link */}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <Link
          href="/agents"
          className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-0.5 transition-transform" />
          Back to Agents
        </Link>
      </div>

      {/* Hero Header */}
      <header className="max-w-6xl mx-auto px-4 pt-6 pb-8">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          {/* Agent identity */}
          <div className="flex items-start gap-5">
            {/* Premium icon */}
            <div className="relative flex-shrink-0">
              <div className="w-16 h-16 rounded-[20px] bg-gradient-to-br from-neutral-100 to-neutral-200 flex items-center justify-center shadow-lg">
                <Bot size={32} className="text-neutral-600" />
              </div>
              {agent.status === 'active' && (
                <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-lg bg-emerald-500 flex items-center justify-center shadow-lg">
                  <Activity size={12} className="text-white" />
                </div>
              )}
            </div>

            <div>
              {/* Status badge */}
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl sm:text-3xl font-semibold text-neutral-900 tracking-tight">
                  {agent.name}
                </h1>
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold uppercase tracking-wider',
                    statusConfig.color === 'emerald' && 'bg-emerald-500/10 text-emerald-700',
                    statusConfig.color === 'amber' && 'bg-amber-500/10 text-amber-700',
                    statusConfig.color === 'red' && 'bg-red-500/10 text-red-700',
                    statusConfig.color === 'neutral' && 'bg-neutral-500/10 text-neutral-600'
                  )}
                >
                  {statusConfig.dot && (
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  )}
                  {statusConfig.label}
                </span>
              </div>

              {agent.description && (
                <p className="text-neutral-500 text-lg font-light max-w-xl">
                  {agent.description}
                </p>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={loadAgent}
              className="rounded-xl border-neutral-200/60 hover:bg-white/60 h-11 px-4"
            >
              <RefreshCw size={16} />
            </Button>
            <Button
              variant="outline"
              onClick={handleTest}
              className="rounded-xl border-neutral-200/60 hover:bg-white/60 gap-2 h-11 px-5"
            >
              <TestTube size={16} />
              Test
            </Button>
            {agent.status === 'active' ? (
              <Button
                variant="outline"
                onClick={handlePause}
                className="rounded-xl border-amber-200/60 text-amber-700 hover:bg-amber-500/10 gap-2 h-11 px-5"
              >
                <Pause size={16} />
                Pause
              </Button>
            ) : (
              <Button
                onClick={handleResume}
                className="rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 gap-2 h-11 px-5"
              >
                <Play size={16} />
                Resume
              </Button>
            )}
            <Button
              variant="outline"
              onClick={handleDelete}
              className="rounded-xl border-red-200/60 text-red-600 hover:bg-red-500/10 h-11 px-4"
            >
              <Trash2 size={16} />
            </Button>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {agent.status === 'error' && agent.error_message && (
        <div className="max-w-6xl mx-auto px-4 mb-6">
          <div className="bg-red-500/5 glass rounded-2xl border border-red-200/60 p-5">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle size={20} className="text-red-600" />
              </div>
              <div>
                <div className="font-semibold text-red-900 mb-1">Agent Error</div>
                <div className="text-sm text-red-700">{agent.error_message}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Premium Tab Navigation */}
      <div className="max-w-6xl mx-auto px-4 mb-8">
        <div className="bg-white/40 glass rounded-2xl border border-white/60 p-2">
          <div className="flex items-center gap-2">
            {TABS.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-neutral-900 text-white shadow-lg'
                      : 'text-neutral-600 hover:bg-white/60 hover:text-neutral-900'
                  )}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <div className="max-w-6xl mx-auto px-4">
        {activeTab === 'overview' && <OverviewTab agent={agent} />}
        {activeTab === 'events' && <EventsTab events={events} />}
        {activeTab === 'actions' && <ActionsTab actions={actions} />}
        {activeTab === 'settings' && <SettingsTab agent={agent} onUpdate={loadAgent} />}
      </div>
    </div>
  );
}

/**
 * OverviewTab - Agent status and stats with premium design
 */
function OverviewTab({ agent }) {
  const {
    entities_count = 0,
    total_evaluations = 0,
    total_triggers = 0,
    last_evaluated_at,
    last_triggered_at,
    condition,
    accumulation,
    trigger_mode,
    actions: agentActions = [],
    scope,
    current_states = []
  } = agent;

  // Format times
  const lastEvaluatedText = last_evaluated_at
    ? formatDistanceToNow(new Date(last_evaluated_at), { addSuffix: true })
    : 'Never';
  const lastTriggeredText = last_triggered_at
    ? formatDistanceToNow(new Date(last_triggered_at), { addSuffix: true })
    : 'Never';

  // Count states
  const stateBreakdown = current_states.reduce((acc, state) => {
    acc[state.state] = (acc[state.state] || 0) + 1;
    return acc;
  }, {});

  // Get unique action types
  const actionTypes = [...new Set(agentActions?.map(a => a.type) || [])];

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Stats KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Entities Watched */}
        <div className="bg-white/40 glass rounded-[24px] p-5 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300">
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Entities</span>
            <div className="p-2 rounded-xl bg-blue-500/10">
              <Target size={16} className="text-blue-600" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl font-medium text-neutral-900 number-display tracking-tighter">
            {entities_count}
          </div>
        </div>

        {/* Total Evaluations */}
        <div className="bg-white/40 glass rounded-[24px] p-5 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300">
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Evaluations</span>
            <div className="p-2 rounded-xl bg-violet-500/10">
              <Activity size={16} className="text-violet-600" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl font-medium text-violet-600 number-display tracking-tighter">
            {total_evaluations >= 1000
              ? `${(total_evaluations / 1000).toFixed(1)}K`
              : total_evaluations.toLocaleString()}
          </div>
        </div>

        {/* Total Triggers */}
        <div className="bg-white/40 glass rounded-[24px] p-5 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300">
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Triggers</span>
            <div className="p-2 rounded-xl bg-emerald-500/10">
              <Zap size={16} className="text-emerald-600" />
            </div>
          </div>
          <div className="text-3xl sm:text-4xl font-medium text-emerald-600 number-display tracking-tighter">
            {total_triggers}
          </div>
        </div>

        {/* Last Evaluated */}
        <div className="bg-white/40 glass rounded-[24px] p-5 sm:p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-0.5 transition-all duration-300">
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs sm:text-sm font-medium text-neutral-500 tracking-wide">Last Check</span>
            <div className="p-2 rounded-xl bg-amber-500/10">
              <Clock size={16} className="text-amber-600" />
            </div>
          </div>
          <div className="text-lg sm:text-xl font-medium text-neutral-900 tracking-tight">
            {lastEvaluatedText}
          </div>
        </div>
      </div>

      {/* Configuration Cards */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Condition Card */}
        <div className="bg-white/40 glass rounded-[24px] border border-white/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200/30">
            <h3 className="font-semibold text-neutral-900 flex items-center gap-2">
              <Eye size={18} className="text-neutral-500" />
              Condition
            </h3>
          </div>
          <div className="p-6">
            <div className="bg-neutral-900/5 rounded-xl p-4 overflow-auto max-h-48">
              <pre className="text-sm text-neutral-700 font-mono">
                {JSON.stringify(condition, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Accumulation & Actions Card */}
        <div className="bg-white/40 glass rounded-[24px] border border-white/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200/30">
            <h3 className="font-semibold text-neutral-900 flex items-center gap-2">
              <Settings size={18} className="text-neutral-500" />
              Configuration
            </h3>
          </div>
          <div className="p-6 space-y-5">
            {/* Accumulation */}
            <div className="bg-white/50 rounded-xl p-4">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Timer size={12} />
                Accumulation
              </div>
              <div className="font-semibold text-neutral-900">
                {accumulation?.required || 1} {accumulation?.unit || 'evaluations'}
              </div>
              {accumulation?.mode && (
                <div className="text-xs text-neutral-400 mt-1 capitalize">
                  {accumulation.mode} mode
                </div>
              )}
            </div>

            {/* Trigger Mode */}
            <div className="bg-white/50 rounded-xl p-4">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Zap size={12} />
                Trigger Mode
              </div>
              <div className="font-semibold text-neutral-900 capitalize">
                {trigger_mode?.mode || 'once'}
              </div>
              {trigger_mode?.cooldown_minutes && (
                <div className="text-xs text-neutral-400 mt-1">
                  {trigger_mode.cooldown_minutes} min cooldown
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="bg-white/50 rounded-xl p-4">
              <div className="text-neutral-500 text-[10px] uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Bell size={12} />
                Actions
              </div>
              <div className="flex flex-wrap gap-2">
                {actionTypes.length > 0 ? (
                  actionTypes.map(type => {
                    const config = ACTION_CONFIG[type] || { icon: Bell, color: 'text-neutral-500', bg: 'bg-neutral-500/10' };
                    const Icon = config.icon;
                    return (
                      <div
                        key={type}
                        className={cn('flex items-center gap-2 px-3 py-1.5 rounded-lg', config.bg)}
                      >
                        <Icon size={14} className={config.color} />
                        <span className="text-xs font-medium text-neutral-700 capitalize">
                          {type.replace('_', ' ')}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <span className="text-sm text-neutral-400">No actions configured</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Entity States */}
      {current_states.length > 0 && (
        <div className="bg-white/40 glass rounded-[24px] border border-white/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200/30 flex items-center justify-between">
            <h3 className="font-semibold text-neutral-900 flex items-center gap-2">
              <Target size={18} className="text-neutral-500" />
              Entity States
            </h3>
            {/* State breakdown badges */}
            <div className="flex items-center gap-2">
              {Object.entries(stateBreakdown).map(([state, count]) => {
                const config = STATE_CONFIG[state] || STATE_CONFIG.watching;
                return (
                  <div
                    key={state}
                    className="flex items-center gap-1.5 px-2 py-1 bg-white/60 rounded-lg"
                  >
                    <div className={cn('w-2 h-2 rounded-full', config.color)} />
                    <span className="text-xs font-medium text-neutral-700">
                      {count} {config.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="p-4">
            <div className="space-y-2">
              {current_states.slice(0, 10).map((state, idx) => {
                const config = STATE_CONFIG[state.state] || STATE_CONFIG.watching;
                const Icon = config.icon;
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-white/50 rounded-xl hover:bg-white/80 transition-colors"
                  >
                    <span className="text-sm font-medium text-neutral-700 truncate">
                      {state.entity_name || state.entity_id}
                    </span>
                    <div className={cn(
                      'flex items-center gap-2 px-3 py-1 rounded-lg',
                      config.color === 'bg-blue-500' && 'bg-blue-500/10',
                      config.color === 'bg-amber-500' && 'bg-amber-500/10',
                      config.color === 'bg-emerald-500' && 'bg-emerald-500/10',
                      config.color === 'bg-purple-500' && 'bg-purple-500/10',
                      config.color === 'bg-red-500' && 'bg-red-500/10'
                    )}>
                      <div className={cn('w-2 h-2 rounded-full', config.color)} />
                      <span className="text-xs font-semibold capitalize">
                        {config.label}
                      </span>
                    </div>
                  </div>
                );
              })}
              {current_states.length > 10 && (
                <div className="text-center py-3">
                  <span className="text-sm text-neutral-500">
                    +{current_states.length - 10} more entities
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Quick Stats Footer */}
      <div className="flex items-center justify-center gap-8 text-sm text-neutral-500">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-amber-500" />
          <span>Runs every 15 minutes</span>
        </div>
        <span className="text-neutral-300">•</span>
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-blue-500" />
          <span>Last triggered: {lastTriggeredText}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * EventsTab - Evaluation event log with premium design
 */
function EventsTab({ events }) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in-up">
        <div className="w-20 h-20 rounded-[24px] bg-white/40 glass border border-white/60 flex items-center justify-center mb-6">
          <Activity size={32} className="text-neutral-400" />
        </div>
        <h3 className="text-xl font-semibold text-neutral-900 mb-3">
          No evaluation events yet
        </h3>
        <p className="text-neutral-500 max-w-md">
          Events will appear here after the agent runs its first evaluation. Use the Test button to trigger a manual evaluation.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in-up">
      {events.map((event, idx) => {
        const config = RESULT_TYPE_CONFIG[event.result_type] || RESULT_TYPE_CONFIG.condition_not_met;
        const Icon = config.icon;
        return (
          <div
            key={event.id}
            className="bg-white/40 glass rounded-[20px] border border-white/60 overflow-hidden hover:bg-white/60 transition-all duration-200"
            style={{ animationDelay: `${idx * 0.03}s` }}
          >
            <div className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 flex-1 min-w-0">
                  {/* Icon */}
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', config.bg)}>
                    <Icon size={18} className={config.text} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn(
                        'px-2.5 py-0.5 text-xs font-semibold rounded-lg',
                        config.bg, config.text
                      )}>
                        {config.label}
                      </span>
                      <span className="text-xs text-neutral-400">
                        {format(new Date(event.evaluated_at), 'MMM d, HH:mm:ss')}
                      </span>
                    </div>
                    <div className="font-medium text-neutral-900 mb-1">{event.headline}</div>
                    <div className="text-sm text-neutral-500">
                      {event.entity_name}
                      <span className="mx-1.5 text-neutral-300">•</span>
                      <span className="capitalize">{event.entity_provider}</span>
                    </div>
                  </div>
                </div>

                {/* Duration */}
                <div className="text-xs text-neutral-400 bg-neutral-100/50 px-2 py-1 rounded-lg">
                  {event.evaluation_duration_ms}ms
                </div>
              </div>

              {/* Explanation */}
              {event.condition_explanation && (
                <div className="mt-4 p-3 bg-neutral-900/5 rounded-xl">
                  <p className="text-sm text-neutral-600">{event.condition_explanation}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * ActionsTab - Action execution history with premium design
 */
function ActionsTab({ actions }) {
  if (actions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in-up">
        <div className="w-20 h-20 rounded-[24px] bg-white/40 glass border border-white/60 flex items-center justify-center mb-6">
          <Zap size={32} className="text-neutral-400" />
        </div>
        <h3 className="text-xl font-semibold text-neutral-900 mb-3">
          No actions executed yet
        </h3>
        <p className="text-neutral-500 max-w-md">
          Actions will appear here when the agent triggers. This includes emails sent, budgets scaled, and campaigns paused.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in-up">
      {actions.map((action, idx) => {
        const actionConfig = ACTION_CONFIG[action.action_type] || ACTION_CONFIG.webhook;
        const Icon = actionConfig.icon;
        return (
          <div
            key={action.id}
            className="bg-white/40 glass rounded-[20px] border border-white/60 overflow-hidden hover:bg-white/60 transition-all duration-200"
            style={{ animationDelay: `${idx * 0.03}s` }}
          >
            <div className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 flex-1 min-w-0">
                  {/* Icon with success/fail indicator */}
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 relative',
                    actionConfig.bg
                  )}>
                    <Icon size={18} className={actionConfig.color} />
                    {action.success ? (
                      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full flex items-center justify-center">
                        <CheckCircle2 size={10} className="text-white" />
                      </div>
                    ) : (
                      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                        <XCircle size={10} className="text-white" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-neutral-900 capitalize">
                        {action.action_type.replace('_', ' ')}
                      </span>
                      <span className={cn(
                        'px-2 py-0.5 text-xs font-semibold rounded-lg',
                        action.success
                          ? 'bg-emerald-500/10 text-emerald-700'
                          : 'bg-red-500/10 text-red-700'
                      )}>
                        {action.success ? 'Success' : 'Failed'}
                      </span>
                      <span className="text-xs text-neutral-400">
                        {format(new Date(action.executed_at), 'MMM d, HH:mm:ss')}
                      </span>
                    </div>
                    <div className="text-sm text-neutral-600">{action.description}</div>
                    {action.error && (
                      <div className="mt-2 p-2 bg-red-500/5 rounded-lg text-sm text-red-600">
                        {action.error}
                      </div>
                    )}
                  </div>
                </div>

                {/* Duration */}
                <div className="text-xs text-neutral-400 bg-neutral-100/50 px-2 py-1 rounded-lg">
                  {action.duration_ms}ms
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * SettingsTab - Agent configuration with premium design
 */
function SettingsTab({ agent, onUpdate }) {
  const copyConfig = () => {
    navigator.clipboard.writeText(JSON.stringify(agent, null, 2));
    toast.success('Configuration copied to clipboard');
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Coming Soon Notice */}
      <div className="bg-gradient-to-r from-violet-500/5 to-blue-500/5 glass rounded-[24px] border border-white/60 p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 flex items-center justify-center flex-shrink-0">
            <Sparkles size={24} className="text-violet-600" />
          </div>
          <div>
            <h3 className="font-semibold text-neutral-900 mb-1">
              Visual Editor Coming Soon
            </h3>
            <p className="text-sm text-neutral-600">
              A beautiful visual editor for configuring your agent is in development.
              For now, you can view the raw configuration below.
            </p>
          </div>
        </div>
      </div>

      {/* Configuration JSON */}
      <div className="bg-white/40 glass rounded-[24px] border border-white/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-200/30 flex items-center justify-between">
          <h3 className="font-semibold text-neutral-900 flex items-center gap-2">
            <Settings size={18} className="text-neutral-500" />
            Agent Configuration
          </h3>
          <Button
            variant="outline"
            size="sm"
            onClick={copyConfig}
            className="rounded-lg border-neutral-200/60 hover:bg-white/60 gap-2"
          >
            <Copy size={14} />
            Copy
          </Button>
        </div>
        <div className="p-6">
          <div className="bg-neutral-900 rounded-xl p-5 overflow-auto max-h-[500px]">
            <pre className="text-sm text-emerald-400 font-mono">
              {JSON.stringify(agent, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-red-500/5 glass rounded-[24px] border border-red-200/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-red-200/30">
          <h3 className="font-semibold text-red-900 flex items-center gap-2">
            <Shield size={18} className="text-red-500" />
            Danger Zone
          </h3>
        </div>
        <div className="p-6">
          <p className="text-sm text-red-700 mb-4">
            Once you delete an agent, all of its evaluation history and action logs will be permanently removed.
            This action cannot be undone.
          </p>
          <Button
            variant="outline"
            className="border-red-300 text-red-700 hover:bg-red-500/10 rounded-xl gap-2"
          >
            <Trash2 size={16} />
            Delete Agent
          </Button>
        </div>
      </div>
    </div>
  );
}
