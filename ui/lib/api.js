// API client focused on KPI consumption.
// All functions return plain JSON and throw on non-2xx.
// WHY: centralizing fetch keeps pages dumb and testable.

import { getApiBase } from './config';

const BASE = getApiBase();

/**
 * Get the Clerk session token for API requests.
 * Waits for Clerk to be ready if needed.
 */
async function getClerkToken() {
  if (typeof window === 'undefined') return null;

  // Wait for Clerk to be ready (max 5 seconds)
  let attempts = 0;
  while (!window.Clerk?.session && attempts < 50) {
    await new Promise(resolve => setTimeout(resolve, 100));
    attempts++;
  }

  if (window.Clerk?.session) {
    try {
      return await window.Clerk.session.getToken();
    } catch (e) {
      console.error('Failed to get Clerk token:', e);
      return null;
    }
  }
  return null;
}

/**
 * Make an authenticated API request using Clerk token.
 *
 * WHAT: Wrapper around fetch that adds Clerk authentication.
 * WHY: All API calls need consistent auth handling.
 *
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Response>} - The fetch response
 */
export async function authFetch(url, options = {}) {
  const token = await getClerkToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });
}



export async function fetchWorkspaceKpis({
  workspaceId,
  metrics = ["spend", "revenue", "conversions", "roas"],
  lastNDays = 7,
  dayOffset = 0,
  compareToPrevious = true,
  sparkline = true,
  provider = null,
  level = null,
  onlyActive = false,
  customStartDate = null,
  customEndDate = null,
  entityName = null,
  campaignId = null
}) {
  const params = new URLSearchParams();
  if (provider) params.set("provider", provider);
  if (level) params.set("level", level);
  if (entityName) params.set("entity_name", entityName);
  if (campaignId) params.set("campaign_id", campaignId);
  if (onlyActive) params.set("only_active", "true");
  else params.set("only_active", "false");

  // Format dates as YYYY-MM-DD
  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Calculate time range based on different scenarios
  let timeRange;
  if (customStartDate && customEndDate) {
    // Use custom date range
    timeRange = {
      start: customStartDate,
      end: customEndDate
    };
  } else if (dayOffset > 0) {
    // Calculate specific dates for offset (e.g., yesterday)
    const end = new Date();
    end.setDate(end.getDate() - dayOffset);
    const start = new Date(end);
    start.setDate(start.getDate() - lastNDays + 1);

    timeRange = {
      start: formatDate(start),
      end: formatDate(end)
    };
  } else {
    // Use last_n_days for regular cases
    timeRange = { last_n_days: lastNDays };
  }

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/kpis?${params.toString()}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      metrics,
      time_range: timeRange,
      compare_to_previous: compareToPrevious,
      sparkline
    })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`KPI fetch failed: ${res.status} ${msg}`);
  }
  return res.json();
}


/**
 * Fetch dashboard KPIs with smart data source selection.
 *
 * WHAT: Gets KPIs for the dashboard with Shopify-first data sourcing
 * WHY: Shows "real" revenue from Shopify instead of inflated platform numbers
 * HOW: Backend checks for Shopify connection and switches data source
 *
 * @param {string} workspaceId - Workspace UUID
 * @param {string} timeframe - One of: today, yesterday, last_7_days, last_30_days
 * @returns {Promise<{kpis: Array, data_source: string, has_shopify: boolean}>}
 */
