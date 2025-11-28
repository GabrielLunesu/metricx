'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, Store } from 'lucide-react';
import ShopifyShopModal from './ShopifyShopModal';
import { getApiBase } from '../lib/config';

/**
 * ShopifyConnectButton Component
 *
 * WHAT: Button and input that initiates Shopify OAuth flow
 * WHY: Allow users to connect their Shopify stores via OAuth
 * WHERE USED: Settings page
 *
 * Flow:
 * 1. User enters shop domain (e.g., "mystore" or "mystore.myshopify.com")
 * 2. Click "Connect" redirects to /auth/shopify/authorize?shop=...
 * 3. After OAuth, redirected with shopify_oauth=confirm&session_id=xyz
 * 4. ShopifyShopModal shows shop info for confirmation
 * 5. User confirms, POST /auth/shopify/connect creates the connection
 *
 * REFERENCES:
 * - backend/app/routers/shopify_oauth.py
 * - Similar pattern: MetaConnectButton.jsx
 */
export default function ShopifyConnectButton({ onConnectionComplete }) {
  const [shopDomain, setShopDomain] = useState('');
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null); // 'success' | 'error' | 'info'
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    // Check for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    const oauthStatus = params.get('shopify_oauth');
    const errorMessage = params.get('message');
    const sessionIdParam = params.get('session_id');

    if (oauthStatus === 'confirm' && sessionIdParam) {
      // Show shop confirmation modal
      setSessionId(sessionIdParam);
      setShowConfirmModal(true);

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);
    } else if (oauthStatus === 'success') {
      setMessage('Shopify store connected successfully!');
      setMessageType('success');

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);

      // Notify parent to refresh connections
      if (onConnectionComplete) {
        onConnectionComplete();
      }

      // Clear message after 5 seconds
      setTimeout(() => {
        setMessage(null);
        setMessageType(null);
      }, 5000);
    } else if (oauthStatus === 'error') {
      const errorMessages = {
        missing_code: 'Authorization failed. No authorization code received.',
        missing_shop: 'Shop parameter missing from Shopify response.',
        missing_state: 'OAuth state parameter missing. Please try again.',
        invalid_state: 'Invalid OAuth state. Please try again.',
        shop_mismatch: 'Shop mismatch detected. Please try again.',
        invalid_workspace: 'Invalid workspace. Please try again.',
        token_exchange_failed: 'Failed to exchange authorization code for tokens.',
        shop_info_failed: 'Failed to fetch shop information from Shopify.',
        session_save_failed: 'Failed to save OAuth session. Please try again.',
        access_denied: 'Access denied. You did not authorize the app.',
      };

      setMessage(
        errorMessages[errorMessage] || `Connection failed: ${errorMessage || 'Unknown error'}`
      );
      setMessageType('error');

      // Clear URL parameters
      window.history.replaceState({}, '', window.location.pathname);

      // Clear error message after 10 seconds
      setTimeout(() => {
        setMessage(null);
        setMessageType(null);
      }, 10000);
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

    // Redirect to backend OAuth authorize endpoint with shop parameter
    const baseUrl = getApiBase();
    const encodedShop = encodeURIComponent(shopDomain.trim());
    window.location.href = `${baseUrl}/auth/shopify/authorize?shop=${encodedShop}`;
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleConnect();
    }
  };

  const normalizeShopDomain = (input) => {
    // Show user what domain will be used
    let normalized = input.trim().toLowerCase();

    // Remove protocol if present
    normalized = normalized.replace(/^https?:\/\//, '');

    // Remove trailing slashes and paths
    normalized = normalized.split('/')[0];

    // Add .myshopify.com if not present
    if (!normalized.includes('.myshopify.com') && !normalized.includes('.')) {
      return `${normalized}.myshopify.com`;
    }

    return normalized;
  };

  return (
    <div>
      {message && (
        <div
          className={`mb-4 p-3 rounded-lg text-sm ${
            messageType === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : messageType === 'error'
              ? 'bg-red-50 text-red-800 border border-red-200'
              : 'bg-blue-50 text-blue-800 border border-blue-200'
          }`}
        >
          {message}
        </div>
      )}

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Store className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            value={shopDomain}
            onChange={(e) => setShopDomain(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="mystore or mystore.myshopify.com"
            disabled={connecting}
            className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-200 focus:border-green-400 disabled:opacity-50 disabled:bg-neutral-50"
          />
        </div>
        <button
          onClick={handleConnect}
          disabled={connecting || !shopDomain.trim()}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ExternalLink className="w-4 h-4" />
          {connecting ? 'Connecting...' : 'Connect'}
        </button>
      </div>

      {shopDomain.trim() && (
        <p className="mt-2 text-xs text-neutral-500">
          Will connect: <span className="font-mono">{normalizeShopDomain(shopDomain)}</span>
        </p>
      )}

      <p className="mt-2 text-xs text-neutral-500">
        You'll be redirected to Shopify to authorize access to your store data.
      </p>

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
            setMessage('Shopify store connected successfully!');
            setMessageType('success');
            setShowConfirmModal(false);
            setSessionId(null);

            // Notify parent to refresh connections
            if (onConnectionComplete) {
              onConnectionComplete();
            }

            // Clear message after 5 seconds
            setTimeout(() => {
              setMessage(null);
              setMessageType(null);
            }, 5000);
          }}
        />
      )}
    </div>
  );
}
