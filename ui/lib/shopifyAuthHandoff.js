import { getApiBase } from "./config";
import { getEmbeddedSessionToken } from "./shopifyEmbedded";

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

function decodeBase64Url(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");

  if (typeof window !== "undefined" && typeof window.atob === "function") {
    return window.atob(padded);
  }

  return Buffer.from(padded, "base64").toString("utf-8");
}

function readStoredHandoff(sessionKey) {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw);
    if (!parsed?.handoffId || !parsed?.expiresAt || !parsed?.sessionKey) {
      window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
      return null;
    }

    if (parsed.expiresAt <= Date.now()) {
      window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
      return null;
    }

    if (!sessionKey || parsed.sessionKey !== sessionKey) {
      window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
      return null;
    }

    return parsed.handoffId;
  } catch {
    window.localStorage.removeItem(SHOPIFY_AUTH_HANDOFF_STORAGE_KEY);
    return null;
  }
}

export function persistShopifyAuthHandoff(handoffId, sessionKey) {
  if (typeof window === "undefined" || !handoffId || !sessionKey) {
    return null;
  }

  const payload = {
    handoffId,
    sessionKey,
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
  const sessionKey = getShopifySessionKey(search);

  if (handoffId) {
    return persistShopifyAuthHandoff(handoffId, sessionKey);
  }

  return readStoredHandoff(sessionKey);
}

export function getShopifySessionKey(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  const sessionKey = params.get("session");
  if (sessionKey) {
    return sessionKey;
  }

  const idToken = params.get("id_token");
  if (!idToken) {
    return null;
  }

  try {
    const [, payload] = idToken.split(".");
    if (!payload) {
      return null;
    }

    const claims = JSON.parse(decodeBase64Url(payload));
    return claims?.sid || null;
  } catch {
    return null;
  }
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
  const {
    handoffId: explicitHandoffId,
    headers: optionHeaders,
    ...fetchOptions
  } = options;
  const token = await getClerkToken();
  const handoffId = explicitHandoffId || getShopifyAuthHandoff();
  const headers = {
    ...optionHeaders,
  };

  if (!headers["Content-Type"] && !(fetchOptions.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else if (handoffId) {
    headers["X-Shopify-Auth-Handoff"] = handoffId;
  }

  const url = path.startsWith("http") ? path : `${getApiBase()}${path}`;

  return fetch(url, {
    ...fetchOptions,
    headers,
    credentials: "include",
  });
}

export async function createShopifyAuthHandoff({ sessionKey, shop } = {}) {
  if (!sessionKey) {
    throw new Error("Missing Shopify session key");
  }

  const response = await shopifyFlowFetch("/auth/shopify/handoff", {
    method: "POST",
    body: JSON.stringify({
      session_key: sessionKey,
      shop,
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Shopify auth handoff failed: ${response.status} ${message}`
    );
  }

  const data = await response.json();
  persistShopifyAuthHandoff(data.handoff_id, sessionKey);
  return data.handoff_id;
}

export async function resolveShopifyAuthHandoff({ sessionKey, search } = {}) {
  if (!sessionKey) {
    throw new Error("Missing Shopify session key");
  }

  const token = await getEmbeddedSessionToken(search);
  const response = await fetch(`${getApiBase()}/auth/shopify/handoff/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    credentials: "include",
    body: JSON.stringify({
      session_key: sessionKey,
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Shopify auth handoff resolve failed: ${response.status} ${message}`
    );
  }

  const data = await response.json();
  persistShopifyAuthHandoff(data.handoff_id, sessionKey);
  return data.handoff_id;
}
