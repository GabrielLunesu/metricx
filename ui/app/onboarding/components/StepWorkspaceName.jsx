/**
 * Step 1: Workspace Name
 * ======================
 *
 * WHAT: Collects workspace/business name (required field).
 * WHY: This is the only required field - establishes the workspace identity.
 */

'use client';

import { useState } from 'react';
import { Building2, ArrowRight } from 'lucide-react';

export default function StepWorkspaceName({ formData, updateFormData, onNext }) {
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    const name = formData.workspace_name.trim();
    if (!name) {
      setError('Please enter your business name');
      return;
    }
    if (name.length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }

    setError('');
    onNext();
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 mb-4">
          <Building2 className="w-6 h-6 text-indigo-600" />
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Let's get to know your business
        </h1>
        <p className="mt-2 text-slate-500">
          What's your company or brand name?
        </p>
      </div>

      {/* Input */}
      <div className="mb-6">
        <input
          type="text"
          value={formData.workspace_name}
          onChange={(e) => {
            updateFormData({ workspace_name: e.target.value });
            if (error) setError('');
          }}
          placeholder="e.g., ACME Corp, My Brand"
          className={`
            w-full px-4 py-3 text-lg rounded-xl border
            focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
            ${error ? 'border-red-300 bg-red-50' : 'border-slate-200'}
          `}
          autoFocus
        />
        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl
          bg-indigo-600 text-white font-medium
          hover:bg-indigo-700 transition-colors"
      >
        Continue
        <ArrowRight className="w-4 h-4" />
      </button>
    </form>
  );
}
