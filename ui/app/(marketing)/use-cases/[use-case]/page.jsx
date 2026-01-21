/**
 * Individual Use Case Page
 *
 * WHAT: Deep dive page for each use case
 * WHY: SEO page targeting use case-related keywords
 *
 * Related files:
 * - content/use-cases/data.json - Use case data
 * - lib/seo/content-loader.js - Data loading
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import { getUseCases, getUseCase } from "@/lib/seo/content-loader";
import { Breadcrumbs, FAQ, CTABanner } from "@/components/seo";
import { JsonLd } from "@/components/seo/JsonLd";
import { generateBreadcrumbSchema, generateFAQSchema, generateArticleSchema } from "@/lib/seo/schemas";
import {
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  Target,
  Users,
  Quote,
  BookOpen,
} from "lucide-react";

/**
 * Generate static params for all use cases.
 */
export async function generateStaticParams() {
  const useCases = await getUseCases();
  return useCases.map((u) => ({
    "use-case": u.slug,
  }));
}

/**
 * Generate metadata for use case page.
 */
export async function generateMetadata({ params }) {
  const { "use-case": slug } = await params;
  const useCase = await getUseCase(slug);

  if (!useCase) {
    return {
      title: "Use Case Not Found | metricx",
    };
  }

  return {
    title: `${useCase.name} | metricx Use Case`,
    description: `${useCase.tagline}. ${useCase.description.slice(0, 120)}`,
    keywords: [
      useCase.name.toLowerCase(),
      useCase.tagline.toLowerCase(),
      "ecommerce analytics",
      "ad tracking",
      useCase.category,
    ],
    openGraph: {
      title: `${useCase.name} | metricx`,
      description: useCase.tagline,
      type: "article",
      url: `https://www.metricx.ai/use-cases/${useCase.slug}`,
    },
    alternates: {
      canonical: `https://www.metricx.ai/use-cases/${useCase.slug}`,
    },
  };
}

/**
 * Problem section component.
 */
function ProblemSection({ problem }) {
  if (!problem) return null;

  return (
    <div className="bg-red-50 border border-red-100 rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-red-600" />
        <h2 className="font-semibold text-red-800">The Problem</h2>
      </div>
      <p className="text-red-700">{problem}</p>
    </div>
  );
}

/**
 * Solution section component.
 */
function SolutionSection({ solution }) {
  if (!solution) return null;

  return (
    <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
        <h2 className="font-semibold text-emerald-800">The Solution</h2>
      </div>
      <p className="text-emerald-700">{solution}</p>
    </div>
  );
}

/**
 * Benefits list component.
 */
