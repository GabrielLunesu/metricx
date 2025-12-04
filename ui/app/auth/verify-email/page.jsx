'use client';

/**
 * VerifyEmailPage - Email verification page
 * Matches the new white theme with blue/cyan accents
 * Related: login/page.jsx
 */

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, AlertCircle, ArrowRight, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { verifyEmail } from '@/lib/api';

function VerifyEmailContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get('token');
    const [status, setStatus] = useState('verifying'); // verifying, success, error
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!token) {
            setStatus('error');
            setError('Missing verification token.');
            return;
        }

        const verify = async () => {
            try {
                await verifyEmail({ token });
                setStatus('success');
            } catch (err) {
                setStatus('error');
                setError(err.message);
            }
        };

        verify();
    }, [token]);

    if (status === 'verifying') {
        return (
            <div className="text-center py-8">
                <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-6" />
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Verifying your email...</h2>
                <p className="text-gray-500">Please wait while we confirm your email address.</p>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className="text-center py-8">
                <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">Email Verified!</h2>
                <p className="text-gray-500 mb-8">
                    Your email address has been successfully verified. You can now access all features.
                </p>
                <Link
                    href="/dashboard"
                    className="inline-flex items-center justify-center gap-2 bg-gradient-to-b from-gray-800 to-gray-950 text-white py-3.5 px-6 rounded-xl hover:shadow-lg hover:shadow-gray-900/20 transition-all font-medium"
                >
                    Go to Dashboard
                    <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        );
    }

    return (
        <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <AlertCircle className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">Verification Failed</h2>
            <p className="text-red-600 mb-8 bg-red-50 border border-red-200 p-4 rounded-xl text-sm">
                {error || 'An unknown error occurred.'}
            </p>
            <Link
                href="/login"
                className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Login
            </Link>
        </div>
    );
}

export default function VerifyEmailPage() {
    return (
        <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 w-full max-w-md">
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
                    <Suspense fallback={
                        <div className="flex justify-center py-8">
                            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                        </div>
                    }>
                        <VerifyEmailContent />
                    </Suspense>
                </div>
            </div>
        </main>
    );
}