export async function fetchDashboardKpis({ workspaceId, timeframe = 'last_7_days' }) {
  const res = await authFetch(
    `${BASE}/workspaces/${workspaceId}/dashboard/kpis?timeframe=${timeframe}`,
    {
      method: 'GET',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' }
    }
  );
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Dashboard KPI fetch failed: ${res.status} ${msg}`);
  }
  return res.json();
}


// Call backend QA endpoint (DSL v1.1) - Async Job Queue Version.
// WHY: LLM/DB operations can take 5-30 seconds, causing HTTP timeouts.
//      Using async job queue prevents timeouts and enables production reliability.
//
// Flow:
// 1. POST /qa → Returns { job_id, status: "queued" }
// 2. Poll GET /qa/jobs/{job_id} → { status, answer, executed_dsl, data }
// 3. Repeat polling until status is "completed" or "failed"
//
// Returns:
// {
//   answer: "Your ROAS for the selected period is 2.45...",
//   executed_dsl: { metric: "roas", time_range: {...}, ... },
//   data: { summary: 2.45, previous: 2.06, delta_pct: 0.189, timeseries: [...], breakdown: [...] }
// }
//
// The backend uses a DSL pipeline:
// 1. Canonicalize question (synonym mapping)
// 2. Translate to DSL via LLM (GPT-4o-mini, temp=0, JSON mode)
// 3. Validate DSL (Pydantic)
// 4. Plan execution (resolve dates, map metrics)
// 5. Execute via SQLAlchemy (workspace-scoped, safe math)
// 6. Build human-readable answer (template-based)
// 7. Log to telemetry (success/failure tracking)
export async function fetchQA({ workspaceId, question, context = {}, maxRetries = 30, pollInterval = 2000 }) {
  // Append context to question if provided
  let finalQuestion = question;
  if (context && Object.keys(context).length > 0) {
    const contextStr = Object.entries(context)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    finalQuestion = `${question} (Context: ${contextStr})`;
  }

  // Step 1: Enqueue the job
  const enqueueRes = await authFetch(
    `${BASE}/qa/?workspace_id=${workspaceId}`,
    {
      method: "POST",
      body: JSON.stringify({ question: finalQuestion })
    }
  );
  if (!enqueueRes.ok) {
    const msg = await enqueueRes.text();
    throw new Error(`QA enqueue failed: ${enqueueRes.status} ${msg}`);
  }
  const { job_id } = await enqueueRes.json();

  // Step 2: Poll for results
  for (let i = 0; i < maxRetries; i++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusRes = await authFetch(
      `${BASE}/qa/jobs/${job_id}`,
      {
        method: "GET",
      }
    );

    if (!statusRes.ok) {
      const msg = await statusRes.text();
      throw new Error(`QA status poll failed: ${statusRes.status} ${msg}`);
    }

    const status = await statusRes.json();

    if (status.status === "completed") {
      return {
        answer: status.answer,
        executed_dsl: status.executed_dsl,
        data: status.data,
        context_used: status.context_used,
        visuals: status.visuals
      };
    } else if (status.status === "failed") {
      throw new Error(status.error || "QA job failed");
    }

    // If queued or processing, continue polling
  }

  throw new Error("QA job polling timeout - job took too long to complete");
}

// =============================================================================
// AGENTIC COPILOT ENDPOINT (NEW - v4.0)
// =============================================================================
// WHAT: Uses LangGraph agent with Claude for fully agentic responses
// WHY: Understands natural language better, handles "why" questions,
//      provides insightful analysis, not just data retrieval.
//
// This is a SYNCHRONOUS endpoint for simplicity.
// Use /qa/agent + /qa/agent/stream/{job_id} for streaming in production.
//
// CALLBACKS:
// - onStage(stage): Called when agent state changes ("understanding", "processing", etc.)
// - onToken(token): Called for each answer token (typing effect)
// - onToolEvent(event): NEW - Called for tool_start and tool_end events
//   - { type: "tool_start", tool: "query_metrics", args: {...}, description: "..." }
//   - { type: "tool_end", tool: "query_metrics", preview: "...", success: true, duration_ms: 234, data_source: "snapshots" }
//
// REFERENCES:
// - backend/app/agent/ (LangGraph agent)
// - backend/app/routers/qa.py (POST /qa/agent/sync)
export async function fetchQAAgent({ workspaceId, question, context = {}, onStage, onToken, onToolEvent }) {
  // Append context to question if provided
  let finalQuestion = question;
  if (context && Object.keys(context).length > 0) {
    const contextStr = Object.entries(context)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    finalQuestion = `${question} (Context: ${contextStr})`;
  }

  // Notify stage
  onStage?.('understanding');

  const res = await authFetch(`${BASE}/qa/agent/sse?workspace_id=${workspaceId}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: finalQuestion })
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Agent QA failed: ${res.status} ${msg}`);
  }

  // Process SSE stream
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult = null;
  let toolEvents = []; // Collect tool events for final result

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    const chunk = decoder.decode(value, { stream: true });
    buffer += chunk;

    // Split on double newline (SSE event separator)
    const events = buffer.split('\n\n');
    buffer = events.pop() || ''; // Keep incomplete event in buffer

    for (const eventBlock of events) {
      const lines = eventBlock.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));

            switch (event.type) {
              case 'thinking':
                onStage?.(event.data);
                break;

              case 'tool_start':
                // NEW: Tool execution started
                {
                  const toolEvent = {
                    type: 'tool_start',
                    tool: event.data.tool,
                    args: event.data.args,
                    description: event.data.description,
                    timestamp: Date.now(),
                  };
                  toolEvents.push(toolEvent);
                  onToolEvent?.(toolEvent);
                }
                break;

              case 'tool_end':
                // NEW: Tool execution finished
                {
                  const toolEvent = {
                    type: 'tool_end',
                    tool: event.data.tool,
                    preview: event.data.preview,
                    success: event.data.success,
                    duration_ms: event.data.duration_ms,
                    data_source: event.data.data_source,
                    timestamp: Date.now(),
                  };
                  toolEvents.push(toolEvent);
                  onToolEvent?.(toolEvent);
                }
                break;

              // Legacy events (for backwards compatibility)
              case 'tool_call':
                {
                  const toolEvent = {
                    type: 'tool_start',
                    tool: event.data.tool,
                    args: event.data.args,
                    timestamp: Date.now(),
                  };
                  toolEvents.push(toolEvent);
                  onToolEvent?.(toolEvent);
                }
                break;

              case 'tool_result':
                {
                  const toolEvent = {
                    type: 'tool_end',
                    tool: event.data.tool,
                    preview: event.data.preview,
                    success: event.data.success ?? true,
                    timestamp: Date.now(),
                  };
                  toolEvents.push(toolEvent);
                  onToolEvent?.(toolEvent);
                }
                break;

              case 'token':
                if (onToken) {
                  onToken(event.data);
                }
                break;

              case 'visual':
                // Visuals received, will be in final result
                break;

              case 'done':
                finalResult = event.data;
                break;

              case 'error':
                throw new Error(event.data);
            }
          } catch (e) {
            // Re-throw if it's an actual error from the event
            if (e.message === event?.data) {
              throw e;
            }
            // Otherwise ignore parse errors for malformed SSE chunks
          }
        }
      }
    }
  }

  if (!finalResult) {
    throw new Error('No result received from agent');
  }

  // Map agent response to expected format
  return {
    answer: finalResult.answer,
    executed_dsl: finalResult.semantic_query,
    data: finalResult.data,
    visuals: finalResult.visuals,
    context_used: [],
    intent: finalResult.intent,
    error: finalResult.error,
    // NEW: Include tool events and data sources
    toolEvents: toolEvents,
    toolCallsMade: finalResult.tool_calls_made || [],
  };
}


// =============================================================================
// SEMANTIC QA ENDPOINT (v3.0 - fallback)
// =============================================================================
// WHAT: Uses the new Semantic Layer for composable queries
// WHY: Enables queries that were impossible before:
//      - "Compare CPC for top 3 ads this week vs last week" (breakdown + comparison)
//      - "Graph daily spend for top 5 campaigns" (breakdown + timeseries)
//
// This is a SYNCHRONOUS endpoint (no Redis queue, no SSE streaming).
// Simpler and faster for most queries.
//
// REFERENCES:
// - backend/app/services/semantic_qa_service.py
// - backend/app/semantic/ (the semantic layer)
export async function fetchQASemantic({ workspaceId, question, context = {}, onStage }) {
  // Append context to question if provided
  let finalQuestion = question;
  if (context && Object.keys(context).length > 0) {
    const contextStr = Object.entries(context)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    finalQuestion = `${question} (Context: ${contextStr})`;
  }

  // Notify stage (semantic is synchronous, so just show "processing")
  onStage?.('processing');

  const res = await authFetch(`${BASE}/qa/semantic?workspace_id=${workspaceId}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: finalQuestion })
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Semantic QA failed: ${res.status} ${msg}`);
  }

  const result = await res.json();

  // Map semantic response to expected format
  return {
    answer: result.answer,
    executed_dsl: result.query,  // Semantic uses 'query' not 'executed_dsl'
    data: result.data,
    visuals: result.visuals,
    context_used: [],
    // NEW: Semantic-specific fields
    telemetry: result.telemetry,
    error: result.error
  };
}


// =============================================================================
// INSIGHTS ENDPOINT (Lightweight, no visuals)
// =============================================================================
//
// WHAT: Fetches AI-generated text insights WITHOUT visual generation.
// WHY: Optimized for dashboard widgets where visuals are already rendered.
//
// BENEFITS:
// - Faster response (skips visual building)
// - Lower token usage
// - Concise 2-3 sentence answers
//
// USAGE:
//   const insight = await fetchInsights({
//     workspaceId: '...',
//     question: 'What is my biggest performance drop this week?',
//     metricsData: { ... }  // Optional: pre-fetched metrics for context
//   });
//
// REFERENCES:
// - backend/app/routers/qa.py (POST /qa/insights)
export async function fetchInsights({ workspaceId, question, metricsData = null }) {
  const body = { question };
  if (metricsData) {
    body.metrics_data = metricsData;
  }

  const res = await authFetch(`${BASE}/qa/insights?workspace_id=${workspaceId}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Insights request failed: ${res.status} ${msg}`);
  }

  const result = await res.json();

  if (!result.success) {
    throw new Error(result.answer || 'Failed to generate insight');
  }

  return {
    answer: result.answer,
    intent: result.intent,
    // No visuals in insights response
    visuals: null,
    data: null
  };
}


// SSE Streaming version of QA endpoint (v2.1).
// WHAT: Uses Server-Sent Events for real-time progress updates instead of polling.
// WHY: Better UX with live stage updates ("Understanding...", "Fetching...", "Preparing...")
//      and eliminates polling overhead.
//
// Flow:
// 1. POST /qa/stream → Starts streaming SSE events
// 2. Receive stage updates: queued → translating → executing → formatting → complete
// 3. Call onStage callback for each stage change (UI updates)
// 4. Resolve with final result when complete
//
// REFERENCES:
// - backend/app/routers/qa.py (SSE endpoint)
// - backend/app/workers/qa_worker.py (stage metadata)
// - docs/living-docs/QA_SYSTEM_ARCHITECTURE.md
export async function fetchQAStream({ workspaceId, question, context = {}, onStage }) {
  // Append context to question if provided (same as fetchQA)
  let finalQuestion = question;
  if (context && Object.keys(context).length > 0) {
    const contextStr = Object.entries(context)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
    finalQuestion = `${question} (Context: ${contextStr})`;
  }

  return new Promise(async (resolve, reject) => {
    // Get Clerk token for auth
    let token = null;
    if (typeof window !== 'undefined' && window.Clerk?.session) {
      try {
        token = await window.Clerk.session.getToken();
      } catch (e) {
        console.error('Failed to get Clerk token:', e);
      }
    }

    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // POST to SSE endpoint
    fetch(`${BASE}/qa/stream?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ question: finalQuestion })
    })
      .then(response => {
        // Check for non-2xx response
        if (!response.ok) {
          return response.text().then(msg => {
            throw new Error(`QA stream failed: ${response.status} ${msg}`);
          });
        }

        // Get reader for streaming response body
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = ''; // Buffer for incomplete chunks

        // Recursive read function for streaming
        function read() {
          reader.read().then(({ done, value }) => {
            if (done) {
              // Stream ended without complete event (shouldn't happen)
              reject(new Error('Stream ended unexpectedly'));
              return;
            }

            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete lines (SSE format: "data: {...}\n\n")
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete chunk in buffer

            for (const line of lines) {
              // Parse SSE data lines
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));

                  // Handle different stages
                  if (data.stage === 'complete') {
                    // Job finished successfully - resolve with result
                    resolve({
                      answer: data.answer,
                      executed_dsl: data.executed_dsl,
                      data: data.data,
                      context_used: data.context_used,
                      visuals: data.visuals
                    });
                    return; // Stop reading
                  } else if (data.stage === 'error') {
                    // Job failed - reject with error
                    reject(new Error(data.error || 'QA job failed'));
                    return; // Stop reading
                  } else {
                    // Stage update - call callback if provided
                    // Stages: queued, translating, executing, formatting
                    onStage?.(data.stage, data.job_id);
                  }
                } catch {
                  // Ignore parse errors for malformed SSE chunks
                }
              }
            }

            // Continue reading
            read();
          }).catch(error => {
            reject(new Error(`Stream read error: ${error.message}`));
          });
        }

        // Start reading stream
        read();
      })
      .catch(reject);
  });
}

