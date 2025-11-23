"use client";
import { useState } from "react";
import { TrendingDown, Image, AlertCircle, DollarSign, ArrowUp } from "lucide-react";

const intentChips = [
  { icon: TrendingDown, text: "Why is ROAS down?" },
  { icon: Image, text: "Show best creatives" },
  { icon: AlertCircle, text: "Campaigns with zero sales" },
  { icon: DollarSign, text: "Spend vs last week" },
];

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
    <div className="absolute w-full z-[80] bottom-24 md:bottom-0 md:left-[90px] md:right-6 md:w-auto pointer-events-auto">
      {/* Gradient Fade for background */}
      <div className="absolute bottom-0 w-full h-48 bg-gradient-to-t from-slate-50 via-slate-50/90 to-transparent pointer-events-none"></div>

      <div className="relative max-w-[900px] mx-auto px-4 pb-6 pt-4 flex flex-col gap-3 pointer-events-auto">

        {/* Intent Chips */}
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar w-full mask-linear pl-2">
          {intentChips.map((chip, idx) => {
            const Icon = chip.icon;
            return (
              <button
                key={idx}
                onClick={() => handleChipClick(chip.text)}
                disabled={disabled}
                className="shrink-0 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm hover:border-blue-300 hover:shadow-md hover:text-blue-600 transition-all text-[11px] font-medium text-slate-600 group flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Icon className="w-3 h-3 text-slate-400 group-hover:text-blue-500" />
                {chip.text}
              </button>
            );
          })}
        </div>

        {/* Input Container */}
        <form onSubmit={handleSubmit} className="relative group">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-100 to-cyan-100 rounded-full blur opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none"></div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled}
            className="w-full h-16 pl-6 pr-16 rounded-full bg-white border border-slate-200 shadow-float text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all text-base disabled:opacity-50"
            placeholder="Ask: what should I scale today?"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={disabled || !input.trim() || noWorkspace}
            className="absolute right-2 top-2 bottom-2 w-12 h-12 rounded-full bg-gradient-to-br from-slate-50 to-white border border-slate-100 shadow-sm hover:shadow-md hover:scale-105 transition-all flex items-center justify-center group/btn disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            <div className="p-2 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 text-white group-hover/btn:rotate-45 transition-transform duration-300">
              <ArrowUp className="w-4 h-4" />
            </div>
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
  );
}
