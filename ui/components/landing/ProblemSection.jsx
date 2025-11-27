"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Clock, DollarSign, Brain } from "lucide-react";

export default function ProblemSection() {
  const problems = [
    {
      icon: AlertTriangle,
      title: "Data Chaos",
      description: "Jumping between Meta Ads Manager and Google Ads. Different metrics, different dashboards, no single source of truth.",
      stat: "4+ hours/week",
      statLabel: "wasted on manual reporting"
    },
    {
      icon: Clock,
      title: "Slow Decisions",
      description: "By the time you pull reports, analyze data, and spot trends, you've already wasted budget on underperforming campaigns.",
      stat: "23%",
      statLabel: "of ad spend typically wasted"
    },
    {
      icon: DollarSign,
      title: "Hidden Costs",
      description: "Attribution gaps, platform discrepancies, and missing P&L visibility mean you never know your true ROAS.",
      stat: "$2,400",
      statLabel: "avg. monthly hidden waste"
    },
    {
      icon: Brain,
      title: "Analysis Paralysis",
      description: "Too much data, not enough insights. You know something's wrong but can't pinpoint where to optimize.",
      stat: "67%",
      statLabel: "of marketers feel overwhelmed"
    }
  ];

  return (
    <section id="problem" className="w-full py-20 md:py-28 bg-gray-50">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-red-500 uppercase tracking-wider">The Problem</span>
          <h2 className="mt-4 text-3xl md:text-4xl lg:text-5xl font-bold text-black tracking-tight">
            Running ads shouldn't feel like this
          </h2>
          <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
            You're spending thousands on ads but flying blind. Sound familiar?
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {problems.map((problem, index) => (
            <motion.div
              key={index}
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="bg-white rounded-2xl p-6 md:p-8 border border-gray-100 hover:border-gray-200 transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
                  <problem.icon className="w-6 h-6 text-red-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-black mb-2">{problem.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed mb-4">{problem.description}</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-red-500">{problem.stat}</span>
                    <span className="text-sm text-gray-400">{problem.statLabel}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
