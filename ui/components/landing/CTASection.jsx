"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export default function CTASection() {
  return (
    <div className="w-full bg-black py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white tracking-tight">
            Ready to understand your marketing?
          </h2>
          <p className="mt-6 text-gray-400 text-lg max-w-lg mx-auto">
            Join marketers who are making smarter decisions with unified data and AI-powered insights.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="/dashboard"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-black text-base font-medium rounded-full hover:bg-gray-100 transition-colors group"
            >
              Start for free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a
              href="mailto:hello@metricx.ai"
              className="text-gray-400 hover:text-white text-sm font-medium transition-colors"
            >
              Contact sales
            </a>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
