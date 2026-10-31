"use client";

import "@xyflow/react/dist/style.css";

import { Background, Controls, Handle, Position, ReactFlow } from "@xyflow/react";
import type { Edge, Node, NodeProps, NodeTypes } from "@xyflow/react";
import Link from "next/link";
import { useMemo } from "react";

import { useApi } from "@/auth/SessionProvider";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { StatusChip, statusLabel } from "@/components/StatusChip";
import { kindLabel, loadKinds } from "@/features/domain/vocabulary";
import { detailHref } from "@/features/memories/MemoryCard";
import { useRequest } from "@/lib/useRequest";

import { buildGraph } from "./graph";
import type { MapGraph, MapNodeData } from "./graph";

/** A kind as a CSS class suffix; globals.css colours the kinds it knows and leaves the
 * rest on the neutral node colour. */
function kindClass(kind: string): string {
  return `map-node map-node-${kind.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

/** The user's visible memories and their links as one graph (FR-13). One GET /graph
 * call (same I1 boundary as the list) plus GET /vocabulary for the kinds' order; a
 * failed vocabulary only loses that order, never the map. */
export function MapView() {
  const api = useApi();
  const request = useRequest(async () => {
    const [graph, known] = await Promise.all([api.getGraph(), loadKinds(api)]);
    return buildGraph(graph, known.kinds);
  });

  return (
    <RequestView request={request} what="the openings map">
      {(graph) =>
        graph.nodes.length === 0 ? (
          <Empty>No memories to map yet. The map fills as Ripple learns.</Empty>
        ) : (
          <FlowMap graph={graph} />
        )
      }
    </RequestView>
  );
}

type MemoryFlowNode = Node<MapNodeData, "memory">;

function MemoryNode({ data }: NodeProps<MemoryFlowNode>) {
  return (
    <div className={kindClass(data.kind)}>
      <Handle type="target" position={Position.Left} />
      <span className="meta">{kindLabel(data.kind)}</span>
      <Link className="label" href={detailHref(data.memoryId)} title={data.label}>
        {data.label}
      </Link>
      <StatusChip status={data.status} />
      {data.flagged ? <span className="chip chip-flagged">Flagged</span> : null}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES: NodeTypes = { memory: MemoryNode };
const MIN_ZOOM = 0.2;
const FIT = { padding: 0.08, minZoom: MIN_ZOOM };

function FlowMap({ graph }: { graph: MapGraph }) {
  const nodes = useMemo<MemoryFlowNode[]>(
    () => graph.nodes.map((node) => ({ ...node })),
    [graph],
  );
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        // Solid for depends_on, dashed for snapshot_of, as the legend says. React Flow's
        // `animated` would dash propagating edges too (and move them regardless of
        // prefers-reduced-motion), so it is not used.
        style: edge.propagates ? undefined : { strokeDasharray: "4 4" },
        // The link type shows on hover or selection only (globals.css): on every edge at
        // once the labels bury the graph.
        className: "map-edge",
      })),
    [graph],
  );

  return (
    <>
      <p className="map-legend" aria-hidden="true">
        {graph.kinds.map((kind) => (
          <span key={kind} className={kindClass(kind)}>
            {kindLabel(kind)}
          </span>
        ))}
        <span>
          Solid edge: ripples propagate · dashed: snapshot · hover or select an edge for its
          link type
        </span>
      </p>
      <div className="map-wrap">
        <ReactFlow
          // A new node count is a new graph: remount so the fit below runs again.
          key={nodes.length}
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          // React Flow queues this fit until the nodes are measured. The default minZoom
          // (0.5) clamped a tall graph and left it out of view; the layout keeps the graph
          // about square, and 0.2 lets even a large one fit.
          fitView
          fitViewOptions={FIT}
          // The queued fit can run while the pane is still settling; fit once more on the
          // next frame, when sizes are final.
          onInit={(instance) => {
            requestAnimationFrame(() => void instance.fitView(FIT));
          }}
          minZoom={MIN_ZOOM}
          nodesConnectable={false}
          nodesDraggable={false}
          proOptions={{ hideAttribution: true }}
          aria-label="Openings map"
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <GraphAsList graph={graph} />
    </>
  );
}

/** The same graph as text, for keyboard and screen-reader users and for anyone who
 * wants to read the edges rather than trace them. */
function GraphAsList({ graph }: { graph: MapGraph }) {
  const labels = new Map(graph.nodes.map((node) => [node.id, node.data.label]));
  return (
    <details>
      <summary>
        Map as a list ({graph.nodes.length} nodes, {graph.edges.length} links)
      </summary>
      <h2>Nodes</h2>
      <ul aria-label="Map nodes">
        {graph.nodes.map((node) => (
          <li key={node.id}>
            {kindLabel(node.data.kind)}:{" "}
            <Link href={detailHref(node.id)}>{node.data.label}</Link> (
            {statusLabel(node.data.status)}
            {node.data.flagged ? ", flagged" : ""})
          </li>
        ))}
      </ul>
      <h2>Links</h2>
      {graph.edges.length === 0 ? (
        <p>No links between these memories.</p>
      ) : (
        <ul aria-label="Map links">
          {graph.edges.map((edge) => (
            <li key={edge.id}>
              {labels.get(edge.target)} {edge.propagates ? "depends on" : "is a snapshot of"}{" "}
              {labels.get(edge.source)} (<em>{edge.label}</em>)
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}
