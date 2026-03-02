/**
 * FlowNode — A single node in the Sankey flow diagram.
 *
 * WHAT: Renders a rounded rect with label, count, and optional revenue.
 *       Highlights on hover to show connected paths.
 *
 * WHY: Each node represents a channel (Meta Ads), funnel stage (Add to Cart),
 *       or outcome (Purchased). Users hover to focus on specific paths.
 *
 * PROPS:
 *   - node: { id, label, x, y, width, height, count, revenue, color }
 *   - isHighlighted: boolean — true when this node or its links are active
 *   - isDimmed: boolean — true when another node is highlighted (dim this one)
 *   - onHover: (nodeId | null) => void
 *
 * REFERENCES:
 *   - useFlowLayout.js (provides positioned data)
 *   - JourneyFlow.jsx (parent orchestrator)
 */

'use client';

/**
 * Format a number in compact notation for display inside nodes.
 *
 * @param {number} num
 * @returns {string}
 */
function formatCompact(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

/**
 * Format currency in compact notation.
 *
 * @param {number} value
 * @returns {string}
 */
function formatRevenue(value) {
  if (!value || value === 0) return '';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

export default function FlowNode({ node, isHighlighted, isDimmed, onHover }) {
  const opacity = isDimmed ? 0.2 : 1;
  const strokeWidth = isHighlighted ? 2 : 0;

  return (
    <g
      onMouseEnter={() => onHover?.(node.id)}
      onMouseLeave={() => onHover?.(null)}
      style={{ cursor: 'pointer', opacity, transition: 'opacity 0.2s ease' }}
    >
      {/* Background rect */}
      <rect
        x={node.x}
        y={node.y}
        width={node.width}
        height={node.height}
        rx={6}
        ry={6}
        fill={node.color || '#64748b'}
        stroke={isHighlighted ? '#171717' : 'transparent'}
        strokeWidth={strokeWidth}
      />

      {/* Label */}
      <text
        x={node.x + 8}
        y={node.y + 14}
        fontSize={11}
        fontWeight={500}
        fill="white"
        opacity={0.9}
      >
        {node.label}
      </text>

      {/* Count */}
      <text
        x={node.x + 8}
        y={node.y + node.height - 8}
        fontSize={13}
        fontWeight={600}
        fill="white"
        fontFamily="tabular-nums"
      >
        {formatCompact(node.count)}
        {node.revenue > 0 && (
          <tspan fontSize={10} opacity={0.7} dx={6}>
            {formatRevenue(node.revenue)}
          </tspan>
        )}
      </text>
    </g>
  );
}
