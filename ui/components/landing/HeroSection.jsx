"use client";

import { useState, useEffect, useRef } from "react";
import { AuroraBackground } from "@/components/AuroraBackground";
import { Bot, LineChart, Receipt } from "lucide-react";

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

function FeatureCard({ title, description, isActive, progress, onClick }) {
  return (
    <div
      className={`w-full md:flex-1 self-stretch px-6 py-5 overflow-hidden flex flex-col justify-start items-start gap-2 cursor-pointer relative border-b md:border-b-0 last:border-b-0 transition-all duration-200 ${
        isActive
          ? "bg-white shadow-[0px_0px_0px_0.75px_#E0DEDB_inset]"
          : "border-l-0 border-r-0 md:border border-[#E0DEDB]/80 hover:bg-white/50"
      }`}
      onClick={onClick}
    >
      {isActive && (
        <div className="absolute top-0 left-0 w-full h-0.5 bg-[rgba(50,45,43,0.08)]">
          <div
            className="h-full bg-[#322D2B] transition-all duration-100 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="self-stretch flex justify-center flex-col text-[#49423D] text-sm md:text-sm font-semibold leading-6 md:leading-6 font-sans">
        {title}
      </div>
      <div className="self-stretch text-[#605A57] text-[13px] md:text-[13px] font-normal leading-[22px] md:leading-[22px] font-sans">
        {description}
      </div>
    </div>
  );
}

export default function HeroSection() {
  const [activeCard, setActiveCard] = useState(0);
  const [progress, setProgress] = useState(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    const progressInterval = setInterval(() => {
      if (!mountedRef.current) return;

      setProgress((prev) => {
        if (prev >= 100) {
          if (mountedRef.current) {
            setActiveCard((current) => (current + 1) % 3);
          }
          return 0;
        }
        return prev + 2;
      });
    }, 100);

    return () => {
      clearInterval(progressInterval);
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleCardClick = (index) => {
    if (!mountedRef.current) return;
    setActiveCard(index);
    setProgress(0);
  };

  const features = [
    {
      title: "AI Copilot",
      description: "Ask any question in plain English. Get instant insights on ROAS, spend, and performance.",
      icon: <Bot className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />,
    },
    {
      title: "Unified Analytics",
      description: "See every channel, ad set, and trend in one dashboard. Compare Google vs Meta in real time.",
      icon: <LineChart className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />,
    },
    {
      title: "Finance & P&L",
      description: "Track budget vs actuals. Understand profit margins with visual variance alerts.",
      icon: <Receipt className="w-6 h-6 text-cyan-600" strokeWidth={1.5} />,
    },
  ];

  return (
    <AuroraBackground className="relative w-full">
      <div className="w-full max-w-none px-4 sm:px-6 md:px-8 lg:px-0 lg:max-w-[1060px] lg:w-[1060px] mx-auto relative flex flex-col justify-start items-start">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-4 sm:left-6 md:left-8 lg:left-0 top-0 bg-[rgba(55,50,47,0.12)] shadow-[1px_0px_0px_white] z-0"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-4 sm:right-6 md:right-8 lg:right-0 top-0 bg-[rgba(55,50,47,0.12)] shadow-[1px_0px_0px_white] z-0"></div>

        <div className="self-stretch pt-[9px] overflow-hidden border-b border-[rgba(55,50,47,0.06)] flex flex-col justify-center items-center gap-4 sm:gap-6 md:gap-8 lg:gap-[66px] relative z-10">
          {/* Navigation */}
          <div className="w-full h-12 sm:h-14 md:h-16 lg:h-[84px] absolute left-0 top-0 flex justify-center items-center z-20 px-6 sm:px-8 md:px-12 lg:px-0">
            <div className="w-full h-0 absolute left-0 top-6 sm:top-7 md:top-8 lg:top-[42px] border-t border-[rgba(55,50,47,0.12)] shadow-[0px_1px_0px_white]"></div>

            <div className="w-full max-w-[calc(100%-32px)] sm:max-w-[calc(100%-48px)] md:max-w-[calc(100%-64px)] lg:max-w-[700px] lg:w-[700px] h-10 sm:h-11 md:h-12 py-1.5 sm:py-2 px-3 sm:px-4 md:px-4 pr-2 sm:pr-3 bg-white/80 backdrop-blur-sm shadow-[0px_0px_0px_2px_white] overflow-hidden rounded-[50px] flex justify-between items-center relative z-30">
              <div className="flex justify-center items-center">
                <div className="flex justify-start items-center">
                  <a href="/" className="flex items-center">
                    <img src="/logo.png" alt="metricx" className="h-6 sm:h-7 md:h-8" />
                  </a>
                </div>
                <div className="pl-3 sm:pl-4 md:pl-5 lg:pl-5 hidden sm:flex flex-row gap-2 sm:gap-3 md:gap-4 lg:gap-4">
                  <a href="#features" className="flex justify-start items-center">
                    <div className="flex flex-col justify-center text-[rgba(49,45,43,0.80)] text-xs md:text-[13px] font-medium leading-[14px] font-sans hover:text-[#37322F] transition-colors">
                      Features
                    </div>
                  </a>
                  <a href="#pricing" className="flex justify-start items-center">
                    <div className="flex flex-col justify-center text-[rgba(49,45,43,0.80)] text-xs md:text-[13px] font-medium leading-[14px] font-sans hover:text-[#37322F] transition-colors">
                      Pricing
                    </div>
                  </a>
                  <a href="#faq" className="flex justify-start items-center">
                    <div className="flex flex-col justify-center text-[rgba(49,45,43,0.80)] text-xs md:text-[13px] font-medium leading-[14px] font-sans hover:text-[#37322F] transition-colors">
                      FAQ
                    </div>
                  </a>
                </div>
              </div>
              <div className="h-6 sm:h-7 md:h-8 flex justify-start items-start gap-2 sm:gap-3">
                <a
                  href="/login"
                  className="px-2 sm:px-3 md:px-[14px] py-1 sm:py-[6px] bg-white shadow-[0px_1px_2px_rgba(55,50,47,0.12)] overflow-hidden rounded-full flex justify-center items-center hover:bg-gray-50 transition-colors"
                >
                  <div className="flex flex-col justify-center text-[#37322F] text-xs md:text-[13px] font-medium leading-5 font-sans">
                    Log in
                  </div>
                </a>
              </div>
            </div>
          </div>

          {/* Hero Section */}
          <div className="pt-16 sm:pt-20 md:pt-24 lg:pt-[216px] pb-8 sm:pb-12 md:pb-16 flex flex-col justify-start items-center px-2 sm:px-4 md:px-8 lg:px-0 w-full">
            <div className="w-full max-w-[937px] lg:w-[937px] flex flex-col justify-center items-center gap-3 sm:gap-4 md:gap-5 lg:gap-6">
              <div className="self-stretch rounded-[3px] flex flex-col justify-center items-center gap-4 sm:gap-5 md:gap-6 lg:gap-8">
                <div className="w-full max-w-[748.71px] lg:w-[748.71px] text-center flex justify-center flex-col text-[#37322F] text-[24px] xs:text-[28px] sm:text-[36px] md:text-[52px] lg:text-[80px] font-normal leading-[1.1] sm:leading-[1.15] md:leading-[1.2] lg:leading-24 px-2 sm:px-4 md:px-0">
                  The First
                  <br />
                  <span className="font-semibold">Agentic CMO</span>
                </div>
                <div className="w-full max-w-[506.08px] lg:w-[506.08px] text-center flex justify-center flex-col text-[rgba(55,50,47,0.80)] sm:text-lg md:text-xl leading-[1.4] sm:leading-[1.45] md:leading-[1.5] lg:leading-7 font-sans px-2 sm:px-4 md:px-0 lg:text-lg font-medium text-sm">
                  Google & Meta, unified. Ask anything about your campaigns.
                  <br className="hidden sm:block" />
                  Always know what's working — and what's not.
                </div>
              </div>
            </div>

            <div className="w-full max-w-[497px] lg:w-[497px] flex flex-col justify-center items-center gap-6 sm:gap-8 md:gap-10 lg:gap-12 relative z-10 mt-6 sm:mt-8 md:mt-10 lg:mt-12">
              <div className="backdrop-blur-[8.25px] flex justify-start items-center gap-4">
                <a
                  href="/dashboard"
                  className="h-10 sm:h-11 md:h-12 px-6 sm:px-8 md:px-10 lg:px-12 py-2 sm:py-[6px] relative bg-[#37322F] shadow-[0px_0px_0px_2.5px_rgba(255,255,255,0.08)_inset] overflow-hidden rounded-full flex justify-center items-center hover:bg-[#2A2520] transition-colors"
                >
                  <div className="w-20 sm:w-24 md:w-28 lg:w-44 h-[41px] absolute left-0 top-[-0.5px] bg-gradient-to-b from-[rgba(255,255,255,0)] to-[rgba(0,0,0,0.10)] mix-blend-multiply"></div>
                  <div className="flex flex-col justify-center text-white text-sm sm:text-base md:text-[15px] font-medium leading-5 font-sans">
                    Try for free
                  </div>
                </a>
              </div>
            </div>

            {/* Dashboard Preview */}
            <div className="w-full max-w-[960px] lg:w-[960px] pt-2 sm:pt-4 pb-6 sm:pb-8 md:pb-10 px-2 sm:px-4 md:px-6 lg:px-11 flex flex-col justify-center items-center gap-2 relative z-5 my-8 sm:my-12 md:my-16 lg:my-16 mb-0 lg:pb-0">
              <div className="w-full max-w-[960px] lg:w-[960px] h-[200px] sm:h-[280px] md:h-[450px] lg:h-[500px] bg-white shadow-[0px_0px_0px_0.9056603908538818px_rgba(0,0,0,0.08)] overflow-hidden rounded-[6px] sm:rounded-[8px] lg:rounded-[9.06px] flex flex-col justify-start items-start">
                {/* Dashboard Content */}
                <div className="self-stretch flex-1 flex justify-start items-start">
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="relative w-full h-full overflow-hidden">
                      {/* AI Copilot View */}
                      <div
                        className={`absolute inset-0 transition-all duration-500 ease-in-out p-4 sm:p-6 md:p-8 ${
                          activeCard === 0 ? "opacity-100 scale-100 blur-0" : "opacity-0 scale-95 blur-sm"
                        }`}
                      >
                        <div className="flex flex-col gap-4 h-full">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center flex-shrink-0">
                              <Bot className="w-4 h-4 text-white" strokeWidth={1.5} />
                            </div>
                            <div className="flex-1 space-y-2">
                              <div className="bg-gray-50 rounded-2xl rounded-tl-none p-4 border border-gray-100">
                                <p className="text-sm text-gray-700">Your ROAS increased by 18% this week. Campaign "Summer Sale" is your top performer at 4.2x.</p>
                              </div>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3 flex-1">
                            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">Revenue</p>
                              <p className="text-2xl font-semibold text-gray-900">$89.2K</p>
                              <span className="text-xs text-green-600 font-medium">+18.2%</span>
                            </div>
                            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">ROAS</p>
                              <p className="text-2xl font-semibold text-gray-900">3.63x</p>
                              <span className="text-xs text-green-600 font-medium">+5.8%</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Analytics View */}
                      <div
                        className={`absolute inset-0 transition-all duration-500 ease-in-out p-4 sm:p-6 md:p-8 ${
                          activeCard === 1 ? "opacity-100 scale-100 blur-0" : "opacity-0 scale-95 blur-sm"
                        }`}
                      >
                        <div className="flex flex-col gap-4 h-full">
                          <div className="grid grid-cols-3 gap-3">
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">Spend</p>
                              <p className="text-xl font-semibold text-gray-900">$24.5K</p>
                            </div>
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">Revenue</p>
                              <p className="text-xl font-semibold text-gray-900">$89.2K</p>
                            </div>
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">ROAS</p>
                              <p className="text-xl font-semibold text-gray-900">3.63x</p>
                            </div>
                          </div>
                          <div className="flex-1 bg-gray-50 rounded-xl p-4 border border-gray-100">
                            <div className="h-full flex items-end justify-between gap-2">
                              {[40, 55, 48, 70, 82, 100, 65, 75, 88, 72].map((height, i) => (
                                <div key={i} className="flex-1 bg-gradient-to-t from-cyan-500 to-cyan-300 rounded-t" style={{ height: `${height}%`, opacity: 0.6 + (height / 250) }}></div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Finance View */}
                      <div
                        className={`absolute inset-0 transition-all duration-500 ease-in-out p-4 sm:p-6 md:p-8 ${
                          activeCard === 2 ? "opacity-100 scale-100 blur-0" : "opacity-0 scale-95 blur-sm"
                        }`}
                      >
                        <div className="flex flex-col gap-4 h-full">
                          <div className="grid grid-cols-2 gap-3">
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">Ad Spend</p>
                              <p className="text-xl font-semibold text-gray-900">$24.5K</p>
                              <span className="text-xs text-green-600 font-medium">Under budget</span>
                            </div>
                            <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                              <p className="text-xs text-gray-500 mb-1">Net Profit</p>
                              <p className="text-xl font-semibold text-gray-900">$64.7K</p>
                              <span className="text-xs text-green-600 font-medium">+22%</span>
                            </div>
                          </div>
                          <div className="flex-1 bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-3">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-gray-600">Revenue</span>
                              <span className="text-gray-900 font-medium">$89,200</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-gray-600">Ad Spend</span>
                              <span className="text-red-600 font-medium">-$24,500</span>
                            </div>
                            <div className="flex items-center justify-between text-sm border-t pt-2">
                              <span className="text-gray-900 font-semibold">Net Profit</span>
                              <span className="text-green-600 font-semibold">$64,700</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature Cards */}
            <div className="self-stretch border-t border-[#E0DEDB] border-b border-[#E0DEDB] flex justify-center items-start">
              <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
                <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
                  {Array.from({ length: 50 }).map((_, i) => (
                    <div
                      key={i}
                      className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                    ></div>
                  ))}
                </div>
              </div>

              <div className="flex-1 px-0 sm:px-2 md:px-0 flex flex-col md:flex-row justify-center items-stretch gap-0">
                {features.map((feature, index) => (
                  <FeatureCard
                    key={index}
                    title={feature.title}
                    description={feature.description}
                    isActive={activeCard === index}
                    progress={activeCard === index ? progress : 0}
                    onClick={() => handleCardClick(index)}
                  />
                ))}
              </div>

              <div className="w-4 sm:w-6 md:w-8 lg:w-12 self-stretch relative overflow-hidden">
                <div className="w-[120px] sm:w-[140px] md:w-[162px] left-[-40px] sm:left-[-50px] md:left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
                  {Array.from({ length: 50 }).map((_, i) => (
                    <div
                      key={i}
                      className="self-stretch h-3 sm:h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                    ></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuroraBackground>
  );
}
