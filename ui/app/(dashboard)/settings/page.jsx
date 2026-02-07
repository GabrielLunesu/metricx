'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Settings, Loader2 } from 'lucide-react';
import { currentUser, getBillingStatus } from '@/lib/workspace';
import SettingsTabs from './components/SettingsTabs';
import ConnectionsTab from './components/ConnectionsTab';
import AttributionTab from './components/AttributionTab';
import ProfileTab from './components/ProfileTab';
import UsersTab from './components/UsersTab';
import WorkspacesTab from './components/WorkspacesTab';
import BusinessProfileTab from './components/BusinessProfileTab';
import BillingTab from './components/BillingTab';

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const [user, setUser] = useState(null);
  const [billingTier, setBillingTier] = useState(null);
  const [billingStatus, setBillingStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('connections');
  const [error, setError] = useState(null);

  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && ['connections', 'attribution', 'profile', 'business', 'users', 'invites', 'workspaces', 'billing'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        // Fetch user and billing status in parallel
        const [userData, billingData] = await Promise.all([
          currentUser(),
          getBillingStatus(),
        ]);
        if (mounted) {
          setUser(userData);
          if (billingData?.billing) {
            setBillingTier(billingData.billing.billing_tier);
            setBillingStatus(billingData.billing.billing_status);
          }
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

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  const tabs = [
    { id: 'connections', label: 'Connections' },
    { id: 'attribution', label: 'Attribution' },
    { id: 'profile', label: 'Profile' },
    { id: 'business', label: 'Business' },
    { id: 'workspaces', label: 'Workspaces' },
    { id: 'users', label: 'Members' },
    { id: 'invites', label: 'Invites' },
    { id: 'billing', label: 'Billing' }
  ];

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <div className="flex items-center gap-3 mb-6 md:mb-8">
          <Settings className="w-5 md:w-6 h-5 md:h-6 text-neutral-600" />
          <h1 className="text-xl md:text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <div className="flex items-center gap-3 mb-6 md:mb-8">
          <Settings className="w-5 md:w-6 h-5 md:h-6 text-neutral-600" />
          <h1 className="text-xl md:text-2xl font-semibold text-neutral-900">Settings</h1>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 pb-16 md:pb-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6 md:mb-8">
        <Settings className="w-5 md:w-6 h-5 md:h-6 text-neutral-600" />
        <h1 className="text-xl md:text-2xl font-semibold text-neutral-900">Settings</h1>
      </div>

      <SettingsTabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <div className="mt-8">
        {activeTab === 'connections' && <ConnectionsTab user={user} billingTier={billingTier} />}
        {activeTab === 'attribution' && <AttributionTab user={user} />}
        {activeTab === 'profile' && <ProfileTab />}
        {activeTab === 'business' && <BusinessProfileTab user={user} />}
        {activeTab === 'workspaces' && <WorkspacesTab user={user} />}
        {activeTab === 'users' && <UsersTab user={user} billingTier={billingTier} billingStatus={billingStatus} />}
        {activeTab === 'invites' && <UsersTab user={user} view="invites" billingTier={billingTier} billingStatus={billingStatus} />}
        {activeTab === 'billing' && <BillingTab user={user} />}
      </div>
    </div>
  );
}
