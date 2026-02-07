'use client';

import { useState } from 'react';

export default function SettingsTabs({ tabs, activeTab, onTabChange }) {
    return (
        <div className="border-b border-neutral-200 mb-6 md:mb-8">
            <nav className="-mb-px flex space-x-4 md:space-x-8 overflow-x-auto no-scrollbar" aria-label="Tabs">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        className={`
              whitespace-nowrap py-3 md:py-4 px-1 border-b-2 font-medium text-xs md:text-sm transition-colors flex-shrink-0
              ${activeTab === tab.id
                                ? 'border-neutral-900 text-neutral-900'
                                : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'}
            `}
                        aria-current={activeTab === tab.id ? 'page' : undefined}
                    >
                        {tab.label}
                    </button>
                ))}
            </nav>
        </div>
    );
}
