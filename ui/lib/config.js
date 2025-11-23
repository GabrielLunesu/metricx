// Centralized configuration for frontend
// Handles both local development and production deployment
// WHY: One source of truth for environment-specific settings

/**
 * Get the backend API base URL
 * Priority:
 * 1. NEXT_PUBLIC_API_BASE environment variable (set during build for production)
 * 2. Fallback to localhost for local development
 */
/**
 * Get the backend API base URL
 * 
 * We use a relative path '/api' which is proxied by Next.js to the actual backend.
 * This ensures cookies are treated as first-party (Same-Origin), which is critical
 * for Safari/iOS ITP compliance and prevents login issues on mobile.
 * 
 * See next.config.mjs for the proxy configuration.
 */
export function getApiBase() {
  return '/api';
}

/**
 * Check if we're running in production
 */
export function isProduction() {
  return process.env.NODE_ENV === 'production';
}

/**
 * Check if we're running in development
 */
export function isDevelopment() {
  return process.env.NODE_ENV === 'development';
}

/**
 * Get configuration object
 */
export const config = {
  apiBase: getApiBase(),
  isProduction: isProduction(),
  isDevelopment: isDevelopment(),
};

// Export as default for convenience
export default config;

