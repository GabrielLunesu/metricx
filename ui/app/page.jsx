"use client";

/**
 * HomePage - Landing page with glassmorphic design and WOW effect
 * Compact structure: Hero -> Features -> Pricing -> CTA -> Footer
 * Related: components/landing/*
 */

import HeroSection from "@/components/landing/HeroSection";
import FeaturesSection from "@/components/landing/FeaturesSection";
import PricingSection from "@/components/landing/PricingSection";
import CTASection from "@/components/landing/CTASection";
import FooterSection from "@/components/landing/FooterSection";

export default function HomePage() {
  return (
    <main className="w-full min-h-screen relative overflow-x-hidden">
      {/* Hero with glassmorphic design and animated background */}
      <HeroSection />

      {/* Features bento grid */}
      <FeaturesSection />

      {/* Pricing cards */}
      <PricingSection />

      {/* Final CTA */}
      <CTASection />

      {/* Minimal footer */}
      <FooterSection />
    </main>
  );
}
