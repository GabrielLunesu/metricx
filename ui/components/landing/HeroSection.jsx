"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Bot, ArrowRight } from "lucide-react";
import { ShaderGradientCanvas, ShaderGradient } from "@shadergradient/react";

// Lazy load Cobe globe component
const Cobe = dynamic(
  () => import("@/components/ui/cobe-globe").then((mod) => ({ default: mod.Cobe })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full bg-gradient-to-br from-blue-100 to-cyan-100 rounded-lg animate-pulse" />
    ),
  }
);

function FeatureCard({ title, description, isActive, progress, onClick }) {
  return (
    <div
      className={`w-full md:flex-1 self-stretch px-6 py-5 overflow-hidden flex flex-col justify-start items-start gap-2 cursor-pointer relative transition-all duration-300 rounded-xl mx-1 my-1 ${isActive
        ? "bg-gradient-to-br from-blue-50 to-cyan-50 shadow-lg scale-[1.02] border border-blue-200"
        : "bg-white hover:bg-gray-50 border border-transparent"
        }`}
      onClick={onClick}
    >
      {/* Progress bar at top */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gray-100 rounded-t-xl overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-100 ease-linear ${isActive ? "opacity-100" : "opacity-0"}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className={`self-stretch flex justify-center flex-col text-sm font-bold leading-6 transition-colors ${isActive ? "text-blue-600" : "text-black"}`}>
        {title}
      </div>
      <div className="self-stretch text-gray-500 text-[13px] font-normal leading-[22px]">
        {description}
      </div>
    </div>
  );
}

const scrollToSection = (sectionId) => {
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

export default function HeroSection() {
  const [activeCard, setActiveCard] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  const mountedRef = useRef(true);
  const heroRef = useRef(null);

  // Track visibility - unmount shader when scrolled away to free GPU memory
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0, rootMargin: "200px" }
    );

    if (heroRef.current) {
      observer.observe(heroRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // Progress interval for card rotation
  useEffect(() => {
    if (!isVisible) return;

    const progressInterval = setInterval(() => {
      if (!mountedRef.current) return;

      setProgress((prev) => {
        if (prev >= 100) {
          if (mountedRef.current) {
            setActiveCard((current) => (current + 1) % 3);
          }
          return 0;
        }
        return prev + 2;
      });
    }, 100);

    return () => {
      clearInterval(progressInterval);
      mountedRef.current = false;
    };
  }, [isVisible]);

  const handleCardClick = (index) => {
    if (!mountedRef.current) return;
    setActiveCard(index);
    setProgress(0);
  };

  const features = [
    {
      title: "AI Copilot",
      description: "Ask any question in plain English. Get instant insights on ROAS, spend, and performance.",
    },
    {
      title: "Unified Analytics",
      description: "Meta + Google in one view. Compare platforms side-by-side with consistent metrics.",
    },
    {
      title: "Finance & P&L",
      description: "Track every dollar. See budget vs actuals with real-time profit calculations.",
    },
  ];

  const navItems = [
    { label: "How It Works", href: "how-it-works" },
    { label: "Features", href: "features" },
    { label: "Pricing", href: "pricing" },
  ];

  return (
    <>
      {/* Shader gradient background - unmounts when scrolled past hero to free GPU memory */}
      <div className="shader-gradient-fixed">
        {isVisible ? (
          <ShaderGradientCanvas
            style={{ width: "100%", height: "100%" }}
            pixelDensity={1}
            pointerEvents="none"
          >
            <ShaderGradient
              animate="on"
              type="sphere"
              wireframe={false}
              shader="defaults"
              uTime={0}
              uSpeed={0.2}
              uStrength={0.3}
              uDensity={0.8}
              uFrequency={5.5}
              uAmplitude={3.2}
              positionX={-0.1}
              positionY={0}
              positionZ={0}
              rotationX={0}
              rotationY={130}
              rotationZ={70}
              color1="#3B82F6"
              color2="#06B6D4"
              color3="#ffffff"
              reflection={0.4}
              cAzimuthAngle={270}
              cPolarAngle={180}
              cDistance={0.5}
              cameraZoom={15.1}
              lightType="env"
              brightness={1.2}
              envPreset="city"
              grain="on"
              toggleAxis={false}
              zoomOut={false}
              enableTransition={false}
            />
          </ShaderGradientCanvas>
        ) : (
          // Static fallback when scrolled past - no GPU usage
          <div className="w-full h-full bg-gradient-to-br from-blue-500 via-cyan-500 to-blue-600" />
        )}
      </div>

      <div ref={heroRef} className="relative w-full overflow-hidden min-h-screen">
        {/* Fade to white at bottom of hero */}
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-white to-transparent pointer-events-none z-[1]" />

        <div className="w-full max-w-[1060px] mx-auto relative z-10">

          {/* Navigation */}
          <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="w-full py-4 px-4 sm:px-6 lg:px-0 flex justify-center items-center relative z-20"
          >
            <div className="w-full max-w-[700px] h-12 px-4 bg-white backdrop-blur-lg shadow-[0_4px_20px_rgba(0,0,0,0.1)] rounded-full flex justify-between items-center">
              {/* Logo */}
              <a href="/" className="flex items-center">
                <img src="/logo.png" alt="metricx" className="h-12 sm:h-12" />
              </a>

              {/* Centered Nav Items */}
              <div className="hidden sm:flex items-center justify-center gap-6 absolute left-1/2 -translate-x-1/2">
                {navItems.map((item) => (
                  <button
                    key={item.href}
                    onClick={() => scrollToSection(item.href)}
                    className="text-gray-600 text-sm font-medium hover:text-black transition-colors"
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {/* Login Button */}
              <a
                href="/login"
                className="px-4 py-1.5 bg-black text-white text-sm font-medium rounded-full hover:bg-gray-800 transition-colors"
              >
                Log in
              </a>
            </div>
          </motion.nav>

          {/* Hero Content */}
          <div className="pt-12 sm:pt-16 md:pt-20 pb-8 px-4 sm:px-6 lg:px-0 flex flex-col items-center">
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="text-center max-w-[800px] mx-auto"
            >
              <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight">
                <span className="text-white drop-shadow-lg">Stop Guessing.</span>
                <br />
                <span className="text-white drop-shadow-lg">Start Scaling.</span>
              </h1>
              <p className="mt-6 text-lg sm:text-xl text-white/90 max-w-[540px] mx-auto leading-relaxed drop-shadow">
                The AI marketing copilot that unifies your Google & Meta ads, answers questions in plain English, and shows you exactly where to spend your next dollar.
              </p>
            </motion.div>

            {/* CTA Button */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="mt-8"
            >
              <a
                href="/dashboard"
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-black text-base font-medium rounded-full hover:bg-white/90 transition-colors group shadow-xl"
              >
                Start for free
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </a>
            </motion.div>

            {/* Dashboard Preview with Globe */}
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="w-full max-w-[960px] mt-12 sm:mt-16"
            >
              <div className="bg-white rounded-xl shadow-[0_0_0_1px_rgba(0,0,0,0.06),0_8px_40px_rgba(0,0,0,0.08)] overflow-hidden">
                <div className="grid md:grid-cols-2 gap-0">
                  {/* Left side - Metrics */}
                  <div className="p-6 sm:p-8 border-b md:border-b-0 md:border-r border-gray-100">
                    <div className="flex flex-col gap-6">
                      {/* AI Copilot Preview */}
                      <div
                        className={`transition-all duration-500 ${activeCard === 0 ? "opacity-100" : "opacity-0 absolute pointer-events-none"
                          }`}
                      >
                        <div className="flex items-start gap-3 mb-4">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-white" strokeWidth={2} />
                          </div>
                          <div className="flex-1 bg-gray-50 rounded-2xl rounded-tl-sm p-4">
                            <p className="text-sm text-gray-700">Your ROAS increased by 18% this week. Campaign "Summer Sale" is your top performer at 4.2x.</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 mb-1">Revenue</p>
                            <p className="text-2xl font-bold text-black">$89.2K</p>
                            <span className="text-xs text-green-500 font-medium">+18.2%</span>
                          </div>
                          <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 mb-1">ROAS</p>
                            <p className="text-2xl font-bold text-black">3.63x</p>
                            <span className="text-xs text-green-500 font-medium">+5.8%</span>
                          </div>
                        </div>
                      </div>

                      {/* Analytics Preview */}
                      <div
                        className={`transition-all duration-500 ${activeCard === 1 ? "opacity-100" : "opacity-0 absolute pointer-events-none"
                          }`}
                      >
                        <div className="grid grid-cols-3 gap-3 mb-4">
                          <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-400 mb-1">Spend</p>
                            <p className="text-lg font-bold text-black">$24.5K</p>
                          </div>
                          <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-400 mb-1">Revenue</p>
                            <p className="text-lg font-bold text-black">$89.2K</p>
                          </div>
                          <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-400 mb-1">ROAS</p>
                            <p className="text-lg font-bold text-black">3.63x</p>
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4 h-32">
                          <div className="h-full flex items-end justify-between gap-1.5">
                            {[35, 52, 45, 68, 78, 92, 65, 82, 88, 70, 85, 95].map((h, i) => (
                              <div
                                key={i}
                                className="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t"
                                style={{ height: `${h}%` }}
                              />
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Finance Preview */}
                      <div
                        className={`transition-all duration-500 ${activeCard === 2 ? "opacity-100" : "opacity-0 absolute pointer-events-none"
                          }`}
                      >
                        <div className="grid grid-cols-2 gap-3 mb-4">
                          <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 mb-1">Ad Spend</p>
                            <p className="text-xl font-bold text-black">$24,500</p>
                            <span className="text-xs text-green-500 font-medium">Under budget</span>
                          </div>
                          <div className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xs text-gray-400 mb-1">Net Profit</p>
                            <p className="text-xl font-bold text-black">$64,700</p>
                            <span className="text-xs text-green-500 font-medium">+22% MoM</span>
                          </div>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Revenue</span>
                            <span className="font-semibold text-black">$89,200</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Ad Spend</span>
                            <span className="font-semibold text-red-500">-$24,500</span>
                          </div>
                          <div className="flex justify-between text-sm pt-2 border-t border-gray-200">
                            <span className="font-semibold text-black">Profit</span>
                            <span className="font-bold text-green-500">$64,700</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right side - Globe with glow effect */}
                  <div className="p-6 sm:p-8 bg-white flex items-center justify-center min-h-[300px] md:min-h-[400px] relative overflow-hidden">
                    {/* Subtle glow effects on white bg */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 bg-blue-400/20 rounded-full blur-3xl" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-cyan-400/30 rounded-full blur-2xl" />

                    <div className="relative z-10 h-[300px] w-full max-w-[300px] overflow-hidden rounded-lg">
                      <Cobe
                        variant="default"
                        phi={0}
                        theta={0.2}
                        mapSamples={16000}
                        mapBrightness={1.2}
                        mapBaseBrightness={0.05}
                        diffuse={3}
                        dark={0}
                        baseColor="#ffffff"
                        markerColor="#3b82f6"
                        markerSize={0.07}
                        glowColor="#60a5fa"
                        scale={1.0}
                        offsetX={0.0}
                        offsetY={0.0}
                        opacity={1}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Feature Cards */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
              className="w-full max-w-[960px] mt-4 p-2 bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg"
            >
              <div className="flex flex-col md:flex-row gap-1">
                {features.map((feature, index) => (
                  <FeatureCard
                    key={index}
                    title={feature.title}
                    description={feature.description}
                    isActive={activeCard === index}
                    progress={activeCard === index ? progress : 0}
                    onClick={() => handleCardClick(index)}
                  />
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </>
  );
}
