"use client";

import { LiquidMetal } from '@paper-design/shaders-react';
import { DollarSign, TrendingUp, MessageSquare, BarChart3 } from "lucide-react";

const logo = "/logo-white.webp";

// Static feature card component - clean, no animations
function FeatureCard({ icon: Icon, label, value, x, y }) {
    return (
        <div
            className="absolute z-20 hidden md:flex items-center gap-3 p-3 pr-5 bg-white backdrop-blur-md border border-gray-100 rounded-full shadow-lg"
            style={{ left: x, top: y }}
        >
            <div className="p-2 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600">
                <Icon className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div className="flex flex-col">
                <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wide">{label}</span>
                <span className="text-sm font-semibold text-gray-900">{value}</span>
            </div>
        </div>
    );
}

export default function HeroMinimal() {
    return (
        <section className="relative w-screen min-h-screen  overflow-hidden">

            {/* Navbar */}
            <nav className="absolute top-0 left-0 right-0 z-50 flex justify-between items-center px-6 py-6 max-w-7xl mx-auto w-full">
                <div className="flex items-center gap-2">
                    {/* <img src="/logo-white.png" alt="AdNavi" className="h-8" /> */}
                </div>
                <div className="flex items-center gap-6">
                    <a href="/sign-in" className="text-sm font-medium text-black hover:text-white transition-colors">Log in</a>
                    <a href="/dashboard" className="px-4 py-2 bg-white text-black text-sm font-medium rounded-full hover:bg-gray-200 transition-colors">
                        Get Started
                    </a>
                </div>
            </nav>

            {/* Liquid Metal & Features Container - Full Screen */}
            <div className="relative w-full h-screen">

                {/* The Liquid Metal Component - Centered */}
                <div className="absolute inset-0 flex items-center justify-center z-0">
                    <LiquidMetal
                        width={1980}
                        height={1080}
                        image={logo}
                        colorBack=""
                        colorTint="#00d9ff"
                        shape={undefined}
                        repetition={1.5}
                        softness={0.45}
                        shiftRed={0}
                        shiftBlue={0}
                        distortion={0.4}
                        contour={0.2}
                        angle={58}
                        speed={0.5}
                        scale={0.4}
                        fit="contain"
                    />
                </div>

                {/* Feature cards showing actual use cases */}
                {/* <FeatureCard
                    icon={MessageSquare}
                    label="Ask Your Data"
                    value="What's my ROAS this week?"
                    x="10%"
                    y="30%"
                />
                <FeatureCard
                    icon={BarChart3}
                    label="Unified Dashboard"
                    value="Meta + Google in one view"
                    x="68%"
                    y="22%"
                />
                <FeatureCard
                    icon={TrendingUp}
                    label="Find Winners"
                    value="Compare campaign performance"
                    x="5%"
                    y="65%"
                />
                <FeatureCard
                    icon={DollarSign}
                    label="True Profitability"
                    value="P&L with real costs"
                    x="72%"
                    y="70%"
                /> */}
            </div>
        </section>
    );
}