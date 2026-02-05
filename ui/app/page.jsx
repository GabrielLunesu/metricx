/**
 * HomePage - metricx Landing Page
 * ================================
 *
 * Converted from template.html - Ad Analytics for E-commerce
 * Uses Inter font family with system fallbacks
 *
 * Features:
 * - UnicornStudio interactive gradient background
 * - Animated hero section with stats cards
 * - Problem/Solution sections
 * - Core features grid
 * - Pricing section
 * - Why metricx comparison section
 * - Scroll animations with Intersection Observer
 * - Smooth scrolling navigation
 */

"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function HomePage() {
  // Initialize scroll animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' }
    );

    // Observe all elements with scroll-animate class
    document.querySelectorAll('.scroll-animate').forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  // Smooth scroll handler
  const handleSmoothScroll = (e, targetId) => {
    e.preventDefault();
    const element = document.getElementById(targetId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Initialize UnicornStudio after component mounts
  useEffect(() => {
    // Load UnicornStudio script
    if (!window.UnicornStudio) {
      window.UnicornStudio = { isInitialized: false };
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.29/dist/unicornStudio.umd.js';
      script.onload = () => {
        if (!window.UnicornStudio.isInitialized) {
          window.UnicornStudio.init();
          window.UnicornStudio.isInitialized = true;
        }
      };
      document.head.appendChild(script);
    } else if (!window.UnicornStudio.isInitialized && window.UnicornStudio.init) {
      window.UnicornStudio.init();
      window.UnicornStudio.isInitialized = true;
    }
  }, []);

  return (
    <div className="min-h-screen antialiased text-gray-900 bg-white font-geist scroll-smooth flex flex-col">
      {/* UnicornStudio Interactive Gradient Background */}
      <div className="aura-background-component top-0 w-full -z-10 h-screen absolute">
        <div className="aura-background-component top-0 w-full -z-10 absolute h-full">
          <div
            data-us-project="yACzULFKkgXAmEcep6hu"
            className="absolute w-full h-full left-0 top-0 -z-10"
          />
        </div>
      </div>

      {/* Top Navigation */}
      <Header onSmoothScroll={handleSmoothScroll} />

      {/* Hero */}
      <Hero />

      {/* The Problem Section */}
      <ProblemSection />

      {/* The Solution Section */}
      <SolutionSection />

      {/* Core Features Section */}
      <FeaturesSection />

      {/* Pricing Section */}
      <PricingSection />

      {/* Why metricx Section */}
      <WhyMetricxSection />

      {/* Final CTA Section */}
      <FinalCTASection />

      {/* Footer */}
      <Footer />
    </div>
  );
}

/**
 * Header - Top navigation with mobile menu and logo
 */
function Header({ onSmoothScroll }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="relative z-20 border-b border-gray-100 bg-white/80 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-4 sm:py-6">
          {/* Brand with Logo */}
          <div className="flex items-center gap-3">
            <Link href="/" className="inline-flex items-center gap-2">
              <Image
                src="/logo.png"
                alt="metricx"
                width={160}
                height={48}
                className="h-10 sm:h-11 w-auto"
                priority
              />
            </Link>
          </div>
          {/* Nav */}
          <nav className="hidden md:flex items-center gap-6 lg:gap-8 text-sm text-gray-600">
            <a
              href="#features"
              onClick={(e) => onSmoothScroll(e, 'features')}
              className="hover:text-gray-900 transition-colors font-geist"
            >
              Features
            </a>
            <a
              href="#pricing"
              onClick={(e) => onSmoothScroll(e, 'pricing')}
              className="hover:text-gray-900 transition-colors font-geist"
            >
              Pricing
            </a>
            <Link href="#" className="hover:text-gray-900 transition-colors font-geist">Docs</Link>
            <Link href="#" className="hover:text-gray-900 transition-colors font-geist">Blog</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden sm:inline-flex text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors font-geist">
              Log in
            </Link>
            <Link
              href="/signup"
              className="hidden sm:inline-flex items-center rounded-full bg-gray-900 px-3 sm:px-4 py-2 text-sm font-medium text-white shadow-lg shadow-gray-900/20 hover:bg-black transition-colors font-geist"
            >
              Start Free Trial
            </Link>
            {/* Mobile toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-controls="mobileMenu"
              aria-expanded={mobileMenuOpen}
              className="md:hidden inline-flex items-center rounded-lg border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-900/10"
            >
              {!mobileMenuOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                  <path d="M4 5h16" />
                  <path d="M4 12h16" />
                  <path d="M4 19h16" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              )}
              <span className="sr-only font-geist">Toggle navigation</span>
            </button>
          </div>
        </div>
      </div>
      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div id="mobileMenu" className="md:hidden bg-white border-t border-gray-100">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="py-3 space-y-1 divide-y divide-gray-100 border-b border-gray-100">
              <a href="#features" onClick={(e) => { onSmoothScroll(e, 'features'); setMobileMenuOpen(false); }} className="block px-2 py-3 text-sm text-gray-700 hover:text-gray-900 font-geist">Features</a>
              <a href="#pricing" onClick={(e) => { onSmoothScroll(e, 'pricing'); setMobileMenuOpen(false); }} className="block px-2 py-3 text-sm text-gray-700 hover:text-gray-900 font-geist">Pricing</a>
              <Link href="#" className="block px-2 py-3 text-sm text-gray-700 hover:text-gray-900 font-geist">Docs</Link>
              <Link href="#" className="block px-2 py-3 text-sm text-gray-700 hover:text-gray-900 font-geist">Blog</Link>
              <div className="pt-3 space-y-2">
                <Link href="/login" className="block text-sm text-gray-700 hover:text-gray-900 font-geist">Log in</Link>
                <Link
                  href="/signup"
                  className="inline-flex w-full items-center justify-center rounded-full bg-gray-900 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-gray-900/20 hover:bg-black transition-colors font-geist"
                >
                  Start Free Trial
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

/**
 * Hero - Main hero section with copy and stats card
 */
function Hero() {
  return (
    <main className="relative">
      <div className="sm:px-6 lg:px-8 sm:pt-24 lg:pt-32 xl:pt-40 sm:pb-24 lg:pb-32 xl:pb-40 max-w-7xl mr-auto ml-auto pt-24 pr-4 pb-24 pl-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 sm:gap-16 lg:gap-24 xl:gap-32 items-center">
          {/* Left: Copy */}
          <section className="order-2 lg:order-1 relative">
            <div
              className="inline-flex text-xs text-gray-700 font-geist bg-white/50 border-gray-200 border rounded-full pt-1 pr-3 pb-1 pl-3 backdrop-blur-md gap-x-2 items-center animate-fade-slide-in"
              style={{ animationDelay: '0.1s' }}
            >
              <span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Ad Analytics for E-commerce
            </div>

            <h1
              className="sm:mt-6 sm:text-5xl md:text-6xl lg:text-5xl xl:text-6xl 2xl:text-7xl leading-[0.95] text-4xl tracking-tighter font-geist mt-6 animate-fade-slide-in"
              style={{ animationDelay: '0.2s' }}
            >
              Stop guessing which ads make you money.
            </h1>

            <p
              className="sm:mt-6 sm:text-lg lg:text-base xl:text-lg lg:max-w-none text-base text-gray-600 font-geist max-w-xl mt-6 animate-fade-slide-in"
              style={{ animationDelay: '0.3s' }}
            >
              Connect your ad accounts, see unified performance data, and finally understand your true return on ad spend.
            </p>

            <div
              className="flex flex-col sm:flex-row sm:mt-8 gap-3 sm:items-center mt-8 items-start animate-fade-slide-in"
              style={{ animationDelay: '0.4s' }}
            >
              <Link
                href="/signup"
                className="group inline-flex items-center gap-3 hover:bg-gray-800 hover:shadow-xl transition-all duration-300 transform hover:scale-105 xl:pt-4 xl:pb-4 text-sm font-medium text-white bg-black rounded-full pt-3 pr-8 pb-3 pl-8 shadow-[0_2.8px_2.2px_rgba(0,_0,_0,_0.034),_0_6.7px_5.3px_rgba(0,_0,_0,_0.048),_0_12.5px_10px_rgba(0,_0,_0,_0.06),_0_22.3px_17.9px_rgba(0,_0,_0,_0.072),_0_41.8px_33.4px_rgba(0,_0,_0,_0.086),_0_100px_80px_rgba(0,_0,_0,_0.12)]"
              >
                <span>Start Free Trial</span>
                <div className="relative flex items-center justify-center w-5 h-5 bg-white/20 rounded-full group-hover:bg-white/30 transition-all duration-300">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-300 group-hover:translate-x-0.5">
                    <path d="M5 12h14" />
                    <path d="m12 5 7 7-7 7" />
                  </svg>
                </div>
              </Link>
              <button className="inline-flex sm:px-5 hover:bg-gray-100 transition sm:w-auto text-sm font-medium text-gray-900 font-geist bg-white/80 w-full border-gray-200 border rounded-full pt-3 pr-4 pb-3 pl-4 shadow-sm backdrop-blur-md gap-x-2 items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 text-gray-700">
                  <path d="M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z" />
                  <circle cx="12" cy="12" r="10" />
                </svg>
                Watch demo
              </button>
            </div>

            {/* Divider */}
            <div className="sm:mt-8 h-px bg-gray-200 mt-6" />

            {/* Feature bullets */}
            <div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-3 sm:gap-6 sm:mt-8 mt-8 gap-x-4 gap-y-4 animate-fade-slide-in"
              style={{ animationDelay: '0.5s' }}
            >
              <FeatureBullet
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 sm:h-5 sm:w-5 text-gray-700">
                    <rect width="18" height="18" x="3" y="3" rx="2" />
                    <path d="M3 9h18" />
                    <path d="M9 21V9" />
                  </svg>
                }
                title="Unified dashboard"
                description="Meta, Google & Shopify in one view."
              />
              <FeatureBullet
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 sm:h-5 sm:w-5 text-gray-700">
                    <path d="M12 8V4H8" />
                    <rect width="16" height="12" x="4" y="8" rx="2" />
                    <path d="M2 14h2" />
                    <path d="M20 14h2" />
                    <path d="M15 13v2" />
                    <path d="M9 13v2" />
                  </svg>
                }
                title="AI Copilot"
                description="Ask questions in plain English."
              />
              <FeatureBullet
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 sm:h-5 sm:w-5 text-gray-700">
                    <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                    <path d="m9 12 2 2 4-4" />
                  </svg>
                }
                title="Verified attribution"
                description="Real purchase data, not estimates."
              />
            </div>
          </section>

          {/* Right: Visual */}
          <HeroVisual />
        </div>
      </div>
    </main>
  );
}

