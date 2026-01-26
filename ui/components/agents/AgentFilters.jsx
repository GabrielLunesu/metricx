/**
 * AgentFilters - Filter bar for agent list
 * =========================================
 *
 * WHAT: Provides filtering controls for the agent list view
 * WHY: Users need to quickly find specific agents by status
 *
 * FILTERS:
 * - Status: All, Active, Paused, Error, Draft
 * - Search: Filter by agent name
 *
 * REFERENCES:
 * - components/campaigns/CampaignFilters.jsx (similar pattern)
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Search, Filter, X } from 'lucide-react';

const STATUS_OPTIONS = [
  { value: null, label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'error', label: 'Error' },
  { value: 'draft', label: 'Draft' },
];

/**
 * AgentFilters component
 *
 * @param {Object} props
 * @param {string|null} props.status - Current status filter
 * @param {Function} props.onStatusChange - Callback when status changes
 * @param {string} props.search - Current search query
 * @param {Function} props.onSearchChange - Callback when search changes
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element}
 */
export function AgentFilters({
  status,
  onStatusChange,
  search,
  onSearchChange,
  className
}) {
  const [searchFocused, setSearchFocused] = useState(false);

  const hasActiveFilters = status !== null || (search && search.length > 0);

  const clearFilters = () => {
    onStatusChange?.(null);
    onSearchChange?.('');
  };

  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      {/* Status filter tabs */}
      <div className="flex items-center gap-1 bg-neutral-100 p-1 rounded-lg">
        {STATUS_OPTIONS.map(option => (
          <button
            key={option.value ?? 'all'}
            onClick={() => onStatusChange?.(option.value)}
            className={cn(
              'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
              status === option.value
                ? 'bg-white text-neutral-900 shadow-sm'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Search input */}
      <div
        className={cn(
          'relative flex items-center transition-all',
          searchFocused ? 'w-64' : 'w-48'
        )}
      >
        <Search
          size={16}
          className="absolute left-3 text-neutral-400 pointer-events-none"
        />
        <input
          type="text"
          placeholder="Search agents..."
          value={search || ''}
          onChange={(e) => onSearchChange?.(e.target.value)}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setSearchFocused(false)}
          className={cn(
            'w-full pl-9 pr-3 py-2 text-sm',
            'bg-white border border-neutral-200 rounded-lg',
            'placeholder:text-neutral-400',
            'focus:outline-none focus:ring-2 focus:ring-neutral-200 focus:border-neutral-300',
            'transition-all'
          )}
        />
        {search && search.length > 0 && (
          <button
            onClick={() => onSearchChange?.('')}
            className="absolute right-3 text-neutral-400 hover:text-neutral-600"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Clear filters button */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={clearFilters}
          className="text-neutral-500 hover:text-neutral-700"
        >
          <X size={14} className="mr-1" />
          Clear filters
        </Button>
      )}
    </div>
  );
}

export default AgentFilters;