// Fetch workspace summary for sidebar.
// WHY: one tiny endpoint keeps sidebar up to date without heavy joins.
export async function fetchWorkspaceInfo(workspaceId) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/info`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to load workspace info: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Fetch workspace connection status for conditional UI rendering.
 *
 * WHAT: Returns flags indicating which platforms are connected
 * WHY: Frontend uses this to show/hide attribution components
 *
 * @param {string} workspaceId - Workspace UUID
 * @returns {Promise<{
 *   has_shopify: boolean,
 *   has_ad_platform: boolean,
 *   connected_platforms: string[],
 *   attribution_ready: boolean
 * }>}
 *
 * REFERENCES:
 *   - docs/living-docs/FRONTEND_REFACTOR_PLAN.md
 *   - backend/app/routers/workspaces.py (get_workspace_status)
 *
 * Example:
 *   const status = await fetchWorkspaceStatus(workspaceId);
 *   if (status.has_shopify) {
 *     // Show attribution widgets
 *   }
 */
export async function fetchWorkspaceStatus({ workspaceId }) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/status`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch workspace status: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function fetchWorkspaces() {
  const res = await authFetch(`${BASE}/workspaces`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch workspaces: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function switchWorkspace(workspaceId) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/switch`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to switch workspace: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function createWorkspace({ name }) {
  const res = await authFetch(`${BASE}/workspaces`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to create workspace: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function deleteWorkspace(workspaceId) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}`, {
    method: "DELETE",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to delete workspace: ${res.status} ${msg}`);
  }
  return res.json();
}
export async function renameWorkspace({ workspaceId, name }) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to rename workspace: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function fetchQaLog(workspaceId) {
  const res = await authFetch(`${BASE}/qa-log/${workspaceId}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch QA log: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function createQaLog(workspaceId, { question_text, answer_text, dsl_json }) {
  const res = await authFetch(`${BASE}/qa-log/${workspaceId}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_text, answer_text, dsl_json })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to create QA log: ${res.status} ${msg}`);
  }
  return res.json();
}

// Fetch available providers (ad platforms) in workspace.
// WHY: Dynamic provider filter buttons in Analytics page.
// Returns: { providers: ["google", "meta", "tiktok", "other"] }
export async function fetchWorkspaceProviders({ workspaceId }) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/providers`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch providers: ${res.status} ${msg}`);
  }
  return res.json();
}

