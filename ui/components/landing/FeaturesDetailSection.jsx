"use client";

import { motion } from "framer-motion";
import { Bot, BarChart3, DollarSign, Target, Layers, Bell, ArrowRight } from "lucide-react";

export default function FeaturesDetailSection() {
  const features = [
    {
      icon: Bot,
      title: "AI Marketing Copilot",
      description: "Ask questions in plain English and get instant, actionable answers. \"Why did my CPA spike?\" \"Which audience is converting best?\" Your AI analyst works 24/7.",
      benefits: ["Natural language queries", "Instant insights", "Proactive alerts"],
      image: "/features/copilot.png",
      gradient: "from-blue-500 to-cyan-500"
    },
    {
      icon: Layers,
      title: "Unified Dashboard",
      description: "See Google Ads and Meta Ads in one view with consistent metrics. No more switching tabs or reconciling different attribution models.",
      benefits: ["Cross-platform comparison", "Standardized metrics", "Real-time sync"],
      image: "/features/dashboard.png",
      gradient: "from-cyan-500 to-blue-500"
    },
    {
      icon: DollarSign,
      title: "P&L & Finance View",
      description: "Finally know your true profitability. See revenue, ad spend, and profit margins in real-time. Track budget vs actuals automatically.",
      benefits: ["True ROAS calculation", "Budget tracking", "Profit margins"],
      image: "/features/finance.png",
      gradient: "from-blue-600 to-cyan-400"
    },
    {
      icon: Target,
      title: "Smart Recommendations",
      description: "AI analyzes your campaigns and tells you exactly what to do. Scale winning ads, pause losers, and optimize budgets automatically.",
      benefits: ["Budget allocation", "Campaign optimization", "Audience insights"],
      image: "/features/recommendations.png",
      gradient: "from-cyan-400 to-blue-600"
    }
  ];

  return (
    <section id="features" className="w-full py-20 md:py-28 bg-gray-50">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-blue-500 uppercase tracking-wider">Features</span>
          <h2 className="mt-4 text-3xl md:text-4xl lg:text-5xl font-bold text-black tracking-tight">
            Everything you need to scale profitably
          </h2>
          <p className="mt-4 text-lg text-gray-500 max-w-2xl mx-auto">
            Built by marketers who were tired of spreadsheets and disconnected tools.
          </p>
        </motion.div>

        <div className="space-y-12">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ y: 40, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className={`flex flex-col ${index % 2 === 1 ? 'md:flex-row-reverse' : 'md:flex-row'} gap-8 md:gap-12 items-center`}
            >
              {/* Content */}
              <div className="flex-1">
                <div className={`inline-flex w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.gradient} items-center justify-center mb-6 shadow-lg`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-2xl md:text-3xl font-bold text-black mb-4">{feature.title}</h3>
                <p className="text-gray-500 text-lg leading-relaxed mb-6">{feature.description}</p>
                <ul className="space-y-3">
                  {feature.benefits.map((benefit, i) => (
                    <li key={i} className="flex items-center gap-3 text-gray-600">
                      <div className={`w-5 h-5 rounded-full bg-gradient-to-br ${feature.gradient} flex items-center justify-center`}>
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      {benefit}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Visual */}
              <div className="flex-1 w-full">
                <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-lg">
                  <div className="aspect-video bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl flex items-center justify-center">
                    <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center opacity-20`}>
                      <feature.icon className="w-10 h-10 text-white" />
                    </div>
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
