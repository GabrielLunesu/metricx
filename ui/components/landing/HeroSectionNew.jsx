"use client";

/**
 * HeroSectionNew - Premium hero with flowing data visualization
 * Shows ad platforms → AI processing → actionable insights
 * White theme with blue/cyan accents matching metricx brand
 * Related: page.jsx, FeaturesSectionNew.jsx
 */

import { motion } from "framer-motion";
import { ArrowRight, ChevronRight, FileText, Sparkles } from "lucide-react";
import Image from "next/image";

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
      <path d="M15.337 3.415c-.03-.09-.09-.12-.15-.12-.06 0-1.41-.06-1.41-.06s-.93-.93-1.05-1.05c-.12-.12-.33-.09-.42-.06 0 0-.21.06-.54.18-.33-1.02-1.11-1.95-2.4-1.95h-.09C8.807.105 8.427 0 8.067 0c-2.94 0-4.35 3.69-4.8 5.55l-2.04.63c-.63.21-.66.24-.75.84-.06.45-1.71 13.17-1.71 13.17l12.87 2.4 6.96-1.74s-3.03-16.32-3.06-16.44h.03zm-3.72.84c-.51.15-1.11.36-1.74.54 0-.51-.09-1.23-.27-1.8.66.12 1.14.84 1.41 1.26zm-2.85.87c-1.17.36-2.46.78-3.75 1.17.36-1.38 1.05-2.76 1.89-3.66.3-.33.75-.69 1.26-.9.51 1.02.6 2.46.6 3.39zm-1.71-4.38c.42 0 .78.15 1.08.42-.48.24-.93.63-1.35 1.05-.99 1.08-1.74 2.76-2.16 4.41-.99.3-1.98.63-2.88.9.6-2.43 2.88-6.72 5.31-6.78z" />
    </svg>
  );
}

