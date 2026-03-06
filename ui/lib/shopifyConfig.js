export const SHOPIFY_API_KEY =
  process.env.NEXT_PUBLIC_SHOPIFY_API_KEY ||
  process.env.SHOPIFY_API_KEY ||
  "3cd42321fabca39e5c4e9cc29b619aca";

export const SHOPIFY_APP_BRIDGE_CDN_URL =
  "https://cdn.shopify.com/shopifycloud/app-bridge.js";

export const SHOPIFY_EMBEDDED_QUERY_KEYS = ["embedded", "host", "locale", "shop"];
