"use client";

import { motion } from "framer-motion";
import { Bot, LineChart, Zap, Shield } from "lucide-react";

function Badge({ text }) {
  return (
    <div className="px-4 py-1.5 max-w-[120px] mx-auto bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.06)] rounded-full flex items-center gap-2">
      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500" />
      <span className="text-black text-xs font-medium">{text}</span>
    </div>
  );
}

function NaturalLanguageVisual() {
  return (
    <div className="w-full h-full flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
        <span className="text-gray-400 text-sm">Ask:</span>
        <span className="text-black text-sm">"What's my ROAS this week?"</span>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div className="text-2xl font-bold text-black">3.63x</div>
          <div className="text-sm text-green-500 font-medium">+12% vs last week</div>
        </div>
      </div>
    </div>
  );
}

function UnifiedDataVisual() {
  return (
    <div className="w-full h-full flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold">M</div>
        <div className="flex-1 h-2 bg-blue-100 rounded-full">
          <div className="h-full w-3/4 bg-blue-500 rounded-full"></div>
        </div>
        <span className="text-sm text-black font-medium">$18.2K</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded bg-red-100 flex items-center justify-center text-red-600 text-xs font-bold">G</div>
        <div className="flex-1 h-2 bg-red-100 rounded-full">
          <div className="h-full w-1/2 bg-red-500 rounded-full"></div>
        </div>
        <span className="text-sm text-black font-medium">$6.3K</span>
      </div>
      <div className="flex items-center gap-2 mt-2 pt-3 border-t border-gray-100">
        <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center text-black text-xs font-bold">All</div>
        <div className="flex-1 h-2 bg-gray-200 rounded-full">
          <div className="h-full w-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full"></div>
        </div>
        <span className="text-sm text-black font-bold">$24.5K</span>
      </div>
    </div>
  );
}

function RealTimeVisual() {
  const bars = [45, 62, 55, 78, 88, 95, 82];
  return (
    <div className="w-full h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-400">Live Performance</span>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs text-green-500 font-medium">Live</span>
        </div>
      </div>
      <div className="flex-1 flex items-end justify-between gap-2">
        {bars.map((height, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t transition-all duration-500"
              style={{ height: `${height}%` }}
            ></div>
            <span className="text-[10px] text-gray-400">{['M', 'T', 'W', 'T', 'F', 'S', 'S'][i]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SecureVisual() {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-4">
      <div className="w-14 h-14 rounded-full bg-green-50 flex items-center justify-center border border-green-100">
        <Shield className="w-7 h-7 text-green-500" />
      </div>
      <div className="flex flex-col items-center gap-1">
        <div className="text-sm font-bold text-black">Workspace Isolated</div>
        <div className="text-xs text-gray-400 text-center">Your data is scoped & secure</div>
      </div>
      <div className="flex gap-2 mt-2">
        <div className="px-2 py-1 bg-gray-100 rounded text-[10px] text-gray-600 font-medium">JWT Auth</div>
        <div className="px-2 py-1 bg-gray-100 rounded text-[10px] text-gray-600 font-medium">No Raw SQL</div>
      </div>
    </div>
  );
}

export default function BentoGridSection() {
  const features = [
    {
      title: "Natural Language Queries",
      description: "Ask questions in plain English. Get precise answers instantly, no SQL required.",
      visual: <NaturalLanguageVisual />,
    },
    {
      title: "Unified Data Layer",
      description: "Meta + Google in one view. Compare platforms side-by-side with consistent metrics.",
      visual: <UnifiedDataVisual />,
    },
    {
      title: "Real-time Performance",
      description: "Watch your metrics update live. Catch trends and anomalies as they happen.",
      visual: <RealTimeVisual />,
    },
    {
      title: "Secure by Design",
      description: "Workspace-isolated data. No SQL injection possible. Your metrics stay yours.",
      visual: <SecureVisual />,
    },
  ];

  return (
    <div id="features" className="w-full bg-white py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        {/* Header */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <Badge text="Features" />
          <h2 className="mt-6 text-3xl md:text-4xl font-bold text-black tracking-tight">
            Everything you need to understand your marketing
          </h2>
          <p className="mt-4 text-gray-500 text-lg max-w-xl mx-auto">
            From natural language queries to real-time analytics, get the insights you need without the complexity.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="bg-white border border-gray-100 rounded-xl p-6 hover:shadow-lg hover:border-gray-200 transition-all"
            >
              <h3 className="text-lg font-bold text-black mb-2">{feature.title}</h3>
              <p className="text-gray-500 text-sm mb-4">{feature.description}</p>
              <div className="w-full h-48 bg-gray-50 rounded-lg border border-gray-100 overflow-hidden">
                {feature.visual}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
