"use client";

/**
 * FeaturesSectionNew - Showcases AI-powered insights and granular control
 * Two large cards with interactive visualizations
 * White theme with blue/cyan accents
 * Related: page.jsx, HeroSectionNew.jsx
 */

import { motion } from "framer-motion";
import { Sparkles, SlidersHorizontal, TrendingUp, Target, DollarSign, BarChart3 } from "lucide-react";

// AI Insights visualization - shows automated tagging and classification
function AIInsightsViz() {
  return (
    <div className="relative h-[320px] w-full flex flex-col items-center justify-center border border-gray-100 rounded-2xl bg-gray-50/50 overflow-hidden">
      {/* Grid floor effect */}
      <div
        className="absolute inset-0 z-0 opacity-30"
        style={{
          backgroundImage: "linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px)",
          backgroundSize: "30px 30px",
          transform: "perspective(500px) rotateX(60deg) translateY(50px) scale(1.5)"
        }}
      />

      {/* Flow diagram */}
      <div
        className="flex md:gap-4 text-[10px] md:text-xs text-gray-600 font-mono z-20 mb-10 relative gap-x-2 gap-y-2 items-center justify-center"
        style={{
          maskImage: "linear-gradient(90deg, transparent, black 5%, black 90%, transparent)",
          WebkitMaskImage: "linear-gradient(90deg, transparent, black 5%, black 90%, transparent)"
        }}
      >
        {/* Left nodes */}
        <div className="flex flex-col gap-3">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 flex items-center gap-2 shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            AI Analysis
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 flex items-center gap-2 shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" style={{ animationDelay: "75ms" }} />
            Pattern Match
          </motion.div>
        </div>

        {/* Connectors left */}
        <svg className="w-8 h-12 text-gray-300" viewBox="0 0 32 48" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M0 12 C 16 12, 16 24, 32 24" strokeDasharray="3 3" className="opacity-50" />
          <path d="M0 36 C 16 36, 16 24, 32 24" strokeDasharray="3 3" className="opacity-50" />
        </svg>

        {/* Center node */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="px-3 py-2 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 border border-blue-400 shadow-lg text-white font-semibold z-10"
        >
          classify metrics
        </motion.div>

        {/* Connectors right */}
        <svg className="w-8 h-12 text-gray-300" viewBox="0 0 32 48" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M0 24 C 16 24, 16 12, 32 12" strokeDasharray="3 3" className="opacity-50" />
          <path d="M0 24 C 16 24, 16 36, 32 36" strokeDasharray="3 3" className="opacity-50" />
        </svg>

        {/* Right nodes */}
        <div className="flex flex-col gap-3">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-500 shadow-sm"
          >
            by performance
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.6 }}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-500 shadow-sm"
          >
            by trend
          </motion.div>
        </div>
      </div>

      {/* Floating insight tags */}
      <div className="absolute bottom-8 w-full px-10 flex justify-center gap-4 z-10">
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.7 }}
          className="px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 text-[10px] shadow-sm transform -rotate-2 hover:scale-105 transition-transform cursor-default select-none"
        >
          ROAS +24%
        </motion.span>
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8 }}
          className="px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-600 text-[10px] shadow-sm transform rotate-3 hover:scale-105 transition-transform cursor-default select-none"
        >
          CPC Optimal
        </motion.span>
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.9 }}
          className="px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-600 text-[10px] shadow-sm transform -translate-y-2 hover:scale-105 transition-transform cursor-default select-none"
        >
          Scale Ready
        </motion.span>
      </div>
    </div>
  );
}

