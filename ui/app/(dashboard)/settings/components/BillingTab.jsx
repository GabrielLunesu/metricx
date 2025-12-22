'use client';

/**
 * Billing Tab Component
 * ====================
 *
 * WHAT: Displays workspace billing status and subscription management
 * WHY: Users need to view/manage their subscription from Settings
 *
 * Features:
 *   - Shows current plan and status
 *   - Trial countdown if trialing
 *   - Manage subscription button (opens Polar portal)
 *   - Upgrade/change plan options
 *
 * REFERENCES:
 *   - backend/app/routers/polar.py (billing endpoints)
 *   - ui/lib/workspace.js (getBillingStatus, getBillingPortalUrl)
 */

import { useState, useEffect } from 'react';
import { Loader2, CreditCard, Calendar, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getBillingStatus, getBillingPortalUrl, createCheckout } from '@/lib/workspace';

const STATUS_DISPLAY = {
  locked: { label: 'Not Subscribed', color: 'text-gray-500', bg: 'bg-gray-100' },
  trialing: { label: 'Trial', color: 'text-blue-600', bg: 'bg-blue-100' },
  active: { label: 'Active', color: 'text-green-600', bg: 'bg-green-100' },
  canceled: { label: 'Canceled', color: 'text-amber-600', bg: 'bg-amber-100' },
  past_due: { label: 'Past Due', color: 'text-red-600', bg: 'bg-red-100' },
  incomplete: { label: 'Incomplete', color: 'text-amber-600', bg: 'bg-amber-100' },
  revoked: { label: 'Revoked', color: 'text-red-600', bg: 'bg-red-100' },
};

const PLAN_DISPLAY = {
  monthly: { label: 'Monthly', price: '$79/month' },
  annual: { label: 'Annual', price: '$569/year' },
};

export default function BillingTab({ user }) {
  const [loading, setLoading] = useState(true);
  const [billing, setBilling] = useState(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [error, setError] = useState(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  useEffect(() => {
    const loadBilling = async () => {
      try {
        const data = await getBillingStatus();
        setBilling(data.billing);
        setWorkspaceName(data.workspace_name);
        setWorkspaceId(data.workspace_id);
      } catch (err) {
        console.error('[BillingTab] Failed to load billing:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadBilling();
  }, []);

  const handleManageBilling = async () => {
    if (!workspaceId || !billing?.can_manage_billing) return;

    setPortalLoading(true);
    try {
      const { portal_url } = await getBillingPortalUrl(workspaceId);
      window.open(portal_url, '_blank');
    } catch (err) {
      console.error('[BillingTab] Failed to get portal URL:', err);
      setError(err.message);
    } finally {
      setPortalLoading(false);
    }
  };

  const handleSubscribe = async (plan) => {
    if (!workspaceId) return;

    setCheckoutLoading(true);
    try {
      const { checkout_url } = await createCheckout(workspaceId, plan);
      window.location.href = checkout_url;
    } catch (err) {
      console.error('[BillingTab] Checkout failed:', err);
      setError(err.message);
      setCheckoutLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          <span>Error loading billing: {error}</span>
        </div>
      </div>
    );
  }

  const status = STATUS_DISPLAY[billing?.billing_status] || STATUS_DISPLAY.locked;
  const plan = billing?.billing_plan ? PLAN_DISPLAY[billing.billing_plan] : null;
  const isActive = billing?.is_access_allowed;
  const canManage = billing?.can_manage_billing;

  // Format trial end date
  const trialEndDate = billing?.trial_end
    ? new Date(billing.trial_end).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    : null;

  // Format period end date
  const periodEndDate = billing?.current_period_end
    ? new Date(billing.current_period_end).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    : null;

  return (
    <div className="space-y-6">
      {/* Current Plan Card */}
      <Card className="bg-white">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Subscription
          </CardTitle>
          <CardDescription>
            Manage your workspace subscription for {workspaceName}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Status</span>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${status.bg} ${status.color}`}>
              {status.label}
            </span>
          </div>

          {/* Plan Details */}
          {plan && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Plan</span>
              <span className="text-sm font-medium text-gray-900">
                {plan.label} ({plan.price})
              </span>
            </div>
          )}

          {/* Trial Info */}
          {billing?.billing_status === 'trialing' && trialEndDate && (
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-800">Trial ends</span>
              </div>
              <span className="text-sm font-medium text-blue-900">{trialEndDate}</span>
            </div>
          )}

          {/* Next Billing Date */}
          {isActive && periodEndDate && billing?.billing_status !== 'trialing' && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Next billing date</span>
              <span className="text-sm font-medium text-gray-900">{periodEndDate}</span>
            </div>
          )}

          {/* Canceled Notice */}
          {billing?.billing_status === 'canceled' && periodEndDate && (
            <div className="p-3 bg-amber-50 rounded-lg">
              <div className="flex items-center gap-2 text-amber-800">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">
                  Your subscription is canceled. Access continues until {periodEndDate}.
                </span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-4 border-t">
            {isActive && canManage ? (
              <Button
                variant="outline"
                onClick={handleManageBilling}
                disabled={portalLoading}
                className="w-full sm:w-auto"
              >
                {portalLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ExternalLink className="w-4 h-4 mr-2" />
                )}
                Manage Subscription
              </Button>
            ) : !isActive && canManage ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-600">Choose a plan to activate your workspace:</p>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => handleSubscribe('monthly')}
                    disabled={checkoutLoading}
                  >
                    {checkoutLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : null}
                    Monthly ($79/mo)
                  </Button>
                  <Button
                    onClick={() => handleSubscribe('annual')}
                    disabled={checkoutLoading}
                  >
                    {checkoutLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : null}
                    Annual ($569/yr)
                  </Button>
                </div>
              </div>
            ) : !canManage ? (
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  Only workspace owners and admins can manage billing.
                </p>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {/* Features Included */}
      {isActive && (
        <Card className="bg-white">
          <CardHeader>
            <CardTitle className="text-base">What&apos;s Included</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                'Unlimited ad accounts',
                'All analytics features',
                'AI-powered insights',
                'Up to 10 team members',
                'Priority support',
                'Custom integrations',
              ].map((feature, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
