/**
 * useFlowLayout — Computes node positions and link paths for the Sankey flow diagram.
 *
 * WHAT: Takes raw nodes[] and links[] from the API and returns positioned data
 *       ready for SVG rendering. Nodes are arranged in columns; links are
 *       cubic bezier paths.
 *
 * WHY: Layout logic is separated from rendering so FlowNode and FlowLink
 *       components stay purely visual.
 *
 * DESIGN:
 *   - Nodes are arranged in columns (0=sources, 1-3=stages, 4=outcomes)
 *   - Within each column, nodes are sorted by count descending
 *   - Node height is proportional to count (relative to column max)
 *   - Link paths are cubic beziers from source.right to target.left
 *
 * REFERENCES:
 *   - backend/app/routers/attribution.py (journey-flow endpoint)
 *   - FlowNode.jsx, FlowLink.jsx (consumers)
 */

import { useMemo } from 'react';

// Layout constants
const COLUMN_X = [40, 220, 400, 580, 760];  // X position of each column
const NODE_WIDTH = 140;
const NODE_MIN_HEIGHT = 32;
const NODE_MAX_HEIGHT = 80;
const NODE_GAP = 12;
const SVG_PADDING_TOP = 20;

/**
 * Compute positioned nodes and link paths from raw flow data.
 *
 * @param {Array} nodes - Raw nodes from API: [{ id, label, column, count, revenue, color }]
 * @param {Array} links - Raw links from API: [{ source, target, value, revenue }]
 * @param {number} width - SVG container width
 * @param {number} height - SVG container height
 * @returns {{ positionedNodes: Array, positionedLinks: Array, svgHeight: number }}
 */
export default function useFlowLayout(nodes = [], links = [], width = 900, height = 500) {
  return useMemo(() => {
    if (!nodes.length) {
      return { positionedNodes: [], positionedLinks: [], svgHeight: height };
    }

    // Group nodes by column
    const columns = {};
    for (const node of nodes) {
      const col = node.column ?? 0;
      if (!columns[col]) columns[col] = [];
      columns[col].push({ ...node });
    }

    // Sort each column by count descending
    for (const col of Object.values(columns)) {
      col.sort((a, b) => b.count - a.count);
    }

    // Find the column with the most total height to determine SVG height
    let maxColumnHeight = 0;

    // Position nodes within each column
    const positionedNodes = [];
    const nodeMap = {};

    for (const [colIdx, colNodes] of Object.entries(columns)) {
      const colIndex = parseInt(colIdx);
      const maxCount = Math.max(...colNodes.map(n => n.count), 1);

      let y = SVG_PADDING_TOP;

      for (const node of colNodes) {
        // Height proportional to count within column
        const heightRatio = node.count / maxCount;
        const nodeHeight = Math.max(
          NODE_MIN_HEIGHT,
          Math.round(NODE_MIN_HEIGHT + (NODE_MAX_HEIGHT - NODE_MIN_HEIGHT) * heightRatio)
        );

        // Scale X positions to fit container
        const scaleFactor = width / 900;
        const x = (COLUMN_X[colIndex] ?? colIndex * 180 + 40) * scaleFactor;
        const nodeW = NODE_WIDTH * scaleFactor;

        const positioned = {
          ...node,
          x,
          y,
          width: nodeW,
          height: nodeHeight,
        };

        positionedNodes.push(positioned);
        nodeMap[node.id] = positioned;

        y += nodeHeight + NODE_GAP;
      }

      maxColumnHeight = Math.max(maxColumnHeight, y);
    }

    const svgHeight = Math.max(height, maxColumnHeight + SVG_PADDING_TOP);

    // Build link paths
    const positionedLinks = [];

    // Track port offsets per node (how much of the right/left side is used)
    const rightPortOffset = {};
    const leftPortOffset = {};

    for (const link of links) {
      const sourceNode = nodeMap[link.source];
      const targetNode = nodeMap[link.target];

      if (!sourceNode || !targetNode) continue;

      // Calculate vertical offset within source/target nodes
      const sourceTotal = links
        .filter(l => l.source === link.source)
        .reduce((sum, l) => sum + l.value, 0);
      const targetTotal = links
        .filter(l => l.target === link.target)
        .reduce((sum, l) => sum + l.value, 0);

      // Proportional thickness
      const sourceRatio = sourceTotal > 0 ? link.value / sourceTotal : 0;
      const targetRatio = targetTotal > 0 ? link.value / targetTotal : 0;

      const linkThicknessSource = Math.max(2, sourceNode.height * sourceRatio);
      const linkThicknessTarget = Math.max(2, targetNode.height * targetRatio);

      // Port offsets
      if (!rightPortOffset[link.source]) rightPortOffset[link.source] = 0;
      if (!leftPortOffset[link.target]) leftPortOffset[link.target] = 0;

      const sx = sourceNode.x + sourceNode.width;
      const sy = sourceNode.y + rightPortOffset[link.source] + linkThicknessSource / 2;
      const tx = targetNode.x;
      const ty = targetNode.y + leftPortOffset[link.target] + linkThicknessTarget / 2;

      rightPortOffset[link.source] += linkThicknessSource;
      leftPortOffset[link.target] += linkThicknessTarget;

      // Cubic bezier control points (horizontal midpoint)
      const mx = (sx + tx) / 2;
      const path = `M ${sx},${sy} C ${mx},${sy} ${mx},${ty} ${tx},${ty}`;

      const thickness = Math.max(2, (linkThicknessSource + linkThicknessTarget) / 2);

      positionedLinks.push({
        ...link,
        path,
        thickness,
        sx, sy, tx, ty,
      });
    }

    // Sort links: thicker (higher value) drawn first (behind)
    positionedLinks.sort((a, b) => b.value - a.value);

    return { positionedNodes, positionedLinks, svgHeight };
  }, [nodes, links, width, height]);
}
