/**
 * Shopify Embedded App Page
 *
 * WHAT: Landing page when merchants open metricx from Shopify admin.
 * WHY: Shopify embeds this in an iframe. Must show login/register (not homepage)
 *      for app review approval. After auth, handles store connection.
 *
 * FLOW:
 *   1. Merchant installs app -> Shopify opens this page in admin iframe
 *   2. Not signed in -> Show Clerk SignIn/SignUp
 *   3. Signed in -> Show Shopify connect flow (or auto-detect shop from params)
 *   4. After connection -> Show success + link to dashboard
 *
 * REFERENCES:
 *   - shopify-app/metricx/shopify.app.toml (application_url points here)
 *   - ui/components/ShopifyConnectButton.jsx (reuses OAuth flow)
 *   - backend/app/routers/shopify_oauth.py (handles OAuth)
 */

'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { Store, ExternalLink, CheckCircle, ArrowRight, Loader2, LogIn, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import ShopifyShopModal from '@/components/ShopifyShopModal';
import { getApiBase } from '@/lib/config';
import { buildAuthRedirectUrl } from '@/lib/authRedirect';
import {
  buildShopifyReturnPath,
  isShopifyEmbeddedContext,
  persistShopifyEmbeddedContext,
  verifyEmbeddedShopifySession,
} from '@/lib/shopifyEmbedded';

