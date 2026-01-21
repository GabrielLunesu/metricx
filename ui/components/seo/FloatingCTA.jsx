/**
 * Floating CTA Component
 *
 * WHAT: Sticky conversion banner that follows users as they scroll
 * WHY: Maximize conversions from SEO traffic by always showing CTA
 *
 * Related files:
 * - app/(marketing)/layout.jsx - Added to marketing layout
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, X, Sparkles } from "lucide-react";

/**
 * Floating CTA banner that appears after scroll.
 */
export function FloatingCTA() {
  const [isVisible, setIsVisible] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // Check if already dismissed this session
    if (sessionStorage.getItem("floatingCTADismissed")) {
      setIsDismissed(true);
      return;
    }

    const handleScroll = () => {
      // Show after scrolling 300px
      if (window.scrollY > 300) {
        setIsVisible(true);
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    sessionStorage.setItem("floatingCTADismissed", "true");
  };

  if (isDismissed || !isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 animate-slide-up">
      <div className="max-w-4xl mx-auto">
        <div className="relative bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 rounded-2xl shadow-2xl shadow-gray-900/30 border border-gray-700/50 overflow-hidden">
          {/* Gradient accent line */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-cyan-500 to-blue-500" />

          <div className="px-6 py-4 flex items-center justify-between gap-4">
            {/* Content */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold">
                  Ready to unify your ad analytics?
                </p>
                <p className="text-gray-400 text-sm">
                  Join 500+ e-commerce brands using metricx
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="hidden sm:inline-flex items-center gap-2 px-5 py-2.5 bg-white text-gray-900 rounded-full font-semibold text-sm hover:bg-gray-100 transition-all hover:scale-105"
              >
                See Product
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-full font-semibold text-sm hover:from-blue-600 hover:to-cyan-600 transition-all hover:scale-105 shadow-lg shadow-blue-500/25"
              >
                Start Free
                <ArrowRight className="w-4 h-4" />
              </Link>
              <button
                onClick={handleDismiss}
                className="p-2 text-gray-400 hover:text-white transition-colors"
                aria-label="Dismiss"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from {
            transform: translateY(100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-slide-up {
          animation: slide-up 0.4s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

/**
 * Sticky sidebar CTA for desktop.
 */
export function SidebarCTA() {
  return (
    <div className="hidden xl:block fixed right-6 top-1/2 -translate-y-1/2 z-40">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-6 w-64">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <h3 className="font-bold text-gray-900 mb-2">
          Try metricx Free
        </h3>
        <p className="text-gray-500 text-sm mb-4">
          Unify Meta, Google & TikTok ads in one dashboard.
        </p>
        <Link
          href="/sign-up"
          className="block w-full text-center px-4 py-2.5 bg-gray-900 text-white rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors"
        >
          Start Free Trial
        </Link>
        <Link
          href="/"
          className="block w-full text-center px-4 py-2 text-gray-500 hover:text-gray-900 text-sm mt-2 transition-colors"
        >
          See how it works
        </Link>
      </div>
    </div>
  );
}

export default FloatingCTA;
