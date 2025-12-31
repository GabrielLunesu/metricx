"use client";

/**
 * HomePage - Modern landing page for metricx ad analytics platform
 * White theme with flowing data visualizations and premium design
 * Structure: Hero -> Features -> Copilot -> Data Ingestion -> Founder -> Pricing -> CTA -> Footer
 * Optimized for mobile performance with reduced blur/animations on small screens
 * Related: components/landing/*
 */

import HeroSectionNew from "@/components/landing/HeroSectionNew";
import FeaturesSectionNew from "@/components/landing/FeaturesSectionNew";
import VideoSection from "@/components/landing/VideoSection";
import CopilotShowcaseSection from "@/components/landing/CopilotShowcaseSection";
import DataIngestionSection from "@/components/landing/DataIngestionSection";
import FounderSection from "@/components/landing/FounderSection";
import PricingSectionNew from "@/components/landing/PricingSectionNew";
import CTASectionNew from "@/components/landing/CTASectionNew";
import FooterSectionNew from "@/components/landing/FooterSectionNew";

export default function HomePage() {
  return (
    <main className="w-full min-h-screen relative overflow-x-hidden bg-white">
      {/* Subtle grid background */}
      <div className="fixed inset-0 w-full h-full pointer-events-none z-0">
        <div className="absolute inset-0 flex justify-between px-6 md:px-12 lg:px-24 opacity-30">
          <div className="w-px h-full bg-gray-200" />
          <div className="w-px h-full bg-gray-200 hidden sm:block" />
          <div className="w-px h-full bg-gray-200 hidden md:block" />
          <div className="w-px h-full bg-gray-200 hidden lg:block" />
          <div className="w-px h-full bg-gray-200 hidden xl:block" />
          <div className="w-px h-full bg-gray-200" />
        </div>
      </div>

      {/* Hero with data flow visualization */}
      <HeroSectionNew />

      {/* Features with semantic clustering & granular control */}
      <FeaturesSectionNew />

      {/* Video showcase */}
      <VideoSection />

      {/* AI Copilot showcase */}
      <CopilotShowcaseSection />

      {/* Data ingestion / platform integrations */}
      <DataIngestionSection />

      {/* Founder message */}
      <FounderSection />

      {/* Pricing */}
      <PricingSectionNew />

      {/* Final CTA */}
      <CTASectionNew />

      {/* Footer */}
      <FooterSectionNew />
    </main>
  );
}
