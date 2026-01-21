/**
 * Call-to-Action Banner Component
 *
 * WHAT: Renders conversion-focused CTA sections for SEO pages
 * WHY: SEO pages should drive conversions, not just traffic.
 *      CTAs convert organic visitors into trial signups.
 *
 * @example
 * import { CTABanner } from '@/components/seo/CTABanner';
 *
 * <CTABanner
 *   title="Track Your ROAS Automatically"
 *   description="Stop manually calculating ROAS. Connect your ad accounts and see real-time performance."
 *   primaryCTA={{ text: "Start Free Trial", href: "/sign-up" }}
 *   secondaryCTA={{ text: "Learn More", href: "/features" }}
 * />
 */

import Link from "next/link";
import { ArrowRight, Sparkles, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Primary CTA banner.
 *
 * @param {Object} props - Component props
 * @param {string} [props.title] - Banner headline
 * @param {string} [props.description] - Banner description
 * @param {string} [props.buttonText] - CTA button text (legacy)
 * @param {string} [props.buttonHref] - CTA button link (legacy)
 * @param {Object} [props.primaryCTA] - Primary CTA button { text, href }
 * @param {string} [props.secondaryText] - Secondary action text (legacy)
 * @param {string} [props.secondaryHref] - Secondary action link (legacy)
 * @param {Object} [props.secondaryCTA] - Secondary CTA button { text, href }
 * @param {string[]} [props.features] - Feature bullet points
 * @param {string} [props.className] - Additional CSS classes
 * @param {"default" | "gradient" | "dark" | "inline"} [props.variant] - Visual variant
 * @returns {JSX.Element} CTA banner
 */
export function CTABanner({
  title = "Ready to Optimize Your Ad Spend?",
  description = "Join merchants who save hours every week with AI-powered ad analytics.",
  buttonText,
  buttonHref,
  primaryCTA,
  secondaryText,
  secondaryHref,
  secondaryCTA,
  features,
  className = "",
  variant = "default",
}) {
  // Normalize variant - "inline" is an alias for "default"
  const normalizedVariant = variant === "inline" ? "default" : variant;
  const isLightVariant = normalizedVariant === "default";

  // Support both object syntax and legacy props
  const primaryText = primaryCTA?.text || buttonText || "Start Free Trial";
  const primaryHref = primaryCTA?.href || buttonHref || "/sign-up";
  const secondText = secondaryCTA?.text || secondaryText;
  const secondHref = secondaryCTA?.href || secondaryHref;

  const variants = {
    default: "bg-gray-50 border border-gray-200",
    gradient: "bg-gradient-to-r from-blue-500 to-cyan-500 text-white",
    dark: "bg-gray-900 text-white",
  };

  const buttonVariants = {
    default: "bg-gray-900 hover:bg-gray-800 text-white",
    gradient: "bg-white text-blue-600 hover:bg-gray-100",
    dark: "bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white",
  };

  const textColor = isLightVariant ? "text-gray-500" : "text-white/90";
  const titleColor = isLightVariant ? "text-gray-900" : "text-white";

  return (
    <section
      className={`cta-banner rounded-2xl p-8 md:p-10 ${variants[normalizedVariant]} ${className}`}
    >
      <div className="max-w-2xl mx-auto text-center">
        {/* Icon */}
        <div
          className={`inline-flex items-center justify-center w-12 h-12 rounded-full mb-4 ${
            isLightVariant ? "bg-blue-100" : "bg-white/20"
          }`}
        >
          <Sparkles
            className={`w-6 h-6 ${
              isLightVariant ? "text-blue-600" : "text-white"
            }`}
          />
        </div>

        {/* Title */}
        <h2 className={`text-2xl md:text-3xl font-bold ${titleColor}`}>
          {title}
        </h2>

        {/* Description */}
        <p className={`mt-3 text-lg ${textColor}`}>{description}</p>

        {/* Features */}
        {features && features.length > 0 && (
          <ul className="mt-6 flex flex-wrap justify-center gap-4">
            {features.map((feature, index) => (
              <li
                key={index}
                className={`flex items-center gap-2 text-sm ${textColor}`}
              >
                <CheckCircle
                  className={`w-4 h-4 ${
                    isLightVariant ? "text-emerald-500" : "text-white"
                  }`}
                />
                {feature}
              </li>
            ))}
          </ul>
        )}

        {/* Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button asChild size="lg" className={buttonVariants[normalizedVariant]}>
            <Link href={primaryHref} className="flex items-center gap-2">
              {primaryText}
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Button>

          {secondText && secondHref && (
            <Link
              href={secondHref}
              className={`text-sm font-medium ${
                isLightVariant
                  ? "text-gray-600 hover:text-blue-600"
                  : "text-white/80 hover:text-white"
              } transition-colors`}
            >
              {secondText}
            </Link>
          )}
        </div>

        {/* Trust indicator */}
        <p
          className={`mt-6 text-sm ${
            isLightVariant ? "text-gray-400" : "text-white/70"
          }`}
        >
          14-day free trial &middot; No credit card required
        </p>
      </div>
    </section>
  );
}

/**
 * Inline CTA for content sections.
 *
 * @param {Object} props - Component props
 * @param {string} props.text - CTA text
 * @param {string} [props.buttonText] - Button text
 * @param {string} [props.href] - Link destination
 * @returns {JSX.Element} Inline CTA
 */
export function InlineCTA({
  text = "Want to track this metric automatically?",
  buttonText = "Try metricx free",
  href = "/sign-up",
}) {
  return (
    <div className="inline-cta flex flex-col sm:flex-row items-center gap-4 p-4 bg-blue-50 border border-blue-100 rounded-lg my-6">
      <p className="text-gray-700 text-sm">{text}</p>
      <Button asChild variant="outline" size="sm" className="flex-shrink-0 border-blue-200 hover:bg-blue-50">
        <Link href={href}>{buttonText}</Link>
      </Button>
    </div>
  );
}

/**
 * Comparison CTA for vs/alternatives pages.
 *
 * @param {Object} props - Component props
 * @param {string} props.competitorName - Competitor name
 * @param {string} [props.savings] - Savings amount/percentage
 * @returns {JSX.Element} Comparison CTA
 */
export function ComparisonCTA({ competitorName, savings = "77%" }) {
  return (
    <CTABanner
      title={`Switch from ${competitorName} and Save ${savings}`}
      description={`Get the same insights you rely on from ${competitorName}, plus AI-powered recommendations. All for a fraction of the price.`}
      buttonText="Start Your Free Trial"
      features={[
        "Same core features",
        `Save ${savings} vs ${competitorName}`,
        "5-minute setup",
        "Cancel anytime",
      ]}
      variant="gradient"
    />
  );
}

/**
 * Calculator CTA for tool pages.
 *
 * @param {Object} props - Component props
 * @param {string} props.metricName - Metric name (e.g., "ROAS")
 * @returns {JSX.Element} Calculator CTA
 */
export function CalculatorCTA({ metricName }) {
  return (
    <CTABanner
      title={`Track Your ${metricName} in Real-Time`}
      description={`Stop manually calculating ${metricName}. Connect your ad accounts and see live performance across Meta, Google, and TikTok.`}
      buttonText="Connect Your Accounts"
      secondaryText="See how it works"
      secondaryHref="/#demo"
      features={[
        "Real-time tracking",
        "All platforms in one view",
        "AI-powered insights",
      ]}
      variant="default"
    />
  );
}

export default CTABanner;
