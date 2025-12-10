"use client";

/**
 * HeroSection - Minimalistic landing page hero with visual data flow
 * Shows ad platforms connecting through AI to deliver insights
 * Related: page.jsx, FeaturesSection.jsx
 */

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { LiquidMetal } from '@paper-design/shaders-react';

const logo = "/logo-white.webp";

// Platform icon components
function MetaIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 0 0 8.44-9.9c0-5.53-4.5-10.02-10-10.02z" />
    </svg>
  );
}

function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

function TikTokIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" />
    </svg>
  );
}

// Animated connection line
function ConnectionLine({ from, to, delay = 0, color = "blue" }) {
  const colors = {
    blue: "from-blue-500 to-cyan-500",
    purple: "from-purple-500 to-pink-500",
    green: "from-green-500 to-emerald-500",
  };

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ left: from.x, top: from.y }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay, duration: 0.5 }}
    >
      <svg
        width={Math.abs(to.x - from.x) + 20}
        height={Math.abs(to.y - from.y) + 20}
        className="overflow-visible"
      >
        <defs>
          <linearGradient id={`gradient-${color}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color === "blue" ? "#3B82F6" : color === "purple" ? "#A855F7" : "#22C55E"} />
            <stop offset="100%" stopColor={color === "blue" ? "#06B6D4" : color === "purple" ? "#EC4899" : "#10B981"} />
          </linearGradient>
        </defs>
        <motion.path
          d={`M 0 0 Q ${(to.x - from.x) / 2} ${(to.y - from.y) / 4} ${to.x - from.x} ${to.y - from.y}`}
          fill="none"
          stroke={`url(#gradient-${color})`}
          strokeWidth="2"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ delay: delay + 0.3, duration: 1.5, ease: "easeInOut" }}
        />
        {/* Animated dot along path */}
        <motion.circle
          r="4"
          fill={color === "blue" ? "#3B82F6" : color === "purple" ? "#A855F7" : "#22C55E"}
          initial={{ opacity: 0 }}
          animate={{
            opacity: [0, 1, 1, 0],
            offsetDistance: ["0%", "100%"],
          }}
          transition={{
            delay: delay + 1,
            duration: 2,
            repeat: Infinity,
            repeatDelay: 1,
          }}
          style={{
            offsetPath: `path("M 0 0 Q ${(to.x - from.x) / 2} ${(to.y - from.y) / 4} ${to.x - from.x} ${to.y - from.y}")`,
          }}
        />
      </svg>
    </motion.div>
  );
}

// Floating platform card
function PlatformCard({ icon: Icon, name, position, delay, color }) {
  const colorClasses = {
    blue: "from-blue-500/20 to-blue-600/20 border-blue-500/30 shadow-blue-500/20",
    purple: "from-purple-500/20 to-purple-600/20 border-purple-500/30 shadow-purple-500/20",
    black: "from-gray-800/20 to-gray-900/20 border-gray-500/30 shadow-gray-500/20",
  };

  const iconColors = {
    blue: "text-blue-500",
    purple: "text-purple-500",
    black: "text-gray-800",
  };

  return (
    <motion.div
      className={`absolute ${position}`}
      initial={{ opacity: 0, scale: 0.8, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay, duration: 0.6, ease: "easeOut" }}
    >
      <motion.div
        className={`flex items-center gap-3 px-5 py-3 bg-gradient-to-br ${colorClasses[color]} backdrop-blur-xl rounded-2xl border shadow-lg`}
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: delay * 2 }}
      >
        <Icon className={`w-6 h-6 ${iconColors[color]}`} />
        <span className="text-sm font-semibold text-gray-800">{name}</span>
      </motion.div>
    </motion.div>
  );
}

// Central AI hub visualization
function AIHub() {
  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.8, duration: 0.8, ease: "easeOut" }}
    >
      {/* Outer glow rings */}
      <motion.div
        className="absolute inset-0 -m-8 rounded-full bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-blue-500/10"
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute inset-0 -m-4 rounded-full bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-cyan-500/20"
        animate={{ scale: [1, 1.1, 1], opacity: [0.6, 0.3, 0.6] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
      />

      {/* Core hub */}
      <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-2xl shadow-blue-500/40">
        <motion.div
          className="absolute inset-1 rounded-full bg-white/20"
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        />
        <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
        </svg>
      </div>
    </motion.div>
  );
}