/**
 * FeatureBullet - Single feature item in hero
 */
function FeatureBullet({ icon, title, description }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex shrink-0 sm:w-9 sm:h-9 bg-white/80 w-8 h-8 border-gray-200 border rounded-lg mt-0.5 shadow-sm backdrop-blur-md items-center justify-center">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-900 font-geist">{title}</p>
        <p className="text-sm text-gray-600 font-geist">{description}</p>
      </div>
    </div>
  );
}

/**
 * HeroVisual - Right side stats card and floating badges
 */
function HeroVisual() {
  const [activeSlide, setActiveSlide] = useState(0);
  const slides = ['Analytics', 'Agents', 'Copilot'];

  // Auto-rotate slides
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % 3);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="order-1 lg:order-2 relative animate-fade-slide-in" style={{ animationDelay: '0.6s' }}>
      {/* Subtle background glow */}
      <div className="-inset-6 sm:-inset-10 pointer-events-none absolute">
        <div className="absolute right-6 sm:right-10 top-0 h-48 w-48 sm:h-64 sm:w-64 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute left-2 sm:left-5 bottom-12 h-48 w-48 sm:h-64 sm:w-64 rounded-full bg-indigo-500/20 blur-3xl" />
      </div>

      {/* Main Card */}
      <div className="z-10 sm:max-w-md lg:mx-0 lg:ml-auto sm:rounded-3xl sm:p-5 bg-white/90 max-w-sm ring-black/5 ring-1 rounded-2xl mr-auto ml-auto p-4 relative shadow-[0_2.8px_2.2px_rgba(0,_0,_0,_0.02),_0_6.7px_5.3px_rgba(0,_0,_0,_0.028),_0_12.5px_10px_rgba(0,_0,_0,_0.035),_0_22.3px_17.9px_rgba(0,_0,_0,_0.042),_0_41.8px_33.4px_rgba(0,_0,_0,_0.05),_0_100px_80px_rgba(0,_0,_0,_0.07)] backdrop-blur-md overflow-hidden">

        {/* Slide Indicator Tabs */}
        <div className="flex items-center gap-1 mb-4">
          {slides.map((slide, index) => (
            <button
              key={slide}
              onClick={() => setActiveSlide(index)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-300 font-geist ${
                activeSlide === index
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {slide}
            </button>
          ))}
        </div>

        {/* Carousel Content */}
        <div className="relative min-h-[220px]">
          {/* Slide 1: Analytics */}
          <div className={`transition-all duration-500 ${activeSlide === 0 ? 'opacity-100 translate-x-0' : 'opacity-0 absolute inset-0 translate-x-4 pointer-events-none'}`}>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-600">
                      <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
                    </svg>
                  </div>
                  <span className="text-xs text-emerald-600 font-medium font-geist">+18%</span>
                </div>
                <p className="text-[11px] text-gray-500 font-geist">Meta Revenue</p>
                <p className="text-base font-semibold text-gray-900 font-geist">$42,580</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                    <GoogleIcon size={16} />
                  </div>
                  <span className="text-xs text-emerald-600 font-medium font-geist">+12%</span>
                </div>
                <p className="text-[11px] text-gray-500 font-geist">Google Revenue</p>
                <p className="text-base font-semibold text-gray-900 font-geist">$28,340</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-600">
                      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                    </svg>
                  </div>
                </div>
                <p className="text-[11px] text-gray-500 font-geist">Total Spend</p>
                <p className="text-base font-semibold text-gray-900 font-geist">$18,420</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-emerald-600">
                      <path d="M3 3v18h18" />
                      <path d="m19 9-5 5-4-4-3 3" />
                    </svg>
                  </div>
                  <span className="text-xs text-emerald-600 font-medium font-geist">3.8x</span>
                </div>
                <p className="text-[11px] text-gray-500 font-geist">Total Revenue</p>
                <p className="text-base font-semibold text-gray-900 font-geist">$70,920</p>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 mt-3 font-geist">Last 7 days • Updated live</p>
          </div>

          {/* Slide 2: Agents */}
          <div className={`transition-all duration-500 ${activeSlide === 1 ? 'opacity-100 translate-x-0' : 'opacity-0 absolute inset-0 translate-x-4 pointer-events-none'}`}>
            <div className="space-y-3">
              <div className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
                <div className="w-10 h-10 bg-violet-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-violet-600">
                    <path d="M12 8V4H8" />
                    <rect width="16" height="12" x="4" y="8" rx="2" />
                    <path d="M2 14h2" />
                    <path d="M20 14h2" />
                    <path d="M15 13v2" />
                    <path d="M9 13v2" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 font-geist">Performance Monitor</p>
                  <p className="text-xs text-gray-500 font-geist truncate">Watching 12 campaigns</p>
                </div>
                <span className="flex-shrink-0 h-2 w-2 bg-emerald-500 rounded-full animate-pulse" />
              </div>
              <div className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
                <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-amber-600">
                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 font-geist">Budget Guardian</p>
                  <p className="text-xs text-gray-500 font-geist truncate">2 alerts this week</p>
                </div>
                <span className="flex-shrink-0 h-2 w-2 bg-emerald-500 rounded-full animate-pulse" />
              </div>
              <div className="flex items-center gap-3 bg-gray-50 rounded-xl p-3">
                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-600">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                    <polyline points="14 2 14 8 20 8" />
                    <path d="M12 18v-6" />
                    <path d="M8 18v-1" />
                    <path d="M16 18v-3" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 font-geist">Weekly Reporter</p>
                  <p className="text-xs text-gray-500 font-geist truncate">Next report in 2 days</p>
                </div>
                <span className="flex-shrink-0 h-2 w-2 bg-gray-300 rounded-full" />
              </div>
            </div>
            <p className="text-[11px] text-gray-400 mt-3 font-geist">3 agents active • Running 24/7</p>
          </div>

          {/* Slide 3: Copilot */}
          <div className={`transition-all duration-500 ${activeSlide === 2 ? 'opacity-100 translate-x-0' : 'opacity-0 absolute inset-0 translate-x-4 pointer-events-none'}`}>
            <div className="space-y-3">
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs">👤</span>
                  </div>
                  <p className="text-sm text-gray-700 font-geist">What&apos;s my best performing campaign?</p>
                </div>
              </div>
              <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 bg-white/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white">
                      <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-white font-geist">&quot;Summer Sale - Retargeting&quot; is your top performer with 4.2x ROAS and $12,450 revenue this week.</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-400">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4" />
                  <path d="M12 8h.01" />
                </svg>
                <span className="text-xs text-gray-500 font-geist">Ask anything about your ads...</span>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 mt-3 font-geist">Powered by AI • Instant answers</p>
          </div>
        </div>
      </div>

      {/* Social proof - centered */}
      <div className="flex justify-center mt-4 sm:mt-6">
        <div className="z-10 flex gap-2 sm:gap-3 sm:rounded-2xl sm:px-4 sm:py-3 bg-white/90 ring-black/5 ring-1 rounded-xl pt-2 pr-3 pb-2 pl-3 relative shadow-xl backdrop-blur items-center">
          <div className="flex -space-x-1.5 sm:-space-x-2">
            <img alt="Client 1" className="h-6 w-6 sm:h-8 sm:w-8 rounded-full object-cover ring-2 ring-white" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop&crop=face" />
            <img alt="Client 2" className="h-6 w-6 sm:h-8 sm:w-8 rounded-full object-cover ring-2 ring-white" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face" />
            <img alt="Client 3" className="h-6 w-6 sm:h-8 sm:w-8 rounded-full object-cover ring-2 ring-white" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop&crop=face" />
            <img alt="Client 4" className="h-6 w-6 sm:h-8 sm:w-8 rounded-full object-cover ring-2 ring-white" src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face" />
          </div>
          <div className="text-xs">
            <p className="font-medium text-gray-900 font-geist">Trusted by merchants</p>
            <p className="text-gray-600 font-geist">7 figures in ad spend</p>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * StatsCard - Individual stat card in hero
 */
function StatsCard({ icon, iconBg, badge, badgeColor = "text-emerald-600", label, value }) {
  return (
    <div className="bg-white ring-black/5 ring-1 rounded-xl pt-4 pr-4 pb-4 pl-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className={`flex w-10 h-10 ${iconBg} rounded-xl items-center justify-center`}>
          {icon}
        </div>
        <span className={`text-xs ${badgeColor} font-medium font-geist`}>{badge}</span>
      </div>
      <p className="mt-3 text-xs text-gray-500 font-geist">{label}</p>
      <p className="text-lg font-semibold text-gray-900 tracking-tight font-geist">{value}</p>
    </div>
  );
}

/**
 * GoogleIcon - Google colored logo
 */
function GoogleIcon({ size = 20 }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

/**
 * ProblemSection - The problem every merchant faces
 */
function ProblemSection() {
  return (
    <section aria-labelledby="problem-section" className="overflow-hidden border-black/5 border-t relative bg-white/50 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-1/4 top-24 h-[900px] w-[900px] rounded-full border border-gray-100" />
        <div className="absolute -right-1/3 top-64 h-[1200px] w-[1200px] rounded-full border border-gray-50" />
      </div>

      <div className="sm:px-6 lg:px-8 sm:py-24 max-w-7xl mr-auto ml-auto pt-16 pr-4 pb-16 pl-4 relative">
        <div className="flex gap-6 items-start justify-between">
          <div>
            <p className="sm:text-sm text-xs text-gray-500 font-geist scroll-animate opacity-0">
              The problem every merchant faces
            </p>
            <h2
              className="sm:mt-4 sm:text-5xl md:text-6xl text-3xl tracking-tight font-geist mt-4 scroll-animate opacity-0"
              id="problem-section"
            >
              You're flying blind
              <span className="block text-gray-600">hoping ads turn into profit</span>
            </h2>
          </div>
        </div>

        {/* Problem Cards */}
        <div className="relative mt-8 sm:mt-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.1s' }}>
              <ProblemCard
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-600">
                    <path d="M18 6 6 18" />
                    <path d="m6 6 12 12" />
                  </svg>
                }
                iconBg="bg-red-100"
                title="Conflicting data"
                description="Meta says one thing. Google says another. Your bank account tells a different story entirely."
              />
            </div>
            <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.2s' }}>
              <ProblemCard
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-amber-600">
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                    <path d="M12 9v4" />
                    <path d="M12 17h.01" />
                  </svg>
                }
                iconBg="bg-amber-100"
                title="Inflated ROAS"
                description="Platform-reported ROAS doesn't match reality. You're making decisions on unreliable numbers."
              />
            </div>
            <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.3s' }}>
              <ProblemCard
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-600">
                    <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                }
                iconBg="bg-gray-100"
                title="Siloed platforms"
                description="Jumping between tabs and exporting CSVs just to see how your ads are performing across channels."
              />
            </div>
          </div>
        </div>

        <p className="mt-10 text-center text-lg text-gray-600 font-geist scroll-animate opacity-0">
          You shouldn't need a data science degree to know if your ads are working.
        </p>
      </div>
    </section>
  );
}

