/**
 * Onboarding Wizard
 * =================
 *
 * WHAT: Multi-step wizard container for onboarding flow.
 * WHY: Guides users through business profile setup step by step.
 *
 * STEPS:
 *   1. StepWorkspaceName - Workspace/business name (required)
 *   2. StepDomain - Domain + AI analysis (optional)
 *   3. StepBusinessProfile - Niche, markets, voice (optional)
 *   4. StepAdProviders - Ad platforms to connect (optional)
 *
 * STATE:
 *   - step: Current step (1-4)
 *   - formData: Accumulated data from all steps
 *   - aiSuggestions: Suggestions from domain analysis
 *
 * PERSISTENCE:
 *   - State is saved to localStorage to survive OAuth redirects
 *   - Cleared when onboarding completes
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import ProgressIndicator from './ProgressIndicator';
import StepWorkspaceName from './StepWorkspaceName';
import StepDomain from './StepDomain';
import StepBusinessProfile from './StepBusinessProfile';
import StepAdProviders from './StepAdProviders';

const TOTAL_STEPS = 4;
const STORAGE_KEY = 'metricx_onboarding_state';

/**
 * Load persisted state from localStorage
 */
function loadPersistedState() {
  if (typeof window === 'undefined') return null;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('[OnboardingWizard] Failed to load persisted state:', e);
  }
  return null;
}

/**
 * Save state to localStorage
 */
function savePersistedState(step, formData, aiSuggestions) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      step,
      formData,
      aiSuggestions,
      timestamp: Date.now(),
    }));
  } catch (e) {
    console.error('[OnboardingWizard] Failed to save state:', e);
  }
}

/**
 * Clear persisted state from localStorage
 */
function clearPersistedState() {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error('[OnboardingWizard] Failed to clear state:', e);
  }
}

export default function OnboardingWizard() {
  const router = useRouter();
  const [isInitialized, setIsInitialized] = useState(false);
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  // Form data accumulated across steps
  const [formData, setFormData] = useState({
    workspace_name: '',
    domain: '',
    domain_description: '',
    niche: '',
    target_markets: [],
    brand_voice: '',
    business_size: '',
    intended_ad_providers: [],
  });

  // AI suggestions from domain analysis
  const [aiSuggestions, setAiSuggestions] = useState(null);

  // Load persisted state on mount
  useEffect(() => {
    const saved = loadPersistedState();

    // Check URL params for OAuth callback (should go to step 4)
    const params = new URLSearchParams(window.location.search);
    const hasOAuthCallback = params.get('meta_oauth') || params.get('google_oauth');

    if (saved) {
      // Restore saved state
      setFormData(saved.formData || formData);
      setAiSuggestions(saved.aiSuggestions || null);

      // If returning from OAuth, go to step 4 (ad providers)
      if (hasOAuthCallback) {
        setStep(4);
      } else {
        setStep(saved.step || 1);
      }
    } else if (hasOAuthCallback) {
      // OAuth callback but no saved state - go to step 4 anyway
      setStep(4);
    }

    setIsInitialized(true);
  }, []);

  // Persist state when it changes (after initialization)
  useEffect(() => {
    if (isInitialized) {
      savePersistedState(step, formData, aiSuggestions);
    }
  }, [step, formData, aiSuggestions, isInitialized]);

  /**
   * Update form data from a step
   */
  const updateFormData = (updates) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  /**
   * Go to next step
   */
  const nextStep = () => {
    if (step < TOTAL_STEPS) {
      setStep(step + 1);
    }
  };

  /**
   * Go to previous step
   */
  const prevStep = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  /**
   * Skip current step (for optional steps)
   */
  const skipStep = () => {
    nextStep();
  };

  /**
   * Complete onboarding
   */
  const completeOnboarding = async () => {
    setSubmitting(true);
    try {
      const res = await fetch('/api/onboarding/complete', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const error = await res.text();
        throw new Error(error || 'Failed to complete onboarding');
      }

      const data = await res.json();

      if (data.success) {
        // Clear persisted state on successful completion
        clearPersistedState();
        toast.success('Welcome to metricx!');
        router.push(data.redirect_to || '/dashboard');
      } else {
        throw new Error('Onboarding failed');
      }
    } catch (err) {
      toast.error(err.message || 'Something went wrong');
      setSubmitting(false);
    }
  };

  // Show loading while initializing state from localStorage
  if (!isInitialized) {
    return (
      <div className="max-w-xl mx-auto">
        <div className="mt-8 bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="animate-pulse text-slate-400">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto">
      {/* Progress indicator */}
      <ProgressIndicator current={step} total={TOTAL_STEPS} />

      {/* Step content */}
      <div className="mt-8 bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        {step === 1 && (
          <StepWorkspaceName
            formData={formData}
            updateFormData={updateFormData}
            onNext={nextStep}
          />
        )}

        {step === 2 && (
          <StepDomain
            formData={formData}
            updateFormData={updateFormData}
            aiSuggestions={aiSuggestions}
            setAiSuggestions={setAiSuggestions}
            onNext={nextStep}
            onBack={prevStep}
            onSkip={skipStep}
          />
        )}

        {step === 3 && (
          <StepBusinessProfile
            formData={formData}
            updateFormData={updateFormData}
            aiSuggestions={aiSuggestions}
            onNext={nextStep}
            onBack={prevStep}
            onSkip={skipStep}
          />
        )}

        {step === 4 && (
          <StepAdProviders
            formData={formData}
            updateFormData={updateFormData}
            onComplete={completeOnboarding}
            onBack={prevStep}
            onSkip={completeOnboarding}
            submitting={submitting}
          />
        )}
      </div>
    </div>
  );
}
