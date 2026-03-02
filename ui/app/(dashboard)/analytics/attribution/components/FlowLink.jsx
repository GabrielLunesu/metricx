/**
 * FlowLink — SVG cubic bezier path with animated flowing particles.
 *
 * WHAT: Renders a curved path between two nodes in the Sankey diagram.
 *       Small dots animate along the path for a "data flowing" effect.
 *
 * WHY: The animated particles are the "wow factor" — they make the diagram
 *       feel alive and immediately communicate that data is flowing through
 *       the system.
 *
 * PROPS:
 *   - link: { path, thickness, value, revenue, source, target }
 *   - isHighlighted: boolean
 *   - isDimmed: boolean
 *   - color: string (hex color, derived from source node)
 *
 * REFERENCES:
 *   - useFlowLayout.js (computes path geometry)
 *   - JourneyFlow.jsx (parent orchestrator)
 */

'use client';

import { useId } from 'react';

export default function FlowLink({ link, isHighlighted, isDimmed, color = '#94a3b8' }) {
  const id = useId();
  const particleId = `particle-${id}`;

  const opacity = isDimmed ? 0.05 : isHighlighted ? 0.6 : 0.15;
  const strokeWidth = Math.max(1.5, Math.min(link.thickness || 2, 30));

  // Only show animated particles on highlighted or when not dimmed and link is significant
  const showParticles = !isDimmed && link.value > 0;

  // Animation duration — faster for shorter paths, slower for longer ones
  const duration = isHighlighted ? 2 : 4;

  return (
    <g>
      {/* Main path */}
      <path
        d={link.path}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeOpacity={opacity}
        strokeLinecap="round"
        style={{ transition: 'stroke-opacity 0.2s ease, stroke-width 0.2s ease' }}
      />

      {/* Animated particle — only when visible */}
      {showParticles && (
        <circle r={isHighlighted ? 3 : 2} fill={color} opacity={isHighlighted ? 0.8 : 0.4}>
          <animateMotion
            dur={`${duration}s`}
            repeatCount="indefinite"
            path={link.path}
          />
        </circle>
      )}

      {/* Second particle for highlighted links (offset timing) */}
      {isHighlighted && showParticles && (
        <circle r={2.5} fill={color} opacity={0.5}>
          <animateMotion
            dur={`${duration}s`}
            repeatCount="indefinite"
            path={link.path}
            begin={`${duration / 2}s`}
          />
        </circle>
      )}
    </g>
  );
}