/**
 * ProblemCard - Single problem card
 */
function ProblemCard({ icon, iconBg, title, description }) {
  return (
    <article className="relative rounded-3xl bg-white/80 backdrop-blur-md text-gray-800 ring-1 ring-gray-200 p-6 sm:p-8 hover:shadow-lg transition-shadow">
      <div className="relative">
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconBg}`}>
          {icon}
        </div>
        <h3 className="mt-4 text-xl sm:text-2xl text-gray-900 font-geist tracking-tight">{title}</h3>
        <p className="mt-2 text-sm sm:text-base text-gray-600 font-geist">{description}</p>
      </div>
    </article>
  );
}

/**
 * SolutionSection - Ad Analytics First, Attribution Second
 */
function SolutionSection() {
  return (
    <section aria-labelledby="solution-section" className="overflow-hidden bg-gray-950 border-white/10 border-t relative">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-1/4 top-10 h-[900px] w-[900px] rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute -right-1/3 bottom-0 h-[1200px] w-[1200px] rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
          {/* Left: Copy */}
          <div className="scroll-animate opacity-0">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 px-3 py-1 text-[11px] text-white/80 font-geist">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              The solution
            </div>
            <h2 id="solution-section" className="mt-4 sm:mt-6 text-3xl sm:text-5xl md:text-6xl font-geist tracking-tight text-white">
              Ad Analytics First.
              <span className="block text-white/60">Attribution Second.</span>
            </h2>
            <p className="mt-3 sm:mt-4 text-sm sm:text-base text-white/70 font-geist max-w-xl">
              metricx connects to Meta, Google, and Shopify to give you one unified view of your ad performance. No complex setup. No waiting for perfect attribution data.
            </p>
            <p className="mt-4 text-sm sm:text-base text-white/70 font-geist max-w-xl">
              Connect your accounts and see your metrics immediately. When you connect Shopify, we go deeper—verifying which orders actually came from which ads using real purchase data.
            </p>

            {/* CTA */}
            <div className="mt-8">
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 rounded-lg bg-white text-gray-900 px-5 py-2.5 text-sm font-medium hover:bg-gray-100 transition shadow-lg font-geist"
              >
                Connect your accounts
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>

          {/* Right: Visual */}
          <div className="relative lg:justify-self-end scroll-animate opacity-0" style={{ transitionDelay: '0.2s' }}>
            <div className="-right-6 -top-8 bg-blue-500/20 w-40 h-40 rounded-full absolute blur-3xl animate-pulse-slow" />
            <div className="absolute -left-8 -bottom-8 h-40 w-40 rounded-full bg-emerald-400/20 blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />

            <div className="relative bg-white/5 backdrop-blur-md rounded-3xl p-6 ring-1 ring-white/10">
              <div className="space-y-4">
                <PlatformRow platform="Meta Ads" icon="meta" />
                <PlatformRow platform="Google Ads" icon="google" />
                <PlatformRow platform="Shopify" icon="shopify" />
              </div>

              <div className="mt-6 pt-6 border-t border-white/10">
                <p className="text-xs text-white/60 font-geist">All platforms synced</p>
                <p className="text-sm text-white font-geist mt-1">Metrics available in under 2 minutes</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * PlatformRow - Connected platform row in solution section
 */
function PlatformRow({ platform, icon }) {
  const icons = {
    meta: (
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white">
          <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
        </svg>
      </div>
    ),
    google: (
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white">
        <GoogleIcon />
      </div>
    ),
    shopify: (
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#96BF48]">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
          <path d="M3 6h18" />
          <path d="M16 10a4 4 0 0 1-8 0" />
        </svg>
      </div>
    ),
  };

  return (
    <div className="flex items-center gap-3 p-4 bg-white/10 rounded-xl hover:bg-white/15 transition-colors">
      {icons[icon]}
      <div className="flex-1">
        <p className="text-sm font-medium text-white font-geist">{platform}</p>
        <p className="text-xs text-white/60 font-geist">Connected</p>
      </div>
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-400">
        <path d="m5 12 5 5L20 7" />
      </svg>
    </div>
  );
}

/**
 * FeaturesSection - Core features grid
 */
function FeaturesSection() {
  const features = [
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-indigo-600">
          <rect width="18" height="18" x="3" y="3" rx="2" />
          <path d="M3 9h18" />
          <path d="M9 21V9" />
        </svg>
      ),
      iconBg: "bg-indigo-100",
      title: "Unified Dashboard",
      description: "One view across all your ad platforms. See spend, revenue, and ROAS broken down by provider, campaign, and ad set. No more jumping between tabs."
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-purple-600">
          <path d="M12 8V4H8" />
          <rect width="16" height="12" x="4" y="8" rx="2" />
          <path d="M2 14h2" />
          <path d="M20 14h2" />
          <path d="M15 13v2" />
          <path d="M9 13v2" />
        </svg>
      ),
      iconBg: "bg-purple-100",
      title: "AI Copilot",
      description: "Ask questions in plain English. What's my ROAS today? Which campaigns performed best? Copilot fetches live data and tells you exactly where numbers came from."
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-amber-600">
          <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
        </svg>
      ),
      iconBg: "bg-amber-100",
      title: "Autonomous Agents",
      description: "Set rules. Let metricx act. Pause underperforming campaigns before they drain your budget. Get Slack alerts when metrics cross thresholds."
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-emerald-600">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      iconBg: "bg-emerald-100",
      title: "Real-Time Metrics",
      description: "15-minute updates, not daily. See intraday spend progression. Catch runaway campaigns before they blow through your budget."
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-600">
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      ),
      iconBg: "bg-blue-100",
      title: "Verified Attribution",
      description: "Shopify Web Pixel captures the full customer journey. We match UTM parameters to campaigns. See which ads drove which sales—with confidence levels."
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-pink-600">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
          <polyline points="16 6 12 2 8 6" />
          <line x1="12" x2="12" y1="2" y2="15" />
        </svg>
      ),
      iconBg: "bg-pink-100",
      title: "Conversions API",
      description: "We send purchase data back to Meta and Google, improving their ad optimization. Better data in means better targeting out."
    }
  ];

  return (
    <section id="features" aria-labelledby="features-section" className="overflow-hidden border-black/5 border-t relative bg-white/50 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-1/4 top-24 h-[900px] w-[900px] rounded-full border border-gray-100" />
      </div>

      <div className="sm:px-6 lg:px-8 sm:py-24 max-w-7xl mr-auto ml-auto pt-16 pr-4 pb-16 pl-4 relative">
        <div className="text-center max-w-3xl mx-auto">
          <p className="sm:text-sm text-xs text-gray-500 font-geist scroll-animate opacity-0">Core features</p>
          <h2
            className="sm:mt-4 sm:text-5xl md:text-6xl text-3xl tracking-tight font-geist mt-4 scroll-animate opacity-0"
            id="features-section"
          >
            Everything you need to understand your ads
          </h2>
        </div>

        {/* Features Grid */}
        <div className="mt-12 sm:mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="scroll-animate opacity-0"
              style={{ transitionDelay: `${index * 0.1}s` }}
            >
              <FeatureCard {...feature} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * FeatureCard - Single feature card
 */
function FeatureCard({ icon, iconBg, title, description }) {
  return (
    <article className="relative rounded-3xl bg-white/80 backdrop-blur-md text-gray-800 ring-1 ring-gray-200 p-6 sm:p-8 hover:shadow-lg transition-all hover:-translate-y-1">
      <div className="relative">
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconBg}`}>
          {icon}
        </div>
        <h3 className="mt-4 text-xl sm:text-2xl text-gray-900 font-geist tracking-tight">{title}</h3>
        <p className="mt-2 text-sm sm:text-base text-gray-600 font-geist">{description}</p>
      </div>
    </article>
  );
}

