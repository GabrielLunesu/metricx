"use client";
import { useState } from "react";
import { TrendingDown, Image, AlertCircle, DollarSign, ArrowUp } from "lucide-react";

// Intent chips for quick questions (v2.1)
// WHY: Provides common query shortcuts for better UX
const intentChips = [
  { icon: TrendingDown, text: "Why is ROAS down?" },
  { icon: Image, text: "Show best creatives" },
  { icon: AlertCircle, text: "Campaigns with zero sales" },
  { icon: DollarSign, text: "Spend vs last week" },
];

// Chat Console (v2.1 - Apple-inspired subtle glass design)
// WHAT: Input area with quick question chips
// WHY: Clean, minimal aesthetic with subtle focus states
export default function ChatConsole({ onSubmit, disabled, noWorkspace }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled || noWorkspace) return;
    onSubmit(input.trim());
    setInput("");
  };

  const handleChipClick = (question) => {
    if (disabled || noWorkspace) return;
    onSubmit(question);
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 z-[80] pointer-events-none">
      {/* Gradient Fade for background - subtle */}
      <div className="absolute bottom-0 w-full h-48 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent pointer-events-none"></div>

      <div className="relative w-full flex justify-center pointer-events-auto">
        <div className="w-full max-w-[900px] px-4 pb-6 pt-4 flex flex-col gap-3">

        {/* Intent Chips - Subtle glass styling */}
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar w-full mask-linear pl-2">
          {intentChips.map((chip, idx) => {
            const Icon = chip.icon;
            return (
              <button
                key={idx}
                onClick={() => handleChipClick(chip.text)}
                disabled={disabled}
                className="shrink-0 px-4 py-2 rounded-full bg-slate-50 border border-slate-200/60 text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-colors duration-200 text-[11px] font-medium group flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Icon className="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition-colors" />
                {chip.text}
              </button>
            );
          })}
        </div>

        {/* Input Container - Subtle glass design */}
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled}
            className="w-full h-14 pl-6 pr-16 rounded-full bg-white/90 backdrop-blur-sm border border-slate-200/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all duration-200 text-base disabled:opacity-50"
            placeholder="Ask: what should I scale today?"
          />

          {/* Send Button - Subtle styling */}
          <button
            type="submit"
            disabled={disabled || !input.trim() || noWorkspace}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-blue-500 text-white shadow-sm hover:bg-blue-600 hover:shadow-md transition-all duration-200 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </form>

        {/* Footer Disclaimer */}
        <div className="text-center">
          {noWorkspace ? (
            <p className="text-[10px] text-rose-500 font-medium">
              Connect a workspace to start chatting with Copilot.
            </p>
          ) : (
            <p className="text-[10px] text-slate-400 font-medium">
              Copilot is connected to your Meta and Google data. Ask in plain language.
            </p>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}
