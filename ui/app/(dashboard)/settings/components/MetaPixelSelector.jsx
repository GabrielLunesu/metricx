'use client';

/**
 * MetaPixelSelector component for Settings page.
 *
 * WHAT: Allows configuring Meta CAPI pixel for a connection without reconnecting
 * WHY: Better UX than requiring full OAuth reconnect just to select a pixel
 *
 * REFERENCES:
 * - backend/app/routers/connections.py (GET /connections/{id}/meta-pixels, PATCH /connections/{id}/meta-pixel)
 */

import { useState } from 'react';
import { Send, ChevronDown, Check, AlertCircle, CheckCircle, Loader2, Settings } from 'lucide-react';
import { getApiBase } from '@/lib/config';
import { toast } from 'sonner';

export default function MetaPixelSelector({ connection, onUpdate }) {
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [pixels, setPixels] = useState([]);
    const [error, setError] = useState(null);
    const [selectedPixelId, setSelectedPixelId] = useState(connection.meta_pixel_id || '');

    const fetchPixels = async () => {
        setLoading(true);
        setError(null);
        try {
            const baseUrl = getApiBase();
            const response = await fetch(`${baseUrl}/connections/${connection.id}/meta-pixels`, {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to fetch pixels');
            }

            const data = await response.json();
            setPixels(data.pixels || []);
            setSelectedPixelId(data.current_pixel_id || '');

            if (data.pixels.length === 0) {
                setError('No pixels found for this ad account');
            }
        } catch (err) {
            setError(err.message || 'Failed to load pixels');
        } finally {
            setLoading(false);
        }
    };

    const handleConfigure = () => {
        setIsOpen(true);
        fetchPixels();
    };

    const handleSave = async () => {
        if (!selectedPixelId) {
            toast.error('Please select a pixel');
            return;
        }

        setSaving(true);
        try {
            const baseUrl = getApiBase();
            const response = await fetch(`${baseUrl}/connections/${connection.id}/meta-pixel`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ pixel_id: selectedPixelId }),
            });

            if (!response.ok) {
                throw new Error('Failed to save pixel');
            }

            toast.success('Pixel configured for CAPI');
            setIsOpen(false);
            onUpdate?.();
        } catch (err) {
            toast.error(err.message || 'Failed to save pixel');
        } finally {
            setSaving(false);
        }
    };

    // Show inline status
    if (!isOpen) {
        return (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
                <Send className="w-3 h-3 text-neutral-400" />
                <span className="text-xs text-neutral-600">Conversions API (CAPI):</span>

                {connection.meta_pixel_id ? (
                    <>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700">
                            <CheckCircle className="w-3 h-3" />
                            Configured
                        </span>
                        <span className="text-xs text-neutral-500">
                            Pixel: {connection.meta_pixel_id}
                        </span>
                        <button
                            onClick={handleConfigure}
                            className="text-xs text-cyan-600 hover:text-cyan-700 underline"
                        >
                            Change
                        </button>
                    </>
                ) : (
                    <>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
                            <AlertCircle className="w-3 h-3" />
                            Not configured
                        </span>
                        <button
                            onClick={handleConfigure}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-cyan-600 hover:text-cyan-700 hover:bg-cyan-50 rounded transition-colors"
                        >
                            <Settings className="w-3 h-3" />
                            Configure
                        </button>
                    </>
                )}
            </div>
        );
    }

    // Show configuration panel
    return (
        <div className="mt-3 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
            <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-neutral-900">Configure CAPI Pixel</h4>
                <button
                    onClick={() => setIsOpen(false)}
                    className="text-xs text-neutral-500 hover:text-neutral-700"
                >
                    Cancel
                </button>
            </div>

            {loading ? (
                <div className="flex items-center gap-2 py-4 text-neutral-500">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Loading pixels...</span>
                </div>
            ) : error ? (
                <div className="py-2 text-sm text-red-600">{error}</div>
            ) : (
                <div className="space-y-3">
                    <p className="text-xs text-neutral-600">
                        Select a pixel to send purchase conversions via Conversions API.
                    </p>

                    <div className="relative">
                        <select
                            value={selectedPixelId}
                            onChange={(e) => setSelectedPixelId(e.target.value)}
                            className="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-cyan-200"
                        >
                            <option value="">Select a pixel...</option>
                            {pixels.map(pixel => (
                                <option key={pixel.id} value={pixel.id}>
                                    {pixel.name} ({pixel.id})
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleSave}
                            disabled={saving || !selectedPixelId}
                            className="px-3 py-1.5 text-sm font-medium bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                        >
                            {saving ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                                <Check className="w-3 h-3" />
                            )}
                            Save
                        </button>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-800"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
