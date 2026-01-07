'use client';

/**
 * Admin Dashboard Page
 *
 * WHAT: Platform-level admin dashboard for user and workspace management
 * WHY: Superusers need to manage users, delete accounts, grant premium
 *
 * SECURITY: Requires is_superuser flag (checked on load, redirects if not)
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Shield,
  Users,
  Building2,
  Loader2,
  Search,
  Trash2,
  Crown,
  AlertTriangle,
  Check,
  X,
} from 'lucide-react';
import {
  getAdminStatus,
  getUsers,
  getWorkspaces,
  deleteUser,
  toggleSuperuser,
  updateBillingTier,
} from '@/lib/adminApiClient';

// Simple tab component
function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? 'bg-neutral-900 text-white'
          : 'text-neutral-600 hover:bg-neutral-100'
      }`}
    >
      {children}
    </button>
  );
}

// Badge component
function Badge({ variant = 'default', children }) {
  const variants = {
    default: 'bg-neutral-100 text-neutral-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    danger: 'bg-red-100 text-red-700',
    premium: 'bg-purple-100 text-purple-700',
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${variants[variant]}`}>
      {children}
    </span>
  );
}

// Confirmation modal
function ConfirmModal({ open, onClose, onConfirm, title, message, confirmText = 'Confirm', danger = false }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4">
          {danger && (
            <div className="p-2 bg-red-100 rounded-full">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
          )}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
            <p className="mt-2 text-sm text-neutral-600">{message}</p>
          </div>
        </div>
        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium rounded-lg ${
              danger
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-neutral-900 text-white hover:bg-neutral-800'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

// Users Table Component
function UsersTable({ users, onDelete, onToggleSuperuser, loading }) {
  const [deleteModal, setDeleteModal] = useState({ open: false, user: null });
  const [actionLoading, setActionLoading] = useState(null);

  const handleDelete = async () => {
    if (!deleteModal.user) return;
    setActionLoading(deleteModal.user.id);
    try {
      await onDelete(deleteModal.user.id);
    } finally {
      setActionLoading(null);
      setDeleteModal({ open: false, user: null });
    }
  };

  const handleToggleSuperuser = async (user) => {
    setActionLoading(user.id);
    try {
      await onToggleSuperuser(user.id, !user.is_superuser);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        No users found
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">User</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Workspaces</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Status</th>
              <th className="text-right py-3 px-4 text-sm font-medium text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-3">
                    {user.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.name}
                        className="w-8 h-8 rounded-full"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center">
                        <span className="text-xs font-medium text-neutral-600">
                          {user.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                    )}
                    <div>
                      <div className="font-medium text-neutral-900">{user.name}</div>
                      <div className="text-sm text-neutral-500">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {user.workspaces?.slice(0, 2).map((ws) => (
                      <Badge key={ws.id} variant={ws.billing_tier === 'starter' ? 'premium' : 'default'}>
                        {ws.name}
                      </Badge>
                    ))}
                    {user.workspaces?.length > 2 && (
                      <Badge>+{user.workspaces.length - 2}</Badge>
                    )}
                    {!user.workspaces?.length && (
                      <span className="text-sm text-neutral-400">None</span>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex gap-2">
                    {user.is_superuser && (
                      <Badge variant="warning">Superuser</Badge>
                    )}
                    {user.is_verified ? (
                      <Badge variant="success">Verified</Badge>
                    ) : (
                      <Badge variant="danger">Unverified</Badge>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => handleToggleSuperuser(user)}
                      disabled={actionLoading === user.id}
                      className={`p-2 rounded-lg transition-colors ${
                        user.is_superuser
                          ? 'text-yellow-600 hover:bg-yellow-50'
                          : 'text-neutral-400 hover:bg-neutral-100'
                      }`}
                      title={user.is_superuser ? 'Remove superuser' : 'Make superuser'}
                    >
                      {actionLoading === user.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Crown className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={() => setDeleteModal({ open: true, user })}
                      disabled={actionLoading === user.id}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete user"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmModal
        open={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, user: null })}
        onConfirm={handleDelete}
        title="Delete User"
        message={`Are you sure you want to delete "${deleteModal.user?.name}"? This will remove them from Clerk (they can't log in anymore) and delete all workspaces they own. This action cannot be undone.`}
        confirmText="Delete User"
        danger
      />
    </>
  );
}

// Workspaces Table Component
function WorkspacesTable({ workspaces, onUpdateBilling, loading }) {
  const [actionLoading, setActionLoading] = useState(null);

  const handleBillingChange = async (workspace, newTier) => {
    setActionLoading(workspace.id);
    try {
      await onUpdateBilling(workspace.id, newTier);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        No workspaces found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-neutral-200">
            <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Workspace</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Owner</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Members</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Status</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-neutral-500">Tier</th>
          </tr>
        </thead>
        <tbody>
          {workspaces.map((ws) => (
            <tr key={ws.id} className="border-b border-neutral-100 hover:bg-neutral-50">
              <td className="py-3 px-4">
                <div className="font-medium text-neutral-900">{ws.name}</div>
                <div className="text-xs text-neutral-400 font-mono">{ws.id.slice(0, 8)}...</div>
              </td>
              <td className="py-3 px-4">
                <span className="text-sm text-neutral-600">{ws.owner_email || 'Unknown'}</span>
              </td>
              <td className="py-3 px-4">
                <span className="text-sm text-neutral-600">{ws.member_count}</span>
              </td>
              <td className="py-3 px-4">
                <Badge
                  variant={
                    ws.billing_status === 'active' || ws.billing_status === 'trialing'
                      ? 'success'
                      : ws.billing_status === 'locked'
                      ? 'warning'
                      : 'danger'
                  }
                >
                  {ws.billing_status}
                </Badge>
              </td>
              <td className="py-3 px-4">
                <select
                  value={ws.billing_tier}
                  onChange={(e) => handleBillingChange(ws, e.target.value)}
                  disabled={actionLoading === ws.id}
                  className={`text-sm px-3 py-1.5 rounded-lg border border-neutral-200 bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 ${
                    ws.billing_tier === 'starter' ? 'text-purple-700' : 'text-neutral-700'
                  }`}
                >
                  <option value="free">Free</option>
                  <option value="starter">Starter (Premium)</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Main Admin Page
export default function AdminPage() {
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(null);
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  // Check admin access on mount
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const status = await getAdminStatus();
        if (!status.is_superuser) {
          router.push('/dashboard');
          return;
        }
        setIsAdmin(true);
      } catch (err) {
        console.error('Admin check failed:', err);
        router.push('/dashboard');
      } finally {
        setLoading(false);
      }
    };
    checkAccess();
  }, [router]);

  // Load data based on active tab
  const loadData = useCallback(async () => {
    if (!isAdmin) return;
    setDataLoading(true);
    setError(null);

    try {
      if (activeTab === 'users') {
        const data = await getUsers({ search });
        setUsers(data.users);
      } else {
        const data = await getWorkspaces({ search });
        setWorkspaces(data.workspaces);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setDataLoading(false);
    }
  }, [isAdmin, activeTab, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Show toast notification
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Handlers
  const handleDeleteUser = async (userId) => {
    try {
      const result = await deleteUser(userId);
      showToast(result.message);
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleToggleSuperuser = async (userId, isSuperuser) => {
    try {
      await toggleSuperuser(userId, isSuperuser);
      showToast(isSuperuser ? 'Superuser access granted' : 'Superuser access revoked');
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleUpdateBilling = async (workspaceId, tier) => {
    try {
      await updateBillingTier(workspaceId, tier);
      showToast(tier === 'starter' ? 'Upgraded to Starter (Premium)' : 'Downgraded to Free');
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Loading state
  if (loading || isAdmin === null) {
    return (
      <div className="max-w-6xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-6 h-6 text-neutral-600" />
          <h1 className="text-2xl font-semibold text-neutral-900">Admin Dashboard</h1>
        </div>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 ${
            toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
          }`}
        >
          {toast.type === 'error' ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Shield className="w-6 h-6 text-yellow-600" />
        <h1 className="text-2xl font-semibold text-neutral-900">Admin Dashboard</h1>
        <Badge variant="warning">Superuser</Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <TabButton active={activeTab === 'users'} onClick={() => setActiveTab('users')}>
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Users
          </div>
        </TabButton>
        <TabButton active={activeTab === 'workspaces'} onClick={() => setActiveTab('workspaces')}>
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Workspaces
          </div>
        </TabButton>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder={activeTab === 'users' ? 'Search by email or name...' : 'Search by workspace name...'}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          Error: {error}
        </div>
      )}

      {/* Content */}
      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
        {activeTab === 'users' ? (
          <UsersTable
            users={users}
            onDelete={handleDeleteUser}
            onToggleSuperuser={handleToggleSuperuser}
            loading={dataLoading}
          />
        ) : (
          <WorkspacesTable
            workspaces={workspaces}
            onUpdateBilling={handleUpdateBilling}
            loading={dataLoading}
          />
        )}
      </div>

      {/* Stats footer */}
      <div className="mt-4 text-sm text-neutral-500">
        {activeTab === 'users'
          ? `${users.length} user${users.length !== 1 ? 's' : ''}`
          : `${workspaces.length} workspace${workspaces.length !== 1 ? 's' : ''}`}
      </div>
    </div>
  );
}
