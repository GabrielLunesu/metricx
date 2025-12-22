"use client";

/**
 * PricingSectionNew - Simple 2-option pricing section
 * Matches the new landing page style (white theme, blue/cyan accents)
 * Related: app/page.jsx, CTASectionNew.jsx
 */

import { motion } from "framer-motion";

export default function PricingSectionNew() {
  return (
    <section id="pricing" className="relative w-full py-24 lg:py-32 bg-white border-t border-gray-100">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-5xl mx-auto"
        >
          <div className="text-center mb-14">
            <div className="inline-flex items-center rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm text-gray-600">
              Pricing
            </div>
            <h2 className="mt-6 text-4xl md:text-6xl font-normal text-gray-900 tracking-tight">
              Metricx{" "}
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">
                Pricing
              </span>
            </h2>
            <p className="mt-4 text-lg md:text-xl text-gray-500 font-light">
              Simple plans. Start with a free trial, then pick monthly or annual billing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Monthly</h3>
                  <p className="mt-1 text-sm text-gray-500">14-day free trial</p>
                </div>
              </div>

              <div className="mt-6 flex items-baseline gap-2">
                <span className="text-5xl font-semibold text-gray-900">$79</span>
                <span className="text-gray-500">/mo</span>
              </div>

              <a
                href="/register"
                className="mt-8 inline-flex h-12 w-full items-center justify-center rounded-full bg-gray-900 px-6 font-semibold text-white transition-all hover:bg-gray-800"
              >
                Start free trial
              </a>

              <div className="mt-6 text-sm text-gray-500">
                Cancel anytime. No credit card required to start.
              </div>
            </div>

            <div className="relative rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
              <div className="absolute -top-3 right-6 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 px-3 py-1 text-xs font-semibold text-white">
                Best value
              </div>

              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Annual</h3>
                  <p className="mt-1 text-sm text-gray-500">Save 40% (~$47/mo)</p>
                </div>
              </div>

              <div className="mt-6 flex items-baseline gap-2">
                <span className="text-5xl font-semibold text-gray-900">$569</span>
                <span className="text-gray-500">/yr</span>
              </div>

              <a
                href="/register"
                className="mt-8 inline-flex h-12 w-full items-center justify-center rounded-full border border-gray-200 bg-white px-6 font-semibold text-gray-800 transition-all hover:bg-gray-50 hover:border-gray-300"
              >
                Choose annual
              </a>

              <div className="mt-6 text-sm text-gray-500">
                Equivalent to about $47/mo when billed annually.
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

