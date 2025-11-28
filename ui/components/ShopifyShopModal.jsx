'use client';

import { useState, useEffect } from 'react';
import { Check, X, Store, Globe, Mail, DollarSign } from 'lucide-react';
import { getApiBase } from '../lib/config';

/**
 * ShopifyShopModal Component
 *
 * WHAT: Modal for confirming Shopify store connection after OAuth
 * WHY: Show shop details and get user confirmation before creating connection
 * WHERE USED: Settings page, triggered by ShopifyConnectButton
 *
 * Flow:
 * 1. Fetches shop info from /auth/shopify/shop?session_id=...
 * 2. Displays shop details (name, domain, currency, email)
 * 3. User clicks "Connect Store" to confirm
 * 4. POST /auth/shopify/connect creates the Connection and ShopifyShop records
 *
 * REFERENCES:
 * - backend/app/routers/shopify_oauth.py (get_oauth_shop, connect_shop)
 * - Similar pattern: MetaAccountSelectionModal.jsx
 */
export default function ShopifyShopModal({ open, onClose, sessionId, onSuccess }) {
  const [shop, setShop] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !sessionId) return;

    // Fetch shop info from backend
    const fetchShop = async () => {
      try {
        setLoading(true);
        setError(null);
        const baseUrl = getApiBase();
        const response = await fetch(`${baseUrl}/auth/shopify/shop?session_id=${sessionId}`, {
          credentials: 'include',
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to fetch shop info');
        }

        const data = await response.json();
        setShop(data.shop);
      } catch (err) {
        setError(err.message || 'Failed to load shop information');
      } finally {
        setLoading(false);
      }
    };

    fetchShop();
  }, [open, sessionId]);

  const handleConnect = async () => {
    try {
      setSubmitting(true);
      setError(null);
      const baseUrl = getApiBase();
      const response = await fetch(`${baseUrl}/auth/shopify/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to connect store');
      }

      const data = await response.json();
      onSuccess?.(data);
    } catch (err) {
      setError(err.message || 'Failed to connect store');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white w-full max-w-md rounded-3xl border border-black/5 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-black/5 flex items-center justify-between bg-green-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
              <Store className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-black">Connect Shopify Store</h3>
              <p className="text-sm text-neutral-500">Confirm store details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-black transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8 text-neutral-500">Loading store information...</div>
          ) : error && !shop ? (
            <div className="text-center py-8">
              <div className="text-red-600 mb-4">{error}</div>
              <button
                onClick={onClose}
                className="text-sm text-neutral-600 hover:text-black underline"
              >
                Close and try again
              </button>
            </div>
          ) : shop ? (
            <div className="space-y-4">
              {/* Shop Name */}
              <div className="p-4 bg-neutral-50 rounded-xl border border-neutral-200">
                <div className="text-sm text-neutral-500 mb-1">Store Name</div>
                <div className="text-lg font-semibold text-black">{shop.name}</div>
              </div>

              {/* Shop Details Grid */}
              <div className="grid grid-cols-2 gap-3">
                {/* Domain */}
                <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
                  <div className="flex items-center gap-2 text-neutral-500 text-xs mb-1">
                    <Globe className="w-3 h-3" />
                    Domain
                  </div>
                  <div className="text-sm font-medium text-black truncate">{shop.domain}</div>
                </div>

                {/* Currency */}
                <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200">
                  <div className="flex items-center gap-2 text-neutral-500 text-xs mb-1">
                    <DollarSign className="w-3 h-3" />
                    Currency
                  </div>
                  <div className="text-sm font-medium text-black">{shop.currency || 'USD'}</div>
                </div>

                {/* Email */}
                {shop.email && (
                  <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 col-span-2">
                    <div className="flex items-center gap-2 text-neutral-500 text-xs mb-1">
                      <Mail className="w-3 h-3" />
                      Email
                    </div>
                    <div className="text-sm font-medium text-black">{shop.email}</div>
                  </div>
                )}

                {/* Plan */}
                {shop.plan_name && (
                  <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 col-span-2">
                    <div className="text-neutral-500 text-xs mb-1">Shopify Plan</div>
                    <div className="text-sm font-medium text-black capitalize">{shop.plan_name}</div>
                  </div>
                )}
              </div>

              {/* What we'll sync */}
              <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                <div className="text-sm font-medium text-green-800 mb-2">What we'll sync:</div>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• Orders (revenue, profit tracking)</li>
                  <li>• Products (catalog, COGS for profit)</li>
                  <li>• Customers (LTV calculations)</li>
                </ul>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                  {error}
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-black/5 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-neutral-700 hover:text-black transition-colors"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            onClick={handleConnect}
            disabled={submitting || loading || (!shop && !error)}
            className="px-4 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting ? (
              <>Connecting...</>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Connect Store
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