// Granular control/filter visualization
function GranularControlViz() {
  return (
    <div className="w-full bg-white rounded-xl border border-gray-200 p-5 shadow-sm relative overflow-hidden group-hover:shadow-md transition-shadow duration-500">
      {/* Window header */}
      <div className="flex items-center justify-between mb-5 border-b border-gray-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-800 tracking-wide">Filter Rules</span>
          <span className="px-1.5 py-0.5 rounded-md bg-gray-100 text-[9px] font-medium text-gray-500 border border-gray-200">4 active</span>
        </div>
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-gray-200" />
          <div className="w-2 h-2 rounded-full bg-gray-200" />
        </div>
      </div>

      {/* Filter rules */}
      <div className="space-y-3 font-mono text-[10px] sm:text-xs relative z-10">
        {/* Row 1 */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="flex items-center gap-2"
        >
          <span className="w-10 text-gray-400 text-right font-medium">Where</span>
          <div className="flex-1 h-7 bg-gray-50 border border-gray-200 rounded flex items-center px-2 text-blue-500">
            platform
          </div>
          <div className="w-8 h-7 bg-gray-50 border border-gray-200 rounded flex items-center justify-center text-gray-400">
            =
          </div>
          <div className="flex text-gray-700 bg-gray-50 w-20 h-7 border-gray-200 border rounded px-2 items-center text-[10px]">
            meta
          </div>
          <button className="w-5 h-7 flex items-center justify-center text-gray-300 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 12a2 2 0 1 1-4 0a2 2 0 0 1 4 0m7 0a2 2 0 1 1-4 0a2 2 0 0 1 4 0m7 0a2 2 0 1 1-4 0a2 2 0 0 1 4 0" />
            </svg>
          </button>
        </motion.div>

        {/* Row 2 */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="flex items-center gap-2"
        >
          <span className="w-10 text-gray-400 text-right font-medium">And</span>
          <div className="flex-1 h-7 bg-gray-50 border border-gray-200 rounded flex items-center px-2 text-blue-500">
            roas
          </div>
          <div className="w-8 h-7 bg-gray-50 border border-gray-200 rounded flex items-center justify-center text-gray-400">
            &gt;
          </div>
          <div className="w-20 h-7 bg-gray-50 border border-gray-200 rounded flex items-center px-2 text-emerald-500">
            2.0x
          </div>
          <button className="w-5 h-7 flex items-center justify-center text-gray-300 hover:text-gray-600 transition-colors">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 12a2 2 0 1 1-4 0a2 2 0 0 1 4 0m7 0a2 2 0 1 1-4 0a2 2 0 0 1 4 0m7 0a2 2 0 1 1-4 0a2 2 0 0 1 4 0" />
            </svg>
          </button>
        </motion.div>

        {/* Nested group */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="pl-4 border-l border-gray-200 mt-2 pt-2 relative"
        >
          <span className="absolute -left-[17px] top-5 w-4 h-px bg-gray-200" />
          <div className="flex items-center gap-2 mb-2">
            <span className="text-gray-400 text-[9px] uppercase tracking-wider font-semibold">Or Group</span>
          </div>

          <div className="flex items-center gap-2 mb-1">
            <span className="w-10 text-gray-400 text-right font-medium">Where</span>
            <div className="flex-1 h-7 bg-gray-50 border border-gray-200 rounded flex items-center px-2 text-blue-500">
              spend
            </div>
            <div className="w-8 h-7 bg-gray-50 border border-gray-200 rounded flex items-center justify-center text-gray-400">
              &gt;
            </div>
            <div className="flex text-[10px] text-amber-500 bg-gray-50 w-20 h-7 border-gray-200 border rounded px-2 items-center">
              $1,000
            </div>
          </div>
        </motion.div>
      </div>

      {/* Gradient glow */}
      <div className="absolute -right-5 -bottom-10 w-32 h-32 bg-blue-500/5 rounded-full blur-[40px] pointer-events-none group-hover:bg-blue-500/10 transition-all duration-700" />
    </div>
  );
}

// Feature card component
function FeatureCard({ icon: Icon, title, description, color = "blue", index = 0 }) {
  const colorClasses = {
    blue: "from-blue-500 to-cyan-500 shadow-blue-500/20",
    purple: "from-purple-500 to-pink-500 shadow-purple-500/20",
    green: "from-green-500 to-emerald-500 shadow-green-500/20",
    amber: "from-amber-500 to-orange-500 shadow-amber-500/20"
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="group relative rounded-2xl bg-white border border-gray-200 overflow-hidden hover:border-gray-300 hover:shadow-lg transition-all duration-300 p-6"
    >
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${colorClasses[color]} flex items-center justify-center mb-4 shadow-lg`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 text-sm leading-relaxed">{description}</p>
    </motion.div>
  );
}

export default function FeaturesSectionNew() {
  return (
    <section id="features" className="relative w-full py-24 lg:py-32 bg-gray-50/50 border-t border-gray-100">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto text-center mb-20"
        >
          <h2 className="text-3xl md:text-5xl lg:text-6xl font-normal text-gray-900 tracking-tight mb-6">
            Intelligent analytics via
            <span className="block bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">unified data</span>
          </h2>
          <p className="text-lg md:text-xl text-gray-500 font-light leading-relaxed">
            Our AI engine analyzes your campaigns across all platforms, identifying patterns and opportunities you'd otherwise miss.
          </p>
        </motion.div>

        {/* Large feature cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
          {/* Card 1: AI-Powered Insights */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="group relative rounded-3xl bg-white border border-gray-200 overflow-hidden hover:border-gray-300 hover:shadow-xl transition-all duration-500 flex flex-col"
          >
            <div className="p-8 md:p-10 relative z-10 flex-1 flex flex-col">
              <h3 className="text-2xl font-medium text-gray-900 mb-3 flex items-center gap-3 tracking-tight">
                <Sparkles className="w-7 h-7 text-blue-500" />
                AI-Powered Insights
              </h3>
              <p className="text-gray-500 font-light mb-8 text-base leading-relaxed">
                Our AI automatically classifies campaign performance, identifies trends, and surfaces optimization opportunities in real-time.
              </p>
              <div className="mt-auto">
                <AIInsightsViz />
              </div>
            </div>
          </motion.div>

          {/* Card 2: Granular Control */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="group relative rounded-3xl bg-white border border-gray-200 overflow-hidden hover:border-gray-300 hover:shadow-xl transition-all duration-500 flex flex-col"
          >
            <div className="p-8 md:p-10 relative z-10 h-full flex flex-col">
              <h3 className="text-2xl font-medium text-gray-900 mb-3 flex items-center gap-3 tracking-tight">
                <SlidersHorizontal className="w-7 h-7 text-blue-500" />
                Granular Control
              </h3>
              <p className="text-gray-500 font-light mb-8 text-base leading-relaxed">
                Filter, segment, and drill down into your data with powerful boolean operators and custom rules.
              </p>
              <div className="mt-auto">
                <GranularControlViz />
              </div>
            </div>
          </motion.div>
        </div>

        {/* Smaller feature cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <FeatureCard
            icon={TrendingUp}
            title="Real-time Trends"
            description="Watch your metrics update live. Catch opportunities as they happen."
            color="green"
            index={0}
          />
          <FeatureCard
            icon={Target}
            title="Attribution"
            description="Track conversions across the entire customer journey with server-side tracking."
            color="purple"
            index={1}
          />
          <FeatureCard
            icon={DollarSign}
            title="P&L Finance"
            description="Know your true profitability with real-time revenue and cost tracking."
            color="amber"
            index={2}
          />
          <FeatureCard
            icon={BarChart3}
            title="Custom Reports"
            description="Build and schedule reports tailored to your exact needs."
            color="blue"
            index={3}
          />
        </div>
      </div>
    </section>
  );
}
