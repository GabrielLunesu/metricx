'use client';

import { useEffect, useState } from 'react';
import { ExternalLink, Store } from 'lucide-react';
import ShopifyShopModal from './ShopifyShopModal';
import { getApiBase } from '../lib/config';

const SHOPIFY_OAUTH_QUERY_KEYS = ['shopify_oauth', 'message', 'session_id'];

function normalizeShopDomain(input) {
  let normalized = input.trim().toLowerCase();
  normalized = normalized.replace(/^https?:\/\//, '');
  normalized = normalized.split('/')[0];

  if (!normalized.includes('.myshopify.com') && !normalized.includes('.')) {
    return `${normalized}.myshopify.com`;
  }

  return normalized;
}

function buildCleanCallbackUrl() {
  const params = new URLSearchParams(window.location.search);

  for (const key of SHOPIFY_OAUTH_QUERY_KEYS) {
    params.delete(key);
  }

  const query = params.toString();
  return query ? `${window.location.pathname}?${query}` : window.location.pathname;
}

export default function ShopifyConnectButton({
  onConnectionComplete,
  initialShopDomain = '',
  lockShopDomain = false,
  redirectPath = null,
  buttonLabel = 'Connect',
  helperText = "You'll be redirected to Shopify to authorize access to your store data.",
}) {
  const [shopDomain, setShopDomain] = useState(initialShopDomain);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    setShopDomain(initialShopDomain);
  }, [initialShopDomain]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthStatus = params.get('shopify_oauth');
    const errorMessage = params.get('message');
    const sessionIdParam = params.get('session_id');

    if (oauthStatus === 'confirm' && sessionIdParam) {
      setSessionId(sessionIdParam);
      setShowConfirmModal(true);
      window.history.replaceState({}, '', buildCleanCallbackUrl());
      return;
    }

    if (oauthStatus === 'success') {
      setMessage('Shopify store connected successfully!');
      setMessageType('success');
      window.history.replaceState({}, '', buildCleanCallbackUrl());
      onConnectionComplete?.();
      return;
    }

    if (oauthStatus === 'error') {
      const errorMessages = {
        missing_code: 'Authorization failed. No authorization code received.',
        missing_shop: 'Shop parameter missing from Shopify response.',
        missing_state: 'OAuth state parameter missing. Please try again.',
        invalid_state: 'Invalid OAuth state. Please try again.',
        shop_mismatch: 'Shop mismatch detected. Please try again.',
        invalid_workspace: 'Invalid workspace. Please try again.',
        token_exchange_failed: 'Failed to exchange authorization code for tokens.',
        shop_fetch_failed: 'Failed to fetch shop information from Shopify.',
        redis_unavailable: 'Temporary Shopify setup issue. Please try again.',
        access_denied: 'Access denied. You did not authorize the app.',
      };

      setMessage(
        errorMessages[errorMessage] || `Connection failed: ${errorMessage || 'Unknown error'}`
      );
      setMessageType('error');
      window.history.replaceState({}, '', buildCleanCallbackUrl());
    }
  }, [onConnectionComplete]);

  const handleConnect = () => {
    if (!shopDomain.trim()) {
      setMessage('Please enter your Shopify store domain');
      setMessageType('error');
      return;
    }

    setConnecting(true);
    setMessage('Redirecting to Shopify...');
    setMessageType('info');

    const baseUrl = getApiBase();
    const authorizeUrl = new URL(`${baseUrl}/auth/shopify/authorize`, window.location.origin);
    authorizeUrl.searchParams.set('shop', shopDomain.trim());

    if (redirectPath) {
      authorizeUrl.searchParams.set('redirect_path', redirectPath);
    }

    window.location.href = authorizeUrl.toString();
  };

  return (
    <div>
      {message && (
        <div
          className={`mb-4 rounded-lg border p-3 text-sm ${
            messageType === 'success'
              ? 'border-green-200 bg-green-50 text-green-800'
              : messageType === 'error'
              ? 'border-red-200 bg-red-50 text-red-800'
              : 'border-blue-200 bg-blue-50 text-blue-800'
          }`}
        >
          {message}
        </div>
      )}

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Store className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input
            type="text"
            value={shopDomain}
            onChange={(event) => setShopDomain(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleConnect()}
            placeholder="mystore or mystore.myshopify.com"
            disabled={connecting || lockShopDomain}
            className="w-full rounded-lg border border-neutral-300 py-2 pl-10 pr-4 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-200 disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:opacity-70"
          />
        </div>
        <button
          onClick={handleConnect}
          disabled={connecting || !shopDomain.trim()}
          className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ExternalLink className="h-4 w-4" />
          {connecting ? 'Connecting...' : buttonLabel}
        </button>
      </div>

      {shopDomain.trim() ? (
        <p className="mt-2 text-xs text-neutral-500">
          Will connect: <span className="font-mono">{normalizeShopDomain(shopDomain)}</span>
        </p>
      ) : null}

      <p className="mt-2 text-xs text-neutral-500">{helperText}</p>

      <ShopifyShopModal
        open={showConfirmModal}
        onClose={() => {
          setShowConfirmModal(false);
          setSessionId(null);
        }}
        sessionId={sessionId}
        onSuccess={(data) => {
          setMessage('Shopify store connected successfully!');
          setMessageType('success');
          setShowConfirmModal(false);
          setSessionId(null);
          onConnectionComplete?.(data);
        }}
      />
    </div>
  );
}
