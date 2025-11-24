'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, CheckCircle, AlertCircle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
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
                <Loader2 className="w-12 h-12 animate-spin text-neutral-900 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-neutral-900">Verifying your email...</h2>
                <p className="text-neutral-600 mt-2">Please wait while we confirm your email address.</p>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className="text-center py-8">
                <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Email Verified!</h2>
                <p className="text-neutral-600 mb-8">
                    Your email address has been successfully verified. You can now access all features.
                </p>
                <Link
                    href="/dashboard"
                    className="inline-flex items-center justify-center gap-2 bg-neutral-900 text-white py-3 px-6 rounded-xl hover:bg-neutral-800 transition-all font-medium"
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
            <h2 className="text-2xl font-bold text-neutral-900 mb-2">Verification Failed</h2>
            <p className="text-red-600 mb-8 bg-red-50 p-3 rounded-lg inline-block">
                {error || 'An unknown error occurred.'}
            </p>
            <div>
                <Link
                    href="/auth/login"
                    className="text-neutral-900 font-medium hover:underline"
                >
                    Back to Login
                </Link>
            </div>
        </div>
    );
}

export default function VerifyEmailPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-neutral-50 p-4">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-neutral-100 overflow-hidden">
                <div className="p-8">
                    <Suspense fallback={<div className="flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-neutral-400" /></div>}>
                        <VerifyEmailContent />
                    </Suspense>
                </div>
            </div>
        </div>
    );
}
