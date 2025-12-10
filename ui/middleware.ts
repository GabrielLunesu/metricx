/**
 * Clerk Middleware - Server-side route protection.
 *
 * WHAT: Validates Clerk session before allowing access to protected routes
 * WHY: Server-side auth check prevents flash of unauthenticated content
 *
 * REFERENCES:
 *   - https://clerk.com/docs/references/nextjs/clerk-middleware
 *   - ui/app/(dashboard)/layout.jsx (dashboard routes)
 */

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

/**
 * Public routes that don't require authentication.
 *
 * These routes are accessible to all users, regardless of auth state:
 * - / (homepage/landing page)
 * - /sign-in, /sign-up (auth pages)
 * - /privacy, /terms (legal pages)
 * - /login (redirects to /sign-in for backwards compatibility)
 */
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/login',
  '/privacy',
  '/terms',
])

export default clerkMiddleware(async (auth, request) => {
  const { pathname } = request.nextUrl

  // Redirect legacy /login to /sign-in
  if (pathname === '/login') {
    const signInUrl = new URL('/sign-in', request.url)
    return NextResponse.redirect(signInUrl)
  }

  // Protect all routes except public ones
  if (!isPublicRoute(request)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    // Match all routes except:
    // - Static files (_next, images, fonts, etc.)
    // - API routes handled separately
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes (if any frontend API routes exist)
    '/(api|trpc)(.*)',
  ],
}