// Floating card component
function FloatingCard({ children, className = "", delay = 0, position = "" }) {
  return (
    <motion.div
      className={`absolute ${position}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.6, ease: "easeOut" }}
    >
      <motion.div
        className={`bg-white/90 backdrop-blur-xl border border-gray-200/60 rounded-2xl shadow-xl shadow-gray-200/40 ${className}`}
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: delay * 2 }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

// Data ingestion card
function IngestCard({ delay }) {
  return (
    <FloatingCard delay={delay} position="left-[52%] bottom-[12%] lg:left-[48%] lg:bottom-[15%]" className="p-5 w-52">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="w-5 h-5 rounded flex items-center justify-center bg-gray-100 text-[10px] font-bold text-gray-500">01</span>
          <span className="text-xs font-semibold text-gray-800 uppercase tracking-wide">Ingest</span>
        </div>
        <Sparkles className="w-4 h-4 text-gray-400" />
      </div>
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] border border-blue-200">
              <MetaIcon className="w-2.5 h-2.5" />
            </div>
            <span className="text-[10px] font-medium text-gray-600">Meta Ads</span>
          </div>
          <span className="text-[9px] text-emerald-500 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-full font-medium">Live</span>
        </div>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-100 text-red-600 flex items-center justify-center text-[10px] border border-red-200">
              <GoogleIcon className="w-2.5 h-2.5" />
            </div>
            <span className="text-[10px] font-medium text-gray-600">Google Ads</span>
          </div>
          <span className="text-[9px] text-gray-400">Syncing</span>
        </div>
      </div>
    </FloatingCard>
  );
}

// Transform/AI processing card
function TransformCard({ delay }) {
  return (
    <FloatingCard delay={delay} position="right-[25%] bottom-[40%] lg:right-[20%] lg:bottom-[35%]" className="p-5 w-56">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="w-5 h-5 rounded flex items-center justify-center bg-gray-100 text-[10px] font-bold text-gray-500">02</span>
          <span className="text-xs font-semibold text-gray-800 uppercase tracking-wide">AI Process</span>
        </div>
        <div className="w-4 h-4 rounded bg-gradient-to-br from-blue-500 to-cyan-500 animate-pulse" />
      </div>
      <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
        <div className="flex gap-1.5 mb-2">
          <div className="w-2 h-2 rounded-full bg-red-300" />
          <div className="w-2 h-2 rounded-full bg-yellow-300" />
          <div className="w-2 h-2 rounded-full bg-green-300" />
        </div>
        <p className="font-mono text-[10px] text-gray-500 leading-tight">
          <span className="text-blue-500">Analyzing</span> 24 metrics across
          <span className="text-blue-500"> 3 platforms</span>...
        </p>
      </div>
    </FloatingCard>
  );
}

// Insight delivery card
function InsightCard({ delay }) {
  return (
    <FloatingCard delay={delay} position="right-[10%] top-[15%] lg:right-[8%] lg:top-[20%]" className="p-5 w-52">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="w-5 h-5 rounded flex items-center justify-center bg-gray-100 text-[10px] font-bold text-gray-500">03</span>
          <span className="text-xs font-semibold text-gray-800 uppercase tracking-wide">Insight</span>
        </div>
        <div className="w-4 h-4 text-emerald-500">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <div className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
        <span className="text-xs text-gray-600 font-medium">ROAS Trending Up</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-gray-400 font-mono uppercase">Performance</span>
        <span className="text-sm text-emerald-500 font-mono font-semibold">+18.9%</span>
      </div>
    </FloatingCard>
  );
}

// Data flow SVG visualization
function DataFlowSVG() {
  return (
    <div className="absolute inset-0 pointer-events-none w-full h-full overflow-hidden z-0 opacity-60 md:opacity-80">
      <svg className="w-full h-full" viewBox="0 0 1200 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="roadGradientLight" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" style={{ stopColor: "#3B82F6", stopOpacity: 0.2 }} />
            <stop offset="50%" style={{ stopColor: "#06B6D4", stopOpacity: 0.15 }} />
            <stop offset="100%" style={{ stopColor: "#ffffff", stopOpacity: 0.0 }} />
          </linearGradient>
          <linearGradient id="lineGradientLight" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style={{ stopColor: "#3B82F6", stopOpacity: 0.6 }} />
            <stop offset="100%" style={{ stopColor: "#06B6D4", stopOpacity: 0.6 }} />
          </linearGradient>
        </defs>

        {/* Main flow path */}
        <path id="pathMainLight" d="M 400 1000 C 600 900, 900 600, 1300 200" fill="none" />

        {/* Background roads */}
        <path d="M 600 1000 C 700 900, 800 700, 1300 550" fill="none" stroke="#E5E7EB" strokeWidth="30" opacity="0.5" strokeLinecap="round" />
        <path d="M 900 1000 C 950 900, 900 700, 1300 450" fill="none" stroke="#E5E7EB" strokeWidth="20" opacity="0.4" strokeLinecap="round" />

        {/* Main highway */}
        <path d="M 400 1000 C 600 900, 900 600, 1300 200" fill="none" stroke="url(#roadGradientLight)" strokeWidth="50" opacity="0.8" strokeLinecap="butt" />
        <path d="M 400 1000 C 600 900, 900 600, 1300 200" fill="none" stroke="rgba(59,130,246,0.15)" strokeWidth="2" strokeDasharray="20 40" opacity="0.6" />

        {/* Animated data packet */}
        <rect x="-30" y="-15" width="60" height="30" rx="4" fill="url(#lineGradientLight)" opacity="0.9" filter="drop-shadow(0 4px 12px rgba(59,130,246,0.3))">
          <animateMotion dur="5s" repeatCount="indefinite" rotate="auto" keyPoints="0;1" keyTimes="0;1" calcMode="linear">
            <mpath href="#pathMainLight" />
          </animateMotion>
        </rect>
      </svg>

      {/* Track lines - desktop only */}
      <svg className="absolute inset-0 w-full h-full hidden lg:block" viewBox="0 0 1200 900" preserveAspectRatio="xMidYMid slice">
        {/* Track 1 */}
        <rect x="580" y="600" width="120" height="400" rx="60" transform="rotate(-15 640 800)" fill="none" stroke="#E5E7EB" strokeWidth="0.5" opacity="0.5" />
        <rect x="580" y="600" width="120" height="400" rx="60" transform="rotate(-15 640 800)" fill="none" stroke="#3B82F6" strokeWidth="1" strokeLinecap="round" className="animate-beam" opacity="0.3" />

        {/* Track 2 */}
        <rect x="880" y="300" width="140" height="450" rx="70" transform="rotate(-25 950 525)" fill="none" stroke="#E5E7EB" strokeWidth="0.5" opacity="0.5" />
        <rect x="880" y="300" width="140" height="450" rx="70" transform="rotate(-25 950 525)" fill="none" stroke="#06B6D4" strokeWidth="1" strokeLinecap="round" className="animate-beam" opacity="0.3" style={{ animationDelay: "-3s" }} />

        {/* Track 3 */}
        <rect x="1050" y="50" width="100" height="300" rx="50" transform="rotate(-35 1100 200)" fill="none" stroke="#E5E7EB" strokeWidth="0.5" opacity="0.5" />
        <rect x="1050" y="50" width="100" height="300" rx="50" transform="rotate(-35 1100 200)" fill="none" stroke="#3B82F6" strokeWidth="1" strokeLinecap="round" className="animate-beam" opacity="0.3" style={{ animationDelay: "-6s" }} />
      </svg>
    </div>
  );
}

export default function HeroSectionNew() {
  return (
    <section className="relative w-full min-h-screen overflow-hidden flex flex-col">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-gray-50 via-white to-gray-50/50">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-radial from-blue-100/30 via-transparent to-transparent rounded-full blur-3xl" />
      </div>

      {/* Navigation */}
      <nav className="relative z-50 flex items-center justify-between px-6 py-6 md:px-12 md:py-8 max-w-[1400px] mx-auto w-full">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Image
            src="/logo.png"
            alt="metricx"
            width={200}
            height={120}
            className="h-16 w-auto -mt-4"
            priority
          />
        </div>

        {/* Desktop Menu */}
        <div className="hidden md:flex bg-white/80 backdrop-blur-md rounded-full py-1 px-1 shadow-sm border border-gray-200/60 gap-1 items-center">
          <a href="#features" className="px-4 py-1.5 text-sm font-medium text-gray-900 bg-gray-100 rounded-full">Features</a>
          <a href="#copilot" className="px-4 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">Copilot</a>
          <a href="#integrations" className="px-4 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">Integrations</a>
          <a href="#pricing" className="px-4 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">Pricing</a>
        </div>

        {/* CTA */}
        <a
          href="/login"
          className="hidden sm:flex hover:shadow-lg hover:shadow-blue-500/20 transition-all text-sm font-medium text-white bg-gradient-to-b from-blue-500 to-blue-600 rounded-full py-2.5 px-5 shadow-md gap-2 items-center"
        >
          <span>Get Started</span>
          <ArrowRight className="w-4 h-4" />
        </a>

        {/* Mobile Menu Icon */}
        <button className="md:hidden text-gray-600 hover:text-gray-900">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 5h16M4 12h16M4 19h16" />
          </svg>
        </button>
      </nav>

      {/* Content Area */}
      <div className="flex-1 z-20 flex flex-col md:flex-row h-full relative max-w-[1400px] mx-auto w-full">
        {/* Left: Text Content */}
        <div className="w-full md:w-[50%] lg:w-[45%] px-6 md:px-12 pt-8 md:pt-24 z-30 flex flex-col justify-start md:justify-between pb-12 h-full">
          <div className="max-w-xl mx-auto md:mx-0">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200/60 text-blue-600 text-xs font-medium tracking-wide mb-6"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              NOW IN BETA
            </motion.div>

            {/* Title */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.6 }}
              className="text-5xl sm:text-6xl lg:text-7xl font-normal text-gray-900 tracking-tight mb-6 leading-[0.95]"
            >
              Unify your
              <span className="block bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">ad analytics</span>
            </motion.h1>

            {/* Description */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.6 }}
              className="text-lg md:text-xl leading-relaxed text-gray-500 mb-8 md:mb-12 max-w-md font-light"
            >
              Connect Meta & Google Ads. Ask any question. Get instant insights powered by AI.
            </motion.p>

            {/* Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.6 }}
              className="flex flex-col sm:flex-row gap-4 mb-16 md:mb-20 w-full flex-none"
            >
              {/* Primary */}
              <a
                href="/login"
                className="group inline-flex overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-blue-500/20 rounded-full items-center justify-center w-full sm:w-auto"
              >
                <span className="flex items-center justify-center gap-2 text-white text-sm font-medium bg-gradient-to-b from-gray-800 to-gray-950 w-full h-full rounded-full py-3.5 px-8 shadow-md">
                  <span>Start for free</span>
                  <ChevronRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5" />
                </span>
              </a>

              {/* Secondary */}
              <a
                href="#features"
                className="group inline-flex overflow-hidden transition-all duration-300 hover:-translate-y-0.5 rounded-full items-center justify-center w-full sm:w-auto"
              >
                <span className="flex items-center justify-center gap-2 text-gray-600 group-hover:text-gray-900 text-sm font-medium bg-white w-full h-full rounded-full py-3.5 px-8 border border-gray-200 hover:border-gray-300 shadow-sm">
                  <FileText className="w-4 h-4" />
                  <span>Learn more</span>
                </span>
              </a>
            </motion.div>

            {/* Deployed with Defang */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.8 }}
              className="border-gray-200 border-t mt-auto pt-8"
            >
              <a
                href="https://defang.io"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 ml-4 group"
              >
                <span className="text-lg text-black font-medium">Deployed with</span>
                <Image
                  src="/defang.png"
                  alt="Defang"
                  width={70}
                  height={20}
                  className="h-7 w-auto group-hover:opacity-80 transition-opacity"
                />
              </a>
            </motion.div>
          </div>
        </div>

        {/* Right: Visualization */}
        <DataFlowSVG />

        {/* Floating UI Cards */}
        <div className="hidden md:block">
          <InsightCard delay={0.8} />
          <TransformCard delay={1.0} />
          <IngestCard delay={1.2} />
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent pointer-events-none z-10" />

      <style jsx global>{`
        .bg-gradient-radial {
          background: radial-gradient(circle, var(--tw-gradient-stops));
        }
        @keyframes dash-flow {
          0% { stroke-dashoffset: 0; }
          100% { stroke-dashoffset: -1000; }
        }
        .animate-beam {
          stroke-dasharray: 40 400;
          animation: dash-flow 10s linear infinite;
        }
      `}</style>
    </section>
  );
}
