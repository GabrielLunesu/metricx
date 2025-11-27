"use client";

import { motion } from "framer-motion";
import { Quote } from "lucide-react";

export default function FounderStorySection() {
  return (
    <section className="w-full py-20 md:py-28 bg-white">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <div className="grid md:grid-cols-2 gap-12 md:gap-16 items-center">
          {/* Image */}
          <motion.div
            initial={{ x: -40, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative"
          >
            <div className="aspect-[4/5] bg-gradient-to-br from-gray-100 to-gray-200 rounded-3xl overflow-hidden">
              {/* Placeholder for founder image */}
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <div className="w-32 h-32 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4">
                    <span className="text-5xl font-bold text-white">G</span>
                  </div>
                  <p className="text-gray-400 text-sm">Founder Photo</p>
                </div>
              </div>
            </div>
            {/* Decorative elements */}
            <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl -z-10" />
            <div className="absolute -top-6 -left-6 w-16 h-16 bg-gray-100 rounded-xl -z-10" />
          </motion.div>

          {/* Content */}
          <motion.div
            initial={{ x: 40, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <span className="text-sm font-medium text-blue-500 uppercase tracking-wider">Our Story</span>
            <h2 className="mt-4 text-3xl md:text-4xl font-bold text-black tracking-tight">
              Built from frustration,<br />designed for results
            </h2>

            <div className="mt-8 relative">
              <Quote className="absolute -top-2 -left-2 w-8 h-8 text-blue-100" />
              <blockquote className="pl-6 text-lg text-gray-600 leading-relaxed">
                <p className="mb-4">
                  I spent years managing 6-figure ad budgets across Google and Meta. Every week, I'd waste hours
                  copying data into spreadsheets, trying to figure out what was actually working.
                </p>
                <p className="mb-4">
                  The platforms don't talk to each other. The metrics don't match. And by the time you spot a
                  problem, you've already burned through thousands in wasted spend.
                </p>
                <p className="mb-4">
                  I built metricx because I needed it. A single place to see everything, ask questions in plain
                  English, and know exactly where my next dollar should go.
                </p>
                <p className="font-medium text-black">
                  Now I'm sharing it with every marketer who's tired of flying blind.
                </p>
              </blockquote>
            </div>

            <div className="mt-8 flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-xl font-bold text-white">G</span>
              </div>
              <div>
                <p className="font-semibold text-black">Gabriel</p>
                <p className="text-sm text-gray-500">Founder, metricx</p>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-6">
              <div>
                <p className="text-3xl font-bold text-black">$2M+</p>
                <p className="text-sm text-gray-500">Ad spend managed</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-black">50+</p>
                <p className="text-sm text-gray-500">Campaigns optimized</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-black">8 years</p>
                <p className="text-sm text-gray-500">In digital marketing</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
