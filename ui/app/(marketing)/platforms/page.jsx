/**
 * Platforms Hub Page
 *
 * WHAT: Hub page for all advertising platform guides
 * WHY: SEO hub for platform-related keyword targeting
 *
 * Related files:
 * - content/platforms/data.json - Platform data
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getPlatforms } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { Layers, ArrowRight, CheckCircle2, XCircle } from "lucide-react";

/**
 * Generate metadata for the platforms hub page.
 */
export async function generateMetadata() {
  const platforms = await getPlatforms();

  return {
    title: "Ad Platform Guides | Meta, Google, TikTok & More | metricx",
    description: `Comprehensive guides for ${platforms.length}+ advertising platforms. Learn setup, targeting, optimization, and best practices for Meta, Google, TikTok, and more.`,
    keywords: [
      "ad platforms",
      "meta ads guide",
      "google ads guide",
      "tiktok ads guide",
      "advertising platforms comparison",
      "ad platform setup",
    ],
    openGraph: {
      title: "Ad Platform Guides | metricx",
      description: "Master every advertising platform with our comprehensive guides.",
      type: "website",
      url: "https://www.metricx.ai/platforms",
    },
    alternates: {
      canonical: "https://www.metricx.ai/platforms",
    },
  };
}

/**
 * Platform icon component (placeholder using first letter).
 */
function PlatformIcon({ name, className = "" }) {
  const colors = {
    meta: "bg-blue-500",
    google: "bg-red-500",
    tiktok: "bg-slate-900",
    pinterest: "bg-red-600",
    snapchat: "bg-yellow-400",
    linkedin: "bg-blue-700",
    microsoft: "bg-blue-600",
    amazon: "bg-orange-500",
  };

  return (
    <div className={`w-12 h-12 rounded-xl ${colors[name.toLowerCase()] || "bg-slate-500"} flex items-center justify-center text-white font-bold text-lg ${className}`}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

/**
 * Platform card component.
 */
function PlatformCard({ platform }) {
  return (
    <Link
      href={`/platforms/${platform.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start gap-4 mb-4">
        <PlatformIcon name={platform.icon || platform.slug} />
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700">
            {platform.name}
          </h3>
          {platform.aliases && platform.aliases.length > 0 && (
            <p className="text-sm text-slate-500">
              {platform.aliases.slice(0, 2).join(", ")}
            </p>
          )}
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-cyan-500" />
      </div>
      <p className="text-slate-600 mb-4 line-clamp-2">{platform.description}</p>
      <div className="flex flex-wrap gap-2">
        {platform.keyMetrics?.slice(0, 4).map((metric) => (
          <span
            key={metric}
            className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-full uppercase"
          >
            {metric}
          </span>
        ))}
      </div>
    </Link>
  );
}

/**
 * Platform comparison table component.
 */
function PlatformComparison({ platforms }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Platform</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-900">Best For</th>
            <th className="text-center py-3 px-4 font-semibold text-slate-900">E-commerce</th>
            <th className="text-center py-3 px-4 font-semibold text-slate-900">B2B</th>
          </tr>
        </thead>
        <tbody>
          {platforms.map((platform) => {
            const isEcommerce = ["meta-ads", "google-ads", "tiktok-ads", "pinterest-ads", "amazon-ads"].includes(platform.slug);
            const isB2B = ["linkedin-ads", "google-ads", "microsoft-ads"].includes(platform.slug);

            return (
              <tr key={platform.slug} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-4">
                  <Link href={`/platforms/${platform.slug}`} className="font-medium text-slate-900 hover:text-cyan-600">
                    {platform.name}
                  </Link>
                </td>
                <td className="py-3 px-4 text-slate-600">{platform.targetAudience?.split(",")[0]}</td>
                <td className="py-3 px-4 text-center">
                  {isEcommerce ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300 mx-auto" />
                  )}
                </td>
                <td className="py-3 px-4 text-center">
                  {isB2B ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300 mx-auto" />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Platforms Hub Page Component
 */
export default async function PlatformsHubPage() {
  const platforms = await getPlatforms();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Platforms", href: "/platforms" },
  ];

  // Group platforms by category
  const socialPlatforms = platforms.filter((p) =>
    ["meta-ads", "tiktok-ads", "pinterest-ads", "snapchat-ads", "linkedin-ads"].includes(p.slug)
  );
  const searchPlatforms = platforms.filter((p) =>
    ["google-ads", "microsoft-ads", "amazon-ads"].includes(p.slug)
  );

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Ad Platform Guides",
          description: "Comprehensive guides for advertising platforms",
          url: "https://www.metricx.ai/platforms",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Layers className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {platforms.length} Platforms
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Advertising Platform Guides
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Master every ad platform with our comprehensive guides. Learn setup,
          targeting options, optimization strategies, and best practices for
          Meta, Google, TikTok, and more.
        </p>
      </div>

      {/* Quick Comparison */}
      <section className="mb-12 bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-2xl font-bold text-slate-900 mb-4">
          Platform Comparison
        </h2>
        <PlatformComparison platforms={platforms} />
      </section>

      {/* Social Platforms */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Social Media Platforms
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {socialPlatforms.map((platform) => (
            <PlatformCard key={platform.slug} platform={platform} />
          ))}
        </div>
      </section>

      {/* Search & Shopping Platforms */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">
          Search & Shopping Platforms
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {searchPlatforms.map((platform) => (
            <PlatformCard key={platform.slug} platform={platform} />
          ))}
        </div>
      </section>

      {/* CTA */}
      <CTABanner
        title="Track All Platforms in One Dashboard"
        description="metricx unifies Meta, Google, TikTok, and more into a single dashboard with AI-powered insights."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See Features", href: "/#features" }}
      />
    </>
  );
}
