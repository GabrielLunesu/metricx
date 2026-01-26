/**
 * AgentEmptyState - Premium Empty State Component
 * ================================================
 *
 * WHAT: Beautiful empty state with glass morphism design
 * WHY: Guide users to create their first agent with stunning visuals
 *
 * DESIGN PRINCIPLES:
 * - Glass morphism
 * - Gradient backgrounds
 * - Animated elements
 * - Premium feature cards
 *
 * REFERENCES:
 * - Metricx v3.0 design system
 */

'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Bot,
  Sparkles,
  Search,
  Bell,
  TrendingUp,
  Shield,
  Zap,
  ArrowRight,
} from 'lucide-react';

/**
 * AgentEmptyState component
 */
export function AgentEmptyState({
  hasFilters = false,
  onClearFilters,
}) {
  if (hasFilters) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-20 h-20 rounded-[24px] bg-white/40 glass border border-white/60 flex items-center justify-center mb-6">
          <Search size={32} className="text-neutral-400" />
        </div>
        <h3 className="text-xl font-semibold text-neutral-900 mb-3">
          No agents found
        </h3>
        <p className="text-neutral-500 mb-8 max-w-md">
          No agents match your current filters. Try adjusting your search or status filter.
        </p>
        <Button
          onClick={onClearFilters}
          variant="outline"
          className="rounded-xl border-neutral-200/60 hover:bg-white/60"
        >
          Clear filters
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {/* Hero icon with gradient */}
      <div className="relative mb-8">
        <div className="w-24 h-24 rounded-[28px] bg-gradient-to-br from-neutral-100 to-neutral-200 flex items-center justify-center shadow-lg">
          <Bot size={44} className="text-neutral-600" />
        </div>
        <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-500 flex items-center justify-center shadow-lg">
          <Sparkles size={20} className="text-white" />
        </div>
      </div>

      {/* Hero text */}
      <h3 className="text-2xl sm:text-3xl font-semibold text-neutral-900 mb-3 tracking-tight">
        Create your first AI agent
      </h3>
      <p className="text-neutral-500 mb-10 max-w-lg text-lg font-light">
        Agents monitor your ad performance 24/7 and automatically take action when conditions are met.
      </p>

      {/* CTAs */}
      <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
        <Link href="/agents/new">
          <Button className="gap-2 bg-neutral-900 text-white rounded-xl px-6 py-3 hover:bg-neutral-800 hover:scale-105 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Sparkles size={16} />
            Create Agent
          </Button>
        </Link>
        <Link href="/agents/new?template=true">
          <Button
            variant="outline"
            className="gap-2 rounded-xl border-neutral-200/60 hover:bg-white/60 px-6 py-3"
          >
            Browse Templates
            <ArrowRight size={16} />
          </Button>
        </Link>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl">
        {/* Alert Agent */}
        <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-1 transition-all duration-300 text-left">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-4">
            <Bell size={24} className="text-amber-500" />
          </div>
          <h4 className="font-semibold text-neutral-900 mb-2">Alert Agent</h4>
          <p className="text-sm text-neutral-500 leading-relaxed">
            Get notified instantly when ROAS drops below target or spend exceeds your budget.
          </p>
        </div>

        {/* Scaling Agent */}
        <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-1 transition-all duration-300 text-left">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-4">
            <TrendingUp size={24} className="text-emerald-500" />
          </div>
          <h4 className="font-semibold text-neutral-900 mb-2">Scaling Agent</h4>
          <p className="text-sm text-neutral-500 leading-relaxed">
            Automatically increase budget on campaigns that exceed your ROAS targets.
          </p>
        </div>

        {/* Stop-Loss Agent */}
        <div className="bg-white/40 glass rounded-[24px] p-6 border border-white/60 hover:bg-white/60 hover:-translate-y-1 transition-all duration-300 text-left">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
            <Shield size={24} className="text-red-500" />
          </div>
          <h4 className="font-semibold text-neutral-900 mb-2">Stop-Loss Agent</h4>
          <p className="text-sm text-neutral-500 leading-relaxed">
            Automatically pause campaigns that burn budget without converting.
          </p>
        </div>
      </div>

      {/* Bottom highlight */}
      <div className="mt-12 flex items-center gap-3 text-sm text-neutral-500">
        <div className="flex items-center gap-1.5">
          <Zap size={14} className="text-amber-500" />
          <span>Runs every 15 minutes</span>
        </div>
        <span className="text-neutral-300">•</span>
        <div className="flex items-center gap-1.5">
          <Bot size={14} className="text-blue-500" />
          <span>No code required</span>
        </div>
        <span className="text-neutral-300">•</span>
        <div className="flex items-center gap-1.5">
          <Shield size={14} className="text-emerald-500" />
          <span>Safe & reversible</span>
        </div>
      </div>
    </div>
  );
}

export default AgentEmptyState;
