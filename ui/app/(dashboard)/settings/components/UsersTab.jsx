'use client';

import { useEffect, useState, useTransition } from 'react';
import { Users, Loader2, Shield, Trash2, UserPlus, Mail, Check, X, Lock, Zap } from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import { currentUser } from '@/lib/workspace';
import { getApiBase } from '@/lib/config';

const ROLE_OPTIONS = [
  { value: 'Admin', label: 'Admin' },
  { value: 'Viewer', label: 'Viewer' },
];

export default function UsersTab({ user, view = 'members', billingTier, billingStatus }) {
  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pending, startTransition] = useTransition();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('Admin');

  const apiBase = getApiBase();
  const workspaceId = user?.active_workspace_id || user?.workspace_id;
  const canManage = user?.memberships?.some((m) => m.workspace_id === workspaceId && (m.role === 'Owner' || m.role === 'Admin'));
  const isOwner = user?.memberships?.some((m) => m.workspace_id === workspaceId && m.role === 'Owner');

  const fetchMembers = () => {
    if (!workspaceId) return;
    startTransition(() => {
      fetch(`${apiBase}/workspaces/${workspaceId}/users`, { credentials: 'include' })
        .then((res) => res.ok ? res.json() : Promise.reject(res))
        .then(setMembers)
        .catch(() => toast.error('Failed to load members'))
        .finally(() => setLoading(false));
    });
  };

  const fetchInvites = () => {
    if (!workspaceId) return;
    startTransition(() => {
      fetch(`${apiBase}/workspaces/me/invites`, { credentials: 'include' })
        .then((res) => res.ok ? res.json() : Promise.reject(res))
        .then(setInvites)
        .catch(() => toast.error('Failed to load invites'))
        .finally(() => setLoading(false));
    });
  };

  useEffect(() => {
    if (!workspaceId) return;
    if (view === 'members') fetchMembers();
    if (view === 'invites') fetchInvites();
  }, [workspaceId, view]);

  const handleInvite = () => {
    if (!email.trim()) return;
    startTransition(() => {
      fetch(`${apiBase}/workspaces/${workspaceId}/invites`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      })
        .then((res) => res.ok ? res.json() : res.text().then((t) => Promise.reject(t)))
        .then(() => {
          toast.success('Invite sent');
          setEmail('');
          fetchInvites();
        })
        .catch((err) => {
          console.error(err);
          toast.error(typeof err === 'string' ? err : 'Failed to send invite');
        });
    });
  };

  const handleRemove = (memberId) => {
    startTransition(() => {
      fetch(`${apiBase}/workspaces/${workspaceId}/members/${memberId}`, {
        method: 'DELETE',
        credentials: 'include',
      })
        .then((res) => res.ok ? res.json() : res.text().then((t) => Promise.reject(t)))
        .then(() => {
          toast.success('Member removed');
          fetchMembers();
        })
        .catch((err) => {
          console.error(err);
          toast.error(typeof err === 'string' ? err : 'Failed to remove member');
        });
    });
  };

  const handleAccept = (inviteId) => {
    startTransition(() => {
      fetch(`${apiBase}/workspaces/invites/${inviteId}/accept`, {
        method: 'POST',
        credentials: 'include',
      })
        .then((res) => res.ok ? res.json() : res.text().then((t) => Promise.reject(t)))
        .then(() => {
          toast.success('Invite accepted');
          fetchInvites();
        })
        .catch((err) => {
          console.error(err);
          toast.error(typeof err === 'string' ? err : 'Failed to accept invite');
        });
    });
  };

  const handleDecline = (inviteId) => {
    startTransition(() => {
      fetch(`${apiBase}/workspaces/invites/${inviteId}/decline`, {
        method: 'POST',
        credentials: 'include',
      })
        .then((res) => res.ok ? res.json() : res.text().then((t) => Promise.reject(t)))
        .then(() => {
          toast.success('Invite declined');
          fetchInvites();
        })
        .catch((err) => {
          console.error(err);
          toast.error(typeof err === 'string' ? err : 'Failed to decline invite');
        });
    });
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400 mx-auto" />
      </div>
    );
  }

  if (view === 'invites') {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Mail className="w-5 h-5 text-neutral-600" />
          <h3 className="text-lg font-semibold text-neutral-900">Your Invites</h3>
        </div>
        {invites.length === 0 ? (
          <div className="p-4 border border-neutral-200 rounded-xl text-neutral-600">No pending invites.</div>
        ) : (
          <div className="space-y-2">
            {invites.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between p-3 border border-neutral-200 rounded-xl bg-white">
                <div>
                  <div className="font-semibold text-neutral-900">{inv.workspace_name || inv.workspace_id}</div>
                  <div className="text-xs text-neutral-500 capitalize">{inv.role.toLowerCase()}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleAccept(inv.id)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-700 text-sm font-semibold"
                    disabled={pending}
                  >
                    <Check className="w-4 h-4 inline mr-1" /> Accept
                  </button>
                  <button
                    onClick={() => handleDecline(inv.id)}
                    className="px-3 py-1.5 rounded-lg bg-red-100 text-red-700 text-sm font-semibold"
                    disabled={pending}
                  >
                    <X className="w-4 h-4 inline mr-1" /> Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (!workspaceId) {
    return <div className="p-4 border border-neutral-200 rounded-xl text-neutral-600">No workspace context.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Users className="w-5 h-5 text-neutral-600" />
        <h3 className="text-lg font-semibold text-neutral-900">Workspace Members</h3>
      </div>

      {/* Free tier restriction message (only shown for expired trial / free tier, not during active trial) */}
      {canManage && billingTier === 'free' && billingStatus !== 'trialing' && (
        <div className="p-4 border border-amber-200 bg-amber-50 rounded-xl flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
            <Lock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800">Team invites require a paid plan</p>
            <p className="text-xs text-amber-600 mt-1">Upgrade to invite team members and collaborate on your ad analytics.</p>
            <Link
              href="/subscribe"
              className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 transition-colors"
            >
              <Zap className="w-3.5 h-3.5" />
              Upgrade Now
            </Link>
          </div>
        </div>
      )}

      {/* Trial tier info message - show trial member limit */}
      {canManage && billingStatus === 'trialing' && (
        <div className="p-4 border border-blue-200 bg-blue-50 rounded-xl flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-800">Trial: 3 team members max</p>
            <p className="text-xs text-blue-600 mt-1">
              Upgrade to invite up to 10 team members and unlock all features.
            </p>
          </div>
        </div>
      )}

      {/* Invite form - for paid tier or trialing users with manage permissions */}
      {canManage && (billingTier !== 'free' || billingStatus === 'trialing') && (
        <div className="p-4 border border-neutral-200 rounded-xl bg-white flex flex-col md:flex-row gap-3 items-center">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 text-sm"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="px-3 py-2 rounded-lg border border-neutral-300 text-sm"
          >
            {ROLE_OPTIONS.filter((o) => o.value !== 'Owner').map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <button
            onClick={handleInvite}
            disabled={pending}
            className="px-3 py-2 rounded-lg bg-cyan-600 text-white text-sm font-semibold flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            Invite
          </button>
        </div>
      )}

      <div className="space-y-2">
        {members.map((m) => (
          <div key={m.user_id} className="p-4 border border-neutral-200 rounded-xl bg-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-700 font-semibold">
                {m.user_name?.charAt(0)?.toUpperCase() || 'M'}
              </div>
              <div>
                <div className="font-semibold text-neutral-900">{m.user_name || m.user_id}</div>
                <div className="text-xs text-neutral-500">{m.user_email || ''}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 rounded-full text-xs bg-neutral-100 text-neutral-700 capitalize">{m.role.toLowerCase()}</span>
              {isOwner && m.role !== 'Owner' && (
                <button
                  onClick={() => handleRemove(m.user_id)}
                  className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"
                  disabled={pending}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
        {members.length === 0 && (
          <div className="p-4 border border-neutral-200 rounded-xl text-neutral-600">No members yet.</div>
        )}
      </div>
    </div>
  );
}
