"use client";

/**
 * FeaturesSection - Compact glassmorphic bento grid showcasing key features
 * Animated cards with hover effects and visual demonstrations
 * Related: HeroSection.jsx, page.jsx
 */

import { motion } from "framer-motion";
import { Bot, Layers, DollarSign, Zap, BarChart3, Target } from "lucide-react";

// Animated bar chart component
function AnimatedChart() {
  const bars = [45, 65, 55, 80, 70, 90, 75];
  return (
    <div className="flex items-end justify-between gap-1.5 h-24 px-2">
      {bars.map((height, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          whileInView={{ height: `${height}%` }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.1, duration: 0.5, ease: "easeOut" }}
          className="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t-sm"
        />
      ))}
    </div>
  );
}

// Platform comparison visualization
function PlatformComparison() {
  return (
    <div className="space-y-3 px-2">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white text-xs font-bold">M</div>
        <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: "75%" }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="h-full bg-blue-500 rounded-full"
          />
        </div>
        <span className="text-sm font-semibold text-gray-900">$18.2K</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-red-500 flex items-center justify-center text-white text-xs font-bold">G</div>
        <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: "50%" }}
            viewport={{ once: true }}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="h-full bg-red-500 rounded-full"
          />
        </div>
        <span className="text-sm font-semibold text-gray-900">$6.3K</span>
      </div>
    </div>
  );
}

// AI Chat bubble animation
function AIChatBubble() {
  return (
    <div className="space-y-3 px-2">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="flex gap-2"
      >
        <div className="w-6 h-6 rounded-full bg-gray-200 flex-shrink-0" />
        <div className="px-3 py-2 bg-gray-100 rounded-2xl rounded-tl-sm text-xs text-gray-600">
          What's my ROAS this week?
        </div>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
        className="flex gap-2 justify-end"
      >
        <div className="px-3 py-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl rounded-tr-sm text-xs text-white">
          Your ROAS is 3.8x, up 12% from last week!
        </div>
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex-shrink-0 flex items-center justify-center">
          <Bot className="w-3 h-3 text-white" />
        </div>
      </motion.div>
    </div>
  );
}

// P&L visualization
function PLVisualization() {
  return (
    <div className="space-y-2 px-2">
      <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
        <span className="text-xs text-gray-500">Revenue</span>
        <span className="text-sm font-semibold text-gray-900">$89,200</span>
      </div>
      <div className="flex justify-between items-center py-1.5 border-b border-gray-100">
        <span className="text-xs text-gray-500">Ad Spend</span>
        <span className="text-sm font-semibold text-red-500">-$24,500</span>
      </div>
      <div className="flex justify-between items-center py-1.5">
        <span className="text-xs font-medium text-gray-700">Net Profit</span>
        <motion.span
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="text-sm font-bold text-green-500"
        >
          $64,700
        </motion.span>
      </div>
    </div>
  );
}

// Glass card wrapper
function GlassFeatureCard({ children, className = "", index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      whileHover={{ y: -8, transition: { duration: 0.3 } }}
      className={`group relative overflow-hidden rounded-2xl ${className}`}
    >
      {/* Glass effect background */}
      <div className="absolute inset-0 bg-white/60 backdrop-blur-xl border border-white/30 rounded-2xl" />
      {/* Gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-2xl" />
      {/* Content */}
      <div className="relative h-full p-6">
        {children}
      </div>
    </motion.div>
  );
}

export default function FeaturesSection() {
  return (
    <section id="features" className="w-full py-20 bg-gradient-to-b from-white via-gray-50/50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full border border-blue-500/20 mb-6"
          >
            <Zap className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">Powerful Features</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-4">
            <span className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
              Everything you need to
            </span>
            <br />
            <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
              scale profitably
            </span>
          </h2>
          <p className="text-gray-600 text-lg max-w-xl mx-auto">
            From AI-powered insights to unified analytics, get the tools you need in one place.
          </p>
        </motion.div>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* AI Copilot - Large card */}
          <GlassFeatureCard className="md:col-span-2 lg:col-span-2" index={0}>
            <div className="flex flex-col lg:flex-row gap-6 h-full">
              <div className="flex-1">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4 shadow-lg shadow-blue-500/20">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">AI Marketing Copilot</h3>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  Ask questions in plain English and get instant, actionable insights. No SQL required.
                </p>
                <div className="flex flex-wrap gap-2">
                  {["Natural language", "Instant answers", "Smart suggestions"].map((tag) => (
                    <span key={tag} className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex-1 bg-gray-50/80 rounded-xl p-4 min-h-[140px] flex flex-col justify-center">
                <AIChatBubble />
              </div>
            </div>
          </GlassFeatureCard>

          {/* Unified Dashboard */}
          <GlassFeatureCard index={1}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4 shadow-lg shadow-purple-500/20">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Unified Dashboard</h3>
            <p className="text-gray-600 text-sm mb-4">
              Google + Meta in one view with consistent metrics.
            </p>
            <div className="bg-gray-50/80 rounded-xl p-3">
              <PlatformComparison />
            </div>
          </GlassFeatureCard>

          {/* Real-time Analytics */}
          <GlassFeatureCard index={2}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mb-4 shadow-lg shadow-green-500/20">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Real-time Analytics</h3>
            <p className="text-gray-600 text-sm mb-4">
              Watch metrics update live. Catch trends as they happen.
            </p>
            <div className="bg-gray-50/80 rounded-xl p-3">
              <AnimatedChart />
            </div>
          </GlassFeatureCard>

          {/* P&L Finance */}
          <GlassFeatureCard index={3}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center mb-4 shadow-lg shadow-amber-500/20">
              <DollarSign className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">P&L Finance View</h3>
            <p className="text-gray-600 text-sm mb-4">
              Know your true profitability with real-time tracking.
            </p>
            <div className="bg-gray-50/80 rounded-xl p-3">
              <PLVisualization />
            </div>
          </GlassFeatureCard>

          {/* Smart Recommendations */}
          <GlassFeatureCard index={4}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-red-500 flex items-center justify-center mb-4 shadow-lg shadow-rose-500/20">
              <Target className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Smart Recommendations</h3>
            <p className="text-gray-600 text-sm mb-4">
              AI tells you exactly where to increase spend and what to cut.
            </p>
            <div className="flex flex-col gap-2">
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
                className="flex items-center gap-2 p-2 bg-green-50 rounded-lg border border-green-100"
              >
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-xs text-green-700">Scale "Summer Sale" +20%</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 }}
                className="flex items-center gap-2 p-2 bg-red-50 rounded-lg border border-red-100"
              >
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-xs text-red-700">Pause "Brand Awareness"</span>
              </motion.div>
            </div>
          </GlassFeatureCard>
        </div>
      </div>
    </section>
  );
}
