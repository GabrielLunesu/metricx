import { getApiBase } from "./config";

export const SHOPIFY_AUTH_HANDOFF_QUERY_KEY = "shopify_handoff";

const SHOPIFY_AUTH_HANDOFF_STORAGE_KEY = "shopify:auth-handoff";
const SHOPIFY_AUTH_HANDOFF_TTL_MS = 10 * 60 * 1000;

function getCurrentSearch(search) {
  if (typeof search === "string") {
    return search;
  }

  if (typeof window === "undefined") {
    return "";
  }

  return window.location.search;
}

function readStoredHandoff() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    if (!parsed?.handoffId || !parsed?.expiresAt) {
      window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
      return null;
    }

    if (parsed.expiresAt <= Date.now()) {
      window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
      return null;
    }

    return parsed.handoffId;
  } catch {
    window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
    return null;
  }
}

export function persistShopifyAuthHandoff(handoffId) {
  if (typeof window === "undefined" || !handoffId) {
    return null;
  }

  const payload = {
    handoffId,
    expiresAt: Date.now() + SHOPIFY_AUTH_HANDOFF_TTL_MS,
  };

  window.localStorage.setItem(
    SHOPIFY_AUTH_HANDOFF_STORAGE_KEY,
    JSON.stringify(payload)
  );

  return handoffId;
}

export function clearShopifyAuthHandoff() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
}

export function getShopifyAuthHandoff(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  const handoffId = params.get(SHOPIFY_AUTH_HANDOFF_QUERY_KEY);

  if (handoffId) {
    return persistShopifyAuthHandoff(handoffId);
  }

  return readStoredHandoff();
}

export function appendShopifyAuthHandoff(path, handoffId) {
  if (!handoffId || typeof path !== "string" || !path) {
    return path;
  }

  const baseOrigin =
    typeof window !== "undefined" ? window.location.origin : "https://www.metricx.ai";
  const url = new URL(path, baseOrigin);

  url.searchParams.set(SHOPIFY_AUTH_HANDOFF_QUERY_KEY, handoffId);

  return `${url.pathname}${url.search}${url.hash}`;
}

async function getClerkToken() {
  if (typeof window === "undefined") {
    return null;
  }

  let attempts = 0;
  while (!window.Clerk?.session && attempts < 30) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    attempts += 1;
  }

  if (!window.Clerk?.session) {
    return null;
  }

  try {
    return await window.Clerk.session.getToken();
  } catch (error) {
    console.error("[shopify] Failed to get Clerk token:", error);
    return null;
  }
}

export async function shopifyFlowFetch(path, options = {}) {
  const token = await getClerkToken();
  const handoffId = getShopifyAuthHandoff();
  const headers = {
    ...options.headers,
  };

  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else if (handoffId) {
    headers["X-Shopify-Auth-Handoff"] = handoffId;
  }

  const url = path.startsWith("http") ? path : `${getApiBase()}${path}`;

  return fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });
}

export async function createShopifyAuthHandoff() {
  const response = await shopifyFlowFetch("/auth/shopify/handoff", {
    method: "POST",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Shopify auth handoff failed: ${response.status} ${message}`
    );
  }

  const data = await response.json();
  persistShopifyAuthHandoff(data.handoff_id);
  return data.handoff_id;
}