// Fetch campaigns for dropdown filtering.
// WHY: Chart grouping by campaign requires campaign list.
// Returns: { campaigns: [{ id, name, status }, ...] }
export async function fetchWorkspaceCampaigns({
  workspaceId,
  provider = null,
  status = 'active'
}) {
  const params = new URLSearchParams();
  if (provider) params.set('provider', provider);
  if (status) params.set('entity_status', status);

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/campaigns?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch campaigns: ${res.status} ${msg}`);
  }
  return res.json();
}

// Fetch ad platform connections for workspace.
// WHY: Settings page needs to display connected accounts.
// Returns: { connections: [{ id, provider, name, external_account_id, status, connected_at }, ...], total: number }
export async function fetchConnections({ workspaceId, provider = null, status = null }) {
  const params = new URLSearchParams();
  if (provider) params.set('provider', provider);
  if (status) params.set('status', status);

  const res = await authFetch(`${BASE}/connections?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch connections: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Delete a connection
 */
export async function deleteConnection(connectionId) {
  const res = await authFetch(`${BASE}/connections/${connectionId}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to delete connection: ${res.status} ${msg}`);
  }

  return res.json();
}

// Ensure Google connection exists using server-side env.
// WHAT: Creates or updates a Google connection and stores encrypted refresh token.
// WHY: Temporary path before OAuth UI; enables sync button to appear.
export async function ensureGoogleConnectionFromEnv() {
  const res = await authFetch(`${BASE}/connections/google/from-env`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    // Return null on failure to avoid blocking Settings load
    return null;
  }
  return res.json();
}

// Ensure Meta connection exists using server-side env.
// WHAT: Creates or updates a Meta connection and stores encrypted access token.
// WHY: Temporary path before OAuth UI; enables sync button to appear.
export async function ensureMetaConnectionFromEnv() {
  const res = await authFetch(`${BASE}/connections/meta/from-env`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    // Return null on failure to avoid blocking Settings load
    return null;
  }
  return res.json();
}

// Enqueue async sync job for a connection.
// Returns: { job_id, status }
export async function enqueueSyncJob({ connectionId }) {
  const res = await authFetch(`${BASE}/connections/${connectionId}/sync-now`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to enqueue sync: ${res.status} ${msg}`);
  }
  return res.json();
}

// Update sync frequency.
export async function updateSyncFrequency({ connectionId, syncFrequency }) {
  const res = await authFetch(`${BASE}/connections/${connectionId}/sync-frequency`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sync_frequency: syncFrequency })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to update sync frequency: ${res.status} ${msg}`);
  }
  return res.json();
}

