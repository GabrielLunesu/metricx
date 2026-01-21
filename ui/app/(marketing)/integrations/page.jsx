/**
 * Integrations Hub Page
 *
 * WHAT: Hub page for all metricx integrations
 * WHY: SEO hub for integration-related keyword targeting
 *
 * Related files:
 * - content/integrations/data.json - Integration data
 * - lib/seo/content-loader.js - Data loading
 */

import Link from "next/link";
import { getIntegrations } from "@/lib/seo/content-loader";
import { Breadcrumbs, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateWebPageSchema } from "@/lib/seo/schemas";
import { Plug, ArrowRight, Clock, RefreshCw, CheckCircle2 } from "lucide-react";

/**
 * Generate metadata for the integrations hub page.
 */
export async function generateMetadata() {
  const integrations = await getIntegrations();

  return {
    title: "Integrations | Shopify, Klaviyo, Meta & More | metricx",
    description: `Connect metricx with ${integrations.length}+ platforms. One-click integrations with Shopify, WooCommerce, Klaviyo, Meta Ads, Google Ads, and more.`,
    keywords: [
      "metricx integrations",
      "shopify analytics integration",
      "meta ads integration",
      "ecommerce integrations",
      "ad platform integrations",
    ],
    openGraph: {
      title: "Integrations | metricx",
      description: "Connect all your e-commerce and ad platforms in one place.",
      type: "website",
      url: "https://www.metricx.ai/integrations",
    },
    alternates: {
      canonical: "https://www.metricx.ai/integrations",
    },
  };
}

/**
 * Integration card component.
 */
function IntegrationCard({ integration }) {
  return (
    <Link
      href={`/integrations/${integration.slug}`}
      className="group block bg-white border border-slate-200 rounded-xl p-6 hover:border-cyan-300 hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 bg-slate-100 rounded-lg group-hover:bg-cyan-100 transition-colors">
          <Plug className="w-5 h-5 text-slate-600 group-hover:text-cyan-600" />
        </div>
        {integration.popularity && (
          <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
            {integration.popularity}
          </span>
        )}
      </div>
      <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 mb-2">
        {integration.name}
      </h3>
      <p className="text-slate-600 text-sm mb-4 line-clamp-2">{integration.description}</p>
      <div className="flex items-center justify-between text-sm text-slate-500">
        <div className="flex items-center gap-1">
          <Clock className="w-4 h-4" />
          <span>{integration.setupTime}</span>
        </div>
        <div className="flex items-center gap-1">
          <RefreshCw className="w-4 h-4" />
          <span>{integration.dataSync}</span>
        </div>
      </div>
    </Link>
  );
}

/**
 * Category section component.
 */
function CategorySection({ title, integrations }) {
  if (integrations.length === 0) return null;

  return (
    <section className="mb-12">
      <h2 className="text-2xl font-bold text-slate-900 mb-6">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((integration) => (
          <IntegrationCard key={integration.slug} integration={integration} />
        ))}
      </div>
    </section>
  );
}

/**
 * Integrations Hub Page Component
 */
export default async function IntegrationsHubPage() {
  const integrations = await getIntegrations();

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Integrations", href: "/integrations" },
  ];

  // Group by category
  const ecommerceIntegrations = integrations.filter((i) => i.category === "e-commerce");
  const adPlatformIntegrations = integrations.filter((i) => i.category === "ad-platform");
  const emailIntegrations = integrations.filter((i) => i.category === "email-marketing");
  const analyticsIntegrations = integrations.filter((i) => i.category === "analytics");
  const otherIntegrations = integrations.filter(
    (i) => !["e-commerce", "ad-platform", "email-marketing", "analytics"].includes(i.category)
  );

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      <JsonLd
        schema={generateWebPageSchema({
          title: "Integrations",
          description: "Connect your e-commerce and ad platforms with metricx",
          url: "https://www.metricx.ai/integrations",
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-cyan-100 rounded-lg">
            <Plug className="w-6 h-6 text-cyan-600" />
          </div>
          <span className="text-sm font-medium text-cyan-600">
            {integrations.length}+ Integrations
          </span>
        </div>
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          Integrations
        </h1>
        <p className="text-lg text-slate-600 max-w-3xl">
          Connect metricx with your favorite tools. One-click integrations with
          e-commerce platforms, ad networks, email tools, and more.
        </p>
      </div>

      {/* Integration Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-slate-50 rounded-xl p-6">
          <CheckCircle2 className="w-8 h-8 text-cyan-500 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">One-Click Setup</h3>
          <p className="text-slate-600 text-sm">
            Most integrations take less than 5 minutes. No coding required.
          </p>
        </div>
        <div className="bg-slate-50 rounded-xl p-6">
          <RefreshCw className="w-8 h-8 text-cyan-500 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">Real-Time Sync</h3>
          <p className="text-slate-600 text-sm">
            Data syncs automatically so your dashboard is always up to date.
          </p>
        </div>
        <div className="bg-slate-50 rounded-xl p-6">
          <Plug className="w-8 h-8 text-cyan-500 mb-3" />
          <h3 className="font-semibold text-slate-900 mb-2">Secure Connection</h3>
          <p className="text-slate-600 text-sm">
            OAuth authentication and encrypted data transfer keep your data safe.
          </p>
        </div>
      </div>

      {/* E-commerce Platforms */}
      <CategorySection title="E-commerce Platforms" integrations={ecommerceIntegrations} />

      {/* Ad Platforms */}
      <CategorySection title="Ad Platforms" integrations={adPlatformIntegrations} />

      {/* Email Marketing */}
      <CategorySection title="Email Marketing" integrations={emailIntegrations} />

      {/* Analytics */}
      <CategorySection title="Analytics & Data" integrations={analyticsIntegrations} />

      {/* Other */}
      {otherIntegrations.length > 0 && (
        <CategorySection title="Other Integrations" integrations={otherIntegrations} />
      )}

      {/* CTA */}
      <CTABanner
        title="Connect Your Stack"
        description="Get started with metricx and connect all your platforms in minutes."
        primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
        secondaryCTA={{ text: "See All Features", href: "/#features" }}
      />
    </>
  );
}
