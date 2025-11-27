"use client";

import { useState, useEffect } from "react";

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
    }, 10000);

    return () => clearInterval(interval);
  }, [testimonials.length]);

  const handleNavigationClick = (index) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setActiveTestimonial(index);
      setTimeout(() => {
        setIsTransitioning(false);
      }, 100);
    }, 300);
  };

  return (
    <div className="w-full bg-white border-b border-[rgba(55,50,47,0.12)] flex flex-col justify-center items-center">
      <div className="w-full max-w-[1060px] flex flex-col justify-center items-center relative">
        {/* Left vertical line */}
        <div className="w-[1px] h-full absolute left-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Right vertical line */}
        <div className="w-[1px] h-full absolute right-0 top-0 bg-[rgba(55,50,47,0.12)] hidden lg:block"></div>

        {/* Testimonial Content */}
        <div className="self-stretch px-2 overflow-hidden flex justify-start items-center">
          <div className="flex-1 py-12 md:py-16 flex flex-col md:flex-row justify-center items-end gap-6">
            <div className="self-stretch px-3 md:px-12 justify-center items-start gap-4 flex flex-col md:flex-row">
              {/* Avatar */}
              <div
                className="w-32 h-32 md:w-40 md:h-40 rounded-lg bg-gradient-to-br from-cyan-100 to-cyan-200 flex items-center justify-center transition-all duration-700 ease-in-out mx-auto md:mx-0"
                style={{
                  opacity: isTransitioning ? 0.6 : 1,
                  transform: isTransitioning ? "scale(0.95)" : "scale(1)",
                }}
              >
                <span className="text-3xl md:text-4xl font-bold text-cyan-600">
                  {testimonials[activeTestimonial].initials}
                </span>
              </div>

              {/* Quote */}
              <div className="flex-1 px-4 md:px-6 py-6 flex flex-col justify-start items-start gap-6">
                <div
                  className="self-stretch justify-start flex flex-col text-[#49423D] text-xl md:text-2xl lg:text-[28px] font-medium leading-8 md:leading-10 font-sans min-h-[160px] md:min-h-[180px] transition-all duration-700 ease-in-out tracking-tight"
                  style={{
                    filter: isTransitioning ? "blur(4px)" : "blur(0px)",
                  }}
                >
                  "{testimonials[activeTestimonial].quote}"
                </div>
                <div
                  className="self-stretch flex flex-col justify-start items-start gap-1 transition-all duration-700 ease-in-out"
                  style={{
                    filter: isTransitioning ? "blur(4px)" : "blur(0px)",
                  }}
                >
                  <div className="self-stretch justify-center flex flex-col text-[rgba(73,66,61,0.90)] text-base md:text-lg font-medium leading-[26px] font-sans">
                    {testimonials[activeTestimonial].name}
                  </div>
                  <div className="self-stretch justify-center flex flex-col text-[rgba(73,66,61,0.70)] text-sm md:text-base font-medium leading-[26px] font-sans">
                    {testimonials[activeTestimonial].company}
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation Arrows */}
            <div className="pr-6 justify-center md:justify-start items-center md:items-start gap-[14px] flex">
              <button
                onClick={() => handleNavigationClick((activeTestimonial - 1 + testimonials.length) % testimonials.length)}
                className="w-9 h-9 shadow-[0px_1px_2px_rgba(0,0,0,0.08)] overflow-hidden rounded-full border border-[rgba(0,0,0,0.15)] justify-center items-center gap-2 flex hover:bg-gray-50 transition-colors"
              >
                <div className="w-6 h-6 relative overflow-hidden">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M15 18L9 12L15 6"
                      stroke="#46413E"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </button>
              <button
                onClick={() => handleNavigationClick((activeTestimonial + 1) % testimonials.length)}
                className="w-9 h-9 shadow-[0px_1px_2px_rgba(0,0,0,0.08)] overflow-hidden rounded-full border border-[rgba(0,0,0,0.15)] justify-center items-center gap-2 flex hover:bg-gray-50 transition-colors"
              >
                <div className="w-6 h-6 relative overflow-hidden">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M9 18L15 12L9 6"
                      stroke="#46413E"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
