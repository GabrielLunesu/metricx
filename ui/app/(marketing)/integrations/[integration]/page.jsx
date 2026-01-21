/**
 * Individual Integration Page
 *
 * WHAT: Deep dive page for each integration
 * WHY: SEO page targeting "[platform] integration" keywords
 *
 * Related files:
 * - content/integrations/data.json - Integration data
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getIntegrations, getIntegration } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateFAQSchema, generateHowToSchema } from "@/lib/seo/schemas";
import {
  ArrowRight,
  Clock,
  RefreshCw,
  CheckCircle2,
  Database,
  Settings,
  Lightbulb,
  Plug,
} from "lucide-react";

/**
 * Generate static params for all integrations.
 */
export async function generateStaticParams() {
  const integrations = await getIntegrations();
  return integrations.map((i) => ({
    integration: i.slug,
  }));
}

/**
 * Generate metadata for integration page.
 */
export async function generateMetadata({ params }) {
  const { integration: slug } = await params;
  const integration = await getIntegration(slug);

  if (!integration) {
    return {
      title: "Integration Not Found | metricx",
    };
  }

  return {
    title: `${integration.name} Integration | Connect in ${integration.setupTime} | metricx`,
    description: `Connect ${integration.name} with metricx for unified ad analytics. ${integration.setupTime} setup, ${integration.dataSync.toLowerCase()} data sync. ${integration.description.slice(0, 100)}`,
    keywords: [
      `${integration.name.toLowerCase()} metricx integration`,
      `${integration.name.toLowerCase()} analytics`,
      `connect ${integration.name.toLowerCase()}`,
      `${integration.name.toLowerCase()} ad tracking`,
    ],
    openGraph: {
      title: `${integration.name} Integration | metricx`,
      description: integration.description,
      type: "article",
      url: `https://www.metricx.ai/integrations/${integration.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/integrations/${integration.slug}`,
    },
  };
}

/**
 * Features list component.
 */
function FeaturesList({ features }) {
  if (!features || features.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {features.map((feature, index) => (
        <div key={index} className="flex items-center gap-2 text-slate-700">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
          <span>{feature}</span>
        </div>
      ))}
    </div>
  );
}

/**
 * Data points component.
 */
