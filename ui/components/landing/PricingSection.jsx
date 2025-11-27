"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";

function Badge({ text }) {
  return (
    <div className="px-4 py-1.5 max-w-[120px] mx-auto bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.06)] rounded-full flex items-center gap-2">
      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500" />
      <span className="text-black text-xs font-medium">{text}</span>
    </div>
  );
}

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
      description: "Perfect for trying out metricx with a single account.",
      priceKey: "starter",
      cta: "Get started free",
      ctaHref: "/dashboard",
      featured: false,
      features: [
        "1 ad account connection",
        "AI Copilot (50 queries/month)",
        "Basic analytics dashboard",
        "7-day data history",
        "Community support",
      ],
    },
    {
      name: "Professional",
      description: "For growing teams with multiple ad accounts.",
      priceKey: "professional",
      cta: "Start free trial",
      ctaHref: "/dashboard",
      featured: true,
      features: [
        "Unlimited ad account connections",
        "Unlimited AI Copilot queries",
        "Full analytics dashboard",
        "90-day data history",
        "Finance & P&L reports",
        "Team collaboration",
        "Priority support",
        "API access",
      ],
    },
    {
      name: "Enterprise",
      description: "For agencies and large marketing teams.",
      priceKey: "enterprise",
      cta: "Contact sales",
      ctaHref: "mailto:hello@metricx.ai",
      featured: false,
      features: [
        "Everything in Professional",
        "Multiple workspaces",
        "Dedicated account manager",
        "Custom data retention",
        "White-label options",
        "SSO integration",
        "Custom contracts",
        "24/7 phone support",
      ],
    },
  ];

  return (
    <div id="pricing" className="w-full bg-white py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        {/* Header */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <Badge text="Pricing" />
          <h2 className="mt-6 text-3xl md:text-4xl font-bold text-black tracking-tight">
            Simple pricing for every team
          </h2>
          <p className="mt-4 text-gray-500 text-lg">Start free, scale as you grow. No hidden fees.</p>

          {/* Billing Toggle */}
          <div className="flex justify-center mt-8">
            <div className="p-1 bg-gray-100 rounded-full flex items-center gap-1">
              <button
                onClick={() => setBillingPeriod("annually")}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${billingPeriod === "annually"
                    ? "bg-white text-black shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                  }`}
              >
                Annually
                <span className="ml-1.5 text-xs text-green-500">Save 20%</span>
              </button>
              <button
                onClick={() => setBillingPeriod("monthly")}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${billingPeriod === "monthly"
                    ? "bg-white text-black shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                  }`}
              >
                Monthly
              </button>
            </div>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ y: 20, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className={`rounded-xl p-6 flex flex-col ${plan.featured
                  ? "bg-black text-white border-2 border-black"
                  : "bg-white border border-gray-200"
                }`}
            >
              <div className="mb-6">
                <h3 className={`text-lg font-bold ${plan.featured ? "text-white" : "text-black"}`}>
                  {plan.name}
                </h3>
                <p className={`text-sm mt-1 ${plan.featured ? "text-gray-400" : "text-gray-500"}`}>
                  {plan.description}
                </p>
              </div>

              <div className="mb-6">
                <div className="flex items-baseline gap-1">
                  <span className={`text-4xl font-bold ${plan.featured ? "text-white" : "text-black"}`}>
                    ${pricing[plan.priceKey][billingPeriod]}
                  </span>
                  <span className={plan.featured ? "text-gray-400" : "text-gray-500"}>
                    /{billingPeriod === "monthly" ? "mo" : "mo"}
                  </span>
                </div>
                {plan.priceKey !== "starter" && (
                  <p className={`text-sm mt-1 ${plan.featured ? "text-gray-400" : "text-gray-500"}`}>
                    {billingPeriod === "annually" ? "billed annually" : "billed monthly"}
                  </p>
                )}
                {plan.priceKey === "starter" && (
                  <p className={`text-sm mt-1 ${plan.featured ? "text-gray-400" : "text-gray-500"}`}>
                    Free forever
                  </p>
                )}
              </div>

              <a
                href={plan.ctaHref}
                className={`w-full py-3 rounded-full text-center text-sm font-medium transition-colors ${plan.featured
                    ? "bg-white text-black hover:bg-gray-100"
                    : "bg-black text-white hover:bg-gray-800"
                  }`}
              >
                {plan.cta}
              </a>

              <div className="mt-8 flex-1">
                <div className="space-y-3">
                  {plan.features.map((feature, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <Check
                        className={`w-4 h-4 mt-0.5 flex-shrink-0 ${plan.featured ? "text-cyan-400" : "text-blue-500"
                          }`}
                        strokeWidth={2}
                      />
                      <span className={`text-sm ${plan.featured ? "text-gray-300" : "text-gray-600"}`}>
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
    </div>
  );
}
