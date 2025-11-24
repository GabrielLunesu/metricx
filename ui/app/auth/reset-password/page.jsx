'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Lock, ArrowRight, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { confirmPasswordReset } from '@/lib/api';

function ResetPasswordForm() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get('token');

    const [formData, setFormData] = useState({
        new_password: '',
        confirm_password: ''
    });
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!token) {
            setError('Invalid or missing reset token.');
        }
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (formData.new_password !== formData.confirm_password) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            await confirmPasswordReset({ token, new_password: formData.new_password });
            setSuccess(true);
            setTimeout(() => {
                router.push('/auth/login');
            }, 3000);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="text-center space-y-4">
                <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-semibold text-neutral-900">Password Reset Successful</h3>
                <p className="text-sm text-neutral-600">
                    Your password has been updated. Redirecting to login...
                </p>
                <div className="pt-4">
                    <Link
                        href="/auth/login"
                        className="text-sm font-medium text-neutral-900 hover:text-neutral-700 underline"
                    >
                        Go to Login
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                </div>
            )}

            <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">New Password</label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                    <input
                        type="password"
                        value={formData.new_password}
                        onChange={(e) => setFormData({ ...formData, new_password: e.target.value })}
                        className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                        placeholder="Min 8 characters"
                        required
                        minLength={8}
                    />
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Confirm Password</label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                    <input
                        type="password"
                        value={formData.confirm_password}
                        onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                        className="w-full pl-10 pr-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-neutral-900 focus:border-neutral-900 outline-none transition-all"
                        placeholder="Confirm new password"
                        required
                        minLength={8}
                    />
                </div>
            </div>

            <button
                type="submit"
                disabled={loading || !token}
                className="w-full flex items-center justify-center gap-2 bg-neutral-900 text-white py-3 px-4 rounded-xl hover:bg-neutral-800 transition-all disabled:opacity-50 font-medium"
            >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                    <>
                        Reset Password
                        <ArrowRight className="w-4 h-4" />
                    </>
                )}
            </button>

            <div className="text-center">
                <Link
                    href="/auth/login"
                    className="text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
                >
                    Back to Login
                </Link>
            </div>
        </form>
    );
}

export default function ResetPasswordPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-neutral-50 p-4">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-neutral-100 overflow-hidden">
                <div className="p-8">
                    <div className="text-center mb-8">
                        <h1 className="text-2xl font-bold text-neutral-900 mb-2">Reset Password</h1>
                        <p className="text-neutral-600 text-sm">
                            Enter your new password below.
                        </p>
                    </div>
                    <Suspense fallback={<div className="flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-neutral-400" /></div>}>
                        <ResetPasswordForm />
                    </Suspense>
                </div>
            </div>
        </div>
    );
}
