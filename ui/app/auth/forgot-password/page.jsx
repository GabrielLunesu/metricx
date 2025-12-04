'use client';

/**
 * ForgotPasswordPage - Password reset request page
 * Matches the new white theme with blue/cyan accents
 * Related: login/page.jsx, reset-password/page.jsx
 */

import { useState } from 'react';
import { Mail, ArrowRight, ArrowLeft, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { requestPasswordReset } from '@/lib/api';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        try {
            await requestPasswordReset({ email });
            setSuccess(true);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 w-full max-w-md">
                {/* Back to login link */}
                <Link
                    href="/login"
                    className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors mb-8 group"
                >
                    <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
                    Back to login
                </Link>

                {/* Logo */}
                <div className="flex justify-center mb-8">
                    <Image
                        src="/logo.png"
                        alt="metricx"
                        width={180}
                        height={50}
                        className="h-12 w-auto"
                        priority
                    />
                </div>

                {/* Card */}
                <div className="bg-white/80 backdrop-blur-xl border border-gray-200/60 rounded-3xl p-8 shadow-xl shadow-gray-200/40">
                    <div className="text-center mb-8">
                        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Forgot Password?</h1>
                        <p className="text-gray-500 text-sm">
                            Enter your email address and we'll send you a link to reset your password.
                        </p>
                    </div>

                    {success ? (
                        <div className="text-center space-y-4">
                            <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle className="w-8 h-8" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900">Check your email</h3>
                            <p className="text-sm text-gray-500">
                                If an account exists for <strong className="text-gray-700">{email}</strong>, you will receive a password reset link shortly.
                            </p>
                            <div className="pt-4">
                                <Link
                                    href="/login"
                                    className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
                                >
                                    Back to Login
                                    <ArrowRight className="w-4 h-4" />
                                </Link>
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-5">
                            {error && (
                                <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-sm text-red-700">
                                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-400/20 focus:border-blue-400 outline-none transition-all"
                                        placeholder="you@company.com"
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full flex items-center justify-center gap-2 bg-gradient-to-b from-gray-800 to-gray-950 text-white py-3.5 px-4 rounded-xl hover:shadow-lg hover:shadow-gray-900/20 transition-all disabled:opacity-50 font-medium"
                            >
                                {loading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        Send Reset Link
                                        <ArrowRight className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </main>
    );
}
