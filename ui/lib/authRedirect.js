export function getSafeRedirectPath(value, fallbackPath) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return fallbackPath;
  }

  try {
    const normalized = new URL(value, "https://www.metricx.ai");
    return `${normalized.pathname}${normalized.search}${normalized.hash}`;
  } catch {
    return fallbackPath;
  }
}

export function buildAuthRedirectUrl(basePath, redirectPath) {
  const params = new URLSearchParams({ redirect_url: redirectPath });
  return `${basePath}?${params.toString()}`;
}
