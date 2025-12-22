/**
 * Onboarding Layout
 * =================
 *
 * WHAT: Simple centered layout for onboarding flow (no sidebar).
 * WHY: Onboarding should be focused - no distractions from dashboard navigation.
 *
 * REFERENCES:
 *   - ui/app/onboarding/page.jsx (child page)
 */

import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import Image from 'next/image';

export const metadata = {
  title: 'Welcome to metricx',
  description: 'Set up your workspace',
};

export default async function OnboardingLayout({ children }) {
  const { userId } = await auth();

  // Must be authenticated to access onboarding
  if (!userId) {
    redirect('/sign-in');
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Simple header with logo */}
      <header className="fixed top-0 left-0 right-0 z-10 px-6 py-4">
        <Image
          src="/logo.png"
          alt="metricx"
          width={120}
          height={32}
          className="h-12 w-auto"
          priority
        />
      </header>

      {/* Main content */}
      <main className="pt-20 pb-12 px-4">
        {children}
      </main>
    </div>
  );
}
