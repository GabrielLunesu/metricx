/**
 * Marketing Pages Layout
 * =======================
 *
 * WHAT: Premium shared layout for all public content pages (blog, guides, etc.)
 * WHY:  Matches the homepage design language — floating dock nav, glassmorphism,
 *       MeshGradient shader hero bg, dark footer. Provides consistent navigation
 *       and footer separate from the dashboard layout.
 *
 * Related files:
 *  - app/page.jsx           — Homepage (design reference)
 *  - app/globals.css         — Shared animations + design tokens
 *  - app/(marketing)/blog/   — Blog pages
 */

import Link from "next/link";
import Image from "next/image";

/* ─── Navigation links ─── */
const navLinks = [
  { name: "Blog", href: "/blog" },
  { name: "Features", href: "/#features" },
  { name: "Pricing", href: "/#pricing" },
  { name: "How it works", href: "/#solution-section" },
];

/* ─── Footer links ─── */
const footerLinks = {
  product: [
    { name: "Features", href: "/#features" },
    { name: "How it works", href: "/#solution-section" },
    { name: "Pricing", href: "/#pricing" },
    { name: "Why metricx", href: "/#comparison-section" },
  ],
  resources: [
    { name: "Blog", href: "/blog" },
  ],
  company: [
    { name: "Privacy", href: "/privacy" },
    { name: "Terms", href: "/terms" },
    { name: "Contact", href: "mailto:info@metricx.ai" },
  ],
};

export default function MarketingLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col antialiased text-gray-900 font-geist">
      {/* ── Floating Dock Navigation ── */}
      <header className="sticky top-0 z-50 w-full pt-3 px-4 sm:px-6 lg:px-8 bg-transparent">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl sm:rounded-2xl bg-white/80 backdrop-blur-xl border border-gray-200/60 shadow-[0_8px_32px_rgba(0,0,0,0.08),0_0_0_1px_rgba(255,255,255,0.8)_inset]">
            {/* Brand */}
            <Link href="/" className="inline-flex items-center gap-2 shrink-0">
              <Image
                src="/logo.png"
                alt="metricx"
                width={160}
                height={48}
                className="h-8 sm:h-9 w-auto"
                priority
              />
            </Link>

            {/* Center Nav */}
            <nav className="hidden md:flex items-center gap-1 text-sm text-gray-600">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="px-3 py-1.5 rounded-lg hover:bg-black/5 hover:text-gray-900 transition-all font-geist"
                >
                  {link.name}
                </Link>
              ))}
            </nav>

            {/* Right actions */}
            <div className="flex items-center gap-2 sm:gap-3">
              <Link
                href="/sign-in"
                className="hidden sm:inline-flex text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors font-geist px-3 py-1.5 rounded-lg hover:bg-black/5"
              >
                Log in
              </Link>
              <Link
                href="/sign-up"
                className="inline-flex items-center rounded-full bg-gray-900 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-gray-900/20 hover:bg-black transition-colors font-geist"
              >
                Start Free Trial
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="flex-1">{children}</main>

      {/* ── Premium Footer (matches homepage) ── */}
      <footer className="text-white bg-gray-900 border-black/5 border-t relative overflow-hidden mt-auto">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute left-0 top-0 h-[400px] w-[400px] rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute right-0 bottom-0 h-[400px] w-[400px] rounded-full bg-blue-500/10 blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16">
            {/* Brand & Description */}
            <div className="lg:col-span-5">
              <Link href="/" className="inline-flex items-center gap-2">
                <Image
                  src="/logo-white.webp"
                  alt="metricx"
                  width={140}
                  height={44}
                  className="h-9 w-auto brightness-0 invert"
                />
              </Link>
              <p className="mt-4 text-sm text-gray-400 font-geist max-w-sm">
                Ad analytics for e-commerce merchants. Understand which ads make
                you money, cut waste, and grow profitably.
              </p>
              <a
                href="mailto:info@metricx.ai"
                className="mt-3 inline-block text-sm text-gray-300 hover:text-white transition font-geist"
              >
                info@metricx.ai
              </a>
              <div className="mt-6 flex items-center gap-3">
                <a
                  href="https://discord.gg/seRTSw2vAa"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Join our Discord community"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition backdrop-blur-md border border-white/10"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Links Grid */}
            <div className="lg:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-8 sm:gap-12 lg:justify-end">
              <div>
                <h3 className="text-sm font-semibold text-white font-geist tracking-tight">
                  Product
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.product.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-gray-400 hover:text-white transition font-geist"
                      >
                        {link.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white font-geist tracking-tight">
                  Resources
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.resources.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-gray-400 hover:text-white transition font-geist"
                      >
                        {link.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white font-geist tracking-tight">
                  Company
                </h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.company.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-gray-400 hover:text-white transition font-geist"
                      >
                        {link.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="mt-10 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-400 font-geist">
              © {new Date().getFullYear()} metricx. All rights reserved.
            </p>
            <div className="flex items-center gap-6 text-xs text-gray-400">
              <Link
                href="/privacy"
                className="hover:text-white transition font-geist"
              >
                Privacy Policy
              </Link>
              <Link
                href="/terms"
                className="hover:text-white transition font-geist"
              >
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
