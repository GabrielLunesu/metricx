'use client';

import { Bot, ChevronDown } from "lucide-react";

export default function CopilotHeader() {
    return (
        <header className="h-16 glass-nav fixed top-0 w-full z-50 px-6 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-4">
                {/* Logo/Icon */}
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white">
                    <Bot className="w-5 h-5" />
                </div>

                <div className="flex flex-col">
                    <h1 className="text-sm font-bold tracking-tight text-slate-800">metricx Copilot</h1>
                    <span className="text-[11px] text-slate-500 font-medium">Ask anything about your campaigns, ad sets and ads.</span>
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Status Pill */}
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-full shadow-sm">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                    <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-wide">Data Synced</span>
                </div>

                {/* Account Selector */}
                <button className="flex items-center gap-2 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 rounded-full transition-colors text-xs font-medium text-slate-700">
                    <span>Acme Corp US</span>
                    <ChevronDown className="w-3 h-3 text-slate-400" />
                </button>
            </div>
        </header>
    );
}
