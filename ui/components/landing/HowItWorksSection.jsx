"use client";

import { motion } from "framer-motion";
import { Link2, MessageSquare, TrendingUp, Zap } from "lucide-react";

export default function HowItWorksSection() {
  const steps = [
    {
      number: "01",
      icon: Link2,
      title: "Connect in 2 Minutes",
      description: "Link your Google Ads and Meta accounts with one click. We securely sync all your campaign data in real-time.",
      color: "from-blue-500 to-blue-600"
    },
    {
      number: "02",
      icon: MessageSquare,
      title: "Ask Anything",
      description: "\"What's my best performing campaign?\" \"Why did ROAS drop last week?\" Ask in plain English, get instant answers.",
      color: "from-cyan-500 to-cyan-600"
    },
    {
      number: "03",
      icon: TrendingUp,
      title: "See Unified Insights",
      description: "One dashboard, all your data. Compare Google vs Meta performance side-by-side with consistent metrics.",
      color: "from-blue-500 to-cyan-500"
    },
    {
      number: "04",
      icon: Zap,
      title: "Scale What Works",
      description: "AI-powered recommendations tell you exactly where to increase spend and what to cut. No more guessing.",
      color: "from-cyan-500 to-blue-500"
    }
  ];

  return (
    <section id="how-it-works" className="w-full py-20 md:py-28 bg-white">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-blue-500 uppercase tracking-wider">How It Works</span>
          <h2 className="mt-4 text-3xl md:text-4xl lg:text-5xl font-bold text-black tracking-tight">
            From chaos to clarity in minutes
          </h2>
          <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
            No complex setup. No learning curve. Just connect and start asking.
          </p>
        </motion.div>

        <div className="relative">
          {/* Connection line */}
          <div className="hidden md:block absolute top-24 left-[calc(12.5%+24px)] right-[calc(12.5%+24px)] h-0.5 bg-gradient-to-r from-blue-200 via-cyan-200 to-blue-200" />

          <div className="grid md:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ y: 20, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative text-center"
              >
                {/* Number badge */}
                <div className="relative z-10 mx-auto w-12 h-12 rounded-full bg-white border-2 border-gray-100 flex items-center justify-center mb-6">
                  <span className="text-sm font-bold text-gray-400">{step.number}</span>
                </div>

                {/* Icon */}
                <div className={`mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center mb-4 shadow-lg`}>
                  <step.icon className="w-8 h-8 text-white" />
                </div>

                <h3 className="text-lg font-semibold text-black mb-2">{step.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
