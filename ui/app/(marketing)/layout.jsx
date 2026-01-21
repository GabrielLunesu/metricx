/**
 * Marketing Pages Layout
 *
 * WHAT: Shared layout for all SEO/marketing pages
 * WHY: Provides consistent navigation, footer, and structure for public content pages
 *
 * Related files:
 * - components/landing/FooterSectionNew.jsx - Footer component
 * - lib/seo/schemas.js - Organization schema
 * - components/seo/JsonLd.jsx - Structured data
 */

import Link from "next/link";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateOrganizationSchema } from "@/lib/seo/schemas";
import { FloatingCTA } from "@/components/seo/FloatingCTA";

/**
 * Navigation links for marketing pages.
 */
const navLinks = [
  { name: "Glossary", href: "/glossary" },
  { name: "Blog", href: "/blog" },
  { name: "Tools", href: "/tools" },
  { name: "Pricing", href: "/#pricing" },
];

/**
 * Footer links organized by section.
 */
const footerLinks = {
  product: [
    { name: "Features", href: "/#features" },
    { name: "AI Copilot", href: "/#copilot" },
    { name: "Integrations", href: "/#integrations" },
    { name: "Pricing", href: "/#pricing" },
  ],
  resources: [
    { name: "Glossary", href: "/glossary" },
    { name: "Blog", href: "/blog" },
    { name: "Tools", href: "/tools" },
    { name: "Comparisons", href: "/vs" },
  ],
  platforms: [
    { name: "Meta Ads", href: "/platforms/meta-ads" },
    { name: "Google Ads", href: "/platforms/google-ads" },
    { name: "TikTok Ads", href: "/platforms/tiktok-ads" },
  ],
  company: [
    { name: "About", href: "/about" },
    { name: "Privacy", href: "/privacy" },
    { name: "Terms", href: "/terms" },
    { name: "Contact", href: "mailto:info@metricx.ai" },
  ],
};

export default function MarketingLayout({ children }) {
  return (
    <>
      {/* Organization Schema */}
      <JsonLd schema={generateOrganizationSchema()} />

      {/* Floating CTA for conversions */}
      <FloatingCTA />

      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center">
              <img src="/logo.png" alt="metricx" className="h-10" />
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
                >
                  {link.name}
                </Link>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="flex items-center gap-4">
              <Link
                href="/sign-in"
                className="hidden sm:inline-flex text-sm font-medium text-gray-500 hover:text-gray-900"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-b from-blue-500 to-blue-600 rounded-full hover:shadow-lg hover:shadow-blue-500/20 transition-all"
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8">
            {/* Brand */}
            <div className="col-span-2 lg:col-span-1">
              <Link href="/" className="inline-block mb-4">
                <img src="/logo.png" alt="metricx" className="h-10" />
              </Link>
              <p className="text-sm text-gray-500 mb-4">
                AI-powered ad analytics for e-commerce. Track Meta, Google & TikTok in one dashboard.
              </p>
              <p className="text-sm text-gray-400">
                <a href="mailto:info@metricx.ai" className="hover:text-gray-900">
                  info@metricx.ai
                </a>
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Product</h4>
              <ul className="space-y-2">
                {footerLinks.product.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-gray-400 hover:text-gray-900"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Resources</h4>
              <ul className="space-y-2">
                {footerLinks.resources.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-gray-400 hover:text-gray-900"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Platforms */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Platforms</h4>
              <ul className="space-y-2">
                {footerLinks.platforms.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-gray-400 hover:text-gray-900"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Company</h4>
              <ul className="space-y-2">
                {footerLinks.company.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-gray-400 hover:text-gray-900"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Bottom */}
          <div className="mt-12 pt-8 border-t border-gray-100 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-400">
              &copy; {new Date().getFullYear()} metricx. All rights reserved.
            </p>
            <div className="flex items-center gap-6">
              <Link href="/privacy" className="text-sm text-gray-400 hover:text-gray-900">
                Privacy Policy
              </Link>
              <Link href="/terms" className="text-sm text-gray-400 hover:text-gray-900">
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
