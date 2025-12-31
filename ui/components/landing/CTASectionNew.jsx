"use client";

/**
 * CTASectionNew - Final call-to-action section
 * Clean design with gradient text and prominent buttons
 * White theme with blue/cyan accents
 * Related: page.jsx, FooterSectionNew.jsx
 */

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export default function CTASectionNew() {
  return (
    <section className="relative w-full py-24 lg:py-32 bg-white border-t border-gray-100">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex flex-col items-center text-center max-w-4xl mx-auto"
        >
          <h2 className="text-4xl md:text-6xl lg:text-7xl font-normal text-gray-900 tracking-tight mb-8">
            Ready to unify
            <span className="block bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-cyan-500 italic">your ad analytics?</span>
          </h2>

          <p className="text-lg md:text-xl text-gray-500 font-light mb-12 max-w-2xl">
            Join growth teams at high-performance companies who trust metricx for their ad analytics and optimization.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
            {/* Primary button */}
            <a
              href="/register"
              className="group relative inline-flex h-14 items-center justify-center overflow-hidden rounded-full bg-gray-900 px-8 font-semibold text-white transition-all hover:bg-gray-800 hover:scale-105 hover:shadow-xl hover:shadow-gray-900/20"
            >
              <span className="mr-2">Start for free</span>
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </a>

            {/* Secondary button */}
            <a
              href="/sign-in"
              className="inline-flex h-14 items-center justify-center rounded-full border border-gray-200 bg-white px-8 font-semibold text-gray-700 transition-all hover:bg-gray-50 hover:border-gray-300"
            >
              Sign in
            </a>
          </div>

          {/* Trust badges */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-gray-400"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-emerald-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>14-day free trial</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-emerald-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>No credit card required</span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-emerald-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Cancel anytime</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
