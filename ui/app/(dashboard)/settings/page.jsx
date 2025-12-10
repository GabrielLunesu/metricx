'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Settings, Loader2 } from 'lucide-react';
import { currentUser } from '@/lib/workspace';
import SettingsTabs from './components/SettingsTabs';
import ConnectionsTab from './components/ConnectionsTab';
import AttributionTab from './components/AttributionTab';
import ProfileTab from './components/ProfileTab';
import UsersTab from './components/UsersTab';
import WorkspacesTab from './components/WorkspacesTab';

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('connections');
  const [error, setError] = useState(null);

  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['connections', 'attribution', 'profile', 'users', 'invites', 'workspaces'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  useEffect(() => {
    let mounted = true;

    const loadUser = async () => {
      try {
        const userData = await currentUser();
        if (mounted) {
          setUser(userData);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || 'Failed to load user');
          console.error('User load error:', err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadUser();

    return () => {
      mounted = false;
    };
  }, []);

  const tabs = [
    { id: 'connections', label: 'Connections' },
    { id: 'attribution', label: 'Attribution' },
    { id: 'profile', label: 'Profile' },
    { id: 'workspaces', label: 'Workspaces' },
    { id: 'users', label: 'Members' },
    { id: 'invites', label: 'Invites' }
  ];

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8">
          <Settings className="w-6 h-6 text-neutral-600" />
          <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8">
          <Settings className="w-6 h-6 text-neutral-600" />
          <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-6 h-6 text-neutral-600" />
        <h1 className="text-2xl font-semibold text-neutral-900">Settings</h1>
      </div>

      <SettingsTabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <div className="mt-8">
        {activeTab === 'connections' && <ConnectionsTab user={user} />}
        {activeTab === 'attribution' && <AttributionTab user={user} />}
        {activeTab === 'profile' && <ProfileTab user={user} />}
        {activeTab === 'workspaces' && <WorkspacesTab user={user} />}
        {activeTab === 'users' && <UsersTab user={user} />}
        {activeTab === 'invites' && <UsersTab user={user} view="invites" />}
      </div>
    </div>
  );
}
