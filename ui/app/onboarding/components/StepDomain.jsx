/**
 * Step 2: Domain + AI Analysis
 * ============================
 *
 * WHAT: Collects domain and uses AI to suggest business description/niche.
 * WHY: AI can pre-fill profile info to reduce friction.
 *
 * FLOW:
 *   1. User enters domain
 *   2. "Analyze" button triggers AI extraction
 *   3. AI suggestions are shown and can be edited
 *   4. Continue or skip
 */

'use client';

import { useState } from 'react';
import { Globe, Sparkles, ArrowRight, ArrowLeft, Loader2 } from 'lucide-react';

export default function StepDomain({
  formData,
  updateFormData,
  aiSuggestions,
  setAiSuggestions,
  onNext,
  onBack,
  onSkip,
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');

  /**
   * Trigger AI domain analysis
   */
  const analyzeDomain = async () => {
    const domain = formData.domain.trim();
    if (!domain) return;

    setAnalyzing(true);
    setAnalyzeError('');

    try {
      const res = await fetch('/api/onboarding/analyze-domain', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain }),
      });

      const data = await res.json();

      if (data.success && data.suggestions) {
        setAiSuggestions(data.suggestions);

        // Pre-fill form with suggestions
        updateFormData({
          domain_description: data.suggestions.description || '',
          niche: data.suggestions.niche || '',
          brand_voice: data.suggestions.brand_voice || '',
        });
      } else {
        setAnalyzeError(data.error || 'Could not analyze domain');
      }
    } catch (err) {
      setAnalyzeError('Failed to analyze domain');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 mb-4">
          <Globe className="w-6 h-6 text-indigo-600" />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Do you have a website?
        </h1>
        <p className="mt-2 text-slate-500">
          We'll analyze it to learn about your business
        </p>
      </div>

      {/* Domain input */}
      <div className="mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={formData.domain}
            onChange={(e) => updateFormData({ domain: e.target.value })}
            placeholder="yourbusiness.com"
            className="flex-1 px-4 py-3 rounded-xl border border-slate-200
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <button
            type="button"
            onClick={analyzeDomain}
            disabled={analyzing || !formData.domain.trim()}
            className="px-4 py-3 rounded-xl bg-slate-100 text-slate-700 font-medium
              hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center gap-2"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Analyze
              </>
            )}
          </button>
        </div>
        {analyzeError && (
          <p className="mt-2 text-sm text-red-600">{analyzeError}</p>
        )}
      </div>

      {/* AI Suggestions */}
      {aiSuggestions && (
        <div className="mb-6 p-4 rounded-xl bg-indigo-50 border border-indigo-100">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <span className="text-sm font-medium text-indigo-700">
              Based on your website
            </span>
            <span className="text-xs text-indigo-500 ml-auto">
              {Math.round((aiSuggestions.confidence || 0) * 100)}% confidence
            </span>
          </div>

          <div className="space-y-3">
            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                About your business
              </label>
              <textarea
                value={formData.domain_description}
                onChange={(e) => updateFormData({ domain_description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200
                  focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            {/* Niche suggestion */}
            {aiSuggestions.niche && (
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  Industry/Niche
                </label>
                <input
                  type="text"
                  value={formData.niche}
                  onChange={(e) => updateFormData({ niche: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200
                    focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <button
          type="button"
          onClick={onSkip}
          className="flex-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium
            hover:bg-slate-50 transition-colors"
        >
          Skip
        </button>

        <button
          type="button"
          onClick={onNext}
          className="flex-1 px-4 py-3 rounded-xl bg-indigo-600 text-white font-medium
            hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
        >
          Continue
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
