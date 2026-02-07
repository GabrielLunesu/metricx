/**
 * useMediaQuery - Hook for responsive behavior based on CSS media queries
 *
 * WHAT: Returns a boolean indicating if a media query matches
 * WHY: Enable responsive logic in components (e.g., show 1 vs 2 calendar months)
 *
 * @param {string} query - CSS media query string (e.g., "(min-width: 768px)")
 * @returns {boolean} Whether the media query currently matches
 */
import { useState, useEffect } from "react";

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);

    const handler = (e) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}
