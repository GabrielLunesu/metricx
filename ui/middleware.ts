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
 * - /glossary(.*) (SEO glossary pages)
 * - /vs(.*) (SEO competitor comparison pages)
 * - /alternatives(.*) (SEO alternative pages)
 * - /tools(.*) (SEO calculator tool pages)
 * - /metrics(.*) (SEO metric deep-dive pages)
 * - /platforms(.*) (SEO platform guide pages)
 * - /industries(.*) (SEO industry pages)
 * - /integrations(.*) (SEO integration pages)
 * - /use-cases(.*) (SEO use case pages)
 * - /blog(.*) (SEO blog pages)
 */
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/login',
  '/sitemap.xml',
  '/privacy',
  '/terms',
  '/about',
  // SEO marketing pages (programmatic content)
  '/glossary(.*)',
  '/vs(.*)',
  '/alternatives(.*)',
  '/tools(.*)',
  '/metrics(.*)',
  '/platforms(.*)',
  '/industries(.*)',
  '/integrations(.*)',
  '/use-cases(.*)',
  '/blog(.*)',
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
    // - /api/* routes (these are proxied to backend which has its own auth)
    // - .txt/.xml files (for IndexNow verification, robots.txt, sitemap.xml, etc.)
    '/((?!_next|api|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|txt|xml)).*)',
  ],
}
