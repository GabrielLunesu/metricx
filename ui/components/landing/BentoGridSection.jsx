"use client";

import { Bot, LineChart, Zap, Shield } from "lucide-react";

function Badge({ icon, text }) {
  return (
    <div className="px-[14px] py-[6px] bg-white shadow-[0px_0px_0px_4px_rgba(55,50,47,0.05)] overflow-hidden rounded-[90px] flex justify-start items-center gap-[8px] border border-[rgba(2,6,23,0.08)]">
      <div className="w-[14px] h-[14px] relative overflow-hidden flex items-center justify-center">{icon}</div>
      <div className="text-center flex justify-center flex-col text-[#37322F] text-xs font-medium leading-3 font-sans">
        {text}
      </div>
    </div>
  );
}

function NaturalLanguageVisual() {
  return (
    <div className="w-full h-full flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
        <span className="text-gray-400 text-sm">Ask:</span>
        <span className="text-gray-700 text-sm">"What's my ROAS this week?"</span>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div className="text-2xl font-bold text-gray-900">3.63x</div>
          <div className="text-sm text-green-600 font-medium">+12% vs last week</div>
        </div>
      </div>
    </div>
  );
}

function UnifiedDataVisual() {
  return (
    <div className="w-full h-full flex flex-col gap-2 p-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold">M</div>
        <div className="flex-1 h-2 bg-blue-200 rounded-full">
          <div className="h-full w-3/4 bg-blue-500 rounded-full"></div>
        </div>
        <span className="text-sm text-gray-600">$18.2K</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded bg-red-100 flex items-center justify-center text-red-600 text-xs font-bold">G</div>
        <div className="flex-1 h-2 bg-red-200 rounded-full">
          <div className="h-full w-1/2 bg-red-500 rounded-full"></div>
        </div>
        <span className="text-sm text-gray-600">$6.3K</span>
      </div>
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100">
        <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center text-gray-600 text-xs font-bold">All</div>
        <div className="flex-1 h-2 bg-gray-200 rounded-full">
          <div className="h-full w-full bg-gray-600 rounded-full"></div>
        </div>
        <span className="text-sm text-gray-900 font-semibold">$24.5K</span>
      </div>
    </div>
  );
}

