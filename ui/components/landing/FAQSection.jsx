"use client";

import { useState } from "react";
import { motion } from "framer-motion";
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
    setOpenItems((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  return (
    <div id="faq" className="w-full bg-white py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <div className="grid md:grid-cols-2 gap-12">
          {/* Left Column - Header */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-black tracking-tight">
              Frequently Asked Questions
            </h2>
            <p className="mt-4 text-gray-500 text-lg">
              Everything you need to know about metricx. Can't find what you're looking for?{" "}
              <a href="mailto:hello@metricx.ai" className="text-blue-500 hover:underline">
                Contact us
              </a>
              .
            </p>
          </motion.div>

          {/* Right Column - FAQ Items */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="divide-y divide-gray-100">
              {faqData.map((item, index) => {
                const isOpen = openItems.includes(index);

                return (
                  <div key={index} className="py-4">
                    <button
                      onClick={() => toggleItem(index)}
                      className="w-full flex justify-between items-center gap-4 text-left group"
                    >
                      <span className="text-black font-medium group-hover:text-gray-700 transition-colors">
                        {item.question}
                      </span>
                      <ChevronDown
                        className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-300 ${
                          isOpen ? "rotate-180" : ""
                        }`}
                      />
                    </button>
                    <div
                      className={`overflow-hidden transition-all duration-300 ${
                        isOpen ? "max-h-96 opacity-100 mt-3" : "max-h-0 opacity-0"
                      }`}
                    >
                      <p className="text-gray-500 text-sm leading-relaxed">{item.answer}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
