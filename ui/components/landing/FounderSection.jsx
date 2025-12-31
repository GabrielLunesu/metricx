"use client";

/**
 * FounderSection - White background with scroll-activated text highlighting
 * Each line highlights when it reaches the center of the viewport
 * Premium scroll-driven animation effect
 * Related: page.jsx, CTASectionNew.jsx
 */

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

// Line that highlights when in center of viewport
function HighlightLine({ children }) {
  const ref = useRef(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    // "start center" = when top of element hits center of viewport
    // "end center" = when bottom of element hits center of viewport
    offset: ["start 0.7", "start 0.5", "start 0.3"]
  });

  const color = useTransform(
    scrollYProgress,
    [0, 0.5, 1],
    ["rgb(209, 213, 219)", "rgb(17, 24, 39)", "rgb(209, 213, 219)"]
  );

  return (
    <motion.p
      ref={ref}
      style={{ color }}
      className="text-2xl md:text-3xl lg:text-4xl font-light leading-relaxed"
    >
      {children}
    </motion.p>
  );
}

export default function FounderSection() {
  const containerRef = useRef(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  return (
    <section
      ref={containerRef}
      className="relative w-full bg-white border-t border-gray-100 py-[50vh]"
    >
      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 md:px-12 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-gray-500 text-xs font-medium tracking-widest mb-20"
        >
          A MESSAGE FROM THE FOUNDER
        </motion.div>

        {/* Scroll-animated text - each line tracks its own position */}
        <div className="space-y-16">
          <HighlightLine>
            After spending 6-figures on ads, one thing became painfully clear:
          </HighlightLine>

          <HighlightLine>
            seeing all your ad data in one place shouldn't be this hard.
          </HighlightLine>

          <HighlightLine>
            Every morning started the same way.
          </HighlightLine>

          <HighlightLine>
            Open Meta Ads Manager. Check ROAS. Screenshot the numbers.
          </HighlightLine>

          <HighlightLine>
            Switch to Google Ads. Compare campaigns. Another screenshot.
          </HighlightLine>

          <HighlightLine>
            Open Shopify. Cross-reference revenue. Try to make sense of it all.
          </HighlightLine>

          <HighlightLine>
            Hours lost. Every single week. Just trying to answer one simple question:
          </HighlightLine>

          <HighlightLine>
            "Where should I put my next dollar?"
          </HighlightLine>

          <HighlightLine>
            The tools that existed were either too complex or too expensive.
          </HighlightLine>

          <HighlightLine>
            So we built metricx — the ad analytics platform we wished existed.
          </HighlightLine>

          <HighlightLine>
            Simple. Powerful. Finally, clarity.
          </HighlightLine>
        </div>

        {/* Signature */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-20%" }}
          transition={{ duration: 0.8 }}
          className="mt-24 pt-8 border-t border-gray-200 inline-block"
        >
          <p className="text-gray-900 font-medium text-lg mb-1">— Gabriel</p>
          <p className="text-gray-400 text-sm">Founder, metricx</p>
        </motion.div>
      </div>
    </section>
  );
}
