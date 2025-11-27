"use client";

import HeroSection from "@/components/landing/HeroSection";
import SocialProofSection from "@/components/landing/SocialProofSection";
import ProblemSection from "@/components/landing/ProblemSection";
import HowItWorksSection from "@/components/landing/HowItWorksSection";
import FeaturesDetailSection from "@/components/landing/FeaturesDetailSection";
import BentoGridSection from "@/components/landing/BentoGridSection";
import ROISection from "@/components/landing/ROISection";
import FounderStorySection from "@/components/landing/FounderStorySection";
import TestimonialsSection from "@/components/landing/TestimonialsSection";
import PricingSection from "@/components/landing/PricingSection";
import FAQSection from "@/components/landing/FAQSection";
import CTASection from "@/components/landing/CTASection";
import FooterSection from "@/components/landing/FooterSection";

export default function HomePage() {
  return (
    <div className="w-full min-h-screen relative overflow-x-hidden flex flex-col justify-start items-center">
      {/* Hero with shader gradient background */}
      <HeroSection />

      {/* White background sections - covers the shader gradient */}
      <div className="w-full relative z-10 bg-white">
        <SocialProofSection />
        <ProblemSection />
        <HowItWorksSection />
        <FeaturesDetailSection />
        <BentoGridSection />
        <ROISection />
        <FounderStorySection />
        <TestimonialsSection />
        <PricingSection />
        <FAQSection />
        <CTASection />
        <FooterSection />
      </div>
    </div>
  );
}
