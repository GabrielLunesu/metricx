import { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, CheckCircle, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  buildShopifyReturnPath,
  isShopifyEmbeddedContext,
  persistShopifyEmbeddedContext,
  verifyEmbeddedShopifySession,
} from '@/lib/shopifyEmbedded';

const SHOPIFY_URL_STRIP_PARAMS = ['shopify_oauth', 'session_id', 'message'];

function buildShopifyLinkUrl(shop, returnTo) {
  const params = new URLSearchParams();

  if (shop) {
    params.set('shop', shop);
  }

  if (returnTo) {
    params.set('return_to', returnTo);
  }

  const query = params.toString();
  return query ? `/shopify/link?${query}` : '/shopify/link';
}

export default function ShopifyEmbeddedPage() {
  const [state, setState] = useState({
    status: 'loading',
    error: null,
    embeddedStatus: null,
    linkUrl: '/shopify/link',
  });

  useEffect(() => {
    const search = window.location.search;
    const params = new URLSearchParams(search);
    const returnTo = buildShopifyReturnPath('/shopify', search, {
      stripParams: SHOPIFY_URL_STRIP_PARAMS,
    });
    const shopParam = params.get('shop');

    persistShopifyEmbeddedContext(search);
    setState((current) => ({
      ...current,
      linkUrl: buildShopifyLinkUrl(shopParam, returnTo),
    }));

    if (!isShopifyEmbeddedContext(search)) {
      setState((current) => ({
        ...current,
        status: 'error',
        error: 'Open this app from Shopify admin to continue.',
      }));
      return;
    }

    let cancelled = false;

    const loadEmbeddedStatus = async () => {
      try {
        const embeddedStatus = await verifyEmbeddedShopifySession({
          endpoint: '/api/auth/shopify/embedded-status',
          search,
        });

        if (cancelled) {
          return;
        }

        setState({
          status: 'ready',
          error: null,
          embeddedStatus,
          linkUrl: buildShopifyLinkUrl(embeddedStatus.shop || shopParam, returnTo),
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setState((current) => ({
          ...current,
          status: 'error',
          error: error.message || 'Unable to verify your Shopify session.',
        }));
      }
    };

    loadEmbeddedStatus();

    return () => {
      cancelled = true;
    };
  }, []);

  const { status, error, embeddedStatus, linkUrl } = state;
  const shopLabel =
    embeddedStatus?.shop_name ||
    embeddedStatus?.shop ||
    'your Shopify store';

  if (status === 'loading') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-gray-50 via-white to-gray-50/50">
        <div className="flex flex-col items-center gap-3 px-6 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          <p className="text-sm text-gray-500">Checking your Shopify connection...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-b from-gray-50 via-white to-gray-50/50 p-6">
      <div className="pointer-events-none absolute left-1/2 top-1/4 h-[800px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent blur-3xl" />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Image
            src="/logo.png"
            alt="metricx"
            width={180}
            height={50}
            className="h-12 w-auto"
            priority
          />
        </div>

        {error ? (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </div>
        ) : null}

        {embeddedStatus?.linked ? (
          <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
            <CardContent className="space-y-4 py-8 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{shopLabel} is connected</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Linked to {embeddedStatus.workspace_name || 'your Metricx workspace'}.
                </p>
              </div>
              <Button asChild className="w-full rounded-xl">
                <Link href="/dashboard" target="_top">
                  Open Metricx
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="w-full rounded-xl">
                <Link href={linkUrl} target="_top">
                  Manage account link
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
            <CardHeader className="pb-2 text-center">
              <CardTitle className="text-xl font-semibold text-gray-900">
                Finish Setup In Browser
              </CardTitle>
              <p className="mt-1 text-sm text-gray-500">
                Sign in to Metricx and link {shopLabel} in a full browser tab, then return here.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button asChild className="w-full rounded-xl">
                <Link href={linkUrl} target="_top">
                  Continue setup
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <p className="text-center text-xs text-neutral-400">
                The embedded app now uses Shopify session tokens only. Account linking happens outside the iframe.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