function RealTimeVisual() {
  const bars = [45, 62, 55, 78, 88, 95, 82];
  return (
    <div className="w-full h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">Live Performance</span>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs text-green-600">Live</span>
        </div>
      </div>
      <div className="flex-1 flex items-end justify-between gap-1">
        {bars.map((height, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full bg-gradient-to-t from-cyan-500 to-cyan-300 rounded-t transition-all duration-500"
              style={{ height: `${height}%` }}
            ></div>
            <span className="text-[10px] text-gray-400">{['M', 'T', 'W', 'T', 'F', 'S', 'S'][i]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SecureVisual() {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-4">
      <div className="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center border-2 border-green-200">
        <Shield className="w-8 h-8 text-green-600" />
      </div>
      <div className="flex flex-col items-center gap-1">
        <div className="text-sm font-semibold text-gray-900">Workspace Isolated</div>
        <div className="text-xs text-gray-500 text-center">Your data is scoped & secure</div>
      </div>
      <div className="flex gap-2 mt-2">
        <div className="px-2 py-1 bg-gray-100 rounded text-[10px] text-gray-600">JWT Auth</div>
        <div className="px-2 py-1 bg-gray-100 rounded text-[10px] text-gray-600">No Raw SQL</div>
      </div>
    </div>
  );
}

export default function BentoGridSection() {
  return (
    <div id="features" className="w-full bg-white flex flex-col justify-center items-center">
      <div className="w-full max-w-[1060px] border-b border-[rgba(55,50,47,0.12)] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Header Section */}
        <div className="self-stretch px-4 sm:px-6 md:px-8 lg:px-0 py-8 sm:py-12 md:py-16 border-b border-[rgba(55,50,47,0.12)] flex justify-center items-center gap-6">
          <div className="w-full max-w-[616px] lg:w-[616px] px-4 sm:px-6 py-4 sm:py-5 overflow-hidden rounded-lg flex flex-col justify-start items-center gap-3 sm:gap-4">
            <Badge
              icon={
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="1" y="1" width="4" height="4" stroke="#37322F" strokeWidth="1" fill="none" />
                  <rect x="7" y="1" width="4" height="4" stroke="#37322F" strokeWidth="1" fill="none" />
                  <rect x="1" y="7" width="4" height="4" stroke="#37322F" strokeWidth="1" fill="none" />
                  <rect x="7" y="7" width="4" height="4" stroke="#37322F" strokeWidth="1" fill="none" />
                </svg>
              }
              text="Features"
            />
            <div className="w-full max-w-[598.06px] lg:w-[598.06px] text-center flex justify-center flex-col text-[#49423D] text-xl sm:text-2xl md:text-3xl lg:text-4xl font-semibold leading-tight md:leading-[50px] font-sans tracking-tight">
              Everything you need to understand your marketing
            </div>
            <div className="self-stretch text-center text-[#605A57] text-sm sm:text-base font-normal leading-6 sm:leading-7 font-sans">
              From natural language queries to real-time analytics,
              <br className="hidden sm:block" />
              get the insights you need without the complexity.
            </div>
          </div>
        </div>

        {/* Bento Grid Content */}
        <div className="self-stretch flex justify-center items-start">
          <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
            <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
              {Array.from({ length: 200 }).map((_, i) => (
                <div
                  key={i}
                  className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                />
              ))}
            </div>
          </div>

          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-0 border-l border-r border-[rgba(55,50,47,0.12)]">
            {/* Top Left - Natural Language Queries */}
            <div className="border-b border-r-0 md:border-r border-[rgba(55,50,47,0.12)] p-4 sm:p-6 md:p-8 lg:p-12 flex flex-col justify-start items-start gap-4 sm:gap-6">
              <div className="flex flex-col gap-2">
                <h3 className="text-[#37322F] text-lg sm:text-xl font-semibold leading-tight font-sans">
                  Natural Language Queries
                </h3>
                <p className="text-[#605A57] text-sm md:text-base font-normal leading-relaxed font-sans">
                  Ask questions in plain English. Get precise answers instantly, no SQL required.
                </p>
              </div>
              <div className="w-full h-[180px] sm:h-[200px] md:h-[220px] bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center overflow-hidden">
                <NaturalLanguageVisual />
              </div>
            </div>

            {/* Top Right - Unified Data */}
            <div className="border-b border-[rgba(55,50,47,0.12)] p-4 sm:p-6 md:p-8 lg:p-12 flex flex-col justify-start items-start gap-4 sm:gap-6">
              <div className="flex flex-col gap-2">
                <h3 className="text-[#37322F] text-lg sm:text-xl font-semibold leading-tight font-sans">
                  Unified Data Layer
                </h3>
                <p className="text-[#605A57] text-sm md:text-base font-normal leading-relaxed font-sans">
                  Meta + Google in one view. Compare platforms side-by-side with consistent metrics.
                </p>
              </div>
              <div className="w-full h-[180px] sm:h-[200px] md:h-[220px] bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center overflow-hidden">
                <UnifiedDataVisual />
              </div>
            </div>

            {/* Bottom Left - Real-time Analytics */}
            <div className="border-b md:border-b-0 border-r-0 md:border-r border-[rgba(55,50,47,0.12)] p-4 sm:p-6 md:p-8 lg:p-12 flex flex-col justify-start items-start gap-4 sm:gap-6">
              <div className="flex flex-col gap-2">
                <h3 className="text-[#37322F] text-lg sm:text-xl font-semibold leading-tight font-sans">
                  Real-time Performance
                </h3>
                <p className="text-[#605A57] text-sm md:text-base font-normal leading-relaxed font-sans">
                  Watch your metrics update live. Catch trends and anomalies as they happen.
                </p>
              </div>
              <div className="w-full h-[180px] sm:h-[200px] md:h-[220px] bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center overflow-hidden">
                <RealTimeVisual />
              </div>
            </div>

            {/* Bottom Right - Secure by Design */}
            <div className="p-4 sm:p-6 md:p-8 lg:p-12 flex flex-col justify-start items-start gap-4 sm:gap-6">
              <div className="flex flex-col gap-2">
                <h3 className="text-[#37322F] text-lg sm:text-xl font-semibold leading-tight font-sans">
                  Secure by Design
                </h3>
                <p className="text-[#605A57] text-sm md:text-base font-normal leading-relaxed font-sans">
                  Workspace-isolated data. No SQL injection possible. Your metrics stay yours.
                </p>
              </div>
              <div className="w-full h-[180px] sm:h-[200px] md:h-[220px] bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center overflow-hidden">
                <SecureVisual />
              </div>
            </div>
          </div>

          <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
            <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
              {Array.from({ length: 200 }).map((_, i) => (
                <div
                  key={i}
                  className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
