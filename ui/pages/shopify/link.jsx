import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import Head from 'next/head';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, ExternalLink, Loader2, LogIn, UserPlus } from 'lucide-react';
import ShopifyConnectButton from '@/components/ShopifyConnectButton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { buildAuthRedirectUrl, getSafeRedirectPath } from '@/lib/authRedirect';

function getPageState() {
  const params = new URLSearchParams(window.location.search);
  const returnTo = getSafeRedirectPath(params.get('return_to'), '/shopify');

  return {
    currentPath: `${window.location.pathname}${window.location.search}`,
    returnTo,
    shop: params.get('shop') || '',
  };
}

export default function ShopifyLinkPage() {
  const { isLoaded, isSignedIn } = useUser();
  const [pageState, setPageState] = useState({
    currentPath: '/shopify/link',
    returnTo: '/shopify',
    shop: '',
  });
  const [pageReady, setPageReady] = useState(false);
  const [connectionResult, setConnectionResult] = useState(null);

  useEffect(() => {
    setPageState(getPageState());
    setPageReady(true);
  }, []);

  const signInUrl = buildAuthRedirectUrl('/sign-in', pageState.currentPath);
  const signUpUrl = buildAuthRedirectUrl('/sign-up', pageState.currentPath);

  return (
    <>
      <Head>
        <title>metricx - Shopify Link</title>
      </Head>

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

          {!pageReady || !isLoaded ? (
            <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
              <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                <p className="text-sm text-gray-500">Loading your account…</p>
              </CardContent>
            </Card>
          ) : !isSignedIn ? (
            <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-xl font-semibold text-gray-900">
                  Sign In To Link Your Store
                </CardTitle>
                <p className="mt-1 text-sm text-gray-500">
                  Continue in your browser, then come back to Shopify once the store is linked.
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button asChild className="w-full rounded-xl">
                  <Link href={signInUrl}>
                    <LogIn className="mr-2 h-4 w-4" />
                    Open Sign In
                  </Link>
                </Button>
                <Button asChild variant="outline" className="w-full rounded-xl">
                  <Link href={signUpUrl}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Create Account
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : connectionResult ? (
            <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-xl font-semibold text-gray-900">
                  Store Linked Successfully
                </CardTitle>
                <p className="mt-1 text-sm text-gray-500">
                  {connectionResult.shop_name || pageState.shop || 'Your Shopify store'} is now connected to Metricx.
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button asChild className="w-full rounded-xl">
                  <Link href={pageState.returnTo}>
                    Return to Shopify
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" className="w-full rounded-xl">
                  <Link href="/dashboard">
                    Open Metricx Dashboard
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-gray-200/60 shadow-xl shadow-gray-200/40">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-xl font-semibold text-gray-900">
                  Link Your Shopify Store
                </CardTitle>
                <p className="mt-1 text-sm text-gray-500">
                  {pageState.shop
                    ? `Authorize ${pageState.shop} and confirm the connection to finish Shopify setup.`
                    : 'Authorize your Shopify store and confirm the connection to finish setup.'}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <ShopifyConnectButton
                  initialShopDomain={pageState.shop}
                  lockShopDomain={Boolean(pageState.shop)}
                  redirectPath={pageState.currentPath}
                  buttonLabel="Authorize Shopify"
                  helperText="We’ll send you to Shopify for consent, then back here to confirm the store."
                  onConnectionComplete={setConnectionResult}
                />

                <p className="text-center text-xs text-neutral-400">
                  After the store is connected, use the return button below to reopen the embedded app in Shopify admin.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </>
  );
}
