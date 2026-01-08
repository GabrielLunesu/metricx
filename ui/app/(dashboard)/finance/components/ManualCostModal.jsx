"use client";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { manualCostSchema } from "@/lib/validation";

export default function ManualCostModal({
  open,
  onClose,
  onSubmit,
  onDelete,
  defaultMonth,
  defaultYear,
  editingCost = null,
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const defaultDate = useMemo(() => {
    if (!defaultMonth || !defaultYear) return "";
    const start = new Date(defaultYear, defaultMonth - 1, 1);
    return start.toISOString().slice(0, 10);
  }, [defaultMonth, defaultYear]);

  // Validate with zod to keep finance payloads predictable for operators.
  const form = useForm({
    resolver: zodResolver(manualCostSchema),
    defaultValues: {
      label: "",
      category: "Tools / SaaS",
      amount_dollar: "",
      date: defaultDate,
      notes: "",
    },
  });

  useEffect(() => {
    if (!open) return;
    if (editingCost) {
      form.reset({
        label: editingCost.label || "",
        category: editingCost.category || "Tools / SaaS",
        amount_dollar: editingCost.amount_dollar?.toString() || "",
        date: editingCost.allocation?.date || defaultDate,
        notes: editingCost.notes || "",
      });
    } else {
      form.reset({
        label: "",
        category: "Tools / SaaS",
        amount_dollar: "",
        date: defaultDate,
        notes: "",
      });
    }
  }, [open, editingCost, form, defaultDate]);

  if (!open) return null;

  const handleSubmit = form.handleSubmit((values) => {
    const payload = {
      label: values.label.trim(),
      category: values.category,
      amount_dollar: Number(values.amount_dollar),
      allocation: {
        type: "one_off",
        date: values.date, // Include the date for proper allocation
      },
      notes: values.notes || "",
    };
    onSubmit?.(payload);
  });

  const handleDelete = async () => {
    if (!editingCost || !onDelete) return;
    if (!confirm("Delete this cost?")) return;

    setIsDeleting(true);
    try {
      await onDelete(editingCost.id);
      onClose?.();
    } finally {
      setIsDeleting(false);
    }
  };

  const errors = form.formState.errors;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-md rounded-3xl border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-br from-blue-50 to-white border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-slate-900">
                {editingCost ? "Edit Cost" : "Add New Cost"}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {editingCost ? "Update cost details below" : "Track a manual expense or cost"}
              </p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition-all"
              aria-label="Close"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5" noValidate>
          {/* Label */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide">
              Label <span className="text-red-500">*</span>
            </label>
            <input
              {...form.register("label")}
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all placeholder:text-slate-400"
              placeholder="e.g., HubSpot, Agency Retainer"
            />
            {errors.label && <p className="text-xs text-red-600">{errors.label.message}</p>}
          </div>

          {/* Category */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide">
              Category <span className="text-red-500">*</span>
            </label>
            <select
              {...form.register("category")}
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all"
            >
              <option>Tools / SaaS</option>
              <option>Agency Fees</option>
              <option>Events</option>
              <option>Ad Spend - Other</option>
              <option>Miscellaneous</option>
            </select>
            {errors.category && <p className="text-xs text-red-600">{errors.category.message}</p>}
          </div>

          {/* Amount and Date Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide">
                Amount <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  {...form.register("amount_dollar")}
                  className="w-full pl-7 pr-4 py-3 rounded-xl border-2 border-slate-200 text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all placeholder:text-slate-400"
                  placeholder="0.00"
                />
              </div>
              {errors.amount_dollar && <p className="text-xs text-red-600">{errors.amount_dollar.message}</p>}
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide">
                Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                {...form.register("date")}
                className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all"
              />
              {errors.date && <p className="text-xs text-red-600">{errors.date.message}</p>}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide">
              Notes <span className="text-slate-400 text-xs normal-case">(Optional)</span>
            </label>
            <textarea
              {...form.register("notes")}
              rows={3}
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 text-sm bg-white focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all placeholder:text-slate-400 resize-none"
              placeholder="Add any additional context..."
            />
            {errors.notes && <p className="text-xs text-red-600">{errors.notes.message}</p>}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-3">
            {editingCost && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-3 rounded-xl border-2 border-red-200 text-red-600 text-sm font-semibold hover:bg-red-50 transition-all disabled:opacity-50"
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl bg-slate-100 text-slate-700 text-sm font-semibold hover:bg-slate-200 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={form.formState.isSubmitting}
              className="flex-1 px-5 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-bold hover:from-blue-600 hover:to-blue-700 shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all disabled:opacity-60"
            >
              {editingCost ? "Update" : "Add Cost"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
