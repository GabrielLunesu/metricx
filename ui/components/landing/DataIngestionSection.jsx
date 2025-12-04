"use client";

/**
 * DataIngestionSection - Shows platform integrations flowing into unified dashboard
 * Visual representation of data centralization from ad platforms + Shopify
 * White theme with blue/cyan accents
 * Related: page.jsx, FeaturesSectionNew.jsx
 */

import { motion } from "framer-motion";
import { ArrowRight, Database, Plug, RefreshCw, Shield } from "lucide-react";

// Platform Icons
function MetaIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 0 0 8.44-9.9c0-5.53-4.5-10.02-10-10.02z" />
    </svg>
  );
}

function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}


function ShopifyIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M15.337 3.415c-.03-.09-.09-.12-.15-.12-.06 0-1.41-.06-1.41-.06s-.93-.93-1.05-1.05c-.12-.12-.33-.09-.42-.06 0 0-.21.06-.54.18-.33-1.02-1.11-1.95-2.4-1.95h-.09C8.807.105 8.427 0 8.067 0c-2.94 0-4.35 3.69-4.8 5.55l-2.04.63c-.63.21-.66.24-.75.84-.06.45-1.71 13.17-1.71 13.17l12.87 2.4 6.96-1.74s-3.03-16.32-3.06-16.44h.03zm-3.72.84c-.51.15-1.11.36-1.74.54 0-.51-.09-1.23-.27-1.8.66.12 1.14.84 1.41 1.26zm-2.85.87c-1.17.36-2.46.78-3.75 1.17.36-1.38 1.05-2.76 1.89-3.66.3-.33.75-.69 1.26-.9.51 1.02.6 2.46.6 3.39zm-1.71-4.38c.42 0 .78.15 1.08.42-.48.24-.93.63-1.35 1.05-.99 1.08-1.74 2.76-2.16 4.41-.99.3-1.98.63-2.88.9.6-2.43 2.88-6.72 5.31-6.78z"/>
    </svg>
  );
}

// Platform icon component
function PlatformIcon({ icon: Icon, name, color, delay = 0 }) {
  const colorClasses = {
    blue: "bg-blue-100 text-blue-600 border-blue-200 hover:border-blue-300 hover:bg-blue-50",
    red: "bg-red-100 text-red-600 border-red-200 hover:border-red-300 hover:bg-red-50",
    black: "bg-gray-100 text-gray-800 border-gray-200 hover:border-gray-300 hover:bg-gray-50",
    green: "bg-green-100 text-green-600 border-green-200 hover:border-green-300 hover:bg-green-50"
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.4 }}
      className={`w-12 h-12 rounded-xl ${colorClasses[color]} flex items-center justify-center border shadow-sm hover:shadow-md hover:scale-105 transition-all duration-300 cursor-pointer`}
      title={name}
    >
      <Icon className="w-5 h-5" />
    </motion.div>
  );
}

