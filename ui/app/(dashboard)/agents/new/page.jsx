/**
 * Create Agent Page - Premium Multi-step Wizard
 * ==============================================
 *
 * WHAT: Beautiful wizard for creating monitoring agents
 * WHY: Agent configuration is complex - a premium wizard makes it delightful
 *
 * DESIGN PRINCIPLES:
 * - Glass morphism throughout
 * - Smooth step transitions
 * - Visual feedback at every step
 * - Premium color palette
 *
 * STEPS:
 * 1. Template: Choose a starting point
 * 2. Basics: Name and description
 * 3. Scope: Platform, entity level, specific entities
 * 4. Condition: When to trigger
 * 5. Actions: What to do when triggered (with configuration)
 * 6. Review: Confirm and create
 *
 * REFERENCES:
 * - Metricx v3.0 design system
 * - backend/app/schemas.py (AgentCreate)
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { currentUser } from '@/lib/workspace';
import { createAgent, fetchEntities } from '@/lib/api';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Bot,
  Sparkles,
  Bell,
  DollarSign,
  StopCircle,
  Webhook,
  TrendingUp,
  TrendingDown,
  Shield,
  Target,
  Timer,
  Zap,
  Activity,
  CheckCircle2,
  Search,
  X,
  Plus,
  Minus,
  AlertTriangle,
  Info,
  Mail,
  Globe,
  Layers,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';

// Platform options
const PLATFORMS = [
  { value: 'all', label: 'All Platforms', icon: Globe, description: 'Monitor across all connected platforms' },
  { value: 'meta', label: 'Meta Ads', icon: () => <MetaIcon />, description: 'Facebook & Instagram ads' },
  { value: 'google', label: 'Google Ads', icon: () => <GoogleIcon />, description: 'Search, Display & YouTube' },
];

// Entity level options
const ENTITY_LEVELS = [
  { value: 'campaign', label: 'Campaigns', icon: Target, description: 'Monitor at campaign level' },
  { value: 'adset', label: 'Ad Sets', icon: Layers, description: 'Monitor ad sets / ad groups' },
  { value: 'ad', label: 'Ads', icon: Activity, description: 'Monitor individual ads' },
];

// Available metrics for conditions
const METRICS = [
  { value: 'roas', label: 'ROAS', description: 'Return on ad spend', icon: TrendingUp, format: 'number' },
  { value: 'spend', label: 'Spend', description: 'Total spend ($)', icon: DollarSign, format: 'currency' },
  { value: 'revenue', label: 'Revenue', description: 'Total revenue ($)', icon: DollarSign, format: 'currency' },
  { value: 'cpc', label: 'CPC', description: 'Cost per click ($)', icon: Target, format: 'currency' },
  { value: 'cpm', label: 'CPM', description: 'Cost per 1000 impressions', icon: Activity, format: 'currency' },
  { value: 'ctr', label: 'CTR', description: 'Click-through rate (%)', icon: Activity, format: 'percent' },
  { value: 'conversions', label: 'Conversions', description: 'Total conversions', icon: CheckCircle2, format: 'number' },
  { value: 'cpa', label: 'CPA', description: 'Cost per acquisition ($)', icon: DollarSign, format: 'currency' },
  { value: 'impressions', label: 'Impressions', description: 'Total impressions', icon: Activity, format: 'number' },
  { value: 'clicks', label: 'Clicks', description: 'Total clicks', icon: Target, format: 'number' },
];

// Available operators
const OPERATORS = [
  { value: 'gt', label: '>', description: 'Greater than' },
  { value: 'gte', label: '≥', description: 'Greater than or equal' },
  { value: 'lt', label: '<', description: 'Less than' },
  { value: 'lte', label: '≤', description: 'Less than or equal' },
  { value: 'eq', label: '=', description: 'Equal to' },
];

// Action types with configuration options
const ACTION_TYPES = [
  {
    value: 'email',
    label: 'Send Email',
    icon: Mail,
    color: 'blue',
    description: 'Get notified when triggered',
    configurable: false,
  },
  {
    value: 'scale_budget',
    label: 'Scale Budget',
    icon: TrendingUp,
    color: 'emerald',
    description: 'Automatically adjust campaign budget',
    configurable: true,
    configFields: ['direction', 'scale_percent', 'min_budget', 'max_budget'],
  },
  {
    value: 'pause_campaign',
    label: 'Pause Campaign',
    icon: StopCircle,
    color: 'red',
    description: 'Stop underperforming campaigns',
    configurable: false,
  },
  {
    value: 'webhook',
    label: 'Call Webhook',
    icon: Webhook,
    color: 'purple',
    description: 'Send data to external URL',
    configurable: true,
    configFields: ['url'],
  },
];

// Agent templates for quick start
const TEMPLATES = [
  {
    id: 'high-roas-alert',
    name: 'High ROAS Alert',
    description: 'Get notified when campaigns exceed your ROAS target',
    icon: TrendingUp,
    color: 'emerald',
    config: {
      condition: { type: 'threshold', metric: 'roas', operator: 'gt', value: 3 },
      actions: [{ type: 'email' }],
    },
  },
  {
    id: 'low-roas-alert',
    name: 'Low ROAS Alert',
    description: 'Get alerted when ROAS drops below target',
    icon: TrendingDown,
    color: 'amber',
    config: {
      condition: { type: 'threshold', metric: 'roas', operator: 'lt', value: 1 },
      actions: [{ type: 'email' }],
    },
  },
  {
    id: 'budget-scaler',
    name: 'Auto Budget Scaler',
    description: 'Increase budget on high-performing campaigns',
    icon: DollarSign,
    color: 'blue',
    config: {
      condition: { type: 'threshold', metric: 'roas', operator: 'gt', value: 2.5 },
      accumulation: { required: 3, unit: 'days', mode: 'consecutive' },
      actions: [{ type: 'scale_budget', direction: 'up', scale_percent: 20, max_budget: 1000 }],
    },
  },
  {
    id: 'stop-loss',
    name: 'Stop Loss',
    description: 'Pause campaigns burning budget without conversions',
    icon: Shield,
    color: 'red',
    config: {
      condition: {
        type: 'composite',
        operator: 'and',
        conditions: [
          { type: 'threshold', metric: 'spend', operator: 'gt', value: 100 },
          { type: 'threshold', metric: 'conversions', operator: 'eq', value: 0 },
        ],
      },
      actions: [{ type: 'pause_campaign' }, { type: 'email' }],
    },
  },
];

// Platform icons
function MetaIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

/**
 * CreateAgentPage - Premium multi-step agent creation wizard
 */
