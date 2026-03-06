'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { Loader2 } from 'lucide-react';
import {
  clearShopifyAuthHandoff,
  createShopifyAuthHandoff,
  getShopifySessionKey,
} from '@/lib/shopifyAuthHandoff';

function getRedirectTarget() {
  const params = new URLSearchParams(window.location.search);
  const redirectUrl = params.get('redirect_url');

  if (redirectUrl && redirectUrl.startsWith('/')) {
    return redirectUrl;
  }

  return '/shopify';
}

export default function ShopifyAuthReturnPage() {
  const { isLoaded, isSignedIn } = useUser();
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      return;
    }

    let cancelled = false;

    const completeShopifyReturn = async () => {
      const redirectTarget = getRedirectTarget();
      const sessionKey = getShopifySessionKey(redirectTarget);
      const shop = new URL(redirectTarget, window.location.origin).searchParams.get('shop');

      if (!sessionKey) {
        setError('Missing Shopify session. Please reopen the app from Shopify admin.');
        return;
      }

      try {
        clearShopifyAuthHandoff();
        await createShopifyAuthHandoff({
          sessionKey,
          shop,
        });

        if (!cancelled) {
          window.location.replace(redirectTarget);
        }
      } catch (handoffError) {
        if (!cancelled) {
          setError(handoffError.message || 'Failed to resume Shopify session.');
        }
      }
    };

    completeShopifyReturn();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 via-white to-gray-50/50 px-6">
      <div className="flex flex-col items-center gap-4 text-center max-w-md">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <div className="space-y-2">
          <h1 className="text-lg font-semibold text-gray-900">Returning to Shopify</h1>
          <p className="text-sm text-gray-500">
            Finishing your sign-in and reopening the embedded app.
          </p>
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