export default function ShopifyEmbeddedPage() {
  const { isLoaded, isSignedIn } = useUser();
  const [shopDomain, setShopDomain] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);
  const [embeddedReturnUrl, setEmbeddedReturnUrl] = useState('/shopify');

  // Extract Shopify params and handle OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const currentUrl = `${window.location.pathname}${window.location.search}`;

    persistShopifyEmbeddedContext(window.location.search);
    const returnUrl = buildShopifyReturnPath('/shopify', window.location.search, {
      stripParams: ['shopify_oauth', 'session_id', 'message'],
    });

    setEmbeddedReturnUrl(returnUrl);

    // Pre-fill shop domain from Shopify embed params
    const shop = params.get('shop');
    if (shop) {
      setShopDomain(shop.replace('.myshopify.com', ''));
    }

    // Handle OAuth callback (redirect comes back here)
    const oauthStatus = params.get('shopify_oauth');
    const sessionIdParam = params.get('session_id');
    const errorMessage = params.get('message');

    if (oauthStatus === 'confirm' && sessionIdParam) {
      setSessionId(sessionIdParam);
      setShowConfirmModal(true);
      window.history.replaceState({}, '', returnUrl);
    } else if (oauthStatus === 'error') {
      setMessage(`Connection failed: ${errorMessage || 'Unknown error'}`);
      setMessageType('error');
      window.history.replaceState({}, '', returnUrl);
    } else if (returnUrl !== currentUrl) {
      window.history.replaceState({}, '', returnUrl);
    }

    const embeddedSearch = new URL(returnUrl, window.location.origin).search;

    if (isShopifyEmbeddedContext(embeddedSearch)) {
      verifyEmbeddedShopifySession({ search: embeddedSearch }).catch((error) => {
        console.error('[shopify] Embedded session verification failed:', error);
      });
    }
  }, []);

  const handleConnect = () => {
    if (!shopDomain.trim()) {
      setMessage('Please enter your Shopify store domain');
      setMessageType('error');
      return;
    }

    setConnecting(true);
    const baseUrl = getApiBase();
    const encodedShop = encodeURIComponent(shopDomain.trim());
    const redirectPath = encodeURIComponent(embeddedReturnUrl);

    // Use top-level navigation to break out of Shopify iframe for OAuth
    // Pass redirect_path so callback returns to /shopify (not /settings)
    window.top.location.href = `${baseUrl}/auth/shopify/authorize?shop=${encodedShop}&redirect_path=${redirectPath}`;
  };

  const handleAuthRedirect = (path) => {
    const authUrl = buildAuthRedirectUrl(path, embeddedReturnUrl);
    window.top.location.href = authUrl;
  };

  // Loading state while Clerk initializes
  if (!isLoaded) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 via-white to-gray-50/50">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Image
            src="/logo.png"
            alt="metricx"
            width={180}
            height={50}
            className="h-12 w-auto"
            priority
          />
        </div>

        {/* Status messages */}
        {message && (
          <div
            className={`mb-6 p-3 rounded-lg text-sm ${
              messageType === 'error'
                ? 'bg-red-50 text-red-800 border border-red-200'
                : 'bg-blue-50 text-blue-800 border border-blue-200'
            }`}
          >
            {message}
          </div>
        )}

        {/* ─── NOT SIGNED IN: Show Auth ─── */}
        {!isSignedIn && (
          <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-xl font-semibold text-gray-900">
                Sign In To Continue
              </CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                Continue in a full browser tab, then we&apos;ll send you back to Shopify.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() => handleAuthRedirect('/sign-in')}
                className="w-full rounded-xl"
              >
                <LogIn className="w-4 h-4 mr-2" />
                Open Sign In
              </Button>
              <Button
                variant="outline"
                onClick={() => handleAuthRedirect('/sign-up')}
                className="w-full rounded-xl"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Create Account
              </Button>
              <p className="text-xs text-neutral-400 text-center">
                Social login runs top-level to avoid Shopify iframe auth failures.
              </p>
            </CardContent>
          </Card>
        )}

        {/* ─── SIGNED IN + NOT CONNECTED: Show Connect Flow ─── */}
        {isSignedIn && !connected && (
          <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-xl font-semibold text-gray-900">
                Connect Your Store
              </CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                Link your Shopify store to start tracking your ad performance
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Store className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
                  <input
                    type="text"
                    value={shopDomain}
                    onChange={(e) => setShopDomain(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
                    placeholder="mystore"
                    disabled={connecting}
                    className="w-full pl-10 pr-4 py-2.5 border border-neutral-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 disabled:opacity-50 disabled:bg-neutral-50"
                  />
                </div>
                <Button
                  onClick={handleConnect}
                  disabled={connecting || !shopDomain.trim()}
                  className="rounded-xl"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  {connecting ? 'Connecting...' : 'Connect'}
                </Button>
              </div>

              {shopDomain.trim() && (
                <p className="text-xs text-neutral-500">
                  Will connect: <span className="font-mono">{shopDomain.trim().toLowerCase().replace('.myshopify.com', '')}.myshopify.com</span>
                </p>
              )}

              <p className="text-xs text-neutral-400 text-center">
                You&apos;ll be redirected to Shopify to authorize access
              </p>
            </CardContent>
          </Card>
        )}

        {/* ─── CONNECTED: Show Success ─── */}
        {isSignedIn && connected && (
          <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
            <CardContent className="text-center py-8 space-y-4">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Store Connected</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Your Shopify store is now linked to metricx
                </p>
              </div>
              <Button
                asChild
                className="rounded-xl"
              >
                <Link href="/dashboard" target="_top">
                  Go to Dashboard
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Terms footer */}
        <p className="text-xs text-gray-400 text-center mt-6">
          By continuing, you agree to our{' '}
          <Link href="/terms" className="text-gray-500 hover:text-gray-700 underline">Terms</Link>
          {' '}and{' '}
          <Link href="/privacy" className="text-gray-500 hover:text-gray-700 underline">Privacy Policy</Link>
        </p>
      </div>

      {/* Shop Confirmation Modal */}
      {showConfirmModal && (
        <ShopifyShopModal
          open={showConfirmModal}
          onClose={() => {
            setShowConfirmModal(false);
            setSessionId(null);
          }}
          sessionId={sessionId}
          onSuccess={() => {
            setShowConfirmModal(false);
            setSessionId(null);
            setConnected(true);
          }}
        />
      )}
    </main>
  );
}
