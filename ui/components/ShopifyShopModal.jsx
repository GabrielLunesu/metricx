'use client';

import { useEffect, useState } from 'react';
import { Check, X, Store, Globe, Mail, DollarSign } from 'lucide-react';
import { getApiBase } from '../lib/config';
import { authFetch } from '../lib/api';

export default function ShopifyShopModal({
  open,
  onClose,
  sessionId,
  onSuccess,
}) {
  const [shop, setShop] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !sessionId) {
      return;
    }

    let cancelled = false;

    const fetchShop = async () => {
      try {
        setLoading(true);
        setError(null);

        const baseUrl = getApiBase();
        const response = await authFetch(`${baseUrl}/auth/shopify/shop?session_id=${sessionId}`, {
          method: 'GET',
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to fetch shop info');
        }

        const data = await response.json();
        if (!cancelled) {
          setShop(data.shop);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load shop information');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchShop();

    return () => {
      cancelled = true;
    };
  }, [open, sessionId]);

  const handleConnect = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const baseUrl = getApiBase();
      const response = await authFetch(`${baseUrl}/auth/shopify/connect`, {
        method: 'POST',
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

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md overflow-hidden rounded-3xl border border-black/5 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-black/5 bg-green-50 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100">
              <Store className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-black">Connect Shopify Store</h3>
              <p className="text-sm text-neutral-500">Confirm store details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-500 transition-colors hover:text-black"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="py-8 text-center text-neutral-500">Loading store information...</div>
          ) : error && !shop ? (
            <div className="py-8 text-center">
              <div className="mb-4 text-red-600">{error}</div>
              <button
                onClick={onClose}
                className="text-sm text-neutral-600 underline hover:text-black"
              >
                Close and try again
              </button>
            </div>
          ) : shop ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                <div className="mb-1 text-sm text-neutral-500">Store Name</div>
                <div className="text-lg font-semibold text-black">{shop.name}</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <div className="mb-1 flex items-center gap-2 text-xs text-neutral-500">
                    <Globe className="h-3 w-3" />
                    Domain
                  </div>
                  <div className="truncate text-sm font-medium text-black">{shop.domain}</div>
                </div>

                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <div className="mb-1 flex items-center gap-2 text-xs text-neutral-500">
                    <DollarSign className="h-3 w-3" />
                    Currency
                  </div>
                  <div className="text-sm font-medium text-black">{shop.currency || 'USD'}</div>
                </div>

                {shop.email ? (
                  <div className="col-span-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    <div className="mb-1 flex items-center gap-2 text-xs text-neutral-500">
                      <Mail className="h-3 w-3" />
                      Email
                    </div>
                    <div className="text-sm font-medium text-black">{shop.email}</div>
                  </div>
                ) : null}

                {shop.plan_name ? (
                  <div className="col-span-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    <div className="mb-1 text-xs text-neutral-500">Shopify Plan</div>
                    <div className="text-sm font-medium capitalize text-black">{shop.plan_name}</div>
                  </div>
                ) : null}
              </div>

              <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                <div className="mb-2 text-sm font-medium text-green-800">What we&apos;ll sync:</div>
                <ul className="space-y-1 text-sm text-green-700">
                  <li>• Orders (revenue, profit tracking)</li>
                  <li>• Products (catalog, COGS for profit)</li>
                  <li>• Customers (LTV calculations)</li>
                </ul>
              </div>

              {error ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                  {error}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-black/5 px-6 py-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:text-black"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            onClick={handleConnect}
            disabled={submitting || loading || (!shop && !error)}
            className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>Connecting...</>
            ) : (
              <>
                <Check className="h-4 w-4" />
                Connect Store
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