/**
 * PricingSection - Pricing plans
 */
function PricingSection() {
  return (
    <section id="pricing" aria-labelledby="pricing-section" className="overflow-hidden bg-gray-950 border-white/10 border-t relative">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-1/4 top-10 h-[900px] w-[900px] rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute -right-1/3 bottom-0 h-[1200px] w-[1200px] rounded-full bg-emerald-500/10 blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
        <div className="text-center max-w-3xl mx-auto scroll-animate opacity-0">
          <p className="text-xs sm:text-sm text-white/60 font-geist">Simple pricing</p>
          <h2 id="pricing-section" className="mt-4 text-3xl sm:text-5xl md:text-6xl font-geist tracking-tight text-white">
            Start free, scale as you grow
          </h2>
          <p className="mt-4 text-sm sm:text-base text-white/70 font-geist">
            No credit card required. 7-day free trial of Starter.
          </p>
        </div>

        <div className="mt-12 sm:mt-16 grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="relative rounded-3xl bg-white/5 backdrop-blur-md p-8 ring-1 ring-white/10 scroll-animate opacity-0 hover:ring-white/20 transition-all" style={{ transitionDelay: '0.1s' }}>
            <h3 className="text-xl font-semibold text-white font-geist">Free</h3>
            <p className="mt-2 text-sm text-white/60 font-geist">Perfect for getting started</p>
            <p className="mt-6">
              <span className="text-4xl font-semibold text-white font-geist tracking-tight">$0</span>
              <span className="text-white/60 font-geist">/month</span>
            </p>
            <ul className="mt-8 space-y-4">
              <PricingFeature>1 ad account (Meta or Google)</PricingFeature>
              <PricingFeature>Full dashboard access</PricingFeature>
              <PricingFeature>Shopify connection</PricingFeature>
            </ul>
            <Link
              href="/signup"
              className="mt-8 block w-full text-center rounded-lg bg-white/10 px-4 py-3 text-sm font-medium text-white hover:bg-white/20 transition font-geist"
            >
              Get started free
            </Link>
          </div>

          {/* Starter Plan */}
          <div className="relative rounded-3xl bg-white p-8 ring-1 ring-black/5 shadow-2xl scroll-animate opacity-0" style={{ transitionDelay: '0.2s' }}>
            <div className="absolute -top-4 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center rounded-full bg-emerald-500 px-3 py-1 text-xs font-medium text-white font-geist">
                Most popular
              </span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 font-geist">Starter</h3>
            <p className="mt-2 text-sm text-gray-600 font-geist">Everything you need to optimize</p>
            <p className="mt-6">
              <span className="text-4xl font-semibold text-gray-900 font-geist tracking-tight">$29.99</span>
              <span className="text-gray-600 font-geist">/month</span>
            </p>
            <ul className="mt-8 space-y-4">
              <PricingFeature dark>Unlimited ad accounts</PricingFeature>
              <PricingFeature dark>Full Analytics, Finance & Campaigns</PricingFeature>
              <PricingFeature dark>AI Copilot</PricingFeature>
              <PricingFeature dark>Up to 10 team members</PricingFeature>
            </ul>
            <Link
              href="/signup"
              className="mt-8 block w-full text-center rounded-lg bg-gray-900 px-4 py-3 text-sm font-medium text-white hover:bg-gray-800 transition shadow-lg font-geist"
            >
              Start 7-day free trial
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * PricingFeature - Single pricing feature item
 */
function PricingFeature({ children, dark = false }) {
  return (
    <li className="flex items-start gap-3">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className={`${dark ? 'text-emerald-600' : 'text-emerald-400'} shrink-0 mt-0.5`}
      >
        <path d="m5 12 5 5L20 7" />
      </svg>
      <span className={`text-sm ${dark ? 'text-gray-700' : 'text-white/80'} font-geist`}>{children}</span>
    </li>
  );
}

/**
 * WhyMetricxSection - Comparison and benefits
 */
function WhyMetricxSection() {
  return (
    <section aria-labelledby="comparison-section" className="overflow-hidden border-black/5 border-t relative bg-white/50 backdrop-blur-sm">
      <div className="sm:px-6 lg:px-8 sm:py-24 max-w-7xl mr-auto ml-auto pt-16 pr-4 pb-16 pl-4 relative">
        <div className="text-center max-w-3xl mx-auto scroll-animate opacity-0">
          <p className="text-xs sm:text-sm text-gray-500 font-geist">Why metricx?</p>
          <h2 id="comparison-section" className="mt-4 text-3xl sm:text-5xl md:text-6xl font-geist tracking-tight">
            Built for merchants who want clarity
          </h2>
        </div>

        <div className="mt-12 sm:mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.1s' }}>
            <ComparisonCard
              vs="vs. Triple Whale"
              title="Focused, not bloated"
              description="We're focused on ad analytics and profitability, not inventory management and cohort analysis. Do one thing well."
            />
          </div>
          <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.2s' }}>
            <ComparisonCard
              vs="vs. Native Dashboards"
              title="Unified, not siloed"
              description="Meta and Google show you their data in isolation. We show you everything together in one unified view."
            />
          </div>
          <div className="scroll-animate opacity-0" style={{ transitionDelay: '0.3s' }}>
            <ComparisonCard
              vs="vs. Spreadsheets"
              title="Automated, not manual"
              description="Real-time, automated, and actually usable. Stop exporting CSVs and updating formulas every morning."
            />
          </div>
        </div>

        {/* Built for Merchants */}
        <div className="mt-16 sm:mt-20 grid grid-cols-2 md:grid-cols-4 gap-6">
          <BenefitItem
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-indigo-600">
                <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
              </svg>
            }
            iconBg="bg-indigo-100"
            title="Simple onboarding"
            subtitle="Connect in minutes"
            delay="0.1s"
          />
          <BenefitItem
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-emerald-600">
                <path d="M3 3v18h18" />
                <path d="m19 9-5 5-4-4-3 3" />
              </svg>
            }
            iconBg="bg-emerald-100"
            title="Immediate value"
            subtitle="See metrics instantly"
            delay="0.2s"
          />
          <BenefitItem
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-green-600">
                <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
                <path d="M3 6h18" />
                <path d="M16 10a4 4 0 0 1-8 0" />
              </svg>
            }
            iconBg="bg-green-100"
            title="Shopify-native"
            subtitle="Orders, refunds, checkout"
            delay="0.3s"
          />
          <BenefitItem
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-blue-600">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            }
            iconBg="bg-blue-100"
            title="Affordable"
            subtitle="$30/mo for any scale"
            delay="0.4s"
          />
        </div>
      </div>
    </section>
  );
}

