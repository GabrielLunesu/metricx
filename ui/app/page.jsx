/**
 * HomePage - metricx Landing Page
 * ================================
 *
 * WHAT: Apple-style product launch landing page
 * WHY: Present metricx like a premium product launch
 *
 * DESIGN: Minimal, blue & white only
 * - Typography: SF Pro Display, clean hierarchy
 * - Colors: Blue (#0071E3) and white only
 * - Animated blue mesh gradient shader
 * - Apple product launch presentation style
 *
 * PRICING: Free tier + Starter ($29.99/mo or $196/yr)
 */

"use client";

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  Zap,
  BarChart3,
  TrendingUp,
  Shield,
  Activity,
  Check,
  ChevronDown,
  Lock,
  Brain,
  Mail,
  Send,
} from 'lucide-react';

/**
 * Blue Mesh Gradient Shader - Paper.design inspired
 * Pure blue and white, smooth organic movement
 */
function BlueShader() {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth * 2;
      canvas.height = window.innerHeight * 2;
      canvas.style.width = window.innerWidth + 'px';
      canvas.style.height = window.innerHeight + 'px';
    };
    resize();
    window.addEventListener('resize', resize);

    const animate = () => {
      time += 0.002;
      const { width, height } = canvas;

      // Clear with white
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);

      // Primary blue orb - slow drift
      const gradient1 = ctx.createRadialGradient(
        width * (0.3 + Math.sin(time * 0.5) * 0.15),
        height * (0.2 + Math.cos(time * 0.3) * 0.1),
        0,
        width * 0.5,
        height * 0.5,
        width * 0.7
      );
      gradient1.addColorStop(0, 'rgba(0, 113, 227, 0.08)');
      gradient1.addColorStop(0.4, 'rgba(0, 113, 227, 0.04)');
      gradient1.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = gradient1;
      ctx.fillRect(0, 0, width, height);

      // Secondary blue orb
      const gradient2 = ctx.createRadialGradient(
        width * (0.7 + Math.cos(time * 0.4) * 0.12),
        height * (0.6 + Math.sin(time * 0.6) * 0.15),
        0,
        width * 0.5,
        height * 0.5,
        width * 0.5
      );
      gradient2.addColorStop(0, 'rgba(0, 122, 255, 0.06)');
      gradient2.addColorStop(0.5, 'rgba(0, 122, 255, 0.02)');
      gradient2.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = gradient2;
      ctx.fillRect(0, 0, width, height);

      // Subtle third orb for depth
      const gradient3 = ctx.createRadialGradient(
        width * (0.5 + Math.sin(time * 0.7) * 0.2),
        height * (0.8 + Math.cos(time * 0.5) * 0.1),
        0,
        width * 0.5,
        height * 0.5,
        width * 0.4
      );
      gradient3.addColorStop(0, 'rgba(10, 132, 255, 0.05)');
      gradient3.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = gradient3;
      ctx.fillRect(0, 0, width, height);

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 -z-10 pointer-events-none"
      style={{ filter: 'blur(80px)' }}
    />
  );
}

export default function HomePage() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('scroll-enter-active');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    document.querySelectorAll('.scroll-enter').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="antialiased overflow-x-hidden selection:bg-blue-100 selection:text-blue-900 text-neutral-900 bg-white">
      {/* Blue Mesh Shader Background */}
      <BlueShader />

      <Navigation />
      <HeroSection />
      <ProductShowcase />
      <FeaturesSection />
      <PricingSection />
      <FooterCTA />
      <Footer />
    </main>
  );
}

/**
 * Navigation - Apple-style minimal
 */
