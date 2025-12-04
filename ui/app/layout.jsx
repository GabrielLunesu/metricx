/**
 * Root Layout - Global app shell with HTML metadata and SEO configuration.
 *
 * This is the top-level layout for the entire application. It provides:
 * - Comprehensive SEO metadata for Google indexing and social sharing
 * - Favicon and icon configuration
 * - Global CSS imports
 * - Background visual effects
 *
 * Note: Dashboard-specific chrome (sidebar, header) lives in (dashboard)/layout.jsx
 *
 * @see https://nextjs.org/docs/app/api-reference/functions/generate-metadata
 */
import "./globals.css";
import AppProviders from "./providers";

/**
 * Site-wide metadata configuration for SEO and social sharing.
 * This metadata helps with:
 * - Google Search ranking and indexing
 * - Social media link previews (Open Graph, Twitter Cards)
 * - Browser tab display (title, favicon)
 *
 * @see https://nextjs.org/docs/app/api-reference/functions/generate-metadata
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

  // Verification tags (add your actual verification codes when available)
  // verification: {
  //   google: "your-google-verification-code",
  //   yandex: "your-yandex-verification-code",
  //   bing: "your-bing-verification-code",
  // },

  // App-specific metadata
  applicationName: "metricx",
  category: "Business",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-white antialiased overflow-x-hidden">
        {/* Cyan Aura Background Effects */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-cyan-400 rounded-full blur-[120px] opacity-15 aura-glow"></div>
          <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-cyan-300 rounded-full blur-[100px] opacity-10 float-orb" style={{ animationDelay: '1s' }}></div>
          <div className="absolute bottom-1/4 right-1/3 w-[350px] h-[350px] bg-cyan-500 rounded-full blur-[90px] opacity-10 float-orb" style={{ animationDelay: '2.5s' }}></div>
        </div>

        <AppProviders>
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