/**
 * ComparisonCard - Single comparison card
 */
function ComparisonCard({ vs, title, description }) {
  return (
    <div className="relative rounded-3xl bg-white/80 backdrop-blur-md p-6 sm:p-8 ring-1 ring-gray-200 hover:shadow-lg transition-all hover:-translate-y-1">
      <div className="relative">
        <p className="text-xs text-gray-500 font-geist uppercase tracking-wider">{vs}</p>
        <h3 className="mt-3 text-xl text-gray-900 font-geist tracking-tight">{title}</h3>
        <p className="mt-3 text-sm text-gray-600 font-geist">{description}</p>
      </div>
    </div>
  );
}

/**
 * BenefitItem - Single benefit item
 */
function BenefitItem({ icon, iconBg, title, subtitle, delay = '0s' }) {
  return (
    <div className="text-center scroll-animate opacity-0" style={{ transitionDelay: delay }}>
      <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconBg} mx-auto`}>
        {icon}
      </div>
      <p className="mt-3 text-sm font-medium text-gray-900 font-geist">{title}</p>
      <p className="mt-1 text-xs text-gray-600 font-geist">{subtitle}</p>
    </div>
  );
}

/**
 * FinalCTASection - Final call to action
 */
function FinalCTASection() {
  return (
    <section className="overflow-hidden border-black/5 border-t relative bg-white/50 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-32 text-center">
        <h2 className="text-3xl sm:text-5xl md:text-6xl font-geist tracking-tight scroll-animate opacity-0">
          You spend thousands on ads.<br />
          <span className="text-gray-600">You deserve to know what's working.</span>
        </h2>
        <p className="mt-6 text-base sm:text-lg text-gray-600 font-geist max-w-2xl mx-auto scroll-animate opacity-0" style={{ transitionDelay: '0.1s' }}>
          metricx gives you the clarity to spend smarter, cut waste, and grow profitably.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center scroll-animate opacity-0" style={{ transitionDelay: '0.2s' }}>
          <Link
            href="/signup"
            className="group inline-flex items-center justify-center gap-3 hover:bg-gray-800 hover:shadow-xl transition-all duration-300 transform hover:scale-105 text-sm font-medium text-white bg-black rounded-full py-4 px-8 shadow-[0_2.8px_2.2px_rgba(0,_0,_0,_0.034),_0_6.7px_5.3px_rgba(0,_0,_0,_0.048),_0_12.5px_10px_rgba(0,_0,_0,_0.06),_0_22.3px_17.9px_rgba(0,_0,_0,_0.072),_0_41.8px_33.4px_rgba(0,_0,_0,_0.086),_0_100px_80px_rgba(0,_0,_0,_0.12)] font-geist"
          >
            Connect your accounts
            <div className="relative flex items-center justify-center w-5 h-5 bg-white/20 rounded-full group-hover:bg-white/30 transition-all duration-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-300 group-hover:translate-x-0.5">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </div>
          </Link>
          <button className="inline-flex items-center justify-center gap-2 text-sm font-medium text-gray-900 font-geist bg-white/80 backdrop-blur-md border border-gray-200 rounded-full px-6 py-4 hover:bg-gray-100 transition shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-700">
              <path d="M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z" />
              <circle cx="12" cy="12" r="10" />
            </svg>
            Watch demo
          </button>
        </div>
      </div>
    </section>
  );
}

/**
 * Footer - Site footer with logo
 */
function Footer() {
  return (
    <footer className="text-white bg-gray-900 border-black/5 border-t relative overflow-hidden mt-auto">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute left-0 top-0 h-[400px] w-[400px] rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute right-0 bottom-0 h-[400px] w-[400px] rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16">
          {/* Brand & Description */}
          <div className="lg:col-span-5">
            <Link href="/" className="inline-flex items-center gap-2">
              <Image
                src="/logo-white.webp"
                alt="metricx"
                width={140}
                height={44}
                className="h-9 w-auto brightness-0 invert"
              />
            </Link>
            <p className="mt-4 text-sm text-gray-400 font-geist max-w-sm">
              Ad analytics for e-commerce merchants. Understand which ads make you money, cut waste, and grow profitably.
            </p>
            <div className="mt-6 flex items-center gap-3">
              {/* Twitter/X */}
              <a href="#" className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition backdrop-blur-md border border-white/10">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              {/* Discord */}
              <a href="#" className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition backdrop-blur-md border border-white/10">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Links Grid - Only Product and Legal */}
          <div className="lg:col-span-7 grid grid-cols-2 sm:grid-cols-2 gap-8 sm:gap-12 lg:justify-end">
            <FooterColumn title="Product">
              <FooterLink href="#">Features</FooterLink>
              <FooterLink href="#">Integrations</FooterLink>
              <FooterLink href="#">Pricing</FooterLink>
              <FooterLink href="#">Changelog</FooterLink>
            </FooterColumn>
            <FooterColumn title="Legal">
              <FooterLink href="#">Privacy</FooterLink>
              <FooterLink href="#">Terms</FooterLink>
              <FooterLink href="#">Security</FooterLink>
            </FooterColumn>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-400 font-geist">© {new Date().getFullYear()} metricx. All rights reserved.</p>
          <div className="flex items-center gap-6 text-xs text-gray-400">
            <a href="#" className="hover:text-white transition font-geist">Status</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

/**
 * FooterColumn - Footer link column
 */
function FooterColumn({ title, children }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-white font-geist tracking-tight">{title}</h3>
      <ul className="mt-4 space-y-3">
        {children}
      </ul>
    </div>
  );
}

/**
 * FooterLink - Single footer link
 */
function FooterLink({ href, children }) {
  return (
    <li>
      <a href={href} className="text-sm text-gray-400 hover:text-white transition font-geist">
        {children}
      </a>
    </li>
  );
}