// Data flow visualization
function DataFlowViz() {
  return (
    <div className="relative w-full max-w-lg mx-auto lg:mx-0">
      {/* Labels */}
      <div className="flex justify-between text-[10px] font-mono text-gray-400 uppercase tracking-widest mb-6 px-4">
        <span>Ad Platforms</span>
        <span className="mr-12">Unified Dashboard</span>
      </div>

      {/* Platform icons row */}
      <div className="flex mb-12 px-2 relative items-center justify-between">
        {/* Left group - Ad platforms */}
        <div className="flex gap-3 md:gap-4">
          <PlatformIcon icon={MetaIcon} name="Meta Ads" color="blue" delay={0.1} />
          <PlatformIcon icon={GoogleIcon} name="Google Ads" color="red" delay={0.2} />
        </div>

        {/* Right group - E-commerce */}
        <div className="flex gap-3 md:gap-4 border-l border-dashed border-gray-200 pl-8">
          <PlatformIcon icon={ShopifyIcon} name="Shopify" color="green" delay={0.4} />
        </div>
      </div>

      {/* Connection lines SVG */}
      <div className="absolute top-10 left-0 w-full h-[180px] pointer-events-none z-0 hidden sm:block">
        <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 512 180">
          <defs>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" style={{ stopColor: "#3B82F6", stopOpacity: 0.6 }} />
              <stop offset="100%" style={{ stopColor: "#06B6D4", stopOpacity: 0.6 }} />
            </linearGradient>
          </defs>

          {/* Background lines */}
          <path d="M 48 24 C 48 80, 256 40, 256 120" fill="none" stroke="#E5E7EB" strokeWidth="1.5" />
          <path d="M 120 24 C 120 80, 256 40, 256 120" fill="none" stroke="#E5E7EB" strokeWidth="1.5" />
          <path d="M 420 24 C 420 80, 256 40, 256 120" fill="none" stroke="#E5E7EB" strokeWidth="1.5" />

          {/* Animated beam lines */}
          <path d="M 48 24 C 48 80, 256 40, 256 120" fill="none" stroke="url(#lineGradient)" strokeWidth="1.5" className="animate-beam-slow" />
          <path d="M 120 24 C 120 80, 256 40, 256 120" fill="none" stroke="url(#lineGradient)" strokeWidth="1.5" className="animate-beam-slow" style={{ animationDelay: "-2s" }} />
          <path d="M 420 24 C 420 80, 256 40, 256 120" fill="none" stroke="url(#lineGradient)" strokeWidth="1.5" className="animate-beam-slow" style={{ animationDelay: "-1s" }} />

          {/* Center convergence node */}
          <circle cx="256" cy="120" r="4" fill="#3B82F6" className="animate-pulse">
            <animate attributeName="r" values="3;5;3" dur="2s" repeatCount="indefinite" />
          </circle>

          {/* Vertical line */}
          <line x1="256" y1="120" x2="256" y2="160" stroke="#3B82F6" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.5" />
        </svg>
      </div>

      {/* Cards stack */}
      <div className="z-10 flex flex-col gap-6 mt-16 relative">
        {/* Incoming data card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="w-full bg-white border border-gray-200 rounded-2xl p-5 shadow-lg relative group"
        >
          <div className="absolute -left-px top-8 h-8 w-[3px] bg-gradient-to-b from-blue-500 to-cyan-500 rounded-r-full" />

          <div className="flex items-start gap-4">
            <div className="mt-1 w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-500 border border-blue-100 shrink-0">
              <Plug className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium text-gray-900 font-mono">Real-time Sync</h4>
                <span className="text-[10px] text-gray-400 font-mono">5 / 15 / 30 min</span>
              </div>
              <p className="text-gray-500 text-xs font-mono leading-relaxed truncate opacity-70">
                Campaigns, ad sets, ads, and metrics from all platforms
              </p>
            </div>
          </div>
        </motion.div>

        {/* Connector node */}
        <div className="relative flex flex-col items-center">
          <div className="h-6 w-px bg-gradient-to-b from-gray-200 to-transparent border-r border-dashed border-gray-300" />
          <div className="my-2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 shadow-sm z-20">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-medium text-gray-500 font-mono">PROCESSING</span>
          </div>
          <div className="h-6 w-px bg-gradient-to-b from-transparent to-gray-200 border-r border-dashed border-gray-300" />
        </div>

        {/* Unified dashboard card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="w-full bg-white border border-gray-200 rounded-2xl p-5 shadow-lg relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

          <div className="flex items-center gap-3 mb-4">
            <Database className="w-5 h-5 text-gray-700" />
            <span className="text-sm font-medium text-gray-800">Unified Dashboard</span>
            <div className="ml-auto flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-200" />
              <span className="w-1.5 h-1.5 rounded-full bg-gray-200" />
            </div>
          </div>

          {/* Metric row */}
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-medium text-gray-900 truncate">All platforms unified</span>
                <span className="text-[10px] text-gray-400 font-mono truncate">24 metrics • 3 platforms • real-time</span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200 text-[10px] text-gray-500 font-mono">Live</span>
            </div>
          </div>
        </motion.div>
      </div>

      <style jsx global>{`
        @keyframes beam-slow {
          0% { stroke-dashoffset: 0; }
          100% { stroke-dashoffset: -1000; }
        }
        .animate-beam-slow {
          stroke-dasharray: 30 300;
          animation: beam-slow 8s linear infinite;
        }
      `}</style>
    </div>
  );
}

// Feature item
function FeatureItem({ icon: Icon, title, description, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.4 }}
      className="flex items-start gap-4"
    >
      <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600 shrink-0">
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-1">{title}</h4>
        <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

export default function DataIngestionSection() {
  return (
    <section id="integrations" className="relative w-full py-24 lg:py-32 bg-gray-50/50 border-t border-gray-100">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left: Text content */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="order-2 lg:order-1 max-w-xl"
          >
            <h2 className="text-3xl md:text-5xl lg:text-6xl font-normal text-gray-900 tracking-tight mb-6">
              Centralize your
              <span className="block bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">data ingestion</span>
            </h2>

            <p className="text-lg text-gray-500 font-light leading-relaxed mb-8">
              Connect all your ad platforms in minutes. We sync your campaigns, metrics, and performance data into a single source of truth.
            </p>

            <p className="text-base text-gray-400 font-light leading-relaxed mb-10">
              metricx integrates seamlessly with the tools you already use. No complex setup, no engineering required.
            </p>

            <div className="space-y-6 mb-10">
              <FeatureItem
                icon={RefreshCw}
                title="Configurable sync intervals"
                description="Choose 5, 15, or 30 minute sync intervals. Your data stays fresh without manual intervention."
                delay={0.2}
              />
              <FeatureItem
                icon={Shield}
                title="Secure OAuth connections"
                description="We never store your ad platform credentials."
                delay={0.3}
              />
              <FeatureItem
                icon={Database}
                title="90-day historical backfill"
                description="Get insights from day one with automatic data import."
                delay={0.4}
              />
            </div>

            <a
              href="#integrations"
              className="inline-flex items-center gap-2 text-sm font-medium text-gray-900 border-b-2 border-blue-500 pb-0.5 hover:text-blue-600 transition-colors"
            >
              Explore integrations
              <ArrowRight className="w-4 h-4" />
            </a>
          </motion.div>

          {/* Right: Visualization */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="order-1 lg:order-2"
          >
            <DataFlowViz />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
