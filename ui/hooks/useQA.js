'use client';

/**
 * useQA Hook
 * ==========
 *
 * WHAT: React hook for QA queries with built-in caching using the Semantic Layer.
 *
 * WHY:
 *   - Centralizes QA fetching logic across all components
 *   - Uses the new Semantic Layer (synchronous, composable queries)
 *   - Built-in caching prevents redundant requests on page refresh
 *   - Deduplication prevents same question being asked simultaneously
 *   - Consistent loading/error state management
 *
 * USAGE:
 *   const { data, loading, error, refetch } = useQA({
 *     workspaceId: '...',
 *     question: 'What is my ROAS?',
 *     enabled: true,  // optional, default true
 *     cacheTTL: 5 * 60 * 1000,  // optional, default 5 min
 *   });
 *
 * REFERENCES:
 *   - lib/api.js (fetchQASemantic)
 *   - lib/qaCache.js (caching layer)
 *   - backend/app/semantic/ (Semantic Layer)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchQAAgent, fetchQASemantic, fetchQAStream, fetchQA } from '@/lib/api';
import { qaCache } from '@/lib/qaCache';

/**
 * Custom hook for QA queries using the Semantic Layer.
 *
 * EXECUTION ORDER:
 *   1. Check cache (if enabled)
 *   2. Try Semantic Layer endpoint (synchronous, composable queries)
 *   3. Fallback to SSE streaming (if semantic fails)
 *   4. Final fallback to polling (if streaming fails)
 *
 * @param {Object} options - Hook options
 * @param {string} options.workspaceId - Workspace UUID
 * @param {string} options.question - The question to ask
 * @param {Object} options.context - Optional context object
 * @param {boolean} options.enabled - Whether to fetch (default: true)
 * @param {number} options.cacheTTL - Cache TTL in ms (default: 5 min)
 * @param {Function} options.onStage - Optional callback for stage updates
 * @param {boolean} options.skipCache - Skip cache lookup (default: false)
 *
 * @returns {Object} { data, loading, error, stage, refetch, answer, visuals, executedDsl }
 */
export function useQA({
  workspaceId,
  question,
  context = {},
  enabled = true,
  cacheTTL = qaCache.DEFAULT_TTL_MS,
  onStage,
  skipCache = false
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stage, setStage] = useState(null);

  // Ref to track if component is mounted (prevent setState after unmount)
  const mountedRef = useRef(true);

  // Ref to track current request (for cancellation/dedup)
  const requestIdRef = useRef(0);

  /**
   * Fetch QA data with caching and streaming.
   */
  const fetchData = useCallback(async (forceRefresh = false) => {
    // Validate inputs
    if (!workspaceId || !question) {
      return;
    }

    // Increment request ID (used for dedup/stale response detection)
    const currentRequestId = ++requestIdRef.current;

    // Check cache first (unless skipCache or forceRefresh)
    if (!skipCache && !forceRefresh) {
      const cached = qaCache.get(workspaceId, question);
      if (cached) {
        setData(cached);
        setLoading(false);
        setError(null);
        setStage(null);
        return;
      }

      // Check if same request is already in-flight (deduplication)
      const inFlight = qaCache.getInFlight(workspaceId, question);
      if (inFlight) {
        console.log('[useQA] Waiting for in-flight request:', question.substring(0, 40) + '...');
        try {
          const result = await inFlight;
          if (mountedRef.current && requestIdRef.current === currentRequestId) {
            setData(result);
            setLoading(false);
            setError(null);
            setStage(null);
          }
        } catch (err) {
          if (mountedRef.current && requestIdRef.current === currentRequestId) {
            setError(err.message);
            setLoading(false);
          }
        }
        return;
      }
    }

    // Start loading
    setLoading(true);
    setError(null);
    setStage('queued');

    // Create fetch promise
    const fetchPromise = (async () => {
      try {
        // Use Agentic Copilot (preferred - LangGraph + Claude for natural understanding)
        const result = await fetchQAAgent({
          workspaceId,
          question,
          context,
          onStage: (newStage) => {
            if (mountedRef.current && requestIdRef.current === currentRequestId) {
              setStage(newStage);
              onStage?.(newStage);
            }
          }
        });

        // Cache the result
        qaCache.set(workspaceId, question, result, cacheTTL);

        return result;
      } catch (agentError) {
        // Fallback to Semantic Layer if agent fails
        console.warn('[useQA] Agent failed, falling back to semantic layer:', agentError.message);

        try {
          const result = await fetchQASemantic({
            workspaceId,
            question,
            context,
            onStage: (newStage) => {
              if (mountedRef.current && requestIdRef.current === currentRequestId) {
                setStage(newStage);
                onStage?.(newStage);
              }
            }
          });

          qaCache.set(workspaceId, question, result, cacheTTL);
          return result;
        } catch (semanticError) {
          // Fallback to legacy SSE streaming if semantic layer fails
          console.warn('[useQA] Semantic layer failed, falling back to streaming:', semanticError.message);

          try {
            const result = await fetchQAStream({
              workspaceId,
              question,
              context,
              onStage: (newStage, jobId) => {
                if (mountedRef.current && requestIdRef.current === currentRequestId) {
                  setStage(newStage);
                  onStage?.(newStage, jobId);
                }
              }
            });

            qaCache.set(workspaceId, question, result, cacheTTL);
            return result;
          } catch (streamError) {
            // Final fallback to polling
            console.warn('[useQA] Streaming also failed, falling back to polling:', streamError.message);

            const result = await fetchQA({
              workspaceId,
              question,
              context,
              maxRetries: 30,
              pollInterval: 1000
            });

            qaCache.set(workspaceId, question, result, cacheTTL);
            return result;
          }
        }
      }
    })();

    // Register in-flight request (for deduplication)
    qaCache.setInFlight(workspaceId, question, fetchPromise);

    try {
      const result = await fetchPromise;

      // Only update state if still mounted and this is the latest request
      if (mountedRef.current && requestIdRef.current === currentRequestId) {
        setData(result);
        setLoading(false);
        setStage(null);
      }
    } catch (err) {
      // Only update state if still mounted and this is the latest request
      if (mountedRef.current && requestIdRef.current === currentRequestId) {
        console.error('[useQA] Fetch failed:', err.message);
        setError(err.message);
        setLoading(false);
        setStage(null);
      }
    }
  }, [workspaceId, question, context, cacheTTL, skipCache, onStage]);

  /**
   * Refetch data (bypasses cache).
   */
  const refetch = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  // Effect to fetch data when dependencies change
  useEffect(() => {
    mountedRef.current = true;

    if (enabled) {
      fetchData();
    }

    return () => {
      mountedRef.current = false;
    };
  }, [enabled, fetchData]);

  return {
    data,
    loading,
    error,
    stage,
    refetch,
    // Convenience accessors
    answer: data?.answer || null,
    visuals: data?.visuals || null,
    executedDsl: data?.executed_dsl || null
  };
}

