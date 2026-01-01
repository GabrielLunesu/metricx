'use client';

/**
 * Subscribe Page
 * ==============
 *
 * WHAT: Upgrade page for free tier users to subscribe to Starter plan
 * WHY: Free tier has limited features; paid unlocks full access
 *
 * Flow:
 *   1. Free tier user clicks "Upgrade" from locked feature or nav
 *   2. Page checks billing status - redirects to dashboard if already subscribed
 *   3. User selects plan (monthly $79 / annual $569)
 *   4. Checkout created via backend
 *   5. User redirected to Polar checkout
 *   6. After success, webhook sets billing_tier = 'starter'
 *   7. Polar redirects back with ?checkout=success
 *
 * Free Tier Limitations (billing_tier = 'free'):
 *   - 1 ad account (Meta OR Google)
 *   - Dashboard only (Analytics, Finance, Campaigns, Copilot locked)
 *   - No team invites
 *
 * REFERENCES:
 *   - backend/app/routers/polar.py (checkout endpoint)
 *   - ui/lib/workspace.js (createCheckout, getBillingStatus)
 *   - docs-arch/living-docs/BILLING.md
 */

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { createCheckout, getBillingStatus } from '@/lib/workspace';
import { Check, Loader2 } from 'lucide-react';

const PLANS = [
  {
    id: 'monthly',
    name: 'Starter Monthly',
    price: '$79',
    period: '/month',
    description: 'Full access to all features',
    features: [
      'Unlimited ad accounts',
      'Full Analytics & Finance',
      'AI Copilot insights',
      'Campaign management',
      'Up to 10 team members',
    ],
    popular: false,
  },
  {
    id: 'annual',
    name: 'Starter Annual',
    price: '$569',
    period: '/year',
    description: 'Best value - save 40%',
    features: [
      'Everything in Monthly',
      '2 months free',
      'Priority onboarding',
      'Dedicated account manager',
      'Custom integrations',
    ],
    popular: true,
    savings: 'Save $379/year',
  },
];

/**
 * SubscribePageContent - Inner component that uses useSearchParams
 * Wrapped in Suspense by the parent to avoid SSR issues
 */
function SubscribePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [error, setError] = useState(null);
  const [billingData, setBillingData] = useState(null);
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);

  // Handle checkout success callback
  useEffect(() => {
    if (searchParams.get('checkout') === 'success') {
      setCheckoutSuccess(true);
      // Redirect to dashboard after short delay
      setTimeout(() => {
        router.push('/dashboard');
      }, 2000);
    }
  }, [searchParams, router]);

  // Load billing status and check if already subscribed
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    
    // Skip billing check if we're showing success state
    if (searchParams.get('checkout') === 'success') {
      setLoading(false);
      return;
    }

    const checkBillingStatus = async () => {
      try {
        const data = await getBillingStatus();
        setBillingData(data);

        // Already has paid subscription (starter tier) - redirect to dashboard
        // Note: billing_tier is the feature tier (free/starter), not billing_status
        if (data.billing?.billing_tier === 'starter') {
          router.replace('/dashboard');
          return;
        }

        // If workspace ID is in URL, verify it matches
        const urlWorkspaceId = searchParams.get('workspaceId');
        if (urlWorkspaceId && urlWorkspaceId !== data.workspace_id) {
          setError('You can only subscribe to your active workspace');
        }
      } catch (err) {
        console.error('[subscribe] Failed to check billing status:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    checkBillingStatus();
  }, [isLoaded, isSignedIn, searchParams, router]);

  const handleSubscribe = async (planId) => {
    if (!billingData) return;

    setSelectedPlan(planId);
    setCheckoutLoading(true);
    setError(null);

    try {
      const { checkout_url } = await createCheckout(billingData.workspace_id, planId);
      // Redirect to Polar checkout
      window.location.href = checkout_url;
    } catch (err) {
      console.error('[subscribe] Checkout failed:', err);
      setError(err.message);
      setCheckoutLoading(false);
      setSelectedPlan(null);
    }
  };

  // Auth loading state
  if (!isLoaded || (isLoaded && !isSignedIn)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // Checkout success state
  if (checkoutSuccess) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-slate-50 to-white">
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="h-8 w-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">Welcome to metricx!</h1>
          <p className="text-gray-600">Your subscription is now active. Redirecting to dashboard...</p>
        </div>
      </div>
    );
  }

  // Loading state (checking billing)
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="px-6 py-4">
        <Image
          src="/logo.png"
          alt="metricx"
          width={120}
          height={32}
          className="h-12 w-auto"
          priority
        />
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">
            Upgrade to Starter
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            {billingData ? (
              <>Unlock full features for <span className="font-medium">{billingData.workspace_name}</span></>
            ) : (
              'Unlock all features with unlimited ad accounts'
            )}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Cancel anytime. 30-day money-back guarantee.
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-lg text-center">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Plan cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {PLANS.map((plan) => (
            <Card
              key={plan.id}
              className={`relative bg-white ${plan.popular ? 'border-blue-500 border-2' : 'border-gray-200'}`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white text-xs font-medium px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}

              <CardHeader className="text-center pt-8">
                <CardTitle className="text-xl">{plan.name}</CardTitle>
                <CardDescription>{plan.description}</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  <span className="text-gray-500">{plan.period}</span>
                </div>
                {plan.savings && (
                  <p className="text-sm text-green-600 font-medium mt-1">{plan.savings}</p>
                )}
              </CardHeader>

              <CardContent>
                <ul className="space-y-3">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
                      <span className="text-gray-700 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>

              <CardFooter>
                <Button
                  className="w-full"
                  variant={plan.popular ? 'default' : 'outline'}
                  size="lg"
                  disabled={checkoutLoading}
                  onClick={() => handleSubscribe(plan.id)}
                >
                  {checkoutLoading && selectedPlan === plan.id ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Redirecting to checkout...
                    </>
                  ) : (
                    'Upgrade Now'
                  )}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        {/* Trust badges */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500">
            Secure payment powered by Polar. Cancel anytime from your account settings.
          </p>
        </div>
      </main>
    </div>
  );
}

/**
 * SubscribePage - Main export wrapped in Suspense for useSearchParams
 */
export default function SubscribePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      }
    >
      <SubscribePageContent />
    </Suspense>
  );
}
