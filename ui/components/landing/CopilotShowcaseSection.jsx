"use client";

/**
 * CopilotShowcaseSection - Showcases the AI Copilot natural language query system
 * Interactive chat-like visualization demonstrating QA capabilities
 * White theme with blue/cyan accents
 * Related: page.jsx, FeaturesSectionNew.jsx
 */

import { motion } from "framer-motion";
import { Bot, Send, ArrowRight, MessageSquare, Zap, Brain, LineChart } from "lucide-react";
import { useState } from "react";

// Example questions for the carousel
const exampleQuestions = [
  { question: "What's my ROAS this week?", answer: "Your ROAS this week is 3.82×, up 18.9% from last week. Meta campaigns are driving the increase." },
  { question: "Which campaign has highest CPA?", answer: "\"Winter Sale Retargeting\" has the highest CPA at $42.50. Consider pausing or optimizing this campaign." },
  { question: "Show me spend by platform", answer: "Meta: $18,240 (58%), Google: $9,820 (31%), TikTok: $3,440 (11%). Total spend: $31,500." },
  { question: "Why did conversions drop?", answer: "Conversions dropped 23% due to Meta's \"Summer Promo\" campaign pausing. Your other campaigns maintained performance." }
];

// Chat message component
function ChatMessage({ type, children, delay = 0 }) {
  const isUser = type === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, x: isUser ? 10 : -10 }}
      whileInView={{ opacity: 1, y: 0, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.4 }}
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex-shrink-0 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}
      <div
        className={`max-w-[280px] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-gray-900 text-white rounded-br-sm"
            : "bg-gray-100 text-gray-700 rounded-bl-sm border border-gray-200"
        }`}
      >
        {children}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0" />
      )}
    </motion.div>
  );
}

// Feature pill component
function FeaturePill({ icon: Icon, children }) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 text-gray-600 text-xs font-medium shadow-sm">
      <Icon className="w-3.5 h-3.5 text-blue-500" />
      {children}
    </div>
  );
}

// Interactive chat demo component
function ChatDemo() {
  const [activeIndex, setActiveIndex] = useState(0);
  const current = exampleQuestions[activeIndex];

  return (
    <div className="w-full max-w-lg mx-auto lg:mx-0">
      {/* Chat window */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xl shadow-gray-200/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-gray-50/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900">metricx Copilot</h4>
              <p className="text-[10px] text-emerald-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Online
              </p>
            </div>
          </div>
          <div className="flex gap-1.5">
            <div className="w-2 h-2 rounded-full bg-gray-200" />
            <div className="w-2 h-2 rounded-full bg-gray-200" />
          </div>
        </div>

        {/* Messages */}
        <div className="p-5 space-y-4 min-h-[200px]">
          <ChatMessage type="user" delay={0}>
            {current.question}
          </ChatMessage>
          <ChatMessage type="ai" delay={0.3}>
            {current.answer}
          </ChatMessage>
        </div>

        {/* Input */}
        <div className="px-5 pb-5">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-50 border border-gray-200">
            <input
              type="text"
              placeholder="Ask anything about your ads..."
              className="flex-1 bg-transparent text-sm text-gray-700 placeholder:text-gray-400 outline-none"
              readOnly
            />
            <button className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-md hover:shadow-lg transition-shadow">
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Example question pills */}
      <div className="mt-6 flex flex-wrap gap-2 justify-center lg:justify-start">
        {exampleQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => setActiveIndex(i)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              i === activeIndex
                ? "bg-blue-500 text-white shadow-md"
                : "bg-white text-gray-500 border border-gray-200 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            {q.question.slice(0, 25)}...
          </button>
        ))}
      </div>
    </div>
  );
}

export default function CopilotShowcaseSection() {
  return (
    <section id="copilot" className="relative w-full py-24 lg:py-32 bg-white border-t border-gray-100">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left: Text content */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="order-2 lg:order-1"
          >
            <div className="max-w-xl">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200/60 text-blue-600 text-xs font-medium tracking-wide mb-6"
              >
                <Zap className="w-3.5 h-3.5" />
                AI-POWERED
              </motion.div>

              <h2 className="text-3xl md:text-5xl lg:text-6xl font-normal text-gray-900 tracking-tight mb-6">
                Ask anything about
                <span className="block bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">your ad data</span>
              </h2>

              <p className="text-lg text-gray-500 font-light leading-relaxed mb-8">
                Skip the SQL. Skip the dashboards. Just ask your question in plain English and get instant, accurate answers backed by your real data.
              </p>

              <p className="text-base text-gray-400 font-light leading-relaxed mb-10">
                Our AI understands context, remembers your previous questions, and surfaces insights you didn't even know to look for.
              </p>

              {/* Feature pills */}
              <div className="flex flex-wrap gap-3 mb-10">
                <FeaturePill icon={MessageSquare}>Natural Language</FeaturePill>
                <FeaturePill icon={Brain}>Context Aware</FeaturePill>
                <FeaturePill icon={LineChart}>Real-time Data</FeaturePill>
              </div>

              <a
                href="/copilot"
                className="inline-flex items-center gap-2 text-sm font-medium text-gray-900 border-b-2 border-blue-500 pb-0.5 hover:text-blue-600 transition-colors"
              >
                Try the Copilot
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </motion.div>

          {/* Right: Chat demo */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="order-1 lg:order-2"
          >
            <ChatDemo />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
