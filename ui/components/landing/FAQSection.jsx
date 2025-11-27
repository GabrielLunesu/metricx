"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqData = [
  {
    question: "What is metricx and who is it for?",
    answer:
      "metricx is an AI-powered marketing analytics platform that unifies your Meta and Google Ads data. It's built for growth marketers, agencies, and founders who want to understand their ad performance without switching between dashboards or writing complex queries.",
  },
  {
    question: "How does the AI Copilot work?",
    answer:
      "Simply ask questions in plain English like 'What's my ROAS this week?' or 'Which campaign has the highest CPC?'. Our AI translates your question into a structured query, safely executes it against your data, and returns a natural language answer with the exact metrics.",
  },
  {
    question: "Which ad platforms do you support?",
    answer:
      "We currently support Meta Ads (Facebook & Instagram) and Google Ads with one-click OAuth integration. TikTok Ads integration is coming soon. Your data syncs automatically and stays up to date.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Absolutely. We use workspace-scoped multi-tenancy, meaning your data is completely isolated. We never execute raw SQL — all queries go through a validated DSL layer. OAuth tokens are encrypted with AES-256-GCM, and passwords are hashed with Bcrypt.",
  },
  {
    question: "Can I try metricx for free?",
    answer:
      "Yes! Our Starter plan is free forever and includes 1 ad account connection, 50 AI queries per month, and 7 days of data history. No credit card required to get started.",
  },
  {
    question: "What metrics can I track?",
    answer:
      "We support 24+ metrics including ROAS, CPC, CPM, CPA, CTR, CVR, and more. You can track spend, revenue, clicks, impressions, conversions, leads, and profit across all connected platforms in one unified view.",
  },
];

export default function FAQSection() {
  const [openItems, setOpenItems] = useState([]);

  const toggleItem = (index) => {
    setOpenItems((prev) => (prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]));
  };

  return (
    <div id="faq" className="w-full bg-white flex justify-center items-start">
      <div className="w-full max-w-[1060px] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        <div className="flex-1 px-4 md:px-12 py-12 md:py-16 flex flex-col lg:flex-row justify-start items-start gap-6 lg:gap-12 w-full">
          {/* Left Column - Header */}
          <div className="w-full lg:flex-1 flex flex-col justify-center items-start gap-4 lg:py-5">
            <div className="w-full flex flex-col justify-center text-[#49423D] font-semibold leading-tight md:leading-[44px] font-sans text-2xl md:text-3xl lg:text-4xl tracking-tight">
              Frequently Asked Questions
            </div>
            <div className="w-full text-[#605A57] text-sm md:text-base font-normal leading-6 md:leading-7 font-sans">
              Everything you need to know about metricx.
              <br className="hidden md:block" />
              Can't find what you're looking for? Contact us.
            </div>
          </div>

          {/* Right Column - FAQ Items */}
          <div className="w-full lg:flex-1 flex flex-col justify-center items-center">
            <div className="w-full flex flex-col">
              {faqData.map((item, index) => {
                const isOpen = openItems.includes(index);

                return (
                  <div key={index} className="w-full border-b border-[rgba(73,66,61,0.16)] overflow-hidden">
                    <button
                      onClick={() => toggleItem(index)}
                      className="w-full px-4 md:px-5 py-[16px] md:py-[18px] flex justify-between items-center gap-4 md:gap-5 text-left hover:bg-[rgba(73,66,61,0.02)] transition-colors duration-200"
                      aria-expanded={isOpen}
                    >
                      <div className="flex-1 text-[#49423D] text-sm md:text-base font-medium leading-6 font-sans">
                        {item.question}
                      </div>
                      <div className="flex justify-center items-center flex-shrink-0">
                        <ChevronDown
                          className={`w-5 h-5 md:w-6 md:h-6 text-[rgba(73,66,61,0.60)] transition-transform duration-300 ease-in-out ${
                            isOpen ? "rotate-180" : "rotate-0"
                          }`}
                          strokeWidth={1.5}
                        />
                      </div>
                    </button>

                    <div
                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                        isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                      }`}
                    >
                      <div className="px-4 md:px-5 pb-[16px] md:pb-[18px] text-[#605A57] text-sm font-normal leading-6 font-sans">
                        {item.answer}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
