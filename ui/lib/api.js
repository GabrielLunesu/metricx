// API client focused on KPI consumption.
// All functions return plain JSON and throw on non-2xx.
// WHY: centralizing fetch keeps pages dumb and testable.

import { getApiBase } from './config';

const BASE = getApiBase(); 



export async function fetchWorkspaceKpis({
  workspaceId,
  metrics = ["spend","revenue","conversions","roas"],
  lastNDays = 7,
  dayOffset = 0,
  compareToPrevious = true,
  sparkline = true,
  provider = null,
  level = null,
  onlyActive = false,
  customStartDate = null,
  customEndDate = null,
  entityName = null
}) {
  const params = new URLSearchParams();
  if (provider) params.set("provider", provider);
  if (level) params.set("level", level);
  if (entityName) params.set("entity_name", entityName);
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

// Call backend QA endpoint (DSL v1.1).
// WHY: isolate fetch logic, keeps components testable and clean.
//
// Returns:
// {
//   answer: "Your ROAS for the selected period is 2.45. That's a +19.0% change vs the previous period.",
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
export async function fetchQA({ workspaceId, question }) {
  const res = await fetch(
    `${BASE}/qa/?workspace_id=${workspaceId}`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    }
  );
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`QA failed: ${res.status} ${msg}`);
  }
  return res.json();
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
