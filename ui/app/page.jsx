"use client";

import HeroSection from "@/components/landing/HeroSection";
import SocialProofSection from "@/components/landing/SocialProofSection";
import BentoGridSection from "@/components/landing/BentoGridSection";
import TestimonialsSection from "@/components/landing/TestimonialsSection";
import PricingSection from "@/components/landing/PricingSection";
import FAQSection from "@/components/landing/FAQSection";
import CTASection from "@/components/landing/CTASection";
import FooterSection from "@/components/landing/FooterSection";

export default function HomePage() {
  return (
    <div className="w-full min-h-screen relative bg-white overflow-x-hidden flex flex-col justify-start items-center">
      {/* Hero with Aurora background */}
      <HeroSection />

      {/* White background sections */}
      <SocialProofSection />
      <BentoGridSection />
      <TestimonialsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <FooterSection />
    </div>
  );
}
