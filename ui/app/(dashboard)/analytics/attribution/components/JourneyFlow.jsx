/**
 * JourneyFlow — Sankey-style journey flow visualization.
 *
 * WHAT: Main orchestrator that fetches journey flow data from the API and
 *       renders an SVG Sankey diagram with animated flowing particles.
 *       Nodes represent channels, funnel stages, and outcomes; links show
 *       how visitors flow between them.
 *
 * WHY: This is the "award-winning" visualization that differentiates us from
 *       Triple Whale. Users can see exactly how visitors from each channel
 *       move through the funnel and where they drop off.
 *
 * DESIGN:
 *   - Left column: Source channels (Meta Ads, Google Ads, Direct, etc.)
 *   - Middle columns: Touchpoint stages (Page View, Product View, ATC, Checkout)
 *   - Right column: Outcomes (Purchased with revenue, Dropped Off)
 *   - Links: Curved SVG bezier paths with width proportional to journey count
 *   - Particles: Small dots flowing along paths using <animateMotion>
 *   - Hover: Highlight a node to show connected paths, dimming the rest
 *
 * RESPONSIVE:
 *   - Desktop (>=1024px): Full Sankey diagram
 *   - Mobile (<768px): Simplified vertical funnel bars fallback
 *
 * PROPS:
 *   - data: { nodes, links, total_journeys, total_revenue } from API
 *   - loading: boolean
 *
 * REFERENCES:
 *   - backend/app/routers/attribution.py (journey-flow endpoint)
 *   - useFlowLayout.js (layout computation)
 *   - FlowNode.jsx, FlowLink.jsx (rendering)
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { GitBranch } from 'lucide-react';
import useFlowLayout from './useFlowLayout';
import FlowNode from './FlowNode';
import FlowLink from './FlowLink';

/**
 * Format currency in compact notation.
 * @param {number} value
 * @returns {string}
 */
function formatCurrency(value) {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

/**
 * Format a number compactly.
 * @param {number} num
 * @returns {string}
 */
function formatCompact(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

/**
 * Mobile fallback — simplified vertical bars showing source → outcome.
 * WHY: Sankey is too complex for small screens; bars are more readable.
 */
function MobileFallback({ data }) {
  if (!data?.nodes?.length) return null;

  const sourceNodes = data.nodes
    .filter(n => n.column === 0)
    .sort((a, b) => b.count - a.count);

  const maxCount = Math.max(...sourceNodes.map(n => n.count), 1);

  return (
    <div className="space-y-2">
      {sourceNodes.map(node => {
        const widthPct = Math.max((node.count / maxCount) * 100, 10);
        return (
          <div key={node.id} className="flex items-center gap-3">
            <div className="w-20 text-xs text-neutral-600 text-right truncate">
              {node.label}
            </div>
            <div className="flex-1">
              <div
                className="h-7 rounded-md flex items-center px-2"
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: node.color || '#64748b',
                  minWidth: '60px',
                }}
              >
                <span className="text-[10px] font-medium text-white tabular-nums">
                  {formatCompact(node.count)}
                </span>
              </div>
            </div>
            {node.revenue > 0 && (
              <div className="text-[10px] text-neutral-400 tabular-nums w-14 text-right">
                {formatCurrency(node.revenue)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function JourneyFlow({ data, loading = false }) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(900);

  // Measure container width for responsive SVG
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Compute layout from data
  const { positionedNodes, positionedLinks, svgHeight } = useFlowLayout(
    data?.nodes || [],
    data?.links || [],
    containerWidth,
    460,
  );

  // Determine which nodes/links are highlighted or dimmed
  const connectedNodeIds = new Set();
  if (hoveredNode) {
    connectedNodeIds.add(hoveredNode);
    for (const link of (data?.links || [])) {
      if (link.source === hoveredNode || link.target === hoveredNode) {
        connectedNodeIds.add(link.source);
        connectedNodeIds.add(link.target);
      }
    }
  }

  // Node color map for link coloring
  const nodeColorMap = {};
  for (const node of (data?.nodes || [])) {
    nodeColorMap[node.id] = node.color || '#94a3b8';
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-white border border-neutral-200 rounded-xl p-4 animate-pulse">
        <div className="h-4 w-48 bg-neutral-100 rounded mb-4" />
        <div className="h-[460px] bg-neutral-50 rounded-lg" />
      </div>
    );
  }

  // Empty state
  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="bg-white border border-neutral-200 rounded-xl p-8 text-center">
        <GitBranch className="w-10 h-10 text-neutral-200 mx-auto mb-3" />
        <h3 className="text-sm font-medium text-neutral-900 mb-1">No journey data yet</h3>
        <p className="text-xs text-neutral-500 max-w-sm mx-auto">
          Journey flow will appear once visitors are tracked through the pixel
          and orders are attributed.
        </p>
      </div>
    );
  }

  const isMobile = containerWidth < 768;

  return (
    <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-neutral-400" />
          <span className="text-sm font-medium text-neutral-900">Journey Flow</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-neutral-500">
          <span className="tabular-nums">{formatCompact(data.total_journeys)} journeys</span>
          {data.total_revenue > 0 && (
            <span className="tabular-nums">{formatCurrency(data.total_revenue)} revenue</span>
          )}
        </div>
      </div>

      {/* Flow diagram or mobile fallback */}
      <div ref={containerRef} className="p-4">
        {isMobile ? (
          <MobileFallback data={data} />
        ) : (
          <>
            {/* Column labels */}
            <div className="flex justify-between mb-2 px-2">
              <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
                Source
              </span>
              <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
                Touchpoints
              </span>
              <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
                Outcome
              </span>
            </div>

            {/* SVG Canvas */}
            <svg
              width="100%"
              height={svgHeight}
              viewBox={`0 0 ${containerWidth} ${svgHeight}`}
              className="overflow-visible"
            >
              {/* Links (drawn first, behind nodes) */}
              {positionedLinks.map((link, idx) => {
                const isLinkHighlighted = hoveredNode
                  ? (link.source === hoveredNode || link.target === hoveredNode)
                  : false;
                const isLinkDimmed = hoveredNode ? !isLinkHighlighted : false;

                return (
                  <FlowLink
                    key={`${link.source}-${link.target}-${idx}`}
                    link={link}
                    isHighlighted={isLinkHighlighted}
                    isDimmed={isLinkDimmed}
                    color={nodeColorMap[link.source] || '#94a3b8'}
                  />
                );
              })}

              {/* Nodes (drawn on top of links) */}
              {positionedNodes.map(node => {
                const isNodeHighlighted = hoveredNode === node.id;
                const isNodeDimmed = hoveredNode ? !connectedNodeIds.has(node.id) : false;

                return (
                  <FlowNode
                    key={node.id}
                    node={node}
                    isHighlighted={isNodeHighlighted}
                    isDimmed={isNodeDimmed}
                    onHover={setHoveredNode}
                  />
                );
              })}
            </svg>
          </>
        )}
      </div>
    </div>
  );
}
