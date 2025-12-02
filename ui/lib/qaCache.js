/**
 * QA Cache Utility
 * ================
 *
 * WHAT: In-memory cache for QA responses with TTL support.
 *
 * WHY:
 *   - Prevents redundant QA requests on page refresh/navigation
 *   - Reduces backend load and improves perceived performance
 *   - Avoids re-asking the same question multiple times
 *
 * HOW:
 *   - Cache key = hash of (workspaceId + question + timeframe)
 *   - TTL-based expiration (default 5 minutes)
 *   - Deduplication: prevents same question being asked simultaneously
 *
 * USAGE:
 *   import { qaCache } from '@/lib/qaCache';
 *
 *   // Check cache before fetching
 *   const cached = qaCache.get(workspaceId, question);
 *   if (cached) return cached;
 *
 *   // Store result after fetching
 *   qaCache.set(workspaceId, question, result);
 *
 * REFERENCES:
 *   - lib/api.js (fetchQA, fetchQAStream)
 *   - hooks/useQA.js (main consumer)
 */

// Default TTL: 5 minutes (in milliseconds)
const DEFAULT_TTL_MS = 5 * 60 * 1000;

// In-flight requests map (for deduplication)
const inFlightRequests = new Map();

// Cache storage
const cache = new Map();

/**
 * Generate a unique cache key from workspace + question.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 * @returns {string} Cache key
 */
function generateKey(workspaceId, question) {
  // Normalize question: lowercase, trim, collapse whitespace
  const normalizedQ = question.toLowerCase().trim().replace(/\s+/g, ' ');
  return `${workspaceId}:${normalizedQ}`;
}

/**
 * Get cached QA result if valid (not expired).
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 * @returns {Object|null} Cached result or null if miss/expired
 */
function get(workspaceId, question) {
  const key = generateKey(workspaceId, question);
  const entry = cache.get(key);

  if (!entry) return null;

  // Check if expired
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return null;
  }

  console.log('[QA_CACHE] Hit:', question.substring(0, 50) + '...');
  return entry.data;
}

/**
 * Store QA result in cache with TTL.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 * @param {Object} data - The QA result to cache
 * @param {number} ttlMs - Time-to-live in milliseconds (default: 5 min)
 */
function set(workspaceId, question, data, ttlMs = DEFAULT_TTL_MS) {
  const key = generateKey(workspaceId, question);

  cache.set(key, {
    data,
    expiresAt: Date.now() + ttlMs,
    cachedAt: Date.now()
  });

  console.log('[QA_CACHE] Stored:', question.substring(0, 50) + '...', `(TTL: ${ttlMs / 1000}s)`);
}

/**
 * Invalidate (delete) a specific cache entry.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 */
function invalidate(workspaceId, question) {
  const key = generateKey(workspaceId, question);
  cache.delete(key);
}

/**
 * Invalidate all cache entries for a workspace.
 *
 * @param {string} workspaceId - Workspace UUID
 */
function invalidateWorkspace(workspaceId) {
  for (const key of cache.keys()) {
    if (key.startsWith(workspaceId + ':')) {
      cache.delete(key);
    }
  }
  console.log('[QA_CACHE] Invalidated all entries for workspace:', workspaceId);
}

/**
 * Clear entire cache.
 */
function clear() {
  cache.clear();
  inFlightRequests.clear();
  console.log('[QA_CACHE] Cleared all entries');
}

/**
 * Get or create an in-flight request promise (deduplication).
 * If the same question is already being fetched, return the existing promise.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 * @returns {Promise|null} Existing promise or null if no in-flight request
 */
function getInFlight(workspaceId, question) {
  const key = generateKey(workspaceId, question);
  return inFlightRequests.get(key) || null;
}

/**
 * Register an in-flight request promise.
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} question - The QA question
 * @param {Promise} promise - The fetch promise
 */
function setInFlight(workspaceId, question, promise) {
  const key = generateKey(workspaceId, question);
  inFlightRequests.set(key, promise);

  // Clean up when promise settles
  promise.finally(() => {
    inFlightRequests.delete(key);
  });
}

/**
 * Get cache statistics (for debugging).
 *
 * @returns {Object} Cache stats
 */
function getStats() {
  let validEntries = 0;
  let expiredEntries = 0;
  const now = Date.now();

  for (const entry of cache.values()) {
    if (now > entry.expiresAt) {
      expiredEntries++;
    } else {
      validEntries++;
    }
  }

  return {
    total: cache.size,
    valid: validEntries,
    expired: expiredEntries,
    inFlight: inFlightRequests.size
  };
}

// Export as object for easy importing
export const qaCache = {
  get,
  set,
  invalidate,
  invalidateWorkspace,
  clear,
  getInFlight,
  setInFlight,
  getStats,
  DEFAULT_TTL_MS
};

export default qaCache;