function DataPoints({ dataPoints }) {
  if (!dataPoints || dataPoints.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Database className="w-5 h-5 text-slate-600" />
        <h3 className="font-semibold text-slate-900">Data We Sync</h3>
      </div>
      <ul className="grid grid-cols-2 gap-2">
        {dataPoints.map((point, index) => (
          <li key={index} className="flex items-center gap-2 text-slate-600 text-sm">
            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" />
            {point}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Setup steps component.
 */
function SetupSteps({ steps }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="space-y-4">
      {steps.map((step, index) => (
        <div key={index} className="flex gap-4">
          <div className="w-8 h-8 flex items-center justify-center bg-cyan-100 text-cyan-700 font-semibold rounded-full flex-shrink-0">
            {index + 1}
          </div>
          <div className="flex-1 pt-1">
            <p className="text-slate-700">{step}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Use cases component.
 */
function UseCases({ useCases }) {
  if (!useCases || useCases.length === 0) return null;

  return (
    <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-cyan-600" />
        <h3 className="font-semibold text-slate-900">Use Cases</h3>
      </div>
      <ul className="space-y-2">
        {useCases.map((useCase, index) => (
          <li key={index} className="flex items-start gap-2 text-slate-700">
            <span className="text-cyan-500 mt-1">•</span>
            <span>{useCase}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Requirements component.
 */
function Requirements({ requirements }) {
  if (!requirements || requirements.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="font-semibold text-slate-900 mb-3">Requirements</h3>
      <ul className="space-y-2">
        {requirements.map((req, index) => (
          <li key={index} className="flex items-center gap-2 text-slate-600 text-sm">
            <CheckCircle2 className="w-4 h-4 text-slate-400" />
            {req}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Related integrations component.
 */
function RelatedIntegrations({ slugs, integrations }) {
  const related = slugs?.map((s) => integrations.find((i) => i.slug === s)).filter(Boolean) || [];
  if (related.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Integrations</h3>
      <div className="space-y-2">
        {related.map((i) => (
          <Link
            key={i.slug}
            href={`/integrations/${i.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <span className="font-medium text-slate-900 group-hover:text-cyan-700">
              {i.name}
            </span>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Integration Page Component
 */
export default async function IntegrationPage({ params }) {
  const { integration: slug } = await params;
  const integration = await getIntegration(slug);
  const allIntegrations = await getIntegrations();

  if (!integration) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Integrations", href: "/integrations" },
    { name: integration.name, href: `/integrations/${integration.slug}` },
  ];

  // Build FAQ items
  const faqItems = integration.faqs?.map((f) => ({
    question: f.question,
    answer: f.answer,
  })) || [];

  // Build HowTo steps
  const howToSteps = integration.setupSteps?.map((step, index) => ({
    name: `Step ${index + 1}`,
    text: step,
  })) || [];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      {faqItems.length > 0 && <JsonLd schema={generateFAQSchema(faqItems)} />}
      {howToSteps.length > 0 && (
        <JsonLd
          schema={generateHowToSchema({
            name: `How to Connect ${integration.name} with metricx`,
            description: `Set up the ${integration.name} integration in ${integration.setupTime}`,
            steps: howToSteps,
          })}
        />
      )}

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Content Column */}
        <div className="lg:col-span-2">
          {/* Header */}
          <header className="mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
              <Link href="/integrations" className="hover:text-cyan-600">
                Integrations
              </Link>
              <span>/</span>
              <span className="capitalize">{integration.category?.replace("-", " ")}</span>
            </div>
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-slate-100 rounded-xl">
                <Plug className="w-8 h-8 text-slate-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-4xl font-bold text-slate-900">{integration.name}</h1>
                {integration.popularity && (
                  <span className="inline-block mt-2 px-2 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
                    {integration.popularity}
                  </span>
                )}
              </div>
            </div>
            <p className="text-lg text-slate-600">{integration.description}</p>
          </header>

          {/* Quick Stats */}
          <div className="flex gap-6 mb-8 p-4 bg-slate-50 rounded-xl">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-cyan-500" />
              <div>
                <div className="text-sm text-slate-500">Setup Time</div>
                <div className="font-semibold text-slate-900">{integration.setupTime}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-cyan-500" />
              <div>
                <div className="text-sm text-slate-500">Data Sync</div>
                <div className="font-semibold text-slate-900">{integration.dataSync}</div>
              </div>
            </div>
          </div>

          {/* Features */}
          {integration.features && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">Features</h2>
              <FeaturesList features={integration.features} />
            </section>
          )}

          {/* Data Points */}
          {integration.dataPoints && (
            <section className="mb-8">
              <DataPoints dataPoints={integration.dataPoints} />
            </section>
          )}

          {/* Setup Steps */}
          {integration.setupSteps && (
            <section className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="w-5 h-5 text-slate-600" />
                <h2 className="text-2xl font-bold text-slate-900">How to Connect</h2>
              </div>
              <SetupSteps steps={integration.setupSteps} />
            </section>
          )}

          {/* Use Cases */}
          <section className="mb-8">
            <UseCases useCases={integration.useCases} />
          </section>

          {/* metricx Feature */}
          {integration.metricxFeature && (
            <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
              <Lightbulb className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">metricx Feature</div>
                <div className="text-cyan-50 text-sm">{integration.metricxFeature}</div>
              </div>
            </div>
          )}

          {/* FAQs */}
          {faqItems.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-4">
                Frequently Asked Questions
              </h2>
              <FAQ items={faqItems} />
            </section>
          )}

          {/* CTA */}
          <CTABanner
            title={`Connect ${integration.name} Today`}
            description={`Get started with the ${integration.name} integration in just ${integration.setupTime}.`}
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "View All Integrations", href: "/integrations" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Requirements */}
          <Requirements requirements={integration.requirements} />

          {/* Related Integrations */}
          <RelatedIntegrations
            slugs={integration.relatedIntegrations}
            integrations={allIntegrations}
          />

          {/* All Integrations Link */}
          <Link
            href="/integrations"
            className="flex items-center justify-center gap-2 p-4 bg-cyan-50 text-cyan-700 rounded-xl hover:bg-cyan-100 transition-colors font-medium"
          >
            View All Integrations
            <ArrowRight className="w-4 h-4" />
          </Link>
        </aside>
      </div>
    </>
  );
}
