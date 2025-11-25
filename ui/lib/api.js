// API client focused on KPI consumption.
// All functions return plain JSON and throw on non-2xx.
// WHY: centralizing fetch keeps pages dumb and testable.

import { getApiBase } from './config';

const BASE = getApiBase();



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

  const res = await fetch(`${BASE}/workspaces/${workspaceId}/kpis?${params.toString()}`, {
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
  const enqueueRes = await fetch(
    `${BASE}/qa/?workspace_id=${workspaceId}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
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

    const statusRes = await fetch(
      `${BASE}/qa/jobs/${job_id}`,
      {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" }
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
        context_used: status.context_used
      };
    } else if (status.status === "failed") {
      throw new Error(status.error || "QA job failed");
    }

    // If queued or processing, continue polling
  }

  throw new Error("QA job polling timeout - job took too long to complete");
}

// Fetch workspace summary for sidebar.
// WHY: one tiny endpoint keeps sidebar up to date without heavy joins.
export async function fetchWorkspaceInfo(workspaceId) {
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/info`, {
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

export async function fetchWorkspaces() {
  const res = await fetch(`${BASE}/workspaces`, {
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
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/switch`, {
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
  const res = await fetch(`${BASE}/workspaces`, {
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
  const res = await fetch(`${BASE}/workspaces/${workspaceId}`, {
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
  const res = await fetch(`${BASE}/workspaces/${workspaceId}`, {
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
  const res = await fetch(`${BASE}/qa-log/${workspaceId}`, {
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
  const res = await fetch(`${BASE}/qa-log/${workspaceId}`, {
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
  const res = await fetch(`${BASE}/workspaces/${workspaceId}/providers`, {
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

  const res = await fetch(`${BASE}/workspaces/${workspaceId}/campaigns?${params.toString()}`, {
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

  const res = await fetch(`${BASE}/connections?${params.toString()}`, {
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
  const res = await fetch(`${BASE}/connections/${connectionId}`, {
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
  const res = await fetch(`${BASE}/connections/google/from-env`, {
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
  const res = await fetch(`${BASE}/connections/meta/from-env`, {
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
  const res = await fetch(`${BASE}/connections/${connectionId}/sync-now`, {
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
  const res = await fetch(`${BASE}/connections/${connectionId}/sync-frequency`, {
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
  const res = await fetch(`${BASE}/connections/${connectionId}/sync-status`, {
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

// Delete user account and all associated data
// WHAT: GDPR/CCPA compliant data deletion
// WHY: Users have the right to delete their data
// REFERENCES: Privacy Policy section 7.3
export async function deleteUserAccount() {
  const res = await fetch(`${BASE}/auth/delete-account`, {
    method: "DELETE",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to delete account: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function updateProfile({ name, email, avatar_url }) {
  const res = await fetch(`${BASE}/auth/me`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, avatar_url })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to update profile: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function changePassword({ old_password, new_password }) {
  const res = await fetch(`${BASE}/auth/change-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password, new_password })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to change password: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function requestPasswordReset({ email }) {
  const res = await fetch(`${BASE}/auth/forgot-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to request password reset: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function confirmPasswordReset({ token, new_password }) {
  const res = await fetch(`${BASE}/auth/reset-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to reset password: ${res.status} ${msg}`);
  }
  return res.json();
}

export async function verifyEmail({ token }) {
  const res = await fetch(`${BASE}/auth/verify-email`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token })
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Failed to verify email: ${res.status} ${msg}`);
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

  const res = await fetch(`${BASE}/entity-performance/list?${params.toString()}`, {
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