function BenefitsList({ benefits }) {
  if (!benefits || benefits.length === 0) return null;

  return (
    <section className="mb-8">
      <h2 className="text-2xl font-bold text-slate-900 mb-4">Benefits</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {benefits.map((benefit, index) => (
          <div key={index} className="flex items-start gap-2 text-slate-700">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
            <span>{benefit}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

/**
 * Features list component.
 */
function FeaturesList({ features }) {
  if (!features || features.length === 0) return null;

  return (
    <section className="mb-8">
      <h2 className="text-2xl font-bold text-slate-900 mb-4">Key Features</h2>
      <ul className="space-y-2">
        {features.map((feature, index) => (
          <li key={index} className="flex items-center gap-2 text-slate-700">
            <Lightbulb className="w-4 h-4 text-cyan-500" />
            {feature}
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Ideal for section component.
 */
function IdealFor({ idealFor }) {
  if (!idealFor || idealFor.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-5 h-5 text-slate-600" />
        <h3 className="font-semibold text-slate-900">Ideal For</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        {idealFor.map((item, index) => (
          <span
            key={index}
            className="px-3 py-1 bg-white border border-slate-200 rounded-full text-sm text-slate-700"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Testimonial component.
 */
function Testimonial({ snippet }) {
  if (!snippet) return null;

  return (
    <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-6 mb-8">
      <Quote className="w-8 h-8 text-cyan-300 mb-3" />
      <p className="text-lg text-slate-700 italic">&ldquo;{snippet}&rdquo;</p>
      <p className="text-sm text-slate-500 mt-2">— metricx Customer</p>
    </div>
  );
}

/**
 * Related use cases component.
 */
function RelatedUseCases({ slugs, useCases }) {
  const related = slugs?.map((s) => useCases.find((u) => u.slug === s)).filter(Boolean) || [];
  if (related.length === 0) return null;

  return (
    <div className="bg-slate-50 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">Related Use Cases</h3>
      <div className="space-y-2">
        {related.map((u) => (
          <Link
            key={u.slug}
            href={`/use-cases/${u.slug}`}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 hover:border-cyan-300 transition-colors group"
          >
            <div>
              <div className="font-medium text-slate-900 group-hover:text-cyan-700">
                {u.name}
              </div>
              <div className="text-sm text-slate-500">{u.tagline}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-cyan-500" />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * Individual Use Case Page Component
 */
export default async function UseCasePage({ params }) {
  const { "use-case": slug } = await params;
  const useCase = await getUseCase(slug);
  const allUseCases = await getUseCases();

  if (!useCase) {
    notFound();
  }

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: "Use Cases", href: "/use-cases" },
    { name: useCase.name, href: `/use-cases/${useCase.slug}` },
  ];

  // Build FAQ items
  const faqItems = useCase.faqs?.map((f) => ({
    question: f.question,
    answer: f.answer,
  })) || [];

  return (
    <>
      {/* Structured Data */}
      <JsonLd schema={generateBreadcrumbSchema(breadcrumbItems)} />
      {faqItems.length > 0 && <JsonLd schema={generateFAQSchema(faqItems)} />}
      <JsonLd
        schema={generateArticleSchema({
          title: useCase.name,
          description: useCase.description,
          url: `https://www.metricx.ai/use-cases/${useCase.slug}`,
          datePublished: "2024-01-01",
          dateModified: new Date().toISOString().split("T")[0],
        })}
      />

      {/* Breadcrumbs */}
      <Breadcrumbs items={breadcrumbItems} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Content Column */}
        <div className="lg:col-span-2">
          {/* Header */}
          <header className="mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
              <Link href="/use-cases" className="hover:text-cyan-600">
                Use Cases
              </Link>
              <span>/</span>
              <span className="capitalize">{useCase.category}</span>
            </div>
            <h1 className="text-4xl font-bold text-slate-900 mb-3">
              {useCase.name}
            </h1>
            <p className="text-xl text-cyan-600 font-medium mb-4">{useCase.tagline}</p>
            <p className="text-lg text-slate-600">{useCase.description}</p>
          </header>

          {/* Problem */}
          <ProblemSection problem={useCase.problem} />

          {/* Solution */}
          <SolutionSection solution={useCase.solution} />

          {/* Benefits */}
          <BenefitsList benefits={useCase.benefits} />

          {/* Features */}
          <FeaturesList features={useCase.features} />

          {/* Ideal For */}
          <IdealFor idealFor={useCase.idealFor} />

          {/* Testimonial */}
          <Testimonial snippet={useCase.testimonialSnippet} />

          {/* metricx Feature */}
          {useCase.metricxFeature && (
            <div className="flex items-start gap-3 p-4 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl mb-8">
              <Target className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">Powered by metricx</div>
                <div className="text-cyan-50 text-sm">{useCase.metricxFeature}</div>
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
            title={useCase.cta || "Try metricx Today"}
            description="Start your free trial and experience this use case firsthand."
            primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
            secondaryCTA={{ text: "See All Use Cases", href: "/use-cases" }}
            variant="inline"
          />
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* Related Use Cases */}
          <RelatedUseCases slugs={useCase.relatedUseCases} useCases={allUseCases} />

          {/* Quick Links */}
          <div className="bg-slate-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Learn More
            </h3>
            <div className="space-y-2">
              <Link
                href="/integrations"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Integrations
              </Link>
              <Link
                href="/platforms"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Platforms
              </Link>
              <Link
                href="/tools"
                className="flex items-center gap-2 text-slate-600 hover:text-cyan-600"
              >
                <BookOpen className="w-4 h-4" />
                Free Tools
              </Link>
            </div>
          </div>

          {/* All Use Cases Link */}
          <Link
            href="/use-cases"
            className="flex items-center justify-center gap-2 p-4 bg-cyan-50 text-cyan-700 rounded-xl hover:bg-cyan-100 transition-colors font-medium"
          >
            View All Use Cases
            <ArrowRight className="w-4 h-4" />
          </Link>
        </aside>
      </div>
    </>
  );
}
