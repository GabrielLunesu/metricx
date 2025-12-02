"use client";

/**
 * HeroSection - Landing page hero with glassmorphic design and animated visuals
 * Creates a WOW effect with floating elements, glass cards, and smooth animations
 * Related: page.jsx, FeaturesSection.jsx
 */

import { useState, useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { ArrowRight, Sparkles, TrendingUp, Zap, Bot } from "lucide-react";

// Animated counter component for stats
function AnimatedNumber({ value, suffix = "" }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => Math.round(latest));
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const controls = animate(count, value, { duration: 2, ease: "easeOut" });
    const unsubscribe = rounded.on("change", (v) => setDisplayValue(v));
    return () => {
      controls.stop();
      unsubscribe();
    };
  }, [value, count, rounded]);

  return <span>{displayValue}{suffix}</span>;
}

// Floating glass orb component
function FloatingOrb({ className, delay = 0 }) {
  return (
    <motion.div
      className={`absolute rounded-full bg-gradient-to-br from-blue-400/30 to-cyan-400/30 backdrop-blur-3xl ${className}`}
      animate={{
        y: [0, -20, 0],
        scale: [1, 1.05, 1],
        opacity: [0.5, 0.8, 0.5],
      }}
      transition={{
        duration: 6,
        repeat: Infinity,
        delay,
        ease: "easeInOut",
      }}
    />
  );
}

// Glass card with animated border
function GlassCard({ children, className = "", hover = true }) {
  return (
    <motion.div
      className={`relative overflow-hidden rounded-2xl ${className}`}
      whileHover={hover ? { scale: 1.02, y: -4 } : {}}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      {/* Animated gradient border */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-500/20 via-cyan-500/20 to-blue-500/20 p-[1px]">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
      </div>
      {/* Glass background */}
      <div className="relative h-full bg-white/70 dark:bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20">
        {children}
      </div>
    </motion.div>
  );
}

// Live metric pill that pulses
function LiveMetric({ label, value, change, positive = true }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex items-center gap-3 px-4 py-2 bg-white/80 backdrop-blur-lg rounded-full border border-white/30 shadow-lg shadow-blue-500/5"
    >
      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
      <span className="text-xs text-gray-500 font-medium">{label}</span>
      <span className="text-sm font-bold text-gray-900">{value}</span>
      <span className={`text-xs font-semibold ${positive ? "text-green-500" : "text-red-500"}`}>
        {positive ? "+" : ""}{change}
      </span>
    </motion.div>
  );
}

// Feature preview card with animation
function FeaturePreview({ icon: Icon, title, value, subtitle, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      className="flex-1 p-4 bg-gradient-to-br from-white/80 to-white/40 backdrop-blur-xl rounded-xl border border-white/30"
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
          <Icon className="w-4 h-4 text-white" />
        </div>
        <span className="text-xs font-medium text-gray-500">{title}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-green-500 font-medium">{subtitle}</div>
    </motion.div>
  );
}

