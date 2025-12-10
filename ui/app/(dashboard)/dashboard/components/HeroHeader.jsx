'use client';

import { Search, SendHorizontal, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";

/**
 * Format relative time (e.g., "2 min ago", "1 hour ago")
 */
function formatRelativeTime(isoString) {
    if (!isoString) return null;

    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHours = Math.floor(diffMin / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSec < 60) return "just now";
        if (diffMin < 60) return `${diffMin} min ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays === 1) return "yesterday";
        return `${diffDays} days ago`;
    } catch {
        return null;
    }
}

export default function HeroHeader({ user, actions, lastSyncedAt }) {
    const name = user?.name || "there";
    const displayName = name.charAt(0).toUpperCase() + name.slice(1);
    const router = useRouter();
    const [question, setQuestion] = useState("");

    const relativeTime = useMemo(() => formatRelativeTime(lastSyncedAt), [lastSyncedAt]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!question.trim()) return;

        // Navigate to copilot page with question
        const params = new URLSearchParams({
            q: question.trim(),
            ws: user.workspace_id
        });
        router.push(`/copilot?${params.toString()}`);
    };

    return (
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 animate-slide-in">
            <div>
                <h1 className="text-3xl pb-2 md:text-5xl font-semibold tracking-tight text-slate-900 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600">
                    Hello, {displayName}.
                </h1>
                <p className="text-slate-900 text-xl mt-2 font-normal">
                    Here's what's happening with your business today.
                </p>
            </div>

            <div className="flex flex-col gap-3 items-end">
                {/* AI Search Bar */}
                <form onSubmit={handleSubmit} className="relative group w-full md:w-[500px]">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="w-5 h-5 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        className="w-full pl-12 pr-12 py-3.5 rounded-full glass-input text-base text-slate-700 placeholder-slate-400 focus:ring-0"
                        placeholder="Ask metricx about your performance..."
                    />
                    <div className="absolute inset-y-0 right-0 pr-4 flex items-center cursor-pointer">
                        <div className="bg-gradient-to-tr from-cyan-500 to-blue-500 p-1.5 rounded-full shadow-lg shadow-cyan-500/30">
                            <SendHorizontal className="w-4 h-4 text-white" />
                        </div>
                    </div>
                </form>

                {/* Timeframe Selector + Sync Status */}
                <div className="flex items-center gap-3">
                    {relativeTime && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                            <RefreshCw className="w-3 h-3" />
                            <span>Updated {relativeTime}</span>
                        </div>
                    )}
                    {actions}
                </div>
            </div>
        </header>
    );
}