// User insight card
function InsightCard({ delay }) {
  return (
    <motion.div
      className="absolute right-8 sm:right-16 top-1/2 -translate-y-1/2"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.6, ease: "easeOut" }}
    >
      <motion.div
        className="p-4 bg-white/80 backdrop-blur-xl rounded-2xl border border-gray-200/50 shadow-xl shadow-gray-200/50 max-w-[180px]"
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <span className="text-xs font-medium text-gray-500">Insights</span>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">ROAS</span>
            <span className="text-sm font-bold text-gray-900">4.2x</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-green-400 to-emerald-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: "84%" }}
              transition={{ delay: delay + 0.5, duration: 1, ease: "easeOut" }}
            />
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// Data flow visualization container
function DataFlowVisualization() {
  const containerRef = useRef(null);

  return (
    <div ref={containerRef} className="relative w-full max-w-3xl h-64 sm:h-80 mx-auto">
      {/* Platform cards - left side */}
      <PlatformCard
        icon={MetaIcon}
        name="Meta Ads"
        position="left-0 sm:left-8 top-4"
        delay={0.2}
        color="blue"
      />
      <PlatformCard
        icon={GoogleIcon}
        name="Google Ads"
        position="left-0 sm:left-4 top-1/2 -translate-y-1/2"
        delay={0.4}
        color="purple"
      />
      <PlatformCard
        icon={TikTokIcon}
        name="TikTok Ads"
        position="left-0 sm:left-8 bottom-4"
        delay={0.6}
        color="black"
      />

      {/* Center AI hub */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <AIHub />
      </div>

      {/* Insight card - right side */}
      <InsightCard delay={1.2} />

      {/* Animated connection particles */}
      <DataParticles />
    </div>
  );
}

// Floating data particles
function DataParticles() {
  const particles = Array.from({ length: 6 }, (_, i) => i);

  return (
    <>
      {particles.map((i) => (
        <motion.div
          key={i}
          className="absolute w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500"
          style={{
            left: `${15 + Math.random() * 20}%`,
            top: `${20 + Math.random() * 60}%`,
          }}
          animate={{
            x: [0, 150, 300],
            opacity: [0, 1, 0],
            scale: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: i * 0.5,
            ease: "easeInOut",
          }}
        />
      ))}
    </>
  );
}

export default function HeroSection() {
  const [isVisible, setIsVisible] = useState(true);
  const heroRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0, rootMargin: "200px" }
    );
    if (heroRef.current) observer.observe(heroRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={heroRef} className="relative w-full min-h-screen overflow-hidden flex flex-col">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-gray-50 via-white to-gray-50">
        {/* Subtle radial gradient accent */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-radial from-blue-100/40 via-transparent to-transparent rounded-full blur-3xl" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-8">
        {/* Logo with LiquidMetal effect */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="mb-4"
        >
          <div className="h-28 sm:h-36 md:h-44 w-full max-w-2xl mx-auto relative flex items-center justify-center overflow-hidden">
            <LiquidMetal
              width={1280}
              height={720}
              image={logo}
              colorBack="#ffffff00"
              colorTint="#00aaff"
              shape={undefined}
              repetition={6.59}
              softness={0.35}
              shiftRed={0.3}
              shiftBlue={0.3}
              distortion={0.07}
              contour={0.15}
              angle={70}
              speed={1}
              scale={1}
              fit="contain"
            />
          </div>
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-base sm:text-lg text-gray-500 text-center max-w-md mb-8 font-light"
        >
          Unify your ads. Understand your data. Optimize everything.
        </motion.p>

        {/* Auth buttons */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="flex items-center gap-4 mb-16"
        >
          <a
            href="/sign-in"
            className="px-8 py-3 text-gray-700 text-sm font-medium rounded-full border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200"
          >
            Login
          </a>
          <a
            href="/sign-up"
            className="px-8 py-3 bg-gray-900 text-white text-sm font-medium rounded-full hover:bg-gray-800 transition-all duration-200 shadow-lg shadow-gray-900/20"
          >
            Register
          </a>
        </motion.div>

        {/* Data flow visualization */}
        {isVisible && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 1 }}
            className="w-full"
          >
            <DataFlowVisualization />
          </motion.div>
        )}
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent pointer-events-none" />

      {/* Minimal styles */}
      <style jsx global>{`
        .bg-gradient-radial {
          background: radial-gradient(circle, var(--tw-gradient-stops));
        }
      `}</style>
    </section>
  );
}
