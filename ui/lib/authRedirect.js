const SAFE_REDIRECT_ORIGINS = new Set([
  "https://www.metricx.ai",
  "https://metricx.ai",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
]);

export function getSafeRedirectPath(value, fallbackPath) {
  if (typeof value !== "string" || !value) {
    return fallbackPath;
  }

  try {
    const normalized = value.startsWith("/")
      ? new URL(value, "https://www.metricx.ai")
      : new URL(value);

    if (!SAFE_REDIRECT_ORIGINS.has(normalized.origin)) {
      return fallbackPath;
    }

    return `${normalized.pathname}${normalized.search}${normalized.hash}`;
  } catch {
    return fallbackPath;
  }
}

export function buildAuthRedirectUrl(basePath, redirectPath) {
  const params = new URLSearchParams({ redirect_url: redirectPath });
  return `${basePath}?${params.toString()}`;
}