export default function HeroSection() {
  const [isVisible, setIsVisible] = useState(true);
  const heroRef = useRef(null);

  // Track visibility for performance
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0, rootMargin: "200px" }
    );
    if (heroRef.current) observer.observe(heroRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={heroRef} className="relative w-full min-h-screen overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50">
        {/* Animated mesh gradient */}
        <div className="absolute inset-0 opacity-60">
          <div className="absolute top-0 -left-40 w-[600px] h-[600px] bg-gradient-to-br from-blue-400/40 to-transparent rounded-full blur-3xl animate-blob" />
          <div className="absolute top-40 -right-40 w-[500px] h-[500px] bg-gradient-to-br from-cyan-400/40 to-transparent rounded-full blur-3xl animate-blob animation-delay-2000" />
          <div className="absolute -bottom-40 left-1/3 w-[600px] h-[600px] bg-gradient-to-br from-blue-300/30 to-cyan-300/30 rounded-full blur-3xl animate-blob animation-delay-4000" />
        </div>
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />
      </div>

      {/* Floating orbs */}
      {isVisible && (
        <>
          <FloatingOrb className="w-32 h-32 top-20 left-[10%]" delay={0} />
          <FloatingOrb className="w-24 h-24 top-40 right-[15%]" delay={1} />
          <FloatingOrb className="w-40 h-40 bottom-32 left-[20%]" delay={2} />
          <FloatingOrb className="w-20 h-20 bottom-40 right-[25%]" delay={3} />
        </>
      )}

      {/* Content */}
      <div className="relative z-10 w-full max-w-6xl mx-auto px-4 sm:px-6 pt-6">
        {/* Navigation */}
        <motion.nav
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="flex justify-center mb-16"
        >
          <div className="flex items-center gap-3 px-2 py-2 bg-white/70 backdrop-blur-xl rounded-full border border-white/30 shadow-lg shadow-black/5">
            <a href="/" className="flex items-center pl-2">
              <img src="/logo.png" alt="metricx" className="h-8" />
            </a>
            <div className="hidden sm:flex items-center gap-1">
              {["Features", "Pricing"].map((item) => (
                <button
                  key={item}
                  onClick={() => document.getElementById(item.toLowerCase())?.scrollIntoView({ behavior: "smooth" })}
                  className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-white/50 rounded-full transition-all"
                >
                  {item}
                </button>
              ))}
            </div>
            <a
              href="/login"
              className="px-5 py-2 bg-gray-900 text-white text-sm font-medium rounded-full hover:bg-gray-800 transition-all shadow-lg shadow-gray-900/20"
            >
              Log in
            </a>
          </div>
        </motion.nav>

        {/* Hero content */}
        <div className="flex flex-col items-center text-center pt-8 pb-16">
          {/* Eyebrow badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 backdrop-blur-sm rounded-full border border-blue-500/20 mb-8"
          >
            <Sparkles className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">AI-Powered Marketing Intelligence</span>
          </motion.div>

          {/* Main headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight mb-6"
          >
            <span className="bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 bg-clip-text text-transparent">
              Stop Guessing.
            </span>
            <br />
            <span className="bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 bg-clip-text text-transparent">
              Start Scaling.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-lg sm:text-xl text-gray-600 max-w-xl mb-10 leading-relaxed"
          >
            Unify Google & Meta ads, ask questions in plain English,
            and know exactly where to spend your next dollar.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center gap-4 mb-16"
          >
            <a
              href="/dashboard"
              className="group flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 text-white text-base font-semibold rounded-full hover:shadow-xl hover:shadow-blue-500/25 transition-all duration-300 hover:-translate-y-0.5"
            >
              Start Free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
            <button
              onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}
              className="px-8 py-4 text-gray-600 text-base font-medium hover:text-gray-900 transition-colors"
            >
              See how it works
            </button>
          </motion.div>

          {/* Live metrics floating */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="flex flex-wrap justify-center gap-3 mb-12"
          >
            <LiveMetric label="ROAS" value="3.8x" change="12%" />
            <LiveMetric label="Revenue" value="$89.2K" change="18%" />
            <LiveMetric label="CPA" value="$24.50" change="8%" positive={false} />
          </motion.div>

          {/* Dashboard preview - glass card */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="w-full max-w-4xl"
          >
            <GlassCard className="p-6 sm:p-8" hover={false}>
              {/* Mock dashboard header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">AI Copilot</div>
                    <div className="text-xs text-gray-500">Ask anything about your ads</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 rounded-full">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-xs font-medium text-green-600">Live</span>
                </div>
              </div>

              {/* AI Chat preview */}
              <div className="mb-6 p-4 bg-gradient-to-r from-gray-50 to-blue-50/50 rounded-xl border border-gray-100">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-700 leading-relaxed">
                      Your <span className="font-semibold text-blue-600">Summer Sale campaign</span> is outperforming others with a 4.2x ROAS.
                      I recommend increasing its budget by 20% and pausing the "Brand Awareness" campaign which has a 0.8x ROAS.
                    </p>
                  </div>
                </div>
              </div>

              {/* Metrics grid */}
              <div className="grid grid-cols-3 gap-4">
                <FeaturePreview
                  icon={TrendingUp}
                  title="Total Revenue"
                  value="$89,247"
                  subtitle="+18.2% this week"
                  delay={0.7}
                />
                <FeaturePreview
                  icon={Zap}
                  title="ROAS"
                  value="3.63x"
                  subtitle="+5.8% vs last week"
                  delay={0.8}
                />
                <FeaturePreview
                  icon={Sparkles}
                  title="Conversions"
                  value="1,847"
                  subtitle="+124 today"
                  delay={0.9}
                />
              </div>
            </GlassCard>
          </motion.div>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent pointer-events-none" />

      {/* Shimmer animation styles */}
      <style jsx global>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 3s infinite;
        }
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          25% { transform: translate(20px, -30px) scale(1.1); }
          50% { transform: translate(-20px, 20px) scale(0.9); }
          75% { transform: translate(30px, 10px) scale(1.05); }
        }
        .animate-blob {
          animation: blob 15s infinite ease-in-out;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </section>
  );
}
