/**
 * Dashboard Layout - Protected shell with Clerk authentication.
 *
 * WHAT: Server-side protected layout with sidebar and content area
 * WHY: All dashboard routes require authentication (enforced by middleware + this layout)
 *
 * Authentication:
 * - Middleware handles initial redirect for unauthenticated users
 * - This layout provides additional server-side check
 * - No client-side auth state management needed (Clerk handles it)
 *
 * REFERENCES:
 *   - ui/middleware.ts (route protection)
 *   - ui/app/layout.jsx (ClerkProvider)
 */

import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import DashboardShell from './DashboardShell';

export default async function DashboardLayout({ children }) {
  // Server-side auth check - redundant with middleware but provides defense in depth
  const { userId } = await auth();

  if (!userId) {
    redirect('/sign-in');
  }

  return <DashboardShell>{children}</DashboardShell>;
}