export default function CreateAgentPage() {
  const router = useRouter();

  // State
  const [workspaceId, setWorkspaceId] = useState(null);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  // Form data
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  // Scope
  const [platform, setPlatform] = useState('all');
  const [entityLevel, setEntityLevel] = useState('campaign');
  const [scopeType, setScopeType] = useState('all'); // 'all', 'filter', 'specific'
  const [selectedEntities, setSelectedEntities] = useState([]);
  const [availableEntities, setAvailableEntities] = useState([]);
  const [entitySearchQuery, setEntitySearchQuery] = useState('');
  const [loadingEntities, setLoadingEntities] = useState(false);

  // Condition
  const [condition, setCondition] = useState({
    type: 'threshold',
    metric: 'roas',
    operator: 'gt',
    value: 2,
  });
  const [accumulation, setAccumulation] = useState({
    required: 1,
    unit: 'evaluations',
    mode: 'consecutive',
  });

  // Actions
  const [triggerMode, setTriggerMode] = useState({ mode: 'once', cooldown_minutes: 60 });
  const [actions, setActions] = useState([{ type: 'email' }]);

  // Get workspace
  useEffect(() => {
    currentUser()
      .then((user) => {
        if (user?.workspace_id) {
          setWorkspaceId(user.workspace_id);
        }
      })
      .catch((err) => console.error('Failed to get user:', err));
  }, []);

  // Load entities when scope type changes to 'specific'
  useEffect(() => {
    if (scopeType === 'specific' && workspaceId) {
      loadEntities();
    }
  }, [scopeType, workspaceId, platform, entityLevel]);

  const loadEntities = async () => {
    setLoadingEntities(true);
    try {
      const result = await fetchEntities({
        workspaceId,
        platform: platform === 'all' ? undefined : platform,
        level: entityLevel,
        limit: 100,
      });
      setAvailableEntities(result.items || []);
    } catch (err) {
      console.error('Failed to load entities:', err);
      toast.error('Failed to load entities');
    } finally {
      setLoadingEntities(false);
    }
  };

  // Apply template
  const applyTemplate = (template) => {
    setName(template.name);
    setDescription(template.description);
    if (template.config.condition) setCondition(template.config.condition);
    if (template.config.accumulation) setAccumulation(template.config.accumulation);
    if (template.config.actions) setActions(template.config.actions);
    setStep(1);
  };

  // Create agent
  const handleCreate = async () => {
    if (!workspaceId) {
      toast.error('No workspace found');
      return;
    }

    if (!name.trim()) {
      toast.error('Please enter an agent name');
      return;
    }

    if (actions.length === 0) {
      toast.error('Please select at least one action');
      return;
    }

    setLoading(true);

    try {
      // Build scope config
      // For 'all' and 'filter' scopes, enable aggregate mode so metrics are
      // summed across all matched entities and evaluated once (workspace-level).
      // Per-entity evaluation only makes sense for 'specific' scope.
      const scopeConfig = {
        platform: platform === 'all' ? null : platform,
        level: entityLevel,
        aggregate: scopeType !== 'specific',
      };

      if (scopeType === 'specific') {
        scopeConfig.entity_ids = selectedEntities.map((e) => e.id);
      }

      const agent = await createAgent({
        workspaceId,
        name: name.trim(),
        description: description.trim() || null,
        scope_type: scopeType,
        scope_config: scopeConfig,
        condition,
        accumulation,
        trigger: triggerMode,
        actions,
        status: 'active',
      });

      toast.success('Agent created successfully');
      router.push(`/agents/${agent.id}`);
    } catch (err) {
      toast.error('Failed to create agent: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Steps config
  const steps = [
    { title: 'Template', icon: Sparkles },
    { title: 'Basics', icon: Bot },
    { title: 'Scope', icon: Target },
    { title: 'Condition', icon: Zap },
    { title: 'Actions', icon: Bell },
    { title: 'Review', icon: CheckCircle2 },
  ];

  return (
    <div className="min-h-screen pb-12">
      {/* Header */}
      <header className="pt-6 pb-8 px-4">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/agents"
            className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-6"
          >
            <ArrowLeft size={14} />
            Back to Agents
          </Link>

          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-neutral-100 to-neutral-200 flex items-center justify-center shadow-lg">
              <Bot size={28} className="text-neutral-700" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold text-neutral-900 tracking-tight">
                Create Agent
              </h1>
              <p className="text-neutral-500 font-light">
                Set up automated monitoring for your campaigns
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="max-w-4xl mx-auto px-4 mb-8">
        <div className="bg-white/40 glass rounded-2xl border border-white/60 p-4">
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
            {steps.map((s, idx) => {
              const Icon = s.icon;
              const isComplete = idx < step;
              const isCurrent = idx === step;

              return (
                <button
                  key={idx}
                  onClick={() => idx <= step && setStep(idx)}
                  disabled={idx > step}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-300',
                    isCurrent && 'bg-neutral-900 text-white shadow-lg',
                    isComplete && 'bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20',
                    !isCurrent && !isComplete && 'bg-white/50 text-neutral-400 cursor-not-allowed'
                  )}
                >
                  {isComplete ? <Check size={14} /> : <Icon size={14} />}
                  <span className="hidden sm:inline">{s.title}</span>
                  <span className="sm:hidden">{idx + 1}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto px-4 mb-8">
        <div className="animate-fade-in-up">
          {step === 0 && (
            <StepTemplate templates={TEMPLATES} onSelect={applyTemplate} onSkip={() => setStep(1)} />
          )}
          {step === 1 && (
            <StepBasics
              name={name}
              setName={setName}
              description={description}
              setDescription={setDescription}
            />
          )}
          {step === 2 && (
            <StepScope
              platform={platform}
              setPlatform={setPlatform}
              entityLevel={entityLevel}
              setEntityLevel={setEntityLevel}
              scopeType={scopeType}
              setScopeType={setScopeType}
              selectedEntities={selectedEntities}
              setSelectedEntities={setSelectedEntities}
              availableEntities={availableEntities}
              entitySearchQuery={entitySearchQuery}
              setEntitySearchQuery={setEntitySearchQuery}
              loadingEntities={loadingEntities}
            />
          )}
          {step === 3 && (
            <StepCondition
              condition={condition}
              setCondition={setCondition}
              accumulation={accumulation}
              setAccumulation={setAccumulation}
            />
          )}
          {step === 4 && (
            <StepActions
              actions={actions}
              setActions={setActions}
              triggerMode={triggerMode}
              setTriggerMode={setTriggerMode}
            />
          )}
          {step === 5 && (
            <StepReview
              name={name}
              description={description}
              platform={platform}
              entityLevel={entityLevel}
              scopeType={scopeType}
              selectedEntities={selectedEntities}
              condition={condition}
              accumulation={accumulation}
              actions={actions}
              triggerMode={triggerMode}
            />
          )}
        </div>
      </div>

      {/* Navigation */}
      {step > 0 && (
        <div className="max-w-4xl mx-auto px-4">
          <div className="bg-white/40 glass rounded-2xl border border-white/60 p-4 flex items-center justify-between">
            <Button
              variant="outline"
              onClick={() => setStep(step - 1)}
              disabled={loading}
              className="rounded-xl border-neutral-200/60 hover:bg-white/60"
            >
              <ArrowLeft size={16} className="mr-2" />
              Back
            </Button>

            {step < steps.length - 1 ? (
              <Button
                onClick={() => setStep(step + 1)}
                className="bg-neutral-900 text-white rounded-xl hover:bg-neutral-800"
              >
                Continue
                <ArrowRight size={16} className="ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleCreate}
                disabled={loading || !name.trim()}
                className="bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-xl hover:from-emerald-600 hover:to-emerald-700 shadow-lg"
              >
                {loading ? 'Creating...' : 'Create Agent'}
                <Sparkles size={16} className="ml-2" />
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Step 0: Template selection
function StepTemplate({ templates, onSelect, onSkip }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">Start with a template</h2>
        <p className="text-neutral-500">Choose a pre-configured agent or start from scratch</p>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {templates.map((template) => {
          const Icon = template.icon;
          return (
            <button
              key={template.id}
              onClick={() => onSelect(template)}
              className="bg-white/40 glass rounded-[24px] p-6 border border-white/60 text-left hover:bg-white/60 hover:-translate-y-1 transition-all duration-300 group"
            >
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110',
                    template.color === 'emerald' && 'bg-emerald-500/10',
                    template.color === 'amber' && 'bg-amber-500/10',
                    template.color === 'blue' && 'bg-blue-500/10',
                    template.color === 'red' && 'bg-red-500/10'
                  )}
                >
                  <Icon
                    size={24}
                    className={cn(
                      template.color === 'emerald' && 'text-emerald-500',
                      template.color === 'amber' && 'text-amber-500',
                      template.color === 'blue' && 'text-blue-500',
                      template.color === 'red' && 'text-red-500'
                    )}
                  />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-neutral-900 mb-1">{template.name}</div>
                  <div className="text-sm text-neutral-500">{template.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="text-center pt-4">
        <button
          onClick={onSkip}
          className="inline-flex items-center gap-2 text-neutral-500 hover:text-neutral-900 transition-colors"
        >
          Start from scratch
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

// Step 1: Basics
function StepBasics({ name, setName, description, setDescription }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">Name your agent</h2>
        <p className="text-neutral-500">Give it a descriptive name so you can find it later</p>
      </div>

      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60 space-y-6">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">Agent Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., High ROAS Alert"
            className="w-full px-4 py-3 bg-white/70 hover:bg-white/90 focus:bg-white rounded-xl border border-neutral-200/60 hover:border-neutral-300/60 focus:border-neutral-300 text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all duration-200"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-2">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this agent do?"
            rows={3}
            className="w-full px-4 py-3 bg-white/70 hover:bg-white/90 focus:bg-white rounded-xl border border-neutral-200/60 hover:border-neutral-300/60 focus:border-neutral-300 text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all duration-200 resize-none"
          />
        </div>
      </div>
    </div>
  );
}

// Step 2: Enhanced Scope
function StepScope({
  platform,
  setPlatform,
  entityLevel,
  setEntityLevel,
  scopeType,
  setScopeType,
  selectedEntities,
  setSelectedEntities,
  availableEntities,
  entitySearchQuery,
  setEntitySearchQuery,
  loadingEntities,
}) {
  const filteredEntities = availableEntities.filter(
    (entity) =>
      entity.name?.toLowerCase().includes(entitySearchQuery.toLowerCase()) ||
      entity.external_id?.toLowerCase().includes(entitySearchQuery.toLowerCase())
  );

  const toggleEntity = (entity) => {
    const exists = selectedEntities.find((e) => e.id === entity.id);
    if (exists) {
      setSelectedEntities(selectedEntities.filter((e) => e.id !== entity.id));
    } else {
      setSelectedEntities([...selectedEntities, entity]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">What should this agent watch?</h2>
        <p className="text-neutral-500">Choose the platform, entity level, and scope</p>
      </div>

      {/* Platform Selection */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Globe size={14} />
          Platform
        </div>
        <div className="grid grid-cols-3 gap-3">
          {PLATFORMS.map((p) => {
            const Icon = p.icon;
            return (
              <button
                key={p.value}
                onClick={() => setPlatform(p.value)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-200',
                  platform === p.value
                    ? 'bg-neutral-900 text-white border-neutral-900 shadow-lg'
                    : 'bg-white/50 border-neutral-200/60 hover:bg-white/80 hover:border-neutral-300/60'
                )}
              >
                <div className={cn(
                  'w-10 h-10 rounded-xl flex items-center justify-center',
                  platform === p.value ? 'bg-white/20' : 'bg-neutral-100'
                )}>
                  {typeof Icon === 'function' ? <Icon /> : <Icon size={20} className={platform === p.value ? 'text-white' : 'text-neutral-600'} />}
                </div>
                <span className="text-sm font-medium">{p.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Entity Level */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Layers size={14} />
          Entity Level
        </div>
        <div className="grid grid-cols-3 gap-3">
          {ENTITY_LEVELS.map((level) => {
            const Icon = level.icon;
            return (
              <button
                key={level.value}
                onClick={() => setEntityLevel(level.value)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-200',
                  entityLevel === level.value
                    ? 'bg-neutral-900 text-white border-neutral-900 shadow-lg'
                    : 'bg-white/50 border-neutral-200/60 hover:bg-white/80 hover:border-neutral-300/60'
                )}
              >
                <Icon size={20} className={entityLevel === level.value ? 'text-white' : 'text-neutral-600'} />
                <span className="text-sm font-medium">{level.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Scope Type */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Filter size={14} />
          Scope
        </div>
        <div className="space-y-3">
          {[
            {
              value: 'all',
              label: `All ${entityLevel}s (combined)`,
              description: `Metrics are totaled across all ${entityLevel}s. You get one notification with your overall performance.`,
              icon: Target,
            },
            {
              value: 'specific',
              label: `Specific ${entityLevel}s (individual)`,
              description: `Each selected ${entityLevel} is monitored separately. You get a notification per ${entityLevel} that meets the condition.`,
              icon: CheckCircle2,
            },
          ].map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.value}
                onClick={() => setScopeType(option.value)}
                className={cn(
                  'w-full flex items-center gap-4 p-4 rounded-xl border transition-all duration-300',
                  scopeType === option.value
                    ? 'border-neutral-900 bg-white/60 shadow-lg'
                    : 'border-white/60 bg-white/40 hover:bg-white/60 hover:-translate-y-0.5'
                )}
              >
                <div
                  className={cn(
                    'w-12 h-12 rounded-2xl flex items-center justify-center',
                    scopeType === option.value ? 'bg-neutral-900' : 'bg-neutral-100'
                  )}
                >
                  <Icon
                    size={24}
                    className={scopeType === option.value ? 'text-white' : 'text-neutral-500'}
                  />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-semibold text-neutral-900">{option.label}</div>
                  <div className="text-sm text-neutral-500">{option.description}</div>
                </div>
                <div
                  className={cn(
                    'w-5 h-5 rounded-full border-2 transition-all',
                    scopeType === option.value ? 'border-neutral-900 bg-neutral-900' : 'border-neutral-300'
                  )}
                >
                  {scopeType === option.value && <Check size={12} className="text-white m-auto mt-0.5" />}
                </div>
              </button>
            );
          })}
        </div>

        {/* Scope mode explanation */}
        <div className={cn(
          'flex items-start gap-3 p-4 rounded-xl border mt-4',
          scopeType === 'all'
            ? 'bg-blue-500/5 border-blue-200/60'
            : 'bg-amber-500/5 border-amber-200/60'
        )}>
          <Info size={16} className={cn(
            'mt-0.5 flex-shrink-0',
            scopeType === 'all' ? 'text-blue-500' : 'text-amber-500'
          )} />
          <div className="text-sm text-neutral-600">
            {scopeType === 'all' ? (
              <>
                <span className="font-medium text-neutral-800">Combined mode: </span>
                Revenue, spend, and other metrics from all your {entityLevel}s are added together.
                The agent checks the total once and sends a single notification.
                Best for account-level monitoring like "alert me when total revenue exceeds $1,000".
              </>
            ) : (
              <>
                <span className="font-medium text-neutral-800">Individual mode: </span>
                Each {entityLevel} is checked on its own. If 5 {entityLevel}s meet the condition,
                you get 5 separate notifications. Best for per-{entityLevel} alerts
                like "alert me when any {entityLevel} drops below $10 ROAS".
              </>
            )}
          </div>
        </div>
      </div>

      {/* Entity Selection (when specific is selected) */}
      {scopeType === 'specific' && (
        <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
          <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} />
              Select {entityLevel}s ({selectedEntities.length} selected)
            </div>
            {selectedEntities.length > 0 && (
              <button
                onClick={() => setSelectedEntities([])}
                className="text-xs text-neutral-400 hover:text-red-500 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              value={entitySearchQuery}
              onChange={(e) => setEntitySearchQuery(e.target.value)}
              placeholder={`Search ${entityLevel}s...`}
              className="w-full pl-11 pr-4 py-3 bg-white/70 hover:bg-white/90 focus:bg-white rounded-xl border border-neutral-200/60 text-sm text-neutral-700 placeholder:text-neutral-400 focus:outline-none transition-all"
            />
          </div>

          {/* Selected entities chips */}
          {selectedEntities.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {selectedEntities.map((entity) => (
                <div
                  key={entity.id}
                  className="flex items-center gap-2 px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-sm"
                >
                  <span className="truncate max-w-[150px]">{entity.name}</span>
                  <button onClick={() => toggleEntity(entity)} className="hover:text-red-300">
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Entity list */}
          <div className="max-h-64 overflow-y-auto space-y-2">
            {loadingEntities ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin" />
              </div>
            ) : filteredEntities.length === 0 ? (
              <div className="text-center py-8 text-neutral-500 text-sm">
                {entitySearchQuery ? 'No entities match your search' : `No ${entityLevel}s found`}
              </div>
            ) : (
              filteredEntities.map((entity) => {
                const isSelected = selectedEntities.some((e) => e.id === entity.id);
                return (
                  <button
                    key={entity.id}
                    onClick={() => toggleEntity(entity)}
                    className={cn(
                      'w-full flex items-center gap-3 p-3 rounded-xl border transition-all',
                      isSelected
                        ? 'border-emerald-500 bg-emerald-500/5'
                        : 'border-neutral-200/60 bg-white/50 hover:bg-white/80'
                    )}
                  >
                    <div
                      className={cn(
                        'w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all',
                        isSelected ? 'border-emerald-500 bg-emerald-500' : 'border-neutral-300'
                      )}
                    >
                      {isSelected && <Check size={12} className="text-white" />}
                    </div>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-neutral-900 truncate">{entity.name}</div>
                      <div className="text-xs text-neutral-500 flex items-center gap-2">
                        <span className="capitalize">{entity.provider}</span>
                        <span>•</span>
                        <span className={cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase',
                          entity.status === 'active' || entity.status === 'ACTIVE'
                            ? 'bg-emerald-500/10 text-emerald-700'
                            : 'bg-neutral-500/10 text-neutral-600'
                        )}>
                          {entity.status}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Step 3: Condition
function StepCondition({ condition, setCondition, accumulation, setAccumulation }) {
  const updateCondition = (field, value) => {
    setCondition({ ...condition, [field]: value });
  };

  const selectedMetric = METRICS.find((m) => m.value === condition.metric);

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">When should this agent trigger?</h2>
        <p className="text-neutral-500">Set the condition that must be met</p>
      </div>

      {/* Condition builder */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap size={14} />
          Condition
        </div>

        {/* Metric selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-neutral-700 mb-3">Select Metric</label>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {METRICS.slice(0, 10).map((metric) => {
              const Icon = metric.icon;
              return (
                <button
                  key={metric.value}
                  onClick={() => updateCondition('metric', metric.value)}
                  className={cn(
                    'flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all',
                    condition.metric === metric.value
                      ? 'bg-neutral-900 text-white border-neutral-900 shadow-lg'
                      : 'bg-white/50 border-neutral-200/60 hover:bg-white/80'
                  )}
                >
                  <Icon size={16} className={condition.metric === metric.value ? 'text-white' : 'text-neutral-500'} />
                  <span className="text-xs font-medium">{metric.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Condition row */}
        <div className="flex flex-wrap items-center gap-3 p-4 bg-neutral-900/5 rounded-xl">
          <span className="text-neutral-600 font-medium">When</span>
          <span className="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-sm font-semibold">
            {selectedMetric?.label || condition.metric}
          </span>
          <span className="text-neutral-600 font-medium">is</span>

          <select
            value={condition.operator}
            onChange={(e) => updateCondition('operator', e.target.value)}
            className="px-4 py-2.5 bg-white/70 hover:bg-white/90 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300 transition-all"
          >
            {OPERATORS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label} {o.description}
              </option>
            ))}
          </select>

          <div className="relative">
            {selectedMetric?.format === 'currency' && (
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
            )}
            <input
              type="number"
              value={condition.value}
              onChange={(e) => updateCondition('value', parseFloat(e.target.value) || 0)}
              className={cn(
                'w-28 py-2.5 bg-white/70 hover:bg-white/90 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300 transition-all',
                selectedMetric?.format === 'currency' ? 'pl-7 pr-4' : 'px-4'
              )}
              step={selectedMetric?.format === 'currency' ? '0.01' : '0.1'}
            />
            {selectedMetric?.format === 'percent' && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">%</span>
            )}
          </div>
        </div>

        {/* Explanation */}
        <div className="mt-4 flex items-start gap-2 text-sm text-neutral-500">
          <Info size={14} className="mt-0.5 flex-shrink-0" />
          <span>
            This agent will check if {selectedMetric?.description?.toLowerCase() || condition.metric} is{' '}
            {OPERATORS.find((o) => o.value === condition.operator)?.description.toLowerCase()}{' '}
            {selectedMetric?.format === 'currency' && '$'}
            {condition.value}
            {selectedMetric?.format === 'percent' && '%'}
          </span>
        </div>
      </div>

      {/* Accumulation */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Timer size={14} />
          Duration Requirement
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-neutral-600 font-medium">Must be true for</span>

          <input
            type="number"
            value={accumulation.required}
            onChange={(e) =>
              setAccumulation({ ...accumulation, required: parseInt(e.target.value) || 1 })
            }
            className="w-20 px-4 py-2.5 bg-white/70 hover:bg-white/90 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300 transition-all"
            min="1"
          />

          <select
            value={accumulation.unit}
            onChange={(e) => setAccumulation({ ...accumulation, unit: e.target.value })}
            className="px-4 py-2.5 bg-white/70 hover:bg-white/90 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300 transition-all"
          >
            <option value="evaluations">evaluations (every 15 min)</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>

          <select
            value={accumulation.mode}
            onChange={(e) => setAccumulation({ ...accumulation, mode: e.target.value })}
            className="px-4 py-2.5 bg-white/70 hover:bg-white/90 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300 transition-all"
          >
            <option value="consecutive">in a row</option>
            <option value="within_window">within window</option>
          </select>
        </div>

        <div className="mt-4 flex items-start gap-2 text-sm text-neutral-500">
          <Info size={14} className="mt-0.5 flex-shrink-0" />
          <span>
            The condition must be true for {accumulation.required} {accumulation.unit}{' '}
            {accumulation.mode === 'consecutive' ? 'consecutively' : 'within the time window'} before triggering.
          </span>
        </div>
      </div>
    </div>
  );
}

// Step 4: Enhanced Actions
function StepActions({ actions, setActions, triggerMode, setTriggerMode }) {
  const toggleAction = (type) => {
    const exists = actions.find((a) => a.type === type);
    if (exists) {
      setActions(actions.filter((a) => a.type !== type));
    } else {
      // Add action with default config
      const actionType = ACTION_TYPES.find((a) => a.value === type);
      const newAction = { type };

      if (type === 'scale_budget') {
        newAction.direction = 'up';
        newAction.scale_percent = 20;
        newAction.min_budget = null;
        newAction.max_budget = 1000;
      } else if (type === 'webhook') {
        newAction.url = '';
      }

      setActions([...actions, newAction]);
    }
  };

  const updateAction = (type, field, value) => {
    setActions(
      actions.map((a) => (a.type === type ? { ...a, [field]: value } : a))
    );
  };

  const getAction = (type) => actions.find((a) => a.type === type);

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">What should happen when triggered?</h2>
        <p className="text-neutral-500">Select actions and configure their parameters</p>
      </div>

      {/* Action selection */}
      <div className="space-y-4">
        {ACTION_TYPES.map((actionType) => {
          const Icon = actionType.icon;
          const isSelected = actions.some((a) => a.type === actionType.value);
          const action = getAction(actionType.value);

          return (
            <div key={actionType.value} className="space-y-0">
              <button
                onClick={() => toggleAction(actionType.value)}
                className={cn(
                  'w-full bg-white/40 glass p-5 border text-left transition-all duration-300',
                  isSelected
                    ? 'border-neutral-900 bg-white/60 shadow-lg rounded-t-[20px]'
                    : 'border-white/60 hover:bg-white/60 hover:-translate-y-0.5 rounded-[20px]',
                  isSelected && actionType.configurable && 'rounded-b-none'
                )}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'w-12 h-12 rounded-2xl flex items-center justify-center transition-all',
                      isSelected
                        ? 'bg-neutral-900'
                        : actionType.color === 'blue'
                          ? 'bg-blue-500/10'
                          : actionType.color === 'emerald'
                            ? 'bg-emerald-500/10'
                            : actionType.color === 'red'
                              ? 'bg-red-500/10'
                              : 'bg-purple-500/10'
                    )}
                  >
                    <Icon
                      size={24}
                      className={cn(
                        isSelected
                          ? 'text-white'
                          : actionType.color === 'blue'
                            ? 'text-blue-500'
                            : actionType.color === 'emerald'
                              ? 'text-emerald-500'
                              : actionType.color === 'red'
                                ? 'text-red-500'
                                : 'text-purple-500'
                      )}
                    />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-neutral-900">{actionType.label}</div>
                    <div className="text-sm text-neutral-500">{actionType.description}</div>
                  </div>
                  {isSelected && (
                    <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                      <Check size={14} className="text-white" />
                    </div>
                  )}
                </div>
              </button>

              {/* Action configuration */}
              {isSelected && actionType.configurable && (
                <div className="bg-neutral-50/80 rounded-b-[20px] border border-t-0 border-neutral-900 p-5">
                  {actionType.value === 'scale_budget' && (
                    <div className="space-y-5">
                      {/* Direction */}
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-3">Direction</label>
                        <div className="flex gap-3">
                          <button
                            onClick={() => updateAction('scale_budget', 'direction', 'up')}
                            className={cn(
                              'flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all',
                              action?.direction === 'up'
                                ? 'bg-emerald-500 text-white border-emerald-500'
                                : 'bg-white border-neutral-200/60 hover:border-emerald-300'
                            )}
                          >
                            <TrendingUp size={18} />
                            <span className="font-medium">Increase Budget</span>
                          </button>
                          <button
                            onClick={() => updateAction('scale_budget', 'direction', 'down')}
                            className={cn(
                              'flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all',
                              action?.direction === 'down'
                                ? 'bg-red-500 text-white border-red-500'
                                : 'bg-white border-neutral-200/60 hover:border-red-300'
                            )}
                          >
                            <TrendingDown size={18} />
                            <span className="font-medium">Decrease Budget</span>
                          </button>
                        </div>
                      </div>

                      {/* Percentage */}
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          {action?.direction === 'up' ? 'Increase' : 'Decrease'} by percentage
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            type="number"
                            value={action?.scale_percent || 20}
                            onChange={(e) =>
                              updateAction('scale_budget', 'scale_percent', parseFloat(e.target.value) || 0)
                            }
                            className="w-24 px-4 py-2.5 bg-white rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300"
                            min="1"
                            max="100"
                          />
                          <span className="text-neutral-500">%</span>
                          <span className="text-sm text-neutral-400">
                            (e.g., $100 budget → ${action?.direction === 'up'
                              ? (100 * (1 + (action?.scale_percent || 20) / 100)).toFixed(0)
                              : (100 * (1 - (action?.scale_percent || 20) / 100)).toFixed(0)
                            })
                          </span>
                        </div>
                      </div>

                      {/* Min/Max Budget */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Minimum Budget (optional)
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
                            <input
                              type="number"
                              value={action?.min_budget || ''}
                              onChange={(e) =>
                                updateAction('scale_budget', 'min_budget', e.target.value ? parseFloat(e.target.value) : null)
                              }
                              placeholder="No minimum"
                              className="w-full pl-7 pr-4 py-2.5 bg-white rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300"
                            />
                          </div>
                          <p className="text-xs text-neutral-400 mt-1">Never go below this amount</p>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-neutral-700 mb-2">
                            Maximum Budget (recommended)
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">$</span>
                            <input
                              type="number"
                              value={action?.max_budget || ''}
                              onChange={(e) =>
                                updateAction('scale_budget', 'max_budget', e.target.value ? parseFloat(e.target.value) : null)
                              }
                              placeholder="No maximum"
                              className="w-full pl-7 pr-4 py-2.5 bg-white rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300"
                            />
                          </div>
                          <p className="text-xs text-neutral-400 mt-1">Safety cap for scaling</p>
                        </div>
                      </div>

                      {/* Warning for no max */}
                      {action?.direction === 'up' && !action?.max_budget && (
                        <div className="flex items-start gap-2 p-3 bg-amber-500/10 rounded-xl border border-amber-200/60">
                          <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-amber-700">
                            Setting a maximum budget is recommended to prevent runaway spending.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {actionType.value === 'webhook' && (
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">Webhook URL</label>
                      <input
                        type="url"
                        value={action?.url || ''}
                        onChange={(e) => updateAction('webhook', 'url', e.target.value)}
                        placeholder="https://your-webhook-url.com/endpoint"
                        className="w-full px-4 py-2.5 bg-white rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300"
                      />
                      <p className="text-xs text-neutral-400 mt-2">
                        We'll POST a JSON payload with event details when triggered
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Trigger mode */}
      <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60">
        <div className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Zap size={14} />
          Trigger Frequency
        </div>
        <div className="space-y-3">
          {[
            { value: 'once', label: 'Once per entity', description: 'Only trigger once, then stop watching' },
            { value: 'cooldown', label: 'With cooldown', description: 'Can trigger again after a cooldown period' },
            { value: 'continuous', label: 'Every check', description: 'Trigger every time the condition is met' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setTriggerMode({ ...triggerMode, mode: option.value })}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-xl transition-all',
                triggerMode.mode === option.value
                  ? 'bg-neutral-900 text-white'
                  : 'bg-white/50 text-neutral-700 hover:bg-white/80'
              )}
            >
              <div
                className={cn(
                  'w-4 h-4 rounded-full border-2',
                  triggerMode.mode === option.value ? 'border-white bg-white' : 'border-neutral-300'
                )}
              >
                {triggerMode.mode === option.value && (
                  <div className="w-2 h-2 bg-neutral-900 rounded-full m-auto mt-0.5" />
                )}
              </div>
              <div className="text-left flex-1">
                <div className="font-medium">{option.label}</div>
                <div
                  className={cn(
                    'text-sm',
                    triggerMode.mode === option.value ? 'text-white/70' : 'text-neutral-500'
                  )}
                >
                  {option.description}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Cooldown duration */}
        {triggerMode.mode === 'cooldown' && (
          <div className="mt-4 pt-4 border-t border-neutral-200/30">
            <label className="block text-sm font-medium text-neutral-700 mb-2">Cooldown Period</label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                value={triggerMode.cooldown_minutes || 60}
                onChange={(e) =>
                  setTriggerMode({ ...triggerMode, cooldown_minutes: parseInt(e.target.value) || 60 })
                }
                className="w-24 px-4 py-2.5 bg-white/70 rounded-xl border border-neutral-200/60 text-neutral-700 focus:outline-none focus:border-neutral-300"
                min="15"
              />
              <span className="text-neutral-500">minutes</span>
              <span className="text-sm text-neutral-400">
                ({((triggerMode.cooldown_minutes || 60) / 60).toFixed(1)} hours)
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Step 5: Enhanced Review
function StepReview({
  name,
  description,
  platform,
  entityLevel,
  scopeType,
  selectedEntities,
  condition,
  accumulation,
  actions,
  triggerMode,
}) {
  const getOperatorSymbol = (op) => {
    const map = { gt: '>', gte: '≥', lt: '<', lte: '≤', eq: '=' };
    return map[op] || op;
  };

  const selectedMetric = METRICS.find((m) => m.value === condition.metric);
  const scaleAction = actions.find((a) => a.type === 'scale_budget');

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-neutral-900 mb-2">Review your agent</h2>
        <p className="text-neutral-500">Make sure everything looks correct before creating</p>
      </div>

      <div className="space-y-4">
        {/* Name */}
        <div className="bg-white/40 glass rounded-[20px] p-5 border border-white/60">
          <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">
            Name
          </div>
          <div className="text-lg font-semibold text-neutral-900">{name || 'Unnamed agent'}</div>
          {description && <div className="text-sm text-neutral-500 mt-1">{description}</div>}
        </div>

        {/* Scope */}
        <div className="bg-white/40 glass rounded-[20px] p-5 border border-white/60">
          <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">
            Scope
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-neutral-100 rounded-lg text-sm font-medium text-neutral-700 capitalize">
                {platform === 'all' ? 'All Platforms' : platform}
              </span>
              <span className="text-neutral-400">→</span>
              <span className="px-2 py-1 bg-neutral-100 rounded-lg text-sm font-medium text-neutral-700 capitalize">
                {entityLevel}s
              </span>
            </div>
            {scopeType === 'specific' && selectedEntities.length > 0 && (
              <div className="text-sm text-neutral-500">
                Watching {selectedEntities.length} specific {entityLevel}
                {selectedEntities.length !== 1 ? 's' : ''} — evaluated individually, one notification per {entityLevel}
              </div>
            )}
            {scopeType === 'all' && (
              <div className="text-sm text-neutral-500">
                All {entityLevel}s combined — metrics totaled, one notification for overall performance
              </div>
            )}
          </div>
        </div>

        {/* Condition */}
        <div className="bg-white/40 glass rounded-[20px] p-5 border border-white/60">
          <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">
            Condition
          </div>
          <div className="font-semibold text-neutral-900">
            When {selectedMetric?.label || condition.metric} {getOperatorSymbol(condition.operator)}{' '}
            {selectedMetric?.format === 'currency' && '$'}
            {condition.value}
            {selectedMetric?.format === 'percent' && '%'}
          </div>
          <div className="text-sm text-neutral-500 mt-1">
            For {accumulation.required} {accumulation.unit} ({accumulation.mode})
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white/40 glass rounded-[20px] p-5 border border-white/60">
          <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-3">
            Actions
          </div>
          <div className="space-y-2">
            {actions.map((action, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="px-3 py-1.5 bg-neutral-900 text-white rounded-xl text-sm font-medium capitalize">
                  {action.type.replace('_', ' ')}
                </span>
                {action.type === 'scale_budget' && (
                  <span className="text-sm text-neutral-500">
                    {action.direction === 'up' ? '↑' : '↓'} {action.scale_percent}%
                    {action.max_budget && ` (max $${action.max_budget})`}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className="text-sm text-neutral-500 mt-3">
            Trigger mode: <span className="font-medium">{triggerMode.mode}</span>
            {triggerMode.mode === 'cooldown' && ` (${triggerMode.cooldown_minutes} min cooldown)`}
          </div>
        </div>
      </div>

      {/* Ready indicator */}
      <div className="flex items-center justify-center gap-3 pt-4">
        <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
          <CheckCircle2 size={20} className="text-emerald-500" />
        </div>
        <span className="text-emerald-600 font-medium">Ready to create</span>
      </div>
    </div>
  );
}
