'use client';

import { useState, useEffect } from 'react';
import { Check, X, Building2 } from 'lucide-react';

import { getApiBase } from '../lib/config';

/**
 * GoogleAccountSelectionModal Component
 * 
 * WHAT: Modal for selecting which Google Ads accounts to connect
 * WHY: Allow users to choose specific accounts when multiple are available (MCC scenario)
 * WHERE USED: Settings page, triggered by GoogleConnectButton
 */
export default function GoogleAccountSelectionModal({
  open,
  onClose,
  sessionId,
  onSuccess
}) {
  const [accounts, setAccounts] = useState([]);
  const [mccs, setMccs] = useState([]);  // All MCCs, even without children
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !sessionId) return;

    // Fetch accounts from backend
    const fetchAccounts = async () => {
      try {
        setLoading(true);
        setError(null);
        const baseUrl = getApiBase();
        const response = await fetch(`${baseUrl}/auth/google/accounts?session_id=${sessionId}`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch accounts');
        }

        const data = await response.json();
        setAccounts(data.accounts || []);
        setMccs(data.mccs || []);  // Store MCC info

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
      const response = await fetch(`${baseUrl}/auth/google/connect-selected`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          account_ids: Array.from(selectedIds),
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to connect accounts');
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

  // Group ad accounts by their parent MCC
  const accountsByParent = {};

  // Initialize all MCCs (even if they have no children)
  mccs.forEach(mcc => {
    accountsByParent[mcc.id] = {
      name: mcc.name,
      id: mcc.id,
      accounts: []
    };
  });

  // Group accounts under their parent MCCs
  accounts.forEach(acc => {
    const parentKey = acc.parent_id || 'standalone';
    if (!accountsByParent[parentKey]) {
      accountsByParent[parentKey] = {
        name: acc.parent_name,
        id: acc.parent_id,
        accounts: []
      };
    }
    accountsByParent[parentKey].accounts.push(acc);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white w-full max-w-2xl rounded-3xl border border-black/5 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 border-b border-black/5 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-black">Select Google Ads Accounts</h3>
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

              {/* Accounts grouped by parent MCC */}
              {Object.entries(accountsByParent).filter(([key]) => key !== 'standalone').map(([parentId, group]) => (
                <div key={parentId} className="border border-neutral-200 rounded-lg overflow-hidden">
                  {/* MCC Header (non-clickable, just informational) */}
                  <div className="flex items-center gap-3 p-3 bg-neutral-50">
                    <Building2 className="w-5 h-5 text-blue-600" />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{group.name || 'MCC Account'}</div>
                      <div className="text-xs text-neutral-500">
                        MCC Account • {parentId} • {group.accounts.length} ad account{group.accounts.length !== 1 ? 's' : ''}
                        {group.accounts.length === 0 && ' (no enabled ad accounts)'}
                      </div>
                    </div>
                  </div>

                  {/* Child Ad Accounts */}
                  {group.accounts.length > 0 ? (
                    <div className="border-t border-neutral-200 bg-white">
                      {group.accounts.map(acc => (
                        <label
                          key={acc.id}
                          className="flex items-center gap-3 p-3 pl-10 cursor-pointer hover:bg-neutral-50 border-b border-neutral-100 last:border-b-0"
                        >
                          <input
                            type="checkbox"
                            checked={selectedIds.has(acc.id)}
                            onChange={() => handleToggle(acc.id)}
                            className="w-4 h-4 rounded border-neutral-300"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{acc.name}</div>
                            <div className="text-xs text-neutral-500">
                              Ad Account • {acc.id}
                              {acc.currency && ` • ${acc.currency}`}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="border-t border-neutral-200 bg-white p-3 pl-10 text-sm text-neutral-500">
                      No enabled ad accounts available under this MCC
                    </div>
                  )}
                </div>
              ))}

              {/* Standalone Ad Accounts (no parent MCC) */}
              {accountsByParent['standalone']?.accounts.map(acc => (
                <label
                  key={acc.id}
                  className="flex items-center gap-3 p-3 border border-neutral-200 rounded-lg cursor-pointer hover:bg-neutral-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(acc.id)}
                    onChange={() => handleToggle(acc.id)}
                    className="w-4 h-4 rounded border-neutral-300"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{acc.name}</div>
                    <div className="text-xs text-neutral-500">
                      Ad Account • {acc.id}
                      {acc.currency && ` • ${acc.currency}`}
                    </div>
                  </div>
                </label>
              ))}
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

