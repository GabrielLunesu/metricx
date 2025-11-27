"use client";

import { motion } from "framer-motion";

function Badge({ text }) {
  return (
    <div className="px-4 py-1.5 max-w-[120px] mx-auto bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.06)] rounded-full flex items-center gap-2">
      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500" />
      <span className="text-black text-xs font-medium">{text}</span>
    </div>
  );
}

export default function SocialProofSection() {
  const logos = [
    { name: "Meta", icon: "M" },
    { name: "Google", icon: "G" },
    { name: "Shopify", icon: "S" },
    { name: "Stripe", icon: "S" },
    { name: "HubSpot", icon: "H" },
    { name: "Klaviyo", icon: "K" },
    { name: "TikTok", icon: "T" },
    { name: "Slack", icon: "S" },
  ];

  return (
    <div className="w-full bg-white py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        {/* Header */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <Badge text="Trusted By" />
          <h2 className="mt-6 text-3xl md:text-4xl font-bold text-black tracking-tight">
            Powering marketing teams everywhere
          </h2>
          <p className="mt-4 text-gray-500 text-lg max-w-lg mx-auto">
            From startups to enterprises, metricx helps teams make smarter marketing decisions.
          </p>
        </motion.div>

        {/* Logo Grid */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-0 border border-gray-100 rounded-xl overflow-hidden"
        >
          {logos.map((logo, index) => (
            <div
              key={index}
              className={`
                h-24 sm:h-28 flex justify-center items-center gap-3
                ${index % 4 !== 3 ? "border-r border-gray-100" : ""}
                ${index < 4 ? "border-b border-gray-100" : ""}
                hover:bg-gray-50 transition-colors
              `}
            >
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                <span className="text-base font-bold text-gray-600">{logo.icon}</span>
              </div>
              <span className="text-black text-lg font-medium">{logo.name}</span>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
