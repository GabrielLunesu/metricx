/**
 * Onboarding Page
 * ===============
 *
 * WHAT: Multi-step wizard for collecting business profile during onboarding.
 * WHY: New users need to provide business context for AI personalization.
 *
 * FLOW:
 *   1. Workspace Name (required)
 *   2. Domain + AI Analysis (optional)
 *   3. Business Profile - niche, markets (optional)
 *   4. Ad Providers to connect (optional)
 *
 * REFERENCES:
 *   - backend/app/routers/onboarding.py (API endpoints)
 *   - backend/app/services/domain_analyzer.py (AI analysis)
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import OnboardingWizard from './components/OnboardingWizard';

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [alreadyCompleted, setAlreadyCompleted] = useState(false);

  // Check onboarding status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch('/api/onboarding/status', {
          credentials: 'include',
        });
        if (res.ok) {
          const data = await res.json();
          if (data.completed) {
            // Already completed, redirect to dashboard
            setAlreadyCompleted(true);
            router.replace('/dashboard');
            return;
          }
        }
      } catch (err) {
        console.error('Failed to check onboarding status:', err);
      }
      setLoading(false);
    };

    checkStatus();
  }, [router]);

  if (loading || alreadyCompleted) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return <OnboardingWizard />;
}
