/**
 * Calculator Layout Component
 *
 * WHAT: Shared layout wrapper for all calculator/tool pages
 * WHY: Consistent UI and structure across all calculator tools
 *
 * Related files:
 * - components/seo/CTABanner.jsx - CTA components
 * - components/seo/FAQ.jsx - FAQ component
 * - lib/seo/schemas.js - HowTo schema
 *
 * @example
 * <CalculatorLayout
 *   title="ROAS Calculator"
 *   description="Calculate your Return on Ad Spend instantly"
 *   howToSteps={[...]}
 *   faqs={[...]}
 * >
 *   <ROASCalculator />
 * </CalculatorLayout>
 */

import { JsonLd } from "@/components/seo/JsonLd";
import { FAQ } from "@/components/seo/FAQ";
import { CalculatorCTA } from "@/components/seo/CTABanner";
import { RelatedContent } from "@/components/seo/RelatedContent";
import { generateHowToSchema } from "@/lib/seo/schemas";

/**
 * Calculator page layout.
 *
 * @param {Object} props - Component props
 * @param {string} props.title - Calculator title
 * @param {string} props.description - Calculator description
 * @param {React.ReactNode} props.children - Calculator component
 * @param {Array<{name: string, text: string}>} [props.howToSteps] - Steps for HowTo schema
 * @param {Array<{question: string, answer: string}>} [props.faqs] - FAQ items
 * @param {Array} [props.relatedTools] - Related calculator links
 * @param {string} [props.metricName] - Metric name for CTA
 * @param {string} [props.formulaSection] - Optional formula explanation
 * @returns {JSX.Element} Calculator layout
 */
export function CalculatorLayout({
  title,
  description,
  children,
  howToSteps,
  faqs,
  relatedTools,
  metricName,
  formulaSection,
}) {
  return (
    <article className="calculator-page">
      {/* HowTo Schema */}
      {howToSteps && (
        <JsonLd
          schema={generateHowToSchema({
            name: `How to Use the ${title}`,
            description,
            steps: howToSteps,
            totalTime: "PT1M",
          })}
        />
      )}

      {/* Page Header */}
      <header className="mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-slate-900">
          {title}
        </h1>
        <p className="mt-3 text-lg text-slate-600 max-w-2xl">{description}</p>
      </header>

      {/* Calculator Component */}
      <section className="calculator-wrapper bg-white border border-slate-200 rounded-2xl p-6 md:p-8 mb-12">
        {children}
      </section>

      {/* Formula Explanation */}
      {formulaSection && (
        <section className="formula-section mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            How It Works
          </h2>
          <div className="prose prose-slate max-w-none">{formulaSection}</div>
        </section>
      )}

      {/* FAQs */}
      {faqs && faqs.length > 0 && (
        <section className="faq-section mb-12">
          <FAQ title="Frequently Asked Questions" items={faqs} />
        </section>
      )}

      {/* CTA */}
      <section className="cta-section mb-12">
        <CalculatorCTA metricName={metricName || title.replace(" Calculator", "")} />
      </section>

      {/* Related Tools */}
      {relatedTools && relatedTools.length > 0 && (
        <section className="related-section">
          <RelatedContent
            title="More Calculators"
            items={relatedTools}
            basePath="/tools"
            columns={3}
          />
        </section>
      )}
    </article>
  );
}

/**
 * Calculator input field component.
 *
 * @param {Object} props - Component props
 * @param {string} props.label - Input label
 * @param {string} props.id - Input ID
 * @param {string} [props.type="number"] - Input type
 * @param {string|number} props.value - Input value
 * @param {Function} props.onChange - Change handler
 * @param {string} [props.prefix] - Input prefix (e.g., "$")
 * @param {string} [props.suffix] - Input suffix (e.g., "%")
 * @param {string} [props.placeholder] - Placeholder text
 * @param {string} [props.helperText] - Helper text below input
 * @returns {JSX.Element} Calculator input
 */
export function CalculatorInput({
  label,
  id,
  type = "number",
  value,
  onChange,
  prefix,
  suffix,
  placeholder,
  helperText,
}) {
  return (
    <div className="calculator-input">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 mb-1"
      >
        {label}
      </label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            {prefix}
          </span>
        )}
        <input
          type={type}
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-colors ${
            prefix ? "pl-8" : ""
          } ${suffix ? "pr-12" : ""}`}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
            {suffix}
          </span>
        )}
      </div>
      {helperText && (
        <p className="mt-1 text-sm text-slate-500">{helperText}</p>
      )}
    </div>
  );
}

/**
 * Calculator result display component.
 *
 * @param {Object} props - Component props
 * @param {string} props.label - Result label
 * @param {string|number} props.value - Result value
 * @param {string} [props.suffix] - Value suffix
 * @param {string} [props.interpretation] - Result interpretation
 * @param {"success" | "warning" | "error" | "neutral"} [props.status] - Status color
 * @returns {JSX.Element} Calculator result
 */
export function CalculatorResult({
  label,
  value,
  suffix,
  interpretation,
  status = "neutral",
}) {
  const statusColors = {
    success: "bg-emerald-50 border-emerald-200 text-emerald-700",
    warning: "bg-amber-50 border-amber-200 text-amber-700",
    error: "bg-red-50 border-red-200 text-red-700",
    neutral: "bg-cyan-50 border-cyan-200 text-cyan-700",
  };

  return (
    <div
      className={`calculator-result p-6 rounded-xl border-2 ${statusColors[status]}`}
    >
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-4xl font-bold mt-1">
        {value}
        {suffix && <span className="text-2xl ml-1">{suffix}</span>}
      </p>
      {interpretation && (
        <p className="text-sm mt-2 opacity-80">{interpretation}</p>
      )}
    </div>
  );
}

export default CalculatorLayout;