/**
 * Hook for multiple parallel QA queries with caching.
 *
 * @param {Array} queries - Array of { workspaceId, question, context }
 * @param {Object} options - Shared options
 *
 * @returns {Object} { results, loading, errors, refetchAll }
 */
export function useQAMultiple(queries, options = {}) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState([]);

  const mountedRef = useRef(true);
  const { enabled = true, cacheTTL = qaCache.DEFAULT_TTL_MS } = options;

  const fetchAll = useCallback(async (forceRefresh = false) => {
    if (!queries || queries.length === 0) return;

    setLoading(true);
    setErrors([]);

    const fetchPromises = queries.map(async (query, index) => {
      const { workspaceId, question, context = {} } = query;

      // Check cache first
      if (!forceRefresh) {
        const cached = qaCache.get(workspaceId, question);
        if (cached) return { index, data: cached, error: null };
      }

      try {
        // Use Agentic Copilot (preferred)
        const result = await fetchQAAgent({
          workspaceId,
          question,
          context,
          onStage: () => {}  // Silent for batch
        });

        // Cache result
        qaCache.set(workspaceId, question, result, cacheTTL);

        return { index, data: result, error: null };
      } catch (err) {
        // Fallback to Semantic Layer then streaming then polling
        try {
          const result = await fetchQASemantic({
            workspaceId,
            question,
            context,
            onStage: () => {}
          });
          qaCache.set(workspaceId, question, result, cacheTTL);
          return { index, data: result, error: null };
        } catch (semanticErr) {
          try {
            const result = await fetchQAStream({
              workspaceId,
              question,
              context,
              onStage: () => {}
            });
            qaCache.set(workspaceId, question, result, cacheTTL);
            return { index, data: result, error: null };
          } catch (streamErr) {
            try {
              const result = await fetchQA({ workspaceId, question, context });
              qaCache.set(workspaceId, question, result, cacheTTL);
              return { index, data: result, error: null };
            } catch (fallbackErr) {
              return { index, data: null, error: fallbackErr.message };
            }
          }
        }
      }
    });

    try {
      const settled = await Promise.all(fetchPromises);

      if (mountedRef.current) {
        const newResults = queries.map(() => null);
        const newErrors = queries.map(() => null);

        settled.forEach(({ index, data, error }) => {
          newResults[index] = data;
          newErrors[index] = error;
        });

        setResults(newResults);
        setErrors(newErrors);
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [queries, cacheTTL]);

  const refetchAll = useCallback(() => {
    return fetchAll(true);
  }, [fetchAll]);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled && queries?.length > 0) {
      fetchAll();
    }

    return () => {
      mountedRef.current = false;
    };
  }, [enabled, fetchAll, queries?.length]);

  return {
    results,
    loading,
    errors,
    refetchAll
  };
}

export default useQA;
