/**
 * Sign-In Page - Clerk-powered authentication.
 *
 * WHAT: Renders Clerk's SignIn component with custom styling
 * WHY: Replaces custom login form with Clerk's secure, feature-rich auth
 *
 * Features (handled by Clerk):
 * - Email/password authentication
 * - Google OAuth
 * - Password reset
 * - Email verification
 * - Remember me
 *
 * REFERENCES:
 *   - https://clerk.com/docs/components/authentication/sign-in
 *   - ui/app/layout.jsx (ClerkProvider)
 */

import { SignIn } from '@clerk/nextjs';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function SignInPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-b from-gray-50 via-white to-gray-50/50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-br from-blue-100/40 via-cyan-100/30 to-transparent rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">
        {/* Back to home */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors mb-8 group"
        >
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          Back to home
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

        {/* Clerk SignIn Component */}
        <SignIn
          signUpUrl="/sign-up"
          forceRedirectUrl="/dashboard"
          appearance={{
            elements: {
              rootBox: 'w-full',
              card: 'bg-white/80 backdrop-blur-xl border border-gray-200/60 rounded-3xl shadow-xl shadow-gray-200/40 p-0',
              headerTitle: 'text-gray-900 text-xl font-semibold',
              headerSubtitle: 'text-gray-500',
              formButtonPrimary: 'bg-gradient-to-b from-gray-800 to-gray-950 hover:shadow-lg hover:shadow-gray-900/20 transition-all rounded-xl',
              formFieldInput: 'rounded-xl border-gray-200 focus:border-blue-400 focus:ring-blue-400/20',
              formFieldLabel: 'text-gray-700 font-medium',
              footerActionLink: 'text-blue-600 hover:text-blue-700 font-medium',
              socialButtonsBlockButton: 'border-gray-200 hover:bg-gray-50 rounded-xl',
              socialButtonsBlockButtonText: 'text-gray-700 font-medium',
              dividerLine: 'bg-gray-200',
              dividerText: 'text-gray-400 text-sm',
              identityPreviewEditButton: 'text-blue-600 hover:text-blue-700',
              formFieldInputShowPasswordButton: 'text-gray-500 hover:text-gray-700',
              footer: 'hidden', // Hide "Secured by Clerk" footer
            },
            layout: {
              socialButtonsPlacement: 'top',
              socialButtonsVariant: 'blockButton',
            },
          }}
        />

        <p className="text-xs text-gray-400 text-center mt-6">
          By signing in, you agree to our{" "}
          <Link href="/terms" className="text-gray-500 hover:text-gray-700 underline">Terms of Service</Link>
          {" "}and{" "}
          <Link href="/privacy" className="text-gray-500 hover:text-gray-700 underline">Privacy Policy</Link>
        </p>
      </div>
    </main>
  );
}
