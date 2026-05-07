import { useMemo, useState } from "react";
import type { PublicRelationships } from "@/lib/schemas";

export function RelationshipGraph({
  relationships,
  highlightId,
  onHover
}: {
  relationships: PublicRelationships;
  highlightId: string | null;
  onHover: (id: string | null) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const active = highlightId ?? hovered;
  const width = 560;
  const height = 360;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 2 - 70;
  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    relationships.nodes.forEach((node, index) => {
      const angle = (index / Math.max(relationships.nodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
      map.set(node.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius
      });
    });
    return map;
  }, [relationships.nodes, radius]);
  const neighbors = useMemo(() => {
    const map = new Map<string, Set<string>>();
    relationships.nodes.forEach((node) => map.set(node.id, new Set()));
    relationships.edges.forEach((edge) => {
      map.get(edge.source)?.add(edge.target);
      map.get(edge.target)?.add(edge.source);
    });
    return map;
  }, [relationships.edges, relationships.nodes]);
  const renderedEdges = useMemo(
    () => [...relationships.edges].sort((left, right) => left.similarity_score - right.similarity_score),
    [relationships.edges]
  );

  const isEdgeActive = (source: string, target: string) => !active || source === active || target === active;
  const isNodeActive = (id: string) => !active || id === active || neighbors.get(active)?.has(id);

  return (
    <div className="graph-panel">
      <div className="panel-heading">
        <span>Channel relationship graph</span>
        <code>{relationships.nodes.length} nodes · {relationships.edges.length} edges</code>
      </div>
      <div className="graph-surface">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Channel relationship graph">
          <defs>
            <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M 24 0 L 0 0 0 24" fill="none" stroke="var(--border)" strokeWidth="0.5" opacity="0.6" />
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#grid)" />
          {renderedEdges.map((edge) => {
            const source = positions.get(edge.source);
            const target = positions.get(edge.target);
            if (!source || !target) {
              return null;
            }
            const activeEdge = isEdgeActive(edge.source, edge.target);
            const edgeWeight = Math.pow(edge.similarity_score, 1.25);
            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={activeEdge ? "var(--info)" : "var(--border-strong)"}
                strokeWidth={0.45 + edgeWeight * 2.9}
                opacity={activeEdge ? 0.12 + edgeWeight * 0.82 : 0.035}
                strokeLinecap="round"
              >
                <title>{edge.explanation}</title>
              </line>
            );
          })}
          {relationships.nodes.map((node) => {
            const position = positions.get(node.id) ?? { x: centerX, y: centerY };
            const nodeActive = isNodeActive(node.id);
            const isCenter = active === node.id;
            const nodeRadius = 6 + Math.min(node.video_count, 400) / 60;
            return (
              <g
                key={node.id}
                transform={`translate(${position.x}, ${position.y})`}
                onMouseEnter={() => {
                  setHovered(node.id);
                  onHover(node.id);
                }}
                onMouseLeave={() => {
                  setHovered(null);
                  onHover(null);
                }}
                opacity={nodeActive ? 1 : 0.22}
              >
                <circle r={nodeRadius + 7} fill={isCenter ? "color-mix(in oklab, var(--info) 18%, transparent)" : "transparent"} />
                <circle
                  r={nodeRadius}
                  fill={isCenter ? "var(--info)" : "var(--surface)"}
                  stroke={isCenter ? "var(--info)" : "var(--border-strong)"}
                  strokeWidth="1.5"
                />
                <text y={nodeRadius + 14} textAnchor="middle" className="graph-node-label">
                  {node.label}
                </text>
                <text y={nodeRadius + 26} textAnchor="middle" className="graph-node-sub">
                  {node.video_count} videos
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="graph-footer">
        {active ? (
          <span>
            <strong>{relationships.nodes.find((node) => node.id === active)?.label}</strong> · top topics:{" "}
            {relationships.nodes.find((node) => node.id === active)?.top_topics.join(", ")}
          </span>
        ) : (
          <span>Hover a node to highlight related channels.</span>
        )}
      </div>
    </div>
  );
}
