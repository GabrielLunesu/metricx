"use client";

import { motion } from "framer-motion";
import { TrendingUp, Clock, Target, DollarSign } from "lucide-react";

export default function ROISection() {
  const stats = [
    {
      icon: TrendingUp,
      value: "32%",
      label: "Average ROAS improvement",
      description: "Our users see significant returns within the first 30 days"
    },
    {
      icon: Clock,
      value: "10+",
      label: "Hours saved per week",
      description: "No more manual reporting or switching between platforms"
    },
    {
      icon: Target,
      value: "2.4x",
      label: "Faster optimization",
      description: "Spot trends and make decisions in minutes, not days"
    },
    {
      icon: DollarSign,
      value: "$4,200",
      label: "Avg. monthly savings",
      description: "By cutting wasted spend and scaling winners"
    }
  ];

  return (
    <section className="w-full py-20 md:py-28 bg-black text-white">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-cyan-400 uppercase tracking-wider">Results</span>
          <h2 className="mt-4 text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight">
            How metricx makes you money
          </h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            Real results from real marketers. No fluff, just profits.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 hover:border-white/20 transition-colors"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4">
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="text-4xl font-bold text-white mb-1">{stat.value}</div>
              <div className="text-sm font-medium text-cyan-400 mb-2">{stat.label}</div>
              <p className="text-sm text-gray-400">{stat.description}</p>
            </motion.div>
          ))}
        </div>

        {/* Calculator Preview */}
        <motion.div
          initial={{ y: 40, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-3xl p-8 md:p-12 border border-white/10"
        >
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-2xl md:text-3xl font-bold mb-4">Calculate your ROI</h3>
              <p className="text-gray-400 mb-6">
                Most teams spending $10K+/month on ads see ROI within the first week.
                Here's a typical breakdown:
              </p>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-green-400 text-sm">+</span>
                  </div>
                  <div>
                    <span className="text-white font-medium">Cut wasted spend:</span>
                    <span className="text-gray-400"> $1,500-3,000/mo by pausing underperformers faster</span>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-green-400 text-sm">+</span>
                  </div>
                  <div>
                    <span className="text-white font-medium">Scale winners:</span>
                    <span className="text-gray-400"> 20-40% more revenue by doubling down on what works</span>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-green-400 text-sm">+</span>
                  </div>
                  <div>
                    <span className="text-white font-medium">Save time:</span>
                    <span className="text-gray-400"> 10+ hours/week = $500+ in labor costs</span>
                  </div>
                </li>
              </ul>
            </div>
            <div className="bg-white/5 rounded-2xl p-6 border border-white/10">
              <div className="text-center">
                <p className="text-gray-400 text-sm mb-2">Average monthly ROI</p>
                <div className="text-5xl md:text-6xl font-bold text-gradient-blue bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  847%
                </div>
                <p className="text-gray-500 text-sm mt-2">Based on $99/mo plan</p>
                <div className="mt-6 pt-6 border-t border-white/10">
                  <p className="text-gray-400 text-sm">That's like getting</p>
                  <p className="text-2xl font-bold text-white mt-1">$8.47 back for every $1 spent</p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
