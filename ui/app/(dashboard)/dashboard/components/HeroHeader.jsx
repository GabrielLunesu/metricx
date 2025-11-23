'use client';

import { Search, SendHorizontal } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function HeroHeader({ user, actions }) {
    const name = user?.email?.split('@')[0] || "there";
    const displayName = name.charAt(0).toUpperCase() + name.slice(1);
    const router = useRouter();
    const [question, setQuestion] = useState("");

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
                    Good morning, {displayName}.
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
                        placeholder="Ask AdNavi about your performance..."
                    />
                    <div className="absolute inset-y-0 right-0 pr-4 flex items-center cursor-pointer">
                        <div className="bg-gradient-to-tr from-cyan-500 to-blue-500 p-1.5 rounded-full shadow-lg shadow-cyan-500/30">
                            <SendHorizontal className="w-4 h-4 text-white" />
                        </div>
                    </div>
                </form>

                {/* Timeframe Selector */}
                {actions}
            </div>
        </header>
    );
}
