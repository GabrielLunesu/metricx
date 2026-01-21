/**
 * Dashboard Shell - Client-side layout with sidebar and animations.
 *
 * WHAT: Handles sidebar, route animations, and layout variations
 * WHY: Separated from layout.jsx because this needs client-side hooks (usePathname)
 *
 * Layout Variations:
 * - Normal: Sidebar + scrollable content area
 * - Immersive (/canvas): Full-screen, no sidebar
 * - Copilot (/copilot): Full-height, no overflow scroll
 *
 * Billing Gating:
 * - Checks workspace billing status before allowing access
 * - If locked: Owner/Admin → redirect to /subscribe
 * - If locked: Viewer/Member → show "ask admin" message
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/layout.jsx (parent server component)
 *   - ui/app/(dashboard)/components/shared/Sidebar.jsx
 *   - backend/app/routers/polar.py (billing status endpoint)
 */
"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./components/shared";
import FooterDashboard from "../../components/FooterDashboard";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { getBillingStatus } from "@/lib/workspace";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CreditCard, Clock, Zap } from "lucide-react";
import { UpgradeModal } from "@/components/UpgradeModal";
import Link from "next/link";

// Routes that require paid tier (free tier users are redirected)
const PAID_ONLY_ROUTES = ['/analytics', '/finance', '/campaigns', '/copilot'];

export default function DashboardShell({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [billingBlocked, setBillingBlocked] = useState(null);
  const [upgradeModal, setUpgradeModal] = useState({ open: false, feature: null });
  const [billing, setBilling] = useState(null); // Store billing status for trial banner

  // Check billing and onboarding status on mount
  // WHY: Ensure users can't bypass billing or onboarding by navigating directly
  useEffect(() => {
    const checkAccess = async () => {
      try {
        // Step 1: Check billing status
        const billingData = await getBillingStatus();
        const { billing: billingInfo, workspace_id } = billingData;
        setBilling(billingInfo); // Store for trial banner

        if (!billingInfo.is_access_allowed) {
          // Billing blocked
          if (billingInfo.can_manage_billing) {
            // Owner/Admin - redirect to subscribe
            router.replace(`/subscribe?workspaceId=${workspace_id}`);
            return;
          } else {
            // Viewer/Member - show message
            setBillingBlocked({
              message: "This workspace requires an active subscription. Please ask your workspace owner or admin to subscribe.",
              canManage: false,
            });
            setCheckingAccess(false);
            return;
          }
        }

        // Step 2: Free tier page gating
        // WHY: Free tier users only get Dashboard access
        if (billingInfo.billing_tier === 'free') {
          const isPaidRoute = PAID_ONLY_ROUTES.some(route => pathname?.startsWith(route));
          if (isPaidRoute) {
            // Get feature name from route for upgrade modal
            const routeToFeature = {
              '/analytics': 'Analytics',
              '/finance': 'Finance',
              '/campaigns': 'Campaigns',
              '/copilot': 'Copilot AI',
            };
            const feature = Object.entries(routeToFeature).find(([route]) =>
              pathname?.startsWith(route)
            )?.[1] || 'this feature';

            // Redirect to dashboard and show upgrade modal
            router.replace('/dashboard');
            setUpgradeModal({ open: true, feature });
            setCheckingAccess(false);
            return;
          }
        }

        // Step 3: Check onboarding status (billing OK)
        const onboardingRes = await fetch('/api/onboarding/status', {
          credentials: 'include',
        });
        if (onboardingRes.ok) {
          const onboardingData = await onboardingRes.json();
          if (!onboardingData.completed) {
            // Not completed - redirect to onboarding
            router.replace('/onboarding');
            return;
          }
        }
      } catch (err) {
        // If check fails, allow access (fail open)
        console.error('[DashboardShell] Access check failed:', err);
      }
      setCheckingAccess(false);
    };

    checkAccess();
  }, [router, pathname]);

  // Route-based layout variations
  const immersive = pathname === "/canvas";
  const isCopilot = pathname === "/copilot";

  const contentClass = immersive || isCopilot
    ? "w-full h-full"
    : "p-6 lg:p-8";

  // Show loading while checking access
  if (checkingAccess) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
          <span className="text-sm text-slate-500">Loading...</span>
        </div>
      </div>
    );
  }

  // Show billing blocked message for non-admin users
  if (billingBlocked) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-b from-slate-50 to-white p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="h-6 w-6 text-amber-600" />
            </div>
            <CardTitle>Subscription Required</CardTitle>
            <CardDescription className="mt-2">
              {billingBlocked.message}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-sm text-gray-500 mb-4">
              Contact your workspace owner or administrator to activate the subscription.
            </p>
            <Button
              variant="outline"
              onClick={() => router.push('/')}
            >
              Return Home
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full hero-gradient relative overflow-hidden text-neutral-900 font-sans antialiased selection:bg-neutral-100 selection:text-neutral-900">
      {/* Trial Banner - shows countdown for trialing users */}
      {billing?.billing_status === 'trialing' && billing?.trial_end && (
        <TrialBanner trialEnd={billing.trial_end} />
      )}

      {/* Dashboard Shell */}
      <div className={`flex h-screen overflow-hidden ${billing?.billing_status === 'trialing' ? 'pt-10' : ''}`}>
        {/* Sidebar - hidden in immersive mode */}
        {!immersive && <Sidebar />}

        {/* Main Content */}
        <main
          className={`
            flex-1 h-full overflow-x-hidden relative
            ${!isCopilot ? 'overflow-y-auto' : 'overflow-hidden'}
            ${!immersive ? "ml-20 lg:ml-72" : ""}
          `}
        >
          <div className={contentClass}>
            <AnimatePresence mode="wait">
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="h-full"
              >
                {children}
                {!immersive && !isCopilot && (
                  <div className="mt-12">
                    <FooterDashboard />
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>

      {/* Upgrade Modal for free tier users accessing paid features */}
      <UpgradeModal
        open={upgradeModal.open}
        onClose={() => setUpgradeModal({ open: false, feature: null })}
        feature={upgradeModal.feature}
      />
    </div>
  );
}

/**
 * TrialBanner - Shows countdown for trial users
 *
 * WHAT: Fixed banner at top of dashboard showing trial days remaining
 * WHY: Creates urgency and provides clear CTA for conversion
 *
 * @param {string} trialEnd - ISO date string when trial expires
 */
function TrialBanner({ trialEnd }) {
  const now = new Date();
  const end = new Date(trialEnd);
  const daysLeft = Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)));

  // Don't show if already expired (backend will handle downgrade)
  if (daysLeft <= 0) return null;

  const isUrgent = daysLeft <= 2;

  return (
    <div
      className={`fixed top-0 left-0 md:left-20 lg:left-72 right-0 z-40 px-4 py-2.5 text-center text-sm flex items-center justify-center gap-2 transition-all duration-300 ${
        isUrgent
          ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white'
          : 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white'
      }`}
    >
      <Clock className="w-4 h-4" />
      <span>
        <span className="font-semibold">
          {daysLeft === 1 ? 'Last day' : `${daysLeft} days left`}
        </span>
        {' '}of your free trial.
      </span>
      <Link
        href="/subscribe"
        className="inline-flex items-center gap-1 ml-2 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-full text-xs font-medium transition-colors"
      >
        <Zap className="w-3 h-3" />
        Upgrade now
      </Link>
    </div>
  );
}