// Fetch sync status for a connection.
export async function getSyncStatus({ connectionId }) {
  const res = await authFetch(`${BASE}/connections/${connectionId}/sync-status`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch sync status: ${res.status} ${msg}`);
  }
  return res.json();
}

// =============================================================================
// AUTH FUNCTIONS (Clerk Migration 2025-12-09)
// =============================================================================
// Most auth functions are now handled by Clerk:
// - updateProfile → Clerk UserProfile component
// - changePassword → Clerk UserProfile component
// - requestPasswordReset → Clerk handles this
// - confirmPasswordReset → Clerk handles this
// - verifyEmail → Clerk handles this
//
// REMAINING: deleteUserAccount - still needed to clean up local workspace data
// before Clerk user deletion (called from ProfileTab.jsx)
//
// REFERENCES:
// - backend/app/routers/clerk_webhooks.py (handles user lifecycle sync)
// - backend/app/routers/auth.py (delete-account endpoint)
// - https://clerk.com/docs/components/user/user-profile
// =============================================================================

/**
 * Delete the current user's account and all associated workspace data.
 *
 * WHAT: Calls backend to delete all local data (connections, entities, metrics, etc.)
 * WHY: GDPR/CCPA compliance - users have right to data deletion
 *
 * NOTE: After calling this, you should also delete the Clerk user via
 * `useClerk().user.delete()` to complete the account deletion.
 *
 * @returns {Promise<object>} - { detail: "Account deleted successfully" }
 * @throws {Error} - If deletion fails
 *
 * REFERENCES:
 * - backend/app/routers/auth.py:605-740 (DELETE /auth/delete-account)
 */
export async function deleteUserAccount() {
  const res = await authFetch(`${BASE}/auth/delete-account`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete account');
  }

  return res.json();
}

export async function fetchEntityPerformance({
  workspaceId,
  entityType = 'campaign',
  timeRange = { last_n_days: 7 },
  limit = 25,
  sortBy = 'roas',
  sortDir = 'desc',
  status = 'active',
  campaignId = null,
  provider = null
}) {
  const params = new URLSearchParams();
  params.set('entity_level', entityType);
  params.set('page_size', limit);
  params.set('sort_by', sortBy);
  params.set('sort_dir', sortDir);
  params.set('status', status);
  if (campaignId) params.set('parent_id', campaignId);
  if (provider) params.set('platform', provider);

  if (timeRange.start && timeRange.end) {
    // Custom date range - backend expects date_end to be exclusive
    // FastAPI defaults timeframe=7d, so explicitly mark custom ranges
    params.set('timeframe', 'custom');
    params.set('date_start', timeRange.start);

    const endDate = new Date(timeRange.end);
    endDate.setDate(endDate.getDate() + 1); // Make end exclusive
    params.set('date_end', endDate.toISOString().split('T')[0]);
  } else if (timeRange.last_n_days) {
    // Use timeframe param for known presets (backend prefers this)
    if (timeRange.last_n_days === 7) {
      params.set('timeframe', '7d');
    } else if (timeRange.last_n_days === 30) {
      params.set('timeframe', '30d');
    } else {
      // For other values (like 1 for yesterday), convert to actual dates
      params.set('timeframe', 'custom');
      const end = new Date();
      end.setDate(end.getDate() + 1); // Make end exclusive (tomorrow)
      const start = new Date();
      start.setDate(start.getDate() - timeRange.last_n_days + 1);

      params.set('date_start', start.toISOString().split('T')[0]);
      params.set('date_end', end.toISOString().split('T')[0]);
    }
  }

  const res = await authFetch(`${BASE}/entity-performance/list?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch entity performance: ${res.status} ${msg}`);
  }

  // Transform response to match expected format if needed,
  // but for now return as is (TopCreative expects .items which might be .rows in actual response)
  const data = await res.json();
  return { items: data.rows, meta: data.meta };
}

/**
 * Fetch immediate children entities for drill-down (campaign → ad sets → ads/creatives).
 *
 * WHAT: Mirrors `GET /entity-performance/{entity_id}/children`
 * WHY: Analytics "command center" needs ad-level filtering without loading full breakdown tables.
 *
 * NOTE: Backend expects `date_end` to be exclusive (same as `fetchEntityPerformance`).
 */
export async function fetchEntityChildren({
  entityId,
  timeRange = { last_n_days: 7 },
  limit = 50,
  sortBy = "roas",
  sortDir = "desc",
  status = "active",
  provider = null,
}) {
  const params = new URLSearchParams();
  params.set("page_size", String(limit));
  params.set("sort_by", sortBy);
  params.set("sort_dir", sortDir);
  params.set("status", status);
  if (provider) params.set("platform", provider);

  if (timeRange.start && timeRange.end) {
    // Custom date range - backend expects date_end to be exclusive
    params.set("timeframe", "custom");
    params.set("date_start", timeRange.start);

    const endDate = new Date(timeRange.end);
    endDate.setDate(endDate.getDate() + 1); // Make end exclusive
    params.set("date_end", endDate.toISOString().split("T")[0]);
  } else if (timeRange.last_n_days) {
    if (timeRange.last_n_days === 7) {
      params.set("timeframe", "7d");
    } else if (timeRange.last_n_days === 30) {
      params.set("timeframe", "30d");
    } else {
      // Convert to custom dates (end exclusive)
      params.set("timeframe", "custom");
      const end = new Date();
      end.setDate(end.getDate() + 1);
      const start = new Date();
      start.setDate(start.getDate() - timeRange.last_n_days + 1);
      params.set("date_start", start.toISOString().split("T")[0]);
      params.set("date_end", end.toISOString().split("T")[0]);
    }
  }

  const res = await authFetch(`${BASE}/entity-performance/${entityId}/children?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch entity children: ${res.status} ${msg}`);
  }

  const data = await res.json();
  return { items: data.rows, meta: data.meta };
}

// =============================================================================
// ATTRIBUTION & PIXEL HEALTH
// =============================================================================

/**
 * Fetch pixel health status and event statistics.
 * WHAT: Returns pixel status, event counts, health score, and issues
 * WHY: Users need visibility into whether their pixel is working
 *
 * @param {string} workspaceId - The workspace UUID
 * @returns {Promise<Object>} Pixel health data
 */
export async function fetchPixelHealth({ workspaceId }) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/pixel/health`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch pixel health: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Reinstall the Shopify web pixel.
 * WHAT: Deletes existing pixel and creates a new one
 * WHY: Sometimes pixels need to be reset if they're not working
 *
 * @param {string} workspaceId - The workspace UUID
 * @returns {Promise<Object>} Reinstall result with old/new pixel IDs
 */
export async function reinstallPixel({ workspaceId }) {
  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/pixel/reinstall`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to reinstall pixel: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Fetch attribution summary by channel/provider.
 * WHAT: Returns revenue attribution breakdown by provider and confidence
 * WHY: Users need to see which channels drive their sales
 *
 * @param {string} workspaceId - The workspace UUID
 * @param {number} days - Number of days to analyze (default 30)
 * @returns {Promise<Object>} Attribution summary data
 */
export async function fetchAttributionSummary({ workspaceId, days = 30 }) {
  const params = new URLSearchParams();
  params.set("days", days.toString());

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/attribution/summary?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch attribution summary: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Fetch top campaigns by attributed revenue.
 * WHAT: Returns campaigns ranked by attributed revenue
 * WHY: Users need to see which campaigns are performing best
 *
 * @param {string} workspaceId - The workspace UUID
 * @param {number} days - Number of days to analyze (default 30)
 * @param {number} limit - Max campaigns to return (default 20)
 * @returns {Promise<Object>} Attributed campaigns data
 */
export async function fetchAttributedCampaigns({ workspaceId, days = 30, limit = 20 }) {
  const params = new URLSearchParams();
  params.set("days", days.toString());
  params.set("limit", limit.toString());

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/attribution/campaigns?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch attributed campaigns: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Fetch recent attribution feed for live display.
 * WHAT: Returns recent attributions in chronological order
 * WHY: Users want real-time visibility into attribution activity
 *
 * @param {string} workspaceId - The workspace UUID
 * @param {number} limit - Max items to return (default 20)
 * @returns {Promise<Object>} Attribution feed data
 */
export async function fetchAttributionFeed({ workspaceId, limit = 20 }) {
  const params = new URLSearchParams();
  params.set("limit", limit.toString());

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/attribution/feed?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch attribution feed: ${res.status} ${msg}`);
  }
  return res.json();
}

