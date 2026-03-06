import createApp from "@shopify/app-bridge";
import { getSessionToken } from "@shopify/app-bridge/utilities";

import {
  SHOPIFY_API_KEY,
  SHOPIFY_EMBEDDED_QUERY_KEYS,
} from "./shopifyConfig";

const SHOPIFY_EMBEDDED_STORAGE_KEY = "shopify:embedded-query";

function getCurrentSearch(search) {
  if (typeof search === "string") {
    return search;
  }

  if (typeof window === "undefined") {
    return "";
  }

  return window.location.search;
}

export function isShopifyEmbeddedContext(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  return (
    params.get("embedded") === "1" ||
    params.has("host") ||
    params.has("shop")
  );
}

function getStoredEmbeddedParams() {
  if (typeof window === "undefined") {
    return new URLSearchParams();
  }

  return new URLSearchParams(
    window.sessionStorage.getItem(SHOPIFY_EMBEDDED_STORAGE_KEY) || ""
  );
}

export function persistShopifyEmbeddedContext(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  const preserved = new URLSearchParams();

  for (const key of SHOPIFY_EMBEDDED_QUERY_KEYS) {
    const value = params.get(key);
    if (value) {
      preserved.set(key, value);
    }
  }

  if (typeof window !== "undefined" && preserved.toString()) {
    window.sessionStorage.setItem(
      SHOPIFY_EMBEDDED_STORAGE_KEY,
      preserved.toString()
    );
  }
}

export function buildShopifyReturnPath(
  pathname = "/shopify",
  search,
  { stripParams = [] } = {}
) {
  const params = new URLSearchParams(getCurrentSearch(search));
  const stored = getStoredEmbeddedParams();
  const merged = new URLSearchParams(params);

  for (const key of stripParams) {
    merged.delete(key);
  }

  for (const key of SHOPIFY_EMBEDDED_QUERY_KEYS) {
    if (!merged.has(key)) {
      const storedValue = stored.get(key);
      if (storedValue) {
        merged.set(key, storedValue);
      }
    }
  }

  if (isShopifyEmbeddedContext(merged.toString())) {
    const preserved = new URLSearchParams();
    for (const key of SHOPIFY_EMBEDDED_QUERY_KEYS) {
      const value = merged.get(key);
      if (value) {
        preserved.set(key, value);
      }
    }

    if (typeof window !== "undefined" && preserved.toString()) {
      window.sessionStorage.setItem(
        SHOPIFY_EMBEDDED_STORAGE_KEY,
        preserved.toString()
      );
    }
  }

  const query = merged.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function getHostParam(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  return params.get("host");
}

export async function getEmbeddedSessionToken(search) {
  const host = getHostParam(search);

  if (!host) {
    throw new Error("Missing Shopify host parameter");
  }

  const app = createApp({
    apiKey: SHOPIFY_API_KEY,
    forceRedirect: true,
    host,
  });

  return getSessionToken(app);
}

export async function verifyEmbeddedShopifySession({
  endpoint = "/api/auth/shopify/session",
  search,
} = {}) {
  const token = await getEmbeddedSessionToken(search);
  const response = await fetch(endpoint, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Shopify session verification failed: ${response.status} ${message}`
    );
  }

  return response.json();
}
