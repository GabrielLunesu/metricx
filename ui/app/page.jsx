// Minimal homepage with a CTA to open the dashboard
"use client";
import { useEffect } from "react";
import { ArrowRight, Bot, LineChart, Receipt, Link as LinkIcon, Database, Zap, PlayCircle } from "lucide-react";
import { FloatingNav } from "@/components/FloatingNav";
import { AuroraBackground } from "@/components/AuroraBackground";
import { CanvasShowcase } from "@/components/CanvasShowcase";
import { IconSparkles, IconRoute, IconPresentation, IconMail } from "@tabler/icons-react";

export default function HomePage() {
  useEffect(() => {
    // Scroll reveal animation
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.classList.add('active');
          }, index * 100);
        }
      });
    }, observerOptions);

    document.querySelectorAll('.reveal').forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const navItems = [
    {
      name: "Features",
      link: "#features",
      icon: <IconSparkles className="h-4 w-4 text-neutral-500" />,
    },
    {
      name: "How It Works",
      link: "#how-it-works",
      icon: <IconRoute className="h-4 w-4 text-neutral-500" />,
    },
    {
      name: "Showcase",
      link: "#showcase",
      icon: <IconPresentation className="h-4 w-4 text-neutral-500" />,
    },
    {
      name: "Contact",
      link: "#contact",
      icon: <IconMail className="h-4 w-4 text-neutral-500" />,
    },
  ];

  return (
    <AuroraBackground className="relative w-full">
      {/* Navigation */}
      <FloatingNav navItems={navItems} />

      {/* Hero Section */}
      <section className="min-h-screen flex items-center justify-center pt-20 px-8 relative overflow-hidden">
        <div className="max-w-7xl mx-auto w-full grid lg:grid-cols-2 gap-16 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="space-y-6">
              <h1 className="text-6xl lg:text-7xl font-semibold tracking-tight leading-[1.1]">
                <span className="text-black">The First</span><br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-black to-cyan-600">Agentic CMO.</span>
              </h1>
              <p className="text-xl text-black leading-relaxed max-w-xl font-light">
                Google & Meta, unified. Ask anything about your campaigns. See every dollar spent at granular level. Always know what's working — and what's not.
              </p>
            </div>

            <div className="flex items-center gap-4 flex-wrap">
              <a href="/dashboard" className="px-8 py-4 rounded-full bg-black text-white text-base font-medium btn-primary inline-flex items-center gap-2">
                Launch Dashboard
                <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
              </a>
              <a href="#features" className="px-8 py-4 rounded-full border-2 border-cyan-400/60 text-cyan-700 text-base font-medium btn-secondary inline-flex items-center gap-2">
                Explore Features
              </a>
            </div>

            <div className="flex items-center gap-6 pt-4 flex-wrap">
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Powered by Google & Meta APIs
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Built for growth teams
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                Deployed with Defang
              </div>
            </div>
          </div>

          {/* Right Visual - Animated Dashboard Preview */}
          <div className="relative">
            <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-2xl float-orb">
              <div className="space-y-4">
                {/* Chat Snippet */}
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1 space-y-2">
                    <div className="bg-white/60 rounded-2xl rounded-tl-none p-4 border border-neutral-200/40">
                      <p className="text-sm text-neutral-700">Your ROAS increased by 18% this week. Campaign "Summer Sale" is your top performer at 4.2x.</p>
                    </div>
                  </div>
                </div>

                {/* Mini KPI Cards */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="bg-white/60 rounded-2xl p-4 border border-neutral-200/40">
                    <p className="text-xs text-neutral-500 mb-1">Revenue</p>
                    <p className="text-2xl font-semibold text-neutral-900">$89.2K</p>
                    <span className="text-xs text-green-600 font-medium">+18.2%</span>
                  </div>
                  <div className="bg-white/60 rounded-2xl p-4 border border-neutral-200/40">
                    <p className="text-xs text-neutral-500 mb-1">ROAS</p>
                    <p className="text-2xl font-semibold text-neutral-900">3.63x</p>
                    <span className="text-xs text-green-600 font-medium">+5.8%</span>
                  </div>
                </div>

                {/* Mini Chart */}
                <div className="bg-white/60 rounded-2xl p-4 border border-neutral-200/40">
                  <div className="h-20 flex items-end justify-between gap-1">
                    {[40, 55, 48, 70, 82, 100, 65].map((height, i) => (
                      <div key={i} className="flex-1 bg-gradient-to-t from-cyan-400 to-cyan-200 rounded-t" style={{ height: `${height}%`, opacity: 0.5 + (height / 200) }}></div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 px-8 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20 reveal">
            <h2 className="text-5xl font-semibold tracking-tight text-black mb-4">Everything you need to succeed</h2>
            <p className="text-xl text-neutral-600 font-light">Three powerful modules, one intelligent platform</p>
          </div>

          {/* Canvas Showcase - Full Width */}
          <div className="mb-16 reveal">
            <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-xl">
              <div className="text-center mb-8">
                <h3 className="text-3xl font-semibold text-black mb-3">Visual Campaign Canvas</h3>
                <p className="text-base text-neutral-600">
                  See your entire campaign structure at a glance. Every campaign, ad set, and creative — with spend and performance on every level.
                </p>
              </div>
              <CanvasShowcase />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* AI Copilot Card */}
            <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-xl card-hover reveal">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-50 to-cyan-100 flex items-center justify-center mb-6 mx-auto">
                <Bot className="w-8 h-8 text-cyan-600" strokeWidth={1.5} />
              </div>
              <h3 className="text-2xl font-semibold text-black mb-4 text-center">AI Copilot</h3>
              <p className="text-base text-neutral-600 text-center leading-relaxed">
                Ask any question. Get instant, natural-language insights on ROAS, spend, performance, and profit.
              </p>
              <div className="mt-8 p-4 bg-white/60 rounded-2xl border border-neutral-200/40">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-cyan-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Zap className="w-3 h-3 text-cyan-600" strokeWidth={1.5} />
                  </div>
                  <p className="text-sm text-neutral-700 italic">"Which campaign has the best ROAS this week?"</p>
                </div>
              </div>
            </div>

            {/* Analytics Card */}
            <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-xl card-hover reveal" style={{ animationDelay: '0.2s' }}>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-50 to-cyan-100 flex items-center justify-center mb-6 mx-auto">
                <LineChart className="w-8 h-8 text-cyan-600" strokeWidth={1.5} />
              </div>
              <h3 className="text-2xl font-semibold text-black mb-4 text-center">Analytics & Campaigns</h3>
              <p className="text-base text-neutral-600 text-center leading-relaxed">
                See every channel, ad set, and trend in one unified dashboard. Compare Google vs Meta in real time.
              </p>
              <div className="mt-8 p-4 bg-white/60 rounded-2xl border border-neutral-200/40">
                <div className="h-16 flex items-end justify-between gap-1">
                  {[45, 60, 50, 75, 100, 65].map((height, i) => (
                    <div key={i} className="flex-1 bg-cyan-400 rounded-t" style={{ height: `${height}%`, opacity: 0.6 + (height / 200) }}></div>
                  ))}
                </div>
              </div>
            </div>

            {/* Finance Card */}
            <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-xl card-hover reveal" style={{ animationDelay: '0.3s' }}>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-50 to-cyan-100 flex items-center justify-center mb-6 mx-auto">
                <Receipt className="w-8 h-8 text-cyan-600" strokeWidth={1.5} />
              </div>
              <h3 className="text-2xl font-semibold text-black mb-4 text-center">Finance (P&L)</h3>
              <p className="text-base text-neutral-600 text-center leading-relaxed">
                Understand budget vs actuals instantly. Track profit margins and cost efficiency with visual variance alerts.
              </p>
              <div className="mt-8 p-4 bg-white/60 rounded-2xl border border-neutral-200/40 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-600">Ad Spend</span>
                  <div className="flex items-center gap-2">
                    <span className="text-neutral-900 font-medium">$24.5K</span>
                    <span className="text-green-600 font-medium">↓ 3%</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-600">Revenue</span>
                  <div className="flex items-center gap-2">
                    <span className="text-neutral-900 font-medium">$89.2K</span>
                    <span className="text-green-600 font-medium">↑ 18%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-32 px-8 relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20 reveal">
            <h2 className="text-5xl font-semibold tracking-tight text-black mb-4">From data to clarity — in seconds.</h2>
            <p className="text-xl text-neutral-600 font-light">Three simple steps to transform your marketing workflow</p>
          </div>

          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute top-24 left-0 right-0 h-0.5 timeline-line hidden lg:block"></div>

            <div className="grid md:grid-cols-3 gap-12">
              {/* Step 1 */}
              <div className="text-center reveal" style={{ animationDelay: '0.1s' }}>
                <div className="relative mb-8">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center mx-auto shadow-lg relative z-10 pulse-glow-btn">
                    <LinkIcon className="w-10 h-10 text-white" strokeWidth={1.5} />
                  </div>
                </div>
                <h3 className="text-2xl font-semibold text-black mb-3">Connect your accounts</h3>
                <p className="text-base text-neutral-600 leading-relaxed">Securely sync Google Ads & Meta with one click.</p>
              </div>

              {/* Step 2 */}
              <div className="text-center reveal" style={{ animationDelay: '0.2s' }}>
                <div className="relative mb-8">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center mx-auto shadow-lg relative z-10 pulse-glow-btn" style={{ animationDelay: '1s' }}>
                    <Database className="w-10 h-10 text-white" strokeWidth={1.5} />
                  </div>
                </div>
                <h3 className="text-2xl font-semibold text-black mb-3">metricx unifies your data</h3>
                <p className="text-base text-neutral-600 leading-relaxed">Smart schema + AI reasoning turns raw metrics into human language.</p>
              </div>

              {/* Step 3 */}
              <div className="text-center reveal" style={{ animationDelay: '0.3s' }}>
                <div className="relative mb-8">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center mx-auto shadow-lg relative z-10 pulse-glow-btn" style={{ animationDelay: '2s' }}>
                    <Zap className="w-10 h-10 text-white" strokeWidth={1.5} />
                  </div>
                </div>
                <h3 className="text-2xl font-semibold text-black mb-3">Ask, analyze, act</h3>
                <p className="text-base text-neutral-600 leading-relaxed">Your Copilot interprets, explains, and even suggests your next move.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Showcase Section */}
      <section id="showcase" className="py-32 px-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-white via-cyan-50/30 to-white -z-10"></div>

        <div className="max-w-6xl mx-auto text-center reveal">
          <h2 className="text-5xl font-semibold tracking-tight text-black mb-4">A single platform that understands your marketing.</h2>
          <p className="text-2xl text-neutral-600 font-light mb-3">Intuitive. Connected. Real-time.</p>
          <p className="text-lg text-neutral-500 mb-16">Built for agencies, growth marketers, and founders.</p>

          <div className="glass-card rounded-3xl p-12 border border-neutral-200/60 shadow-2xl">
            <div className="space-y-6">
              {/* Dashboard Preview Grid */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-white/80 rounded-2xl p-6 border border-neutral-200/40">
                  <p className="text-xs text-neutral-500 mb-2 uppercase tracking-wide">Total Spend</p>
                  <p className="text-3xl font-semibold text-neutral-900 mb-2">$24.5K</p>
                  <span className="text-xs text-green-600 font-medium">+12.5%</span>
                </div>
                <div className="bg-white/80 rounded-2xl p-6 border border-neutral-200/40">
                  <p className="text-xs text-neutral-500 mb-2 uppercase tracking-wide">Revenue</p>
                  <p className="text-3xl font-semibold text-neutral-900 mb-2">$89.2K</p>
                  <span className="text-xs text-green-600 font-medium">+18.2%</span>
                </div>
                <div className="bg-white/80 rounded-2xl p-6 border border-neutral-200/40">
                  <p className="text-xs text-neutral-500 mb-2 uppercase tracking-wide">ROAS</p>
                  <p className="text-3xl font-semibold text-neutral-900 mb-2">3.63x</p>
                  <span className="text-xs text-green-600 font-medium">+5.8%</span>
                </div>
              </div>

              {/* Chart Preview */}
              <div className="bg-white/80 rounded-2xl p-8 border border-neutral-200/40">
                <div className="h-40 flex items-end justify-between gap-2">
                  {[50, 62, 55, 78, 88, 100, 70, 82].map((height, i) => (
                    <div key={i} className="flex-1 bg-gradient-to-t from-cyan-400 to-cyan-200 rounded-t" style={{ height: `${height}%`, opacity: 0.6 + (height / 200) }}></div>
                  ))}
                </div>
              </div>

              {/* Copilot Chat Preview */}
              <div className="bg-white/80 rounded-2xl p-6 border border-neutral-200/40 text-left">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-neutral-700">Based on your recent performance, I recommend increasing budget on Campaign "Summer Sale" by 15%. It's currently delivering 4.2x ROAS and has room for scale.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Footer Section */}
      <section id="contact" className="py-32 px-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-cyan-50/40 to-white -z-10"></div>

        <div className="max-w-4xl mx-auto text-center reveal">
          <h2 className="text-6xl font-semibold tracking-tight text-black mb-4">Meet your Copilot.</h2>
          <p className="text-2xl text-neutral-600 font-light mb-12">Start transforming your marketing workflow today.</p>

          <div className="flex items-center justify-center gap-4 mb-16 flex-wrap">
            <a href="/dashboard" className="px-10 py-5 rounded-full bg-black text-white text-lg font-medium btn-primary inline-flex items-center gap-2">
              Try metricx Free
              <ArrowRight className="w-5 h-5" strokeWidth={1.5} />
            </a>
            <a href="#features" className="px-10 py-5 rounded-full border-2 border-cyan-400/60 text-cyan-700 text-lg font-medium btn-secondary inline-flex items-center gap-2">
              <PlayCircle className="w-5 h-5" strokeWidth={1.5} />
              Watch Demo
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-8 border-t border-neutral-200/60">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between flex-wrap gap-8">
            <a href="/" className="flex items-center">
              <img src="/metricx-logo.png" alt="metricx" className="h-12" />
            </a>
            <nav className="flex items-center gap-8 flex-wrap">
              <a href="#features" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Features</a>
              <a href="#how-it-works" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">How It Works</a>
              <a href="#showcase" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Showcase</a>
              <a href="#contact" className="text-sm font-medium text-neutral-500 hover:text-cyan-600 transition-colors">Contact</a>
            </nav>
          </div>
          <div className="mt-8 pt-8 border-t border-neutral-200/60 flex items-center justify-between flex-wrap gap-4">
            <p className="text-sm text-neutral-500">© 2024 metricx. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <a href="/privacy" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Privacy Policy</a>
              <a href="/terms" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Terms of Service</a>
              <a href="/settings" className="text-sm text-neutral-500 hover:text-cyan-600 transition-colors">Delete My Data</a>
            </div>
          </div>
        </div>
      </footer>
    </AuroraBackground>
  );
}