/**
 * Fetch campaign attribution warnings.
 * WHAT: Returns campaigns that have attribution issues
 * WHY: Users need to know which campaigns aren't being tracked properly
 *
 * @param {string} workspaceId - The workspace UUID
 * @param {number} days - Number of days to analyze (default 30)
 * @returns {Promise<Object>} Campaign warnings data
 */
export async function fetchCampaignWarnings({ workspaceId, days = 30 }) {
  const params = new URLSearchParams();
  params.set("days", days.toString());

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/attribution/warnings?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch campaign warnings: ${res.status} ${msg}`);
  }
  return res.json();
}


// =============================================================================
// UNIFIED DASHBOARD ENDPOINT
// =============================================================================
//
// WHAT: Fetches ALL dashboard data in a single request
// WHY: Reduces 8+ API calls to 1, dramatically improving dashboard load time
//
// RETURNS:
// - kpis: Array of KPI data (revenue, ROAS, spend, conversions)
// - chart_data: Merged sparkline data for charts
// - top_creatives: Top 3 performing ads
// - spend_mix: Spend breakdown by platform
// - attribution_summary: Attribution by channel (if Shopify connected)
// - attribution_feed: Recent attribution events (if Shopify connected)
//
// USAGE:
//   const data = await fetchUnifiedDashboard({
//     workspaceId: '...',
//     timeframe: 'last_7_days'  // today, yesterday, last_7_days, last_30_days
//   });
//
// REFERENCES:
// - backend/app/routers/dashboard.py (GET /workspaces/{id}/dashboard/unified)
// - docs/PERFORMANCE_INVESTIGATION.md
export async function fetchUnifiedDashboard({
  workspaceId,
  timeframe = 'last_7_days',
  startDate = null,
  endDate = null,
  platform = null
}) {
  const params = new URLSearchParams();
  params.set("timeframe", timeframe);

  // Use custom dates if provided (for custom date range selection)
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);

  // Platform filter (google, meta) - filters all metrics to single platform
  if (platform) params.set("platform", platform);

  const res = await authFetch(`${BASE}/workspaces/${workspaceId}/dashboard/unified?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch unified dashboard: ${res.status} ${msg}`);
  }

  return res.json();
}


// =============================================================================
// DAILY REVENUE BAR CHART ENDPOINT
// =============================================================================
//
// WHAT: Fetches daily revenue data for bar chart visualization
// WHY: Server-side aggregation - one bar per day, frontend just renders
//
// USAGE:
//   const data = await fetchDailyRevenue({
//     workspaceId: '...',
//     days: 7  // 7 for week, 30 for month
//   });
//
// RESPONSE:
//   { bars: [{date, day_name, revenue, is_today}], total_revenue, average_revenue, highest_day }
//
// REFERENCES:
// - backend/app/routers/analytics.py (GET /analytics/daily-revenue)
export async function fetchDailyRevenue({ workspaceId, days = 7 }) {
  const params = new URLSearchParams();
  params.set('workspace_id', workspaceId);
  params.set('days', days.toString());

  const res = await authFetch(`${BASE}/analytics/daily-revenue?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Daily revenue fetch failed: ${res.status} ${msg}`);
  }

  return res.json();
}


// =============================================================================
// ANALYTICS CHART ENDPOINT (Production - Server-side filtering)
// =============================================================================
//
// WHAT: Fetches chart data with server-side platform/campaign filtering
// WHY: Frontend should be dumb - backend handles all filtering for performance
//
// RESPONSE FORMAT:
// {
//   series: [{ key, label, color, data: [{date, revenue, spend, roas, ...}] }],
//   totals: { revenue, spend, roas, conversions, ... },
//   metadata: { granularity, period_start, period_end, platforms_available, ... }
// }
//
// USAGE:
//   const data = await fetchAnalyticsChart({
//     workspaceId: '...',
//     timeframe: 'last_7_days',
//     platforms: ['google', 'meta'],  // Optional filter
//     campaignIds: ['uuid1', 'uuid2'],  // Optional filter
//     groupBy: 'platform'  // total | platform | campaign
//   });
//
// REFERENCES:
// - backend/app/routers/analytics.py (GET /analytics/chart)
export async function fetchAnalyticsChart({
  workspaceId,
  timeframe = 'last_7_days',
  startDate = null,
  endDate = null,
  platforms = null,
  campaignIds = null,
  groupBy = 'total'
}) {
  const params = new URLSearchParams();
  params.set('workspace_id', workspaceId);
  params.set('timeframe', timeframe);
  params.set('group_by', groupBy);

  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  if (platforms && platforms.length > 0) {
    params.set('platforms', platforms.join(','));
  }
  if (campaignIds && campaignIds.length > 0) {
    params.set('campaign_ids', campaignIds.join(','));
  }

  const res = await authFetch(`${BASE}/analytics/chart?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Analytics chart fetch failed: ${res.status} ${msg}`);
  }

  return res.json();
}


// =============================================================================
// ENTITY TIMESERIES
// =============================================================================
//
// WHAT: Fetches timeseries data for a specific entity (campaign/adset/ad)
// WHY: Analytics drill-down needs chart data at any hierarchy level
//
// USAGE:
//   const data = await fetchEntityTimeseries({
//     workspaceId: '...',
//     entityId: 'campaign-uuid',
//     entityLevel: 'campaign',  // campaign, adset, ad
//     metrics: ['spend', 'revenue', 'roas'],
//     timeRange: { last_n_days: 30 }  // or { start: '2024-01-01', end: '2024-01-31' }
//   });
//
// REFERENCES:
// - backend/app/routers/entity_performance.py
export async function fetchEntityTimeseries({
  workspaceId,
  entityId,
  entityLevel = 'campaign',
  metrics = ['spend', 'revenue', 'roas'],
  timeRange = { last_n_days: 7 }
}) {
  // For now, we use the existing fetchWorkspaceKpis with campaignId parameter
  // The backend aggregates child entity metrics up to the selected entity
  // Future enhancement: dedicated endpoint for entity-level timeseries

  const params = {
    workspaceId,
    metrics,
    sparkline: true,
    compareToPrevious: false,
    campaignId: entityId
  };

  if (timeRange.start && timeRange.end) {
    params.customStartDate = timeRange.start;
    params.customEndDate = timeRange.end;
  } else if (timeRange.last_n_days) {
    params.lastNDays = timeRange.last_n_days;
  }

  return fetchWorkspaceKpis(params);
}


// =============================================================================
// AGENT SYSTEM API
// =============================================================================
//
// WHAT: API functions for the autonomous monitoring agent system
// WHY: Agents watch performance metrics and take automated actions
//
// USAGE:
//   const agents = await fetchAgents({ workspaceId });
//   const agent = await createAgent({ workspaceId, name, condition, actions, ... });
//   await pauseAgent({ agentId, workspaceId });
//   await resumeAgent({ agentId, workspaceId });
//
// REFERENCES:
// - backend/app/routers/agents.py
// - backend/app/services/agents/

/**
 * Fetch all agents for a workspace.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.status - Filter by status (active, paused, error, draft)
 * @param {number} params.limit - Max agents to return
 * @param {number} params.offset - Pagination offset
 * @returns {Promise<Object>} { items: Agent[], meta: { total, limit, offset } }
 */
export async function fetchAgents({ workspaceId, status = null, limit = 50, offset = 0 }) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());

  const res = await authFetch(`${BASE}/agents?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch agents: ${res.status} ${msg}`);
  }

  // Transform backend response {agents, total} to frontend format {items, meta}
  const data = await res.json();
  return {
    items: data.agents || [],
    meta: {
      total: data.total || 0,
      limit,
      offset
    }
  };
}

/**
 * Get a single agent by ID.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @returns {Promise<Object>} Agent details with current states
 */
export async function fetchAgent({ workspaceId, agentId }) {
  const res = await authFetch(`${BASE}/agents/${agentId}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Create a new agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.name - Agent name
 * @param {string} params.description - Agent description
 * @param {string} params.scope_type - Scope type (all, filter, specific)
 * @param {Object} params.scope_config - Scope configuration
 * @param {Object} params.condition - Condition tree
 * @param {Object} params.accumulation - Accumulation config
 * @param {Object} params.trigger - Trigger mode config
 * @param {Array} params.actions - Array of action configurations
 * @param {Object} params.safety - Safety configuration (optional)
 * @param {Object} params.schedule - Schedule configuration (optional)
 * @param {boolean} params.condition_required - Whether condition must be met (optional)
 * @param {Object} params.date_range - Date range configuration (optional)
 * @param {string} params.status - Initial status (active, draft)
 * @returns {Promise<Object>} Created agent
 */
export async function createAgent({
  workspaceId,
  name,
  description = null,
  scope_type = 'all',
  scope_config = { level: 'campaign' },
  condition,
  accumulation = { required: 1, unit: 'evaluations', mode: 'consecutive' },
  trigger = { mode: 'once' },
  actions,
  safety = null,
  schedule,
  condition_required,
  date_range,
  status = 'active'
}) {
  const res = await authFetch(`${BASE}/agents`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      description,
      scope_type,
      scope_config,
      condition,
      accumulation,
      trigger,
      actions,
      safety,
      schedule,
      condition_required,
      date_range,
      status
    })
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to create agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Update an existing agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @param {Object} params.updates - Fields to update
 * @returns {Promise<Object>} Updated agent
 */
export async function updateAgent({ workspaceId, agentId, updates }) {
  const res = await authFetch(`${BASE}/agents/${agentId}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to update agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Delete an agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @returns {Promise<void>}
 */
export async function deleteAgent({ workspaceId, agentId }) {
  const res = await authFetch(`${BASE}/agents/${agentId}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to delete agent: ${res.status} ${msg}`);
  }
}

/**
 * Pause an agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @returns {Promise<Object>} Updated agent
 */
export async function pauseAgent({ workspaceId, agentId }) {
  const res = await authFetch(`${BASE}/agents/${agentId}/pause`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to pause agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Resume a paused agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @returns {Promise<Object>} Updated agent
 */
export async function resumeAgent({ workspaceId, agentId }) {
  const res = await authFetch(`${BASE}/agents/${agentId}/resume`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to resume agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Test an agent (dry run evaluation).
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @returns {Promise<Object>} Test evaluation results
 */
export async function testAgent({ workspaceId, agentId }) {
  const res = await authFetch(`${BASE}/agents/${agentId}/test`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to test agent: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Fetch evaluation events for an agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @param {string} params.result_type - Filter by result type (triggered, condition_met, condition_not_met, cooldown, error)
 * @param {number} params.limit - Max events to return
 * @param {number} params.offset - Pagination offset
 * @returns {Promise<Object>} { items: Event[], meta: { total, limit, offset } }
 */
export async function fetchAgentEvents({ workspaceId, agentId, result_type = null, limit = 50, offset = 0 }) {
  const params = new URLSearchParams();
  if (result_type) params.set('result_type', result_type);
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());

  const res = await authFetch(`${BASE}/agents/${agentId}/events?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch agent events: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Fetch action executions for an agent.
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.agentId - Agent UUID
 * @param {number} params.limit - Max actions to return
 * @param {number} params.offset - Pagination offset
 * @returns {Promise<Object>} { items: Action[], meta: { total, limit, offset } }
 */
export async function fetchAgentActions({ workspaceId, agentId, limit = 50, offset = 0 }) {
  const params = new URLSearchParams();
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());

  const res = await authFetch(`${BASE}/agents/${agentId}/actions?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch agent actions: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Fetch aggregate stats for all agents in workspace.
 *
 * WHAT: Returns dashboard-level metrics for agent system health
 * WHY: Agents dashboard needs quick overview of agent activity
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID (not used in request, but kept for API consistency)
 * @returns {Promise<Object>} { active_agents, triggers_today, evaluations_this_hour, errors_today }
 *
 * REFERENCES:
 * - ui/components/agents/AgentStatsGrid.jsx
 * - GET /v1/agents/stats endpoint
 */
export async function fetchAgentStats({ workspaceId }) {
  const res = await authFetch(`${BASE}/agents/stats`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch agent stats: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Fetch all evaluation events across all agents in workspace.
 *
 * WHAT: Returns paginated list of events for notification feed
 * WHY: Dashboard shows all agent activity in one feed with infinite scroll
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID (not used in request, but kept for consistency)
 * @param {string} params.resultType - Optional filter: 'triggered', 'error', etc.
 * @param {number} params.limit - Max events per page (default 20)
 * @param {string} params.cursor - Cursor for pagination (ISO datetime of last event)
 * @returns {Promise<Object>} { events: [], total: number, next_cursor: string|null }
 *
 * REFERENCES:
 * - ui/components/agents/NotificationFeed.jsx
 * - GET /v1/agents/events endpoint
 */
export async function fetchWorkspaceAgentEvents({
  workspaceId,
  resultType = null,
  limit = 20,
  cursor = null
}) {
  const params = new URLSearchParams();
  params.set('limit', limit.toString());

  if (resultType) {
    params.set('result_type', resultType);
  }

  if (cursor) {
    params.set('cursor', cursor);
  }

  const res = await authFetch(`${BASE}/agents/events?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch workspace agent events: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Rollback a previously executed action.
 *
 * WHAT: Restores state_before for reversible actions (scale_budget, pause_campaign)
 * WHY: Users need safety net for automated actions
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID (for access verification)
 * @param {string} params.actionId - Action execution UUID
 * @returns {Promise<Object>} { success, action_id, action_type, state_before, state_after, message }
 *
 * REFERENCES:
 * - ui/components/agents/NotificationItem.jsx
 * - POST /v1/agents/actions/{action_id}/rollback endpoint
 */
export async function rollbackAgentAction({ workspaceId, actionId }) {
  const res = await authFetch(`${BASE}/agents/actions/${actionId}/rollback`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to rollback action: ${res.status} ${msg}`);
  }

  return res.json();
}

/**
 * Fetch entities for agent scope selection.
 *
 * WHAT: Returns entities (campaigns, adsets, ads) filtered by platform and level
 * WHY: Agent creation wizard needs entity list for scope configuration
 *
 * @param {Object} params
 * @param {string} params.workspaceId - Workspace UUID
 * @param {string} params.platform - Platform filter (meta, google, all)
 * @param {string} params.level - Entity level (campaign, adset, ad)
 * @param {string} params.status - Status filter (active, paused, all)
 * @param {number} params.limit - Max entities to return
 * @returns {Promise<Object>} { items: Entity[], meta: { total } }
 *
 * REFERENCES:
 * - Uses fetchEntityPerformance under the hood
 * - ui/app/(dashboard)/agents/new/page.jsx (scope step)
 */
export async function fetchEntities({
  workspaceId,
  platform = null,
  level = 'campaign',
  status = 'all',
  limit = 100
}) {
  const params = new URLSearchParams();
  params.set('entity_level', level);
  params.set('page_size', limit.toString());
  params.set('sort_by', 'name');
  params.set('sort_dir', 'asc');

  // Map status filter
  if (status === 'all') {
    params.set('status', 'all');
  } else {
    params.set('status', status);
  }

  // Platform filter
  if (platform && platform !== 'all') {
    params.set('platform', platform);
  }

  // Use 7-day timeframe for basic entity listing
  params.set('timeframe', '7d');

  const res = await authFetch(`${BASE}/entity-performance/list?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' }
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to fetch entities: ${res.status} ${msg}`);
  }

  const data = await res.json();

  // Transform to simplified entity format for wizard
  // NOTE: Backend returns EntityPerformanceRow with `id`, `name`, `status` (not entity_*)
  const items = (data.rows || []).map(row => ({
    id: row.id,
    name: row.name,
    platform: row.platform,
    level: level,  // Use request param since all entities in response share same level
    status: row.status,
    // Include basic metrics for display
    spend: row.spend,
    revenue: row.revenue,
    roas: row.roas
  }));

  // Sort: active/enabled campaigns first, then alphabetically by name
  items.sort((a, b) => {
    const aActive = a.status?.toLowerCase() === 'active' || a.status?.toLowerCase() === 'enabled';
    const bActive = b.status?.toLowerCase() === 'active' || b.status?.toLowerCase() === 'enabled';

    if (aActive && !bActive) return -1;
    if (!aActive && bActive) return 1;
    return (a.name || '').localeCompare(b.name || '');
  });

  return {
    items,
    meta: {
      total: data.pagination?.total || items.length
    }
  };
}