function Navigation() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-white/80 backdrop-blur-xl' : ''
    }`}>
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.png"
            alt="metricx"
            width={120}
            height={32}
            className="h-7 w-auto"
            priority
          />
        </Link>

        <div className="hidden md:flex items-center gap-8">
          <Link href="#features" className="text-sm text-neutral-500 hover:text-neutral-900 transition-colors">
            Features
          </Link>
          <Link href="#pricing" className="text-sm text-neutral-500 hover:text-neutral-900 transition-colors">
            Pricing
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm text-neutral-500 hover:text-neutral-900 transition-colors hidden sm:block">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="text-sm text-white bg-[#0071E3] hover:bg-[#0077ED] rounded-full py-2.5 px-5 font-medium transition-colors"
          >
            Get started
          </Link>
        </div>
      </div>
    </nav>
  );
}

/**
 * HeroSection - Apple product launch style
 */
function HeroSection() {
  return (
    <section className="min-h-[90vh] flex flex-col justify-center relative pt-24 pb-20 px-6">
      <div className="max-w-4xl mx-auto w-full text-center">
        {/* Headline - Clean, not oversized */}
        <h1 className="scroll-enter">
          <span className="font-heading text-5xl md:text-6xl lg:text-7xl leading-[1.05] tracking-[-0.02em] text-neutral-900 block">
            Ad analytics.
          </span>
          <span className="font-heading text-5xl md:text-6xl lg:text-7xl leading-[1.05] tracking-[-0.02em] block mt-1">
            <span className="text-[#0071E3]">Reimagined.</span>
          </span>
        </h1>

        {/* Subheadline */}
        <p className="mt-8 text-xl md:text-2xl text-neutral-500 max-w-2xl mx-auto leading-relaxed scroll-enter delay-100">
          Unified dashboard. Autonomous agents. AI copilot.
        </p>

        {/* CTA */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center scroll-enter delay-200">
          <Link
            href="/signup"
            className="px-8 py-4 bg-[#0071E3] hover:bg-[#0077ED] text-white rounded-full font-medium text-lg transition-colors flex items-center justify-center gap-2"
          >
            Start free trial
            <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="#features"
            className="px-8 py-4 text-[#0071E3] rounded-full font-medium text-lg transition-colors hover:bg-blue-50 flex items-center justify-center"
          >
            Learn more
          </Link>
        </div>

        {/* Platform Integration */}
        <div className="mt-16 flex items-center justify-center gap-4 scroll-enter delay-300">
          <span className="text-sm text-neutral-400">Works with</span>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-neutral-200 shadow-sm">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.879V14.89h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.989C18.343 21.129 22 16.99 22 12c0-5.523-4.477-10-10-10z" fill="#1877F2"/>
              </svg>
              <span className="text-xs font-medium text-neutral-600">Meta</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-neutral-200 shadow-sm">
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              <span className="text-xs font-medium text-neutral-600">Google</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * ProductShowcase - Apple-style product sections
 */
function ProductShowcase() {
  return (
    <section id="product" className="py-24 lg:py-32">
      <div className="max-w-6xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center mb-20 scroll-enter">
          <h2 className="font-heading text-4xl md:text-5xl text-neutral-900 tracking-tight mb-4">
            Three tools. One platform.
          </h2>
          <p className="text-xl text-neutral-500 max-w-2xl mx-auto">
            Everything you need to understand and optimize your ad spend.
          </p>
        </div>

        {/* Product Cards */}
        <div className="space-y-16 lg:space-y-24">
          <ProductCard
            number="01"
            title="Analytics"
            tagline="See everything. Instantly."
            description="Unified dashboard with real-time data from Meta and Google. Track ROAS, spend, and conversions in one view."
          >
            <AnalyticsDemo />
          </ProductCard>

          <ProductCard
            number="02"
            title="Agents"
            tagline="Automation that thinks."
            description="Define rules. Agents execute 24/7. Scale winners, pause losers, send alerts—automatically."
          >
            <AgentsDemo />
          </ProductCard>

          <ProductCard
            number="03"
            title="Copilot"
            tagline="Ask anything."
            description="Natural language interface to your ad data. Get insights in seconds, not hours."
          >
            <CopilotDemo />
          </ProductCard>
        </div>
      </div>
    </section>
  );
}

/**
 * ProductCard - Clean product showcase card
 */
function ProductCard({ number, title, tagline, description, children }) {
  return (
    <div className="scroll-enter">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-mono text-[#0071E3]">{number}</span>
            <div className="h-px w-8 bg-[#0071E3]" />
          </div>
          <h3 className="font-heading text-3xl lg:text-4xl text-neutral-900 tracking-tight">
            {title}
          </h3>
          <p className="text-lg text-neutral-400 mt-1">{tagline}</p>
        </div>
        <p className="text-neutral-500 max-w-md leading-relaxed">
          {description}
        </p>
      </div>

      {/* Browser Frame */}
      <div className="bg-neutral-900 rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-4 py-3 flex items-center gap-2 border-b border-neutral-800">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-neutral-700" />
            <div className="w-3 h-3 rounded-full bg-neutral-700" />
            <div className="w-3 h-3 rounded-full bg-neutral-700" />
          </div>
          <div className="flex-1 flex justify-center">
            <div className="bg-neutral-800 rounded-md px-3 py-1 text-xs text-neutral-500 flex items-center gap-1.5">
              <Lock className="w-3 h-3" />
              app.metricx.io
            </div>
          </div>
        </div>
        <div className="bg-[#fafafa] p-6 min-h-[420px]">
          {children}
        </div>
      </div>
    </div>
  );
}

/**
 * AnalyticsDemo - Clean dashboard with blue-only theme
 */
function AnalyticsDemo() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const chartData = [
    { day: 'Mon', revenue: 14200, spend: 3400 },
    { day: 'Tue', revenue: 12800, spend: 3100 },
    { day: 'Wed', revenue: 18400, spend: 4200 },
    { day: 'Thu', revenue: 15600, spend: 3800 },
    { day: 'Fri', revenue: 21200, spend: 4800 },
    { day: 'Sat', revenue: 19800, spend: 4500 },
    { day: 'Sun', revenue: 20340, spend: 4780 },
  ];

  const maxRevenue = Math.max(...chartData.map(d => d.revenue));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-heading text-lg text-neutral-900">Performance</h3>
          <p className="text-xs text-neutral-500">Real-time data</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-neutral-100 rounded-lg text-xs text-neutral-600">
          Last 7 days
          <ChevronDown className="w-3 h-3" />
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Spend', value: '$24,580', change: '-8%', positive: false },
          { label: 'Revenue', value: '$102,340', change: '+23%', positive: true },
          { label: 'ROAS', value: '4.16x', change: '+0.4x', positive: true },
          { label: 'Conversions', value: '1,847', change: '+156', positive: true },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-lg p-3 border border-neutral-200">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider">{kpi.label}</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                kpi.positive ? 'bg-blue-50 text-[#0071E3]' : 'bg-neutral-100 text-neutral-500'
              }`}>
                {kpi.change}
              </span>
            </div>
            <p className="text-lg font-bold text-neutral-900 tracking-tight">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg p-4 border border-neutral-200">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-neutral-900">Revenue vs Spend</h4>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#0071E3]" />
              Revenue
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-neutral-300" />
              Spend
            </span>
          </div>
        </div>

        <div className="h-36 relative">
          <svg viewBox="0 0 700 150" className="w-full h-full" preserveAspectRatio="none">
            {[0, 1, 2, 3].map((i) => (
              <line key={i} x1="0" y1={i * 50} x2="700" y2={i * 50} stroke="#f5f5f5" strokeWidth="1" />
            ))}

            <defs>
              <linearGradient id="blueGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#0071E3" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#0071E3" stopOpacity="0" />
              </linearGradient>
            </defs>

            <path
              d={`M0,${150 - (chartData[0].revenue / maxRevenue) * 130} ${chartData.map((d, i) =>
                `L${(i / 6) * 700},${150 - (d.revenue / maxRevenue) * 130}`
              ).join(' ')} L700,150 L0,150 Z`}
              fill="url(#blueGradient)"
              className={`transition-opacity duration-1000 ${mounted ? 'opacity-100' : 'opacity-0'}`}
            />

            <path
              d={`M0,${150 - (chartData[0].revenue / maxRevenue) * 130} ${chartData.map((d, i) =>
                `L${(i / 6) * 700},${150 - (d.revenue / maxRevenue) * 130}`
              ).join(' ')}`}
              fill="none"
              stroke="#0071E3"
              strokeWidth="2.5"
              strokeLinecap="round"
              className={`transition-opacity duration-1000 ${mounted ? 'opacity-100' : 'opacity-0'}`}
            />

            <path
              d={`M0,${150 - (chartData[0].spend / maxRevenue) * 130} ${chartData.map((d, i) =>
                `L${(i / 6) * 700},${150 - (d.spend / maxRevenue) * 130}`
              ).join(' ')}`}
              fill="none"
              stroke="#d4d4d4"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="4 4"
              className={`transition-opacity duration-1000 delay-300 ${mounted ? 'opacity-100' : 'opacity-0'}`}
            />

            {chartData.map((d, i) => (
              <circle
                key={i}
                cx={(i / 6) * 700}
                cy={150 - (d.revenue / maxRevenue) * 130}
                r="4"
                fill="#0071E3"
                stroke="white"
                strokeWidth="2"
                className={`transition-opacity duration-500 ${mounted ? 'opacity-100' : 'opacity-0'}`}
                style={{ transitionDelay: `${i * 100 + 500}ms` }}
              />
            ))}
          </svg>

          <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[10px] text-neutral-400 -mb-4">
            {chartData.map((d) => <span key={d.day}>{d.day}</span>)}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * AgentsDemo - Shows agent rules with animated decision tree (blue-only)
 */
