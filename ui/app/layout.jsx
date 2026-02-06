/**
 * Root Layout - Global app shell with Clerk authentication and SEO configuration.
 *
 * WHAT: Top-level layout wrapping entire application
 * WHY: Provides authentication context, SEO metadata, and global styles
 *
 * Key Features:
 * - ClerkProvider: Authentication context for all pages
 * - SEO metadata for Google indexing and social sharing
 * - Background visual effects (Cyan Aura)
 *
 * Note: Dashboard-specific chrome (sidebar, header) lives in (dashboard)/layout.jsx
 *
 * REFERENCES:
 *   - https://clerk.com/docs/references/nextjs/clerk-provider
 *   - https://nextjs.org/docs/app/api-reference/functions/generate-metadata
 */

import { ClerkProvider } from '@clerk/nextjs';
import "./globals.css";
import AppProviders from "./providers";

/**
 * Site-wide metadata configuration for SEO and social sharing.
 *
 * WHY: Helps with Google Search ranking, social media previews, and browser display.
 */
export const metadata = {
  // Basic metadata
  title: {
    default: "metricx - AI-Powered Ad Analytics Platform",
    template: "%s | metricx",
  },
  description:
    "Get the most out of your advertising spend with metricx. Aggregate data from Meta Ads, Google Ads, and TikTok with AI-powered insights, real-time ROAS tracking, and unified analytics dashboard.",
  keywords: [
    "ad analytics",
    "advertising analytics",
    "ROAS tracking",
    "Meta Ads analytics",
    "Google Ads analytics",
    "TikTok ads",
    "marketing attribution",
    "e-commerce analytics",
    "ad spend optimization",
    "AI marketing assistant",
    "marketing dashboard",
    "campaign performance",
    "Triple Whale alternative",
    "advertising ROI",
    "multi-platform analytics",
  ],
  authors: [{ name: "metricx" }],
  creator: "metricx",
  publisher: "metricx",

  // Favicon and icons - using the SVG favicon
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },

  // Base URL for absolute URLs
  metadataBase: new URL("https://www.metricx.ai"),

  // Canonical URL and alternates
  alternates: {
    canonical: "/",
  },

  // Open Graph metadata for social sharing (Facebook, LinkedIn, etc.)
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://www.metricx.ai",
    siteName: "metricx",
    title: "metricx - AI-Powered Ad Analytics Platform",
    description:
      "Aggregate data from Meta Ads, Google Ads, and TikTok with AI-powered insights. Track ROAS, optimize campaigns, and understand your ad spend.",
    images: [
      {
        url: "https://www.metricx.ai/logo.png",
        width: 1200,
        height: 630,
        alt: "metricx - AI-Powered Ad Analytics",
      },
    ],
  },

  // Twitter Card metadata
  twitter: {
    card: "summary_large_image",
    title: "metricx - AI-Powered Ad Analytics Platform",
    description:
      "Aggregate data from Meta Ads, Google Ads, and TikTok with AI-powered insights. Track ROAS and optimize your ad spend.",
    images: ["https://www.metricx.ai/logo.png"],
    creator: "@metricx_ai",
  },

  // Search engine directives
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },

  // App-specific metadata
  applicationName: "metricx",
  category: "Business",
};

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <head>
          {/* Google Fonts - Inter for body text */}
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
          <link
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
            rel="stylesheet"
          />
        </head>
        <body className="antialiased overflow-x-hidden">

          <AppProviders>
            {children}
          </AppProviders>
        </body>
      </html>
    </ClerkProvider>
  );
}
