'use client';

import { Users } from 'lucide-react';

export default function UsersTab() {
    return (
        <div className="text-center py-12 bg-neutral-50 border border-neutral-200 rounded-xl">
            <div className="w-16 h-16 bg-neutral-100 text-neutral-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">Workspace Members</h3>
            <p className="text-neutral-600 max-w-md mx-auto">
                Manage users and permissions for your workspace. This feature is coming soon.
            </p>
        </div>
    );
}
