// WHAT: Local layout state and persistence (positions, zoom, viewport)
// WHY: Preserve user adjustments across sessions per workspace
// REFERENCES: docs/canvas/01-functional-spec.md

import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = (workspaceId) => `metricx.canvas.layout.${workspaceId || 'unknown'}`;

export default function useCanvasLayout({ workspaceId }) {
  const [positions, setPositions] = useState({}); // id -> { x, y }
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const mounted = useRef(false);

  // Load
  useEffect(() => {
    if (!workspaceId) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY(workspaceId));
      if (raw) {
        const parsed = JSON.parse(raw);
        setPositions(parsed.positions || {});
        setViewport(parsed.viewport || { x: 0, y: 0, zoom: 1 });
      }
    } catch { }
  }, [workspaceId]);

  // Save
  useEffect(() => {
    if (!workspaceId) return;
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    try {
      const payload = JSON.stringify({ positions, viewport });
      localStorage.setItem(STORAGE_KEY(workspaceId), payload);
    } catch { }
  }, [workspaceId, positions, viewport]);

  const updateNodePosition = useCallback((id, pos) => {
    setPositions((prev) => ({ ...prev, [id]: pos }));
  }, []);

  const updateViewport = useCallback((vp) => {
    setViewport((prev) => ({ ...prev, ...vp }));
  }, []);

  return { positions, viewport, updateNodePosition, updateViewport };
}

