import { useEffect, useRef, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { Store, ExternalLink, CheckCircle, ArrowRight, Loader2, LogIn, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import ShopifyShopModal from '@/components/ShopifyShopModal';
import { buildAuthRedirectUrl } from '@/lib/authRedirect';
import {
  appendShopifyAuthHandoff,
  clearShopifyAuthHandoff,
  createShopifyAuthHandoff,
  getShopifyAuthHandoff,
  shopifyFlowFetch,
} from '@/lib/shopifyAuthHandoff';
import {
  buildShopifyReturnPath,
  isShopifyEmbeddedContext,
  persistShopifyEmbeddedContext,
  verifyEmbeddedShopifySession,
} from '@/lib/shopifyEmbedded';

const SHOPIFY_URL_STRIP_PARAMS = ['shopify_oauth', 'session_id', 'message'];

export default function ShopifyEmbeddedPage() {
  const { isLoaded, isSignedIn } = useUser();
  const [shopDomain, setShopDomain] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);
  const [embeddedReturnBase, setEmbeddedReturnBase] = useState('/shopify');
  const [embeddedSearch, setEmbeddedSearch] = useState('');
  const [handoffId, setHandoffId] = useState(null);
  const [topLevelWindow, setTopLevelWindow] = useState(false);
  const [bootstrappingEmbeddedSession, setBootstrappingEmbeddedSession] = useState(false);
  const sessionBootstrapRef = useRef(false);

  useEffect(() => {
    const search = window.location.search;
    const params = new URLSearchParams(search);
    const appPathname = window.location.pathname;
    const currentUrl = `${appPathname}${search}`;
    const appReturnUrl = buildShopifyReturnPath(appPathname, search, {
      stripParams: SHOPIFY_URL_STRIP_PARAMS,
    });
    const authReturnUrl = buildShopifyReturnPath('/shopify', search, {
      stripParams: SHOPIFY_URL_STRIP_PARAMS,
    });

    persistShopifyEmbeddedContext(search);
    setTopLevelWindow(window.top === window.self);
    setEmbeddedReturnBase(authReturnUrl);
    setEmbeddedSearch(new URL(appReturnUrl, window.location.origin).search);
    setHandoffId(getShopifyAuthHandoff(search));

    const shop = params.get('shop');
    if (shop) {
      setShopDomain(shop.replace('.myshopify.com', ''));
    }

    const oauthStatus = params.get('shopify_oauth');
    const sessionIdParam = params.get('session_id');
    const errorMessage = params.get('message');

    if (oauthStatus === 'confirm' && sessionIdParam) {
      setSessionId(sessionIdParam);
      setShowConfirmModal(true);
      window.history.replaceState({}, '', appReturnUrl);
    } else if (oauthStatus === 'error') {
      setMessage(`Connection failed: ${errorMessage || 'Unknown error'}`);
      setMessageType('error');
      window.history.replaceState({}, '', appReturnUrl);
    } else if (appReturnUrl !== currentUrl) {
      window.history.replaceState({}, '', appReturnUrl);
    }
  }, []);

  useEffect(() => {
    if (!isLoaded || !embeddedSearch || !isShopifyEmbeddedContext(embeddedSearch)) {
      return;
    }

    if (topLevelWindow && !isSignedIn) {
      return;
    }

    if (sessionBootstrapRef.current) {
      return;
    }

    let cancelled = false;
    sessionBootstrapRef.current = true;

    const bootstrapEmbeddedSession = async () => {
      try {
        if (topLevelWindow) {
          setBootstrappingEmbeddedSession(true);

          const activeHandoffId = handoffId || await createShopifyAuthHandoff();
          if (cancelled) {
            return;
          }

          setHandoffId(activeHandoffId);

          const currentPath = appendShopifyAuthHandoff(
            `${window.location.pathname}${window.location.search}`,
            activeHandoffId
          );
          window.history.replaceState({}, '', currentPath);

          await verifyEmbeddedShopifySession({
            search: new URL(currentPath, window.location.origin).search,
          });
          return;
        }

        await verifyEmbeddedShopifySession({ search: embeddedSearch });
      } catch (error) {
        console.error('[shopify] Embedded session bootstrap failed:', error);
        sessionBootstrapRef.current = false;
        clearShopifyAuthHandoff();

        if (!cancelled) {
          setHandoffId(null);
          setMessage('Unable to resume your Shopify session. Please sign in again.');
          setMessageType('error');
        }
      } finally {
        if (!cancelled) {
          setBootstrappingEmbeddedSession(false);
        }
      }
    };

    bootstrapEmbeddedSession();

    return () => {
      cancelled = true;
    };
  }, [embeddedSearch, handoffId, isLoaded, isSignedIn, topLevelWindow]);

  const embeddedReturnUrl = appendShopifyAuthHandoff(embeddedReturnBase, handoffId);
  const isAuthenticatedForShopify = isSignedIn || Boolean(handoffId);

  const handleAuthExpired = () => {
    clearShopifyAuthHandoff();
    setConnecting(false);
    setHandoffId(null);
    setMessage('Your session expired. Please sign in again to continue.');
    setMessageType('error');
  };

  const handleConnect = async () => {
    if (!shopDomain.trim()) {
      setMessage('Please enter your Shopify store domain');
      setMessageType('error');
      return;
    }

    setConnecting(true);
    setMessage(null);
    setMessageType(null);

    try {
      const response = await shopifyFlowFetch('/auth/shopify/authorize-url', {
        method: 'POST',
        body: JSON.stringify({
          shop: shopDomain.trim(),
          redirect_path: embeddedReturnUrl,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          handleAuthExpired();
          setConnecting(false);
          return;
        }

        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to start Shopify authorization');
      }

      const data = await response.json();
      window.top.location.href = data.auth_url;
    } catch (error) {
      setConnecting(false);
      setMessage(error.message || 'Failed to start Shopify authorization');
      setMessageType('error');
    }
  };

  const handleAuthRedirect = (path) => {
    const authUrl = buildAuthRedirectUrl(path, embeddedReturnUrl);
    window.top.location.href = authUrl;
  };

  if (!isLoaded || bootstrappingEmbeddedSession) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 via-white to-gray-50/50">
        <div className="flex flex-col items-center gap-3 text-center px-6">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          {bootstrappingEmbeddedSession ? (
            <p className="text-sm text-gray-500">Returning you to the embedded Shopify app...</p>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">
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

        {!isAuthenticatedForShopify && (
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

        {isAuthenticatedForShopify && !connected && (
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
                    onChange={(event) => setShopDomain(event.target.value)}
                    onKeyDown={(event) => event.key === 'Enter' && handleConnect()}
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

        {isAuthenticatedForShopify && connected && (
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

        <ShopifyShopModal
          open={showConfirmModal}
          onClose={() => {
            setShowConfirmModal(false);
            setSessionId(null);
          }}
          sessionId={sessionId}
          onAuthExpired={handleAuthExpired}
          onSuccess={() => {
            setShowConfirmModal(false);
            setSessionId(null);
            setConnected(true);
            setMessage('Store connected successfully');
            setMessageType('info');
          }}
        />
      </div>
    </main>
  );
}
