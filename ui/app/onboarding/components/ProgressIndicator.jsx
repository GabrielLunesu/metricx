/**
 * Progress Indicator
 * ==================
 *
 * WHAT: Visual progress bar showing current step in onboarding.
 * WHY: Users need to know where they are in the flow.
 */

'use client';

import { Check } from 'lucide-react';

const STEP_LABELS = [
  'Name',
  'Website',
  'Business',
  'Platforms',
];

export default function ProgressIndicator({ current, total }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: total }, (_, i) => {
        const stepNum = i + 1;
        const isCompleted = stepNum < current;
        const isCurrent = stepNum === current;

        return (
          <div key={stepNum} className="flex items-center">
            {/* Step circle */}
            <div
              className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                transition-all duration-200
                ${isCompleted
                  ? 'bg-indigo-600 text-white'
                  : isCurrent
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                    : 'bg-slate-100 text-slate-400'
                }
              `}
            >
              {isCompleted ? (
                <Check className="w-4 h-4" />
              ) : (
                stepNum
              )}
            </div>

            {/* Step label (visible on larger screens) */}
            <span
              className={`
                hidden sm:block ml-2 text-sm font-medium
                ${isCurrent ? 'text-indigo-600' : 'text-slate-400'}
              `}
            >
              {STEP_LABELS[i]}
            </span>

            {/* Connector line */}
            {stepNum < total && (
              <div
                className={`
                  w-8 sm:w-12 h-0.5 mx-2
                  ${isCompleted ? 'bg-indigo-600' : 'bg-slate-200'}
                `}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
