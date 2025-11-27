"use client";

import { useState } from "react";
import { Check } from "lucide-react";

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

export default function PricingSection() {
  const [billingPeriod, setBillingPeriod] = useState("annually");

  const pricing = {
    starter: {
      monthly: 0,
      annually: 0,
    },
    professional: {
      monthly: 49,
      annually: 39,
    },
    enterprise: {
      monthly: 199,
      annually: 159,
    },
  };

  return (
    <div id="pricing" className="w-full bg-white flex flex-col justify-center items-center gap-2">
      <div className="w-full max-w-[1060px] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Header Section */}
        <div className="self-stretch px-6 md:px-24 py-12 md:py-16 border-b border-[rgba(55,50,47,0.12)] flex justify-center items-center gap-6">
          <div className="w-full max-w-[586px] px-6 py-5 overflow-hidden rounded-lg flex flex-col justify-start items-center gap-4">
            <Badge
              icon={
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M6 1V11M8.5 3H4.75C4.28587 3 3.84075 3.18437 3.51256 3.51256C3.18437 3.84075 3 4.28587 3 4.75C3 5.21413 3.18437 5.65925 3.51256 5.98744C3.84075 6.31563 4.28587 6.5 4.75 6.5H7.25C7.71413 6.5 8.15925 6.68437 8.48744 7.01256C8.81563 7.34075 9 7.78587 9 8.25C9 8.71413 8.81563 9.15925 8.48744 9.48744C8.15925 9.81563 7.71413 10 7.25 10H3.5"
                    stroke="#37322F"
                    strokeWidth="1"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              }
              text="Plans & Pricing"
            />

            <div className="self-stretch text-center flex justify-center flex-col text-[#49423D] text-2xl md:text-3xl lg:text-4xl font-semibold leading-tight md:leading-[50px] font-sans tracking-tight">
              Simple pricing for every team
            </div>

            <div className="self-stretch text-center text-[#605A57] text-sm md:text-base font-normal leading-7 font-sans">
              Start free, scale as you grow. No hidden fees.
            </div>
          </div>
        </div>

        {/* Billing Toggle */}
        <div className="self-stretch px-6 md:px-16 py-9 relative flex justify-center items-center gap-4">
          <div className="w-full max-w-[1060px] h-0 absolute left-1/2 transform -translate-x-1/2 top-[63px] border-t border-[rgba(55,50,47,0.12)] z-0"></div>

          <div className="p-3 relative bg-[rgba(55,50,47,0.03)] border border-[rgba(55,50,47,0.02)] backdrop-blur-sm flex justify-center items-center rounded-lg z-20">
            <div className="p-[2px] bg-[rgba(55,50,47,0.10)] shadow-[0px_1px_0px_white] rounded-[99px] border-[0.5px] border-[rgba(55,50,47,0.08)] flex justify-center items-center gap-[2px] relative">
              <div
                className={`absolute top-[2px] w-[calc(50%-1px)] h-[calc(100%-4px)] bg-white shadow-[0px_2px_4px_rgba(0,0,0,0.08)] rounded-[99px] transition-all duration-300 ease-in-out ${
                  billingPeriod === "annually" ? "left-[2px]" : "right-[2px]"
                }`}
              />

              <button
                onClick={() => setBillingPeriod("annually")}
                className="px-4 py-1 rounded-[99px] flex justify-center items-center gap-2 transition-colors duration-300 relative z-10 flex-1"
              >
                <div
                  className={`text-[13px] font-medium leading-5 font-sans transition-colors duration-300 ${
                    billingPeriod === "annually" ? "text-[#37322F]" : "text-[#6B7280]"
                  }`}
                >
                  Annually
                </div>
              </button>

              <button
                onClick={() => setBillingPeriod("monthly")}
                className="px-4 py-1 rounded-[99px] flex justify-center items-center gap-2 transition-colors duration-300 relative z-10 flex-1"
              >
                <div
                  className={`text-[13px] font-medium leading-5 font-sans transition-colors duration-300 ${
                    billingPeriod === "monthly" ? "text-[#37322F]" : "text-[#6B7280]"
                  }`}
                >
                  Monthly
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="self-stretch border-b border-t border-[rgba(55,50,47,0.12)] flex justify-center items-center">
          <div className="flex justify-center items-start w-full">
            {/* Left Pattern */}
            <div className="w-12 self-stretch relative overflow-hidden hidden md:block">
              <div className="w-[162px] left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
                {Array.from({ length: 200 }).map((_, i) => (
                  <div
                    key={i}
                    className="self-stretch h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                  ></div>
                ))}
              </div>
            </div>

            {/* Pricing Cards Container */}
            <div className="flex-1 flex flex-col md:flex-row justify-center items-stretch gap-6 py-12 md:py-8 px-4 md:px-0">
              {/* Starter Plan */}
              <div className="flex-1 max-w-full md:max-w-none self-stretch px-6 py-6 border border-[#E0DEDB] rounded-lg overflow-hidden flex flex-col justify-start items-start gap-8 bg-white">
                <div className="self-stretch flex flex-col justify-start items-center gap-6">
                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="text-[rgba(55,50,47,0.90)] text-lg font-medium leading-7 font-sans">Starter</div>
                    <div className="w-full max-w-[242px] text-[rgba(41,37,35,0.70)] text-sm font-normal leading-5 font-sans">
                      Perfect for trying out metricx with a single account.
                    </div>
                  </div>

                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="relative h-[60px] flex items-center text-[#37322F] text-5xl font-medium leading-[60px]">
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "annually" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.starter.annually}
                      </span>
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "monthly" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.starter.monthly}
                      </span>
                    </div>
                    <div className="text-[#847971] text-sm font-medium font-sans">
                      Free forever
                    </div>
                  </div>

                  <a
                    href="/dashboard"
                    className="self-stretch px-4 py-[10px] relative bg-[#37322F] shadow-[0px_2px_4px_rgba(55,50,47,0.12)] overflow-hidden rounded-[99px] flex justify-center items-center hover:bg-[#2A2520] transition-colors"
                  >
                    <div className="flex justify-center flex-col text-[#FBFAF9] text-[13px] font-medium leading-5 font-sans">
                      Get started free
                    </div>
                  </a>
                </div>

                <div className="self-stretch flex flex-col justify-start items-start gap-2">
                  {[
                    "1 ad account connection",
                    "AI Copilot (50 queries/month)",
                    "Basic analytics dashboard",
                    "7-day data history",
                    "Community support",
                  ].map((feature, index) => (
                    <div key={index} className="self-stretch flex justify-start items-center gap-[13px]">
                      <Check className="w-4 h-4 text-gray-400" strokeWidth={1.5} />
                      <div className="flex-1 text-[rgba(55,50,47,0.80)] text-[12.5px] font-normal leading-5 font-sans">
                        {feature}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Professional Plan */}
              <div className="flex-1 max-w-full md:max-w-none self-stretch px-6 py-6 bg-[#37322F] border border-[rgba(55,50,47,0.12)] rounded-lg overflow-hidden flex flex-col justify-start items-start gap-8">
                <div className="self-stretch flex flex-col justify-start items-center gap-6">
                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="text-[#FBFAF9] text-lg font-medium leading-7 font-sans">Professional</div>
                    <div className="w-full max-w-[242px] text-[#B2AEA9] text-sm font-normal leading-5 font-sans">
                      For growing teams with multiple ad accounts.
                    </div>
                  </div>

                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="relative h-[60px] flex items-center text-[#F0EFEE] text-5xl font-medium leading-[60px]">
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "annually" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.professional.annually}
                      </span>
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "monthly" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.professional.monthly}
                      </span>
                    </div>
                    <div className="text-[#D2C6BF] text-sm font-medium font-sans">
                      per {billingPeriod === "monthly" ? "month" : "month, billed annually"}
                    </div>
                  </div>

                  <a
                    href="/dashboard"
                    className="self-stretch px-4 py-[10px] relative bg-[#FBFAF9] shadow-[0px_2px_4px_rgba(55,50,47,0.12)] overflow-hidden rounded-[99px] flex justify-center items-center hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex justify-center flex-col text-[#37322F] text-[13px] font-medium leading-5 font-sans">
                      Start free trial
                    </div>
                  </a>
                </div>

                <div className="self-stretch flex flex-col justify-start items-start gap-2">
                  {[
                    "Unlimited ad account connections",
                    "Unlimited AI Copilot queries",
                    "Full analytics dashboard",
                    "90-day data history",
                    "Finance & P&L reports",
                    "Team collaboration",
                    "Priority support",
                    "API access",
                  ].map((feature, index) => (
                    <div key={index} className="self-stretch flex justify-start items-center gap-[13px]">
                      <Check className="w-4 h-4 text-cyan-400" strokeWidth={1.5} />
                      <div className="flex-1 text-[#F0EFEE] text-[12.5px] font-normal leading-5 font-sans">{feature}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Enterprise Plan */}
              <div className="flex-1 max-w-full md:max-w-none self-stretch px-6 py-6 bg-white border border-[#E0DEDB] rounded-lg overflow-hidden flex flex-col justify-start items-start gap-8">
                <div className="self-stretch flex flex-col justify-start items-center gap-6">
                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="text-[rgba(55,50,47,0.90)] text-lg font-medium leading-7 font-sans">Enterprise</div>
                    <div className="w-full max-w-[242px] text-[rgba(41,37,35,0.70)] text-sm font-normal leading-5 font-sans">
                      For agencies and large marketing teams.
                    </div>
                  </div>

                  <div className="self-stretch flex flex-col justify-start items-start gap-2">
                    <div className="relative h-[60px] flex items-center text-[#37322F] text-5xl font-medium leading-[60px]">
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "annually" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.enterprise.annually}
                      </span>
                      <span
                        className={`transition-all duration-500 ${
                          billingPeriod === "monthly" ? "opacity-100" : "opacity-0 absolute"
                        }`}
                      >
                        ${pricing.enterprise.monthly}
                      </span>
                    </div>
                    <div className="text-[#847971] text-sm font-medium font-sans">
                      per {billingPeriod === "monthly" ? "month" : "month, billed annually"}
                    </div>
                  </div>

                  <a
                    href="mailto:hello@metricx.ai"
                    className="self-stretch px-4 py-[10px] relative bg-[#37322F] shadow-[0px_2px_4px_rgba(55,50,47,0.12)] overflow-hidden rounded-[99px] flex justify-center items-center hover:bg-[#2A2520] transition-colors"
                  >
                    <div className="flex justify-center flex-col text-[#FBFAF9] text-[13px] font-medium leading-5 font-sans">
                      Contact sales
                    </div>
                  </a>
                </div>

                <div className="self-stretch flex flex-col justify-start items-start gap-2">
                  {[
                    "Everything in Professional",
                    "Multiple workspaces",
                    "Dedicated account manager",
                    "Custom data retention",
                    "White-label options",
                    "SSO integration",
                    "Custom contracts",
                    "24/7 phone support",
                  ].map((feature, index) => (
                    <div key={index} className="self-stretch flex justify-start items-center gap-[13px]">
                      <Check className="w-4 h-4 text-gray-400" strokeWidth={1.5} />
                      <div className="flex-1 text-[rgba(55,50,47,0.80)] text-[12.5px] font-normal leading-5 font-sans">
                        {feature}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Pattern */}
            <div className="w-12 self-stretch relative overflow-hidden hidden md:block">
              <div className="w-[162px] left-[-58px] top-[-120px] absolute flex flex-col justify-start items-start">
                {Array.from({ length: 200 }).map((_, i) => (
                  <div
                    key={i}
                    className="self-stretch h-4 rotate-[-45deg] origin-top-left outline outline-[0.5px] outline-[rgba(3,7,18,0.08)] outline-offset-[-0.25px]"
                  ></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
