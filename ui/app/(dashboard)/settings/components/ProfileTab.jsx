'use client';

import { useEffect, useState } from 'react';
import { User, Mail, Lock, Save, Loader2, AlertCircle, CheckCircle, Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { updateProfile, changePassword, deleteUserAccount } from '@/lib/api';
import { profileSchema, passwordSchema } from '@/lib/validation';

export default function ProfileTab({ user: initialUser }) {
  const [user, setUser] = useState(initialUser);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Forms validated with zod to keep copy friendly for non-technical admins.
  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: initialUser?.name || '',
      email: initialUser?.email || '',
    },
  });

  const passwordForm = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      old_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  useEffect(() => {
    if (initialUser) {
      setUser(initialUser);
      profileForm.reset({
        name: initialUser.name || '',
        email: initialUser.email || '',
      });
    }
  }, [initialUser, profileForm]);

  const handleProfileSubmit = profileForm.handleSubmit(async (values) => {
    setMessage(null);
    try {
      const updatedUser = await updateProfile(values);
      setUser(updatedUser);
      setMessage({ type: 'success', text: 'Profile updated successfully' });
      toast.success('Profile saved');
    } catch (err) {
      const msg = err?.message || 'Failed to update profile';
      setMessage({ type: 'error', text: msg });
      toast.error(msg);
    }
  });

  const handlePasswordSubmit = passwordForm.handleSubmit(async (values) => {
    setMessage(null);
    try {
      await changePassword({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      setMessage({ type: 'success', text: 'Password changed successfully' });
      toast.success('Password updated');
      passwordForm.reset({ old_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      const msg = err?.message || 'Failed to change password';
      setMessage({ type: 'error', text: msg });
      toast.error(msg);
    }
  });

  const handleDeleteAccount = async () => {
    if (!showDeleteConfirm) return;

    setDeleteLoading(true);
    try {
      await deleteUserAccount();
      toast.success('Account deleted');
      window.location.href = '/';
    } catch (err) {
      toast.error(err?.message || 'Failed to delete account');
      setDeleteLoading(false);
    }
  };

  const profileErrors = profileForm.formState.errors;
  const passwordErrors = passwordForm.formState.errors;

  return (
    <div>
      {message && (
        <div className={`p-4 mb-6 rounded-xl flex items-center gap-3 ${message.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Profile Details */}
        <div className="bg-white p-6 rounded-xl border border-neutral-200 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Personal Information</h2>
          <form onSubmit={handleProfileSubmit} className="space-y-4" noValidate>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="text"
                  {...profileForm.register('name')}
                  className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                />
              </div>
              {profileErrors.name && <p className="text-xs text-red-600 mt-1">{profileErrors.name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="email"
                  {...profileForm.register('email')}
                  className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                />
              </div>
              {profileErrors.email && <p className="text-xs text-red-600 mt-1">{profileErrors.email.message}</p>}
              <p className="text-xs text-neutral-500 mt-1">Changing email will require re-verification.</p>
            </div>



            <button
              type="submit"
              disabled={profileForm.formState.isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-neutral-900 text-white py-2 px-4 rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50"
            >
              {profileForm.formState.isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </button>
          </form>
        </div>

        {/* Change Password */}
        <div className="bg-white p-6 rounded-xl border border-neutral-200 shadow-sm h-fit">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Change Password</h2>
          <form onSubmit={handlePasswordSubmit} className="space-y-4" noValidate>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Current Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="password"
                  autoComplete="current-password"
                  {...passwordForm.register('old_password')}
                  className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                />
              </div>
              {passwordErrors.old_password && <p className="text-xs text-red-600 mt-1">{passwordErrors.old_password.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">New Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="password"
                  autoComplete="new-password"
                  {...passwordForm.register('new_password')}
                  className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                />
              </div>
              {passwordErrors.new_password && <p className="text-xs text-red-600 mt-1">{passwordErrors.new_password.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Confirm New Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="password"
                  autoComplete="new-password"
                  {...passwordForm.register('confirm_password')}
                  className="w-full pl-10 pr-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                />
              </div>
              {passwordErrors.confirm_password && <p className="text-xs text-red-600 mt-1">{passwordErrors.confirm_password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={passwordForm.formState.isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-white border border-neutral-300 text-neutral-700 py-2 px-4 rounded-lg hover:bg-neutral-50 transition-colors disabled:opacity-50"
            >
              {passwordForm.formState.isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
              Update Password
            </button>
          </form>
        </div>
      </div>

      {/* Delete Account Section */}
      <div className="mb-8 p-6 bg-red-50 border border-red-200 rounded-xl">
        <div className="flex items-start gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-2">Delete Account & Data</h3>
            <p className="text-sm text-red-800 mb-4">
              Permanently delete your account and all associated data. This action cannot be undone.
              All connections, campaigns, and analytics data will be permanently removed.
            </p>

            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 bg-white border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete My Account
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-red-900">
                  Are you absolutely sure? This cannot be undone.
                </p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleteLoading}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {deleteLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Yes, Delete Everything
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    disabled={deleteLoading}
                    className="px-4 py-2 bg-white border border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
