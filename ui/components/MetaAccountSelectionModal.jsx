'use client';

import { useState, useEffect } from 'react';
import { Check, X } from 'lucide-react';

import { getApiBase } from '../lib/config';

/**
 * MetaAccountSelectionModal Component
 * 
 * WHAT: Modal for selecting which Meta ad accounts to connect
 * WHY: Allow users to choose specific accounts when multiple are available
 * WHERE USED: Settings page, triggered by MetaConnectButton
 */
export default function MetaAccountSelectionModal({
  open,
  onClose,
  sessionId,
  onSuccess,
  existingConnections = [] // Pass existing connections to show which are already connected
}) {
  const [accounts, setAccounts] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Create a set of existing account IDs for quick lookup
  const existingAccountIds = new Set(
    existingConnections
      .filter(c => c.provider === 'meta')
      .map(c => c.external_account_id)
  );

  useEffect(() => {
    if (!open || !sessionId) return;

    // Fetch accounts from backend
    const fetchAccounts = async () => {
      try {
        setLoading(true);
        setError(null);
        const baseUrl = getApiBase();
        const response = await fetch(`${baseUrl}/auth/meta/accounts?session_id=${sessionId}`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch accounts');
        }

        const data = await response.json();
        setAccounts(data.accounts || []);

        // Pre-select all accounts by default
        if (data.accounts && data.accounts.length > 0) {
          setSelectedIds(new Set(data.accounts.map(acc => acc.id)));
        }
      } catch (err) {
        setError(err.message || 'Failed to load accounts');
      } finally {
        setLoading(false);
      }
    };

    fetchAccounts();
  }, [open, sessionId]);

  const handleToggle = (accountId) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(accountId)) {
        next.delete(accountId);
      } else {
        next.add(accountId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === accounts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(accounts.map(acc => acc.id)));
    }
  };

  const handleSubmit = async () => {
    if (selectedIds.size === 0) {
      setError('Please select at least one account');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const baseUrl = getApiBase();
      const response = await fetch(`${baseUrl}/auth/meta/connect-selected`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          selections: Array.from(selectedIds).map(id => ({
            account_id: id,
            pixel_id: null,  // Pixel selection can be added later
          })),
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        // FastAPI validation errors return detail as array, handle both formats
        const detail = errorData.detail;
        const errorMessage = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map(e => e.msg || e).join(', ')
            : 'Failed to connect accounts';
        throw new Error(errorMessage);
      }

      const data = await response.json();
      onSuccess?.(data);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to connect selected accounts');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white w-full max-w-2xl rounded-3xl border border-black/5 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 border-b border-black/5 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-black">Select Meta Ad Accounts</h3>
            <p className="text-sm text-neutral-500 mt-1">
              Choose which accounts you want to connect to metricx
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-black transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-8 text-neutral-500">Loading accounts...</div>
          ) : error && !accounts.length ? (
            <div className="text-center py-8 text-red-600">{error}</div>
          ) : (
            <div className="space-y-4">
              {/* Select All */}
              <div className="flex items-center justify-between pb-2 border-b">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === accounts.length && accounts.length > 0}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded border-neutral-300"
                  />
                  <span className="text-sm font-medium">
                    {selectedIds.size === accounts.length ? 'Deselect All' : 'Select All'}
                    ({selectedIds.size} of {accounts.length})
                  </span>
                </label>
              </div>

              {/* Ad Accounts */}
              {accounts.map(acc => {
                const accountId = acc.account_id || acc.id.replace('act_', '');
                const isAlreadyConnected = existingAccountIds.has(accountId);

                return (
                  <label
                    key={acc.id}
                    className={`flex items-center gap-3 p-3 border rounded-lg ${isAlreadyConnected
                      ? 'border-blue-200 bg-blue-50 cursor-default'
                      : 'border-neutral-200 cursor-pointer hover:bg-neutral-50'
                      }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(acc.id)}
                      onChange={() => handleToggle(acc.id)}
                      disabled={isAlreadyConnected}
                      className="w-4 h-4 rounded border-neutral-300 disabled:opacity-50"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="font-medium text-sm">{acc.name}</div>
                        {isAlreadyConnected && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                            Already Connected
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-neutral-500">
                        Ad Account • {acc.id}
                        {acc.currency && ` • ${acc.currency}`}
                        {acc.timezone && ` • ${acc.timezone}`}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-black/5 flex items-center justify-between">
          {error && (
            <div className="text-sm text-red-600 flex-1">{error}</div>
          )}
          <div className="flex gap-3 ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-neutral-700 hover:text-black transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || selectedIds.size === 0}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? (
                <>Connecting...</>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Connect {selectedIds.size} Account{selectedIds.size !== 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

