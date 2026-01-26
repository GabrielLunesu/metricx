/**
 * AgentStatusBadge - Visual indicator for agent status
 * ====================================================
 *
 * WHAT: Renders a colored badge showing agent's current status
 * WHY: Quick visual identification of agent health in lists and details
 *
 * STATUSES:
 * - active: Green - Agent is monitoring and can execute actions
 * - paused: Yellow - Agent is temporarily stopped by user
 * - error: Red - Agent encountered an error and was auto-paused
 * - draft: Gray - Agent is being configured, not yet active
 * - disabled: Gray - Agent is permanently disabled
 *
 * REFERENCES:
 * - backend/app/models.py (AgentStatusEnum)
 * - backend/app/schemas.py (AgentOut)
 */

'use client';

import { cn } from '@/lib/utils';
import {
  CheckCircle2,
  PauseCircle,
  AlertCircle,
  FileEdit,
  XCircle
} from 'lucide-react';

const STATUS_CONFIG = {
  active: {
    label: 'Active',
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    dotColor: 'bg-emerald-500',
    icon: CheckCircle2,
  },
  paused: {
    label: 'Paused',
    color: 'bg-amber-50 text-amber-700 border-amber-200',
    dotColor: 'bg-amber-500',
    icon: PauseCircle,
  },
  error: {
    label: 'Error',
    color: 'bg-red-50 text-red-700 border-red-200',
    dotColor: 'bg-red-500',
    icon: AlertCircle,
  },
  draft: {
    label: 'Draft',
    color: 'bg-neutral-50 text-neutral-600 border-neutral-200',
    dotColor: 'bg-neutral-400',
    icon: FileEdit,
  },
  disabled: {
    label: 'Disabled',
    color: 'bg-neutral-100 text-neutral-500 border-neutral-200',
    dotColor: 'bg-neutral-400',
    icon: XCircle,
  },
};

/**
 * AgentStatusBadge component
 *
 * @param {Object} props
 * @param {string} props.status - Agent status (active, paused, error, draft, disabled)
 * @param {string} props.size - Badge size (sm, md, lg)
 * @param {boolean} props.showIcon - Whether to show status icon
 * @param {boolean} props.showDot - Whether to show animated dot (for active status)
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element}
 */
export function AgentStatusBadge({
  status,
  size = 'md',
  showIcon = false,
  showDot = true,
  className
}) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  };

  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        sizeClasses[size],
        config.color,
        className
      )}
    >
      {showDot && (
        <span
          className={cn(
            'rounded-full',
            dotSizes[size],
            config.dotColor,
            status === 'active' && 'animate-pulse'
          )}
        />
      )}
      {showIcon && <Icon size={iconSizes[size]} />}
      {config.label}
    </span>
  );
}

export default AgentStatusBadge;
