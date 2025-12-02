"use client";

/**
 * PricingSection - Compact glassmorphic pricing cards
 * Clean, minimal design with glass effects and smooth animations
 * Related: page.jsx, FeaturesSection.jsx
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Sparkles, ArrowRight } from "lucide-react";

export default function PricingSection() {
  const [billingPeriod, setBillingPeriod] = useState("annually");

  const pricing = {
    starter: { monthly: 0, annually: 0 },
    professional: { monthly: 49, annually: 39 },
    enterprise: { monthly: 199, annually: 159 },
  };

  const plans = [
    {
      name: "Starter",
      description: "Try metricx free",
      priceKey: "starter",
      cta: "Get started free",
      ctaHref: "/dashboard",
      featured: false,
      features: [
        "1 ad account",
        "50 AI queries/month",
        "7-day data history",
        "Basic dashboard",
      ],
    },
    {
      name: "Professional",
      description: "For growing teams",
      priceKey: "professional",
      cta: "Start free trial",
      ctaHref: "/dashboard",
      featured: true,
      features: [
        "Unlimited ad accounts",
        "Unlimited AI queries",
        "90-day data history",
        "P&L reports",
        "Team collaboration",
        "Priority support",
      ],
    },
    {
      name: "Enterprise",
      description: "For agencies",
      priceKey: "enterprise",
      cta: "Contact sales",
      ctaHref: "mailto:hello@metricx.ai",
      featured: false,
      features: [
        "Everything in Pro",
        "Multiple workspaces",
        "Custom retention",
        "SSO & white-label",
        "24/7 support",
      ],
    },
  ];

  return (
    <section id="pricing" className="w-full py-20 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-white via-blue-50/30 to-white" />

      {/* Floating orbs */}
      <div className="absolute top-20 left-10 w-64 h-64 bg-blue-400/10 rounded-full blur-3xl" />
      <div className="absolute bottom-20 right-10 w-80 h-80 bg-cyan-400/10 rounded-full blur-3xl" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full border border-blue-500/20 mb-6"
          >
            <Sparkles className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">Simple Pricing</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            <span className="bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
              Start free, scale as you grow
            </span>
          </h2>
          <p className="text-gray-600 text-lg max-w-md mx-auto mb-8">
            No hidden fees. Cancel anytime.
          </p>

          {/* Billing toggle */}
          <div className="inline-flex items-center p-1 bg-white/70 backdrop-blur-xl rounded-full border border-white/30 shadow-lg">
            <button
              onClick={() => setBillingPeriod("annually")}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
                billingPeriod === "annually"
                  ? "bg-gray-900 text-white shadow-lg"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Annually
              <span className="ml-1.5 text-xs text-green-400">-20%</span>
            </button>
            <button
              onClick={() => setBillingPeriod("monthly")}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
                billingPeriod === "monthly"
                  ? "bg-gray-900 text-white shadow-lg"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Monthly
            </button>
          </div>
        </motion.div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -8, transition: { duration: 0.3 } }}
              className={`relative rounded-2xl overflow-hidden ${
                plan.featured ? "md:-mt-4 md:mb-4" : ""
              }`}
            >
              {/* Glass background */}
              <div
                className={`absolute inset-0 ${
                  plan.featured
                    ? "bg-gradient-to-br from-gray-900 to-gray-800"
                    : "bg-white/70 backdrop-blur-xl border border-white/30"
                } rounded-2xl`}
              />

              {/* Featured badge */}
              {plan.featured && (
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-500" />
              )}

              {/* Content */}
              <div className="relative p-6">
                <div className="mb-6">
                  <h3
                    className={`text-lg font-bold ${
                      plan.featured ? "text-white" : "text-gray-900"
                    }`}
                  >
                    {plan.name}
                  </h3>
                  <p
                    className={`text-sm mt-1 ${
                      plan.featured ? "text-gray-400" : "text-gray-500"
                    }`}
                  >
                    {plan.description}
                  </p>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span
                      className={`text-4xl font-bold ${
                        plan.featured ? "text-white" : "text-gray-900"
                      }`}
                    >
                      ${pricing[plan.priceKey][billingPeriod]}
                    </span>
                    <span
                      className={
                        plan.featured ? "text-gray-400" : "text-gray-500"
                      }
                    >
                      /mo
                    </span>
                  </div>
                  <p
                    className={`text-xs mt-1 ${
                      plan.featured ? "text-gray-400" : "text-gray-500"
                    }`}
                  >
                    {plan.priceKey === "starter"
                      ? "Free forever"
                      : billingPeriod === "annually"
                      ? "Billed annually"
                      : "Billed monthly"}
                  </p>
                </div>

                <a
                  href={plan.ctaHref}
                  className={`group w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all ${
                    plan.featured
                      ? "bg-white text-gray-900 hover:bg-gray-100"
                      : "bg-gray-900 text-white hover:bg-gray-800"
                  }`}
                >
                  {plan.cta}
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </a>

                <div className="mt-6 space-y-3">
                  {plan.features.map((feature, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Check
                        className={`w-4 h-4 flex-shrink-0 ${
                          plan.featured ? "text-cyan-400" : "text-blue-500"
                        }`}
                        strokeWidth={2.5}
                      />
                      <span
                        className={`text-sm ${
                          plan.featured ? "text-gray-300" : "text-gray-600"
                        }`}
                      >
                        {feature}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
