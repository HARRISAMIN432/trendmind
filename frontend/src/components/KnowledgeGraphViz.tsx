"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import type { GraphEdgeItem, GraphNodeItem } from "@/lib/types";
import { NODE_TYPE_COLORS } from "@/lib/constants";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)]">
      Loading graph...
    </div>
  ),
});

interface KnowledgeGraphVizProps {
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
}

interface GraphNode {
  id: number;
  name: string;
  type: string;
  color: string;
}

interface GraphLink {
  source: number;
  target: number;
  relation: string;
}

export function KnowledgeGraphViz({ nodes, edges }: KnowledgeGraphVizProps) {
  const graphData = useMemo(() => {
    const graphNodes: GraphNode[] = nodes.map((node) => ({
      id: node.id,
      name: node.name,
      type: node.type,
      color: NODE_TYPE_COLORS[node.type] ?? "#71717A",
    }));

    const graphLinks: GraphLink[] = edges.map((edge) => ({
      source: edge.source_id,
      target: edge.target_id,
      relation: edge.relation,
    }));

    return { nodes: graphNodes, links: graphLinks };
  }, [nodes, edges]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)]">
        No graph data available. Build the graph from the API first.
      </div>
    );
  }

  return (
    <ForceGraph2D
      graphData={graphData}
      nodeId="id"
      nodeLabel={(node) =>
        `${(node as GraphNode).name} (${(node as GraphNode).type})`
      }
      nodeColor={(node) => (node as GraphNode).color}
      nodeRelSize={6}
      linkDirectionalArrowLength={3.5}
      linkDirectionalArrowRelPos={1}
      linkLabel={(link) => (link as GraphLink).relation}
      linkColor={() => "rgba(161, 161, 170, 0.4)"}
      linkWidth={1}
      backgroundColor="#12121a"
      warmupTicks={80}
      cooldownTicks={0}
    />
  );
}
