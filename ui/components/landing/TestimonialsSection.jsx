"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function TestimonialsSection() {
  const [activeTestimonial, setActiveTestimonial] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const testimonials = [
    {
      quote:
        "metricx changed how we understand our ad performance. Instead of switching between Meta and Google dashboards, I just ask 'What's working?' and get a real answer.",
      name: "Sarah Chen",
      company: "Growth Lead, TechFlow",
      initials: "SC",
    },
    {
      quote:
        "The AI copilot is like having a marketing analyst on call 24/7. Our team saves hours every week not having to manually pull reports.",
      name: "Marcus Rodriguez",
      company: "VP Marketing, ScaleUp",
      initials: "MR",
    },
    {
      quote:
        "Finally, a tool that shows me exactly where my ad dollars are going. The P&L view helped us find $15K in wasted spend in our first month.",
      name: "Jamie Marshall",
      company: "Founder, Commerce Labs",
      initials: "JM",
    },
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setIsTransitioning(true);
      setTimeout(() => {
        setActiveTestimonial((prev) => (prev + 1) % testimonials.length);
        setTimeout(() => {
          setIsTransitioning(false);
        }, 100);
      }, 300);
    }, 8000);

    return () => clearInterval(interval);
  }, [testimonials.length]);

  const handleNavigationClick = (direction) => {
    setIsTransitioning(true);
    setTimeout(() => {
      if (direction === "prev") {
        setActiveTestimonial((prev) => (prev - 1 + testimonials.length) % testimonials.length);
      } else {
        setActiveTestimonial((prev) => (prev + 1) % testimonials.length);
      }
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
    }, 300);
  };

  return (
    <div className="w-full bg-gray-50 py-16 md:py-24">
      <div className="w-full max-w-[1060px] mx-auto px-4 sm:px-6 lg:px-0">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex flex-col md:flex-row items-center gap-8 md:gap-12"
        >
          {/* Avatar */}
          <div
            className="w-32 h-32 md:w-40 md:h-40 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0 transition-all duration-500"
            style={{
              opacity: isTransitioning ? 0.7 : 1,
              transform: isTransitioning ? "scale(0.95)" : "scale(1)",
            }}
          >
            <span className="text-4xl md:text-5xl font-bold text-white">
              {testimonials[activeTestimonial].initials}
            </span>
          </div>

          {/* Quote */}
          <div className="flex-1">
            <blockquote
              className="text-xl md:text-2xl font-medium text-black leading-relaxed transition-all duration-500"
              style={{
                opacity: isTransitioning ? 0 : 1,
                filter: isTransitioning ? "blur(4px)" : "blur(0px)",
              }}
            >
              "{testimonials[activeTestimonial].quote}"
            </blockquote>
            <div
              className="mt-6 transition-all duration-500"
              style={{
                opacity: isTransitioning ? 0 : 1,
              }}
            >
              <div className="font-bold text-black">{testimonials[activeTestimonial].name}</div>
              <div className="text-gray-500">{testimonials[activeTestimonial].company}</div>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => handleNavigationClick("prev")}
                className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center hover:bg-white hover:border-gray-300 transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-gray-600" />
              </button>
              <button
                onClick={() => handleNavigationClick("next")}
                className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center hover:bg-white hover:border-gray-300 transition-colors"
              >
                <ChevronRight className="w-5 h-5 text-gray-600" />
              </button>
              <div className="flex gap-1.5 ml-2">
                {testimonials.map((_, index) => (
                  <div
                    key={index}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      index === activeTestimonial ? "bg-blue-500" : "bg-gray-300"
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
