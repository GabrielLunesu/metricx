import createApp from "@shopify/app-bridge";
import { getSessionToken } from "@shopify/app-bridge/utilities";

import {
  SHOPIFY_API_KEY,
  SHOPIFY_EMBEDDED_QUERY_KEYS,
} from "./shopifyConfig";

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

export function buildShopifyReturnPath(pathname = "/shopify", search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  const preserved = new URLSearchParams();

  for (const key of SHOPIFY_EMBEDDED_QUERY_KEYS) {
    const value = params.get(key);
    if (value) {
      preserved.set(key, value);
    }
  }

  const query = preserved.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function getHostParam(search) {
  const params = new URLSearchParams(getCurrentSearch(search));
  return params.get("host");
}

async function getEmbeddedSessionToken(search) {
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