function AgentsDemo() {
  const [triggered, setTriggered] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTriggered(true);
      const stepTimer = setInterval(() => {
        setStep(prev => {
          if (prev >= 3) {
            clearInterval(stepTimer);
            return prev;
          }
          return prev + 1;
        });
      }, 600);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-heading text-lg text-neutral-900">Agent Rules</h3>
          <p className="text-xs text-neutral-500">Define conditions → Agent executes</p>
        </div>
        <span className="px-3 py-1.5 bg-blue-50 text-[#0071E3] rounded-full text-xs font-medium flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0071E3] animate-pulse" />
          Live
        </span>
      </div>

      {/* Agent Rule Card */}
      <div className="bg-white rounded-xl p-5 border border-blue-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-[#0071E3] flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-semibold text-neutral-900">Scale Winners</h4>
            <p className="text-xs text-neutral-500">Monitors every 30 min</p>
          </div>
        </div>

        {/* Rule Definition */}
        <div className="bg-neutral-50 rounded-lg p-3 mb-4 font-mono text-sm">
          <div className="flex items-center gap-2 text-neutral-600 flex-wrap">
            <span className="text-[#0071E3] font-semibold">IF</span>
            <span className="px-2 py-0.5 bg-blue-100 text-[#0071E3] rounded text-xs">ROAS</span>
            <span className="text-neutral-400">&gt;</span>
            <span className="px-2 py-0.5 bg-blue-100 text-[#0071E3] rounded text-xs font-semibold">3.0x</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-600 mt-2 flex-wrap">
            <span className="text-[#0071E3] font-semibold">THEN</span>
            <span className="px-2 py-0.5 bg-blue-50 text-neutral-700 rounded text-xs">Scale +25%</span>
            <span className="text-neutral-400">+</span>
            <span className="px-2 py-0.5 bg-blue-50 text-neutral-700 rounded text-xs">Slack alert</span>
          </div>
        </div>

        {/* Animated Flow */}
        <div className="flex items-center justify-between gap-2">
          {/* Step 1 */}
          <div className={`flex flex-col items-center transition-all duration-500 ${triggered ? 'opacity-100' : 'opacity-40'}`}>
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
              triggered ? 'bg-[#0071E3] shadow-lg' : 'bg-neutral-200'
            }`}>
              <Activity className={`w-4 h-4 ${triggered ? 'text-white' : 'text-neutral-400'}`} />
            </div>
            <span className="text-[10px] text-neutral-500 mt-1.5">Evaluate</span>
          </div>

          <div className={`flex-1 h-0.5 transition-all duration-500 ${step >= 1 ? 'bg-[#0071E3]' : 'bg-neutral-200'}`} />

          {/* Step 2 */}
          <div className={`flex flex-col items-center transition-all duration-500 ${step >= 1 ? 'opacity-100' : 'opacity-40'}`}>
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
              step >= 1 ? 'bg-[#0071E3] shadow-lg' : 'bg-neutral-200'
            }`}>
              <Check className={`w-4 h-4 ${step >= 1 ? 'text-white' : 'text-neutral-400'}`} />
            </div>
            <span className="text-[10px] text-neutral-500 mt-1.5">Condition</span>
          </div>

          <div className={`flex-1 h-0.5 transition-all duration-500 ${step >= 2 ? 'bg-[#0071E3]' : 'bg-neutral-200'}`} />

          {/* Step 3 */}
          <div className={`flex flex-col items-center transition-all duration-500 ${step >= 2 ? 'opacity-100' : 'opacity-40'}`}>
            <div className="flex gap-1">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
                step >= 2 ? 'bg-[#0071E3] shadow-lg' : 'bg-neutral-200'
              }`}>
                <TrendingUp className={`w-4 h-4 ${step >= 2 ? 'text-white' : 'text-neutral-400'}`} />
              </div>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
                step >= 3 ? 'bg-[#0071E3] shadow-lg' : 'bg-neutral-200'
              }`}>
                <Mail className={`w-4 h-4 ${step >= 3 ? 'text-white' : 'text-neutral-400'}`} />
              </div>
            </div>
            <span className="text-[10px] text-neutral-500 mt-1.5">Actions</span>
          </div>
        </div>

        {/* Result */}
        {step >= 3 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <p className="text-sm font-medium text-neutral-900">Budget scaled +25%</p>
            <p className="text-xs text-neutral-500">Notification sent to #marketing</p>
          </div>
        )}
      </div>

      {/* More Rules */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { name: 'Pause Losers', rule: 'IF CTR < 1%' },
          { name: 'Daily Report', rule: 'Every 9am' },
        ].map((agent) => (
          <div key={agent.name} className="bg-white rounded-lg p-3 border border-neutral-200">
            <div className="flex items-center gap-2 mb-1">
              <Bot className="w-3.5 h-3.5 text-neutral-400" />
              <span className="text-sm font-medium text-neutral-900">{agent.name}</span>
            </div>
            <p className="text-xs text-neutral-500 font-mono">{agent.rule}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * CopilotDemo - AI chat interface (blue-only)
 */
function CopilotDemo() {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#0071E3] flex items-center justify-center">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-heading text-lg text-neutral-900">AI Copilot</h3>
          <p className="text-xs text-neutral-500">Ask anything about your ads</p>
        </div>
      </div>

      {/* Chat */}
      <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div className="p-5 space-y-4 min-h-[280px]">
          {/* User Message */}
          <div className="flex justify-end">
            <div className="bg-[#0071E3] text-white rounded-2xl rounded-br-sm px-4 py-2.5 max-w-xs">
              <p className="text-sm">Which campaigns have the best ROAS?</p>
            </div>
          </div>

          {/* AI Response */}
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-[#0071E3] flex items-center justify-center flex-shrink-0">
              <Brain className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="bg-neutral-50 rounded-2xl rounded-tl-sm px-4 py-3 max-w-sm">
              <p className="text-sm text-neutral-700 mb-3">
                Your top 3 campaigns this week:
              </p>
              <div className="space-y-2">
                {[
                  { name: 'Summer Sale', roas: '5.8x' },
                  { name: 'New Collection', roas: '4.2x' },
                  { name: 'Brand Video', roas: '3.9x' },
                ].map((campaign, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-white rounded-lg border border-neutral-100">
                    <span className="text-xs font-medium text-neutral-900">{campaign.name}</span>
                    <span className="text-xs font-semibold text-[#0071E3]">{campaign.roas}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-neutral-500 mt-3">
                Consider scaling "Summer Sale" - highest ROAS.
              </p>
            </div>
          </div>
        </div>

        {/* Input */}
        <div className="p-3 border-t border-neutral-100">
          <div className="flex items-center gap-2 bg-neutral-50 rounded-lg px-3 py-2">
            <input
              type="text"
              placeholder="Ask about your campaigns..."
              className="flex-1 bg-transparent text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
            />
            <button className="w-7 h-7 rounded-md bg-[#0071E3] flex items-center justify-center text-white">
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * FeaturesSection - Clean, blue-only
 */
function FeaturesSection() {
  return (
    <section id="features" className="py-24 lg:py-32 bg-neutral-950 text-white">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-16 scroll-enter">
          <h2 className="font-heading text-4xl md:text-5xl text-white tracking-tight mb-4">
            Built for growth teams
          </h2>
          <p className="text-xl text-neutral-400 max-w-2xl mx-auto">
            Everything you need to understand and optimize your ad spend.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Analytics */}
          <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800 hover:border-blue-500/30 transition-colors scroll-enter">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6">
              <BarChart3 className="w-6 h-6 text-[#0071E3]" />
            </div>
            <h3 className="font-heading text-xl text-white mb-3">
              Real-time Analytics
            </h3>
            <p className="text-neutral-400 leading-relaxed mb-6">
              Unified dashboard with Meta and Google data. Track ROAS, spend, and conversions instantly.
            </p>
            <ul className="space-y-2">
              {['Cross-platform data', 'Custom dashboards', 'Export anywhere'].map((item) => (
                <li key={item} className="flex items-center gap-2 text-sm text-neutral-300">
                  <Check className="w-4 h-4 text-[#0071E3]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Agents */}
          <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800 hover:border-blue-500/30 transition-colors scroll-enter delay-100">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6">
              <Bot className="w-6 h-6 text-[#0071E3]" />
            </div>
            <h3 className="font-heading text-xl text-white mb-3">
              Autonomous Agents
            </h3>
            <p className="text-neutral-400 leading-relaxed mb-6">
              Set rules. Agents execute 24/7. Scale winners, pause losers automatically.
            </p>
            <ul className="space-y-2">
              {['Rule-based automation', 'Slack alerts', 'Scheduled reports'].map((item) => (
                <li key={item} className="flex items-center gap-2 text-sm text-neutral-300">
                  <Check className="w-4 h-4 text-[#0071E3]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Copilot */}
          <div className="bg-neutral-900 rounded-2xl p-8 border border-neutral-800 hover:border-blue-500/30 transition-colors scroll-enter delay-200">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6">
              <Brain className="w-6 h-6 text-[#0071E3]" />
            </div>
            <h3 className="font-heading text-xl text-white mb-3">
              AI Copilot
            </h3>
            <p className="text-neutral-400 leading-relaxed mb-6">
              Ask questions in plain English. Get insights in seconds, not hours.
            </p>
            <ul className="space-y-2">
              {['Natural language', 'Instant insights', 'Recommendations'].map((item) => (
                <li key={item} className="flex items-center gap-2 text-sm text-neutral-300">
                  <Check className="w-4 h-4 text-[#0071E3]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-16 grid grid-cols-3 gap-6 scroll-enter">
          {[
            { value: '< 2 min', label: 'Setup time' },
            { value: '99.9%', label: 'Uptime' },
            { value: '24/7', label: 'Monitoring' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="font-heading text-3xl md:text-4xl text-white tracking-tight">{stat.value}</p>
              <p className="text-sm text-neutral-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * PricingSection - Clean, blue-only
 */
function PricingSection() {
  const [annual, setAnnual] = useState(true);

  return (
    <section id="pricing" className="py-24 lg:py-32 px-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h2 className="font-heading text-4xl md:text-5xl text-neutral-900 tracking-tight mb-4 scroll-enter">
            Simple pricing
          </h2>
          <p className="text-xl text-neutral-500 mb-8 scroll-enter delay-100">
            Start free. Upgrade when you're ready.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center gap-1 p-1 bg-neutral-100 rounded-full scroll-enter delay-200">
            <button
              onClick={() => setAnnual(false)}
              className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all ${
                !annual ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${
                annual ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'
              }`}
            >
              Annual
              <span className="px-2 py-0.5 bg-blue-100 text-[#0071E3] text-xs rounded-full font-semibold">
                -45%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {/* Free */}
          <div className="bg-white rounded-2xl p-8 border border-neutral-200 scroll-enter">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-neutral-900 mb-1">Free</h3>
              <p className="text-neutral-500">Get started with the basics</p>
            </div>
            <div className="mb-6">
              <span className="font-heading text-5xl tracking-tight text-neutral-900">$0</span>
              <span className="text-neutral-400 ml-1">/forever</span>
            </div>
            <ul className="space-y-3 mb-8">
              {['Dashboard access', '1 ad account', 'Shopify connection', 'Basic metrics'].map((f) => (
                <li key={f} className="flex items-center gap-3 text-neutral-600">
                  <Check className="w-4 h-4 text-neutral-400" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/signup"
              className="w-full flex items-center justify-center py-3.5 px-6 bg-neutral-100 text-neutral-900 rounded-full font-medium hover:bg-neutral-200 transition-colors"
            >
              Get started free
            </Link>
          </div>

          {/* Starter */}
          <div className="relative bg-[#0071E3] rounded-2xl p-8 scroll-enter delay-100">
            <div className="absolute top-6 right-6 px-3 py-1 bg-white/20 rounded-full text-xs text-white font-medium">
              Most popular
            </div>
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-1">Starter</h3>
              <p className="text-blue-100">Everything you need to grow</p>
            </div>
            <div className="mb-6">
              <span className="font-heading text-5xl tracking-tight text-white">
                {annual ? '$196' : '$29.99'}
              </span>
              <span className="text-blue-200 ml-1">/{annual ? 'year' : 'mo'}</span>
              {annual && (
                <p className="text-blue-100 text-sm mt-2">$16.33/month billed annually</p>
              )}
            </div>
            <ul className="space-y-3 mb-8">
              {[
                'Full analytics dashboard',
                'Finance & P/L tracking',
                'Unlimited ad accounts',
                'Copilot AI assistant',
                'Agent automation',
                'Up to 10 team members',
              ].map((f) => (
                <li key={f} className="flex items-center gap-3 text-white">
                  <Check className="w-4 h-4 text-blue-200" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/subscribe"
              className="w-full flex items-center justify-center gap-2 py-3.5 px-6 bg-white text-[#0071E3] rounded-full font-medium hover:bg-blue-50 transition-colors"
            >
              Start 7-day free trial
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Trust badges */}
        <p className="mt-10 text-center text-sm text-neutral-400 scroll-enter">
          No credit card required · Cancel anytime
        </p>
      </div>
    </section>
  );
}

/**
 * FooterCTA - Clean, Apple-style
 */
function FooterCTA() {
  return (
    <section className="py-24 lg:py-32 bg-[#0071E3]">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <div className="scroll-enter">
          <h2 className="font-heading text-4xl md:text-5xl lg:text-6xl text-white tracking-tight mb-6">
            Ready to get started?
          </h2>

          <p className="text-xl text-blue-100 max-w-xl mx-auto mb-10">
            Join growth teams using metricx to understand their ad spend.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/signup"
              className="px-8 py-4 bg-white text-[#0071E3] rounded-full font-semibold text-lg hover:bg-blue-50 transition-colors flex items-center justify-center gap-2"
            >
              Start free trial
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="#pricing"
              className="px-8 py-4 text-white border-2 border-white/30 hover:border-white/60 rounded-full font-semibold text-lg transition-colors"
            >
              View pricing
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Footer - Minimal, clean
 */
function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-white">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex flex-col lg:flex-row justify-between gap-12">
          {/* Brand */}
          <div className="lg:max-w-xs">
            <Link href="/" className="flex items-center mb-4">
              <Image
                src="/logo.png"
                alt="metricx"
                width={120}
                height={32}
                className="h-7 w-auto"
              />
            </Link>
            <p className="text-neutral-500 text-sm leading-relaxed">
              Ad analytics, agents, and AI copilot—all in one platform.
            </p>
          </div>

          {/* Links Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 lg:gap-16">
            {[
              { title: 'Product', links: [
                { label: 'Features', href: '#features' },
                { label: 'Pricing', href: '#pricing' },
                { label: 'Demo', href: '#demo' },
              ]},
              { title: 'Company', links: [
                { label: 'About', href: '/about' },
                { label: 'Blog', href: '/blog' },
                { label: 'Contact', href: '/contact' },
              ]},
              { title: 'Legal', links: [
                { label: 'Privacy', href: '/privacy' },
                { label: 'Terms', href: '/terms' },
              ]},
              { title: 'Connect', links: [
                { label: 'Twitter', href: '#' },
                { label: 'LinkedIn', href: '#' },
              ]},
            ].map((col) => (
              <div key={col.title}>
                <h4 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4">{col.title}</h4>
                <ul className="space-y-3">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <Link href={link.href} className="text-neutral-600 hover:text-neutral-900 transition-colors text-sm">
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-neutral-200 flex flex-col md:flex-row justify-between gap-4 text-sm text-neutral-400">
          <p>© {new Date().getFullYear()} metricx. All rights reserved.</p>
          <p>Built with ❤️ for growth teams.</p>
        </div>
      </div>
    </footer>
  );
}
