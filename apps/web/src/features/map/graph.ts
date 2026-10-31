/** Builds the openings map from what GET /graph returned (FR-13, ADR-0087).
 *
 * Input: the visible memories and the links between them, as the API sent them, plus
 * the domain's kinds from GET /vocabulary (for ordering only). Output: React Flow nodes
 * and edges. The only decisions here are presentational: which column a node goes in
 * and where. No eligibility, fit, status or flag is derived; those come with the
 * memories, and which memories exist is the API's answer, not a filter of ours.
 */
import type { GraphOut, Link, MemoryStatus } from "@/api/types";
import { isVisibleInLists } from "@/lib/visibility";

export interface MapNodeData {
  label: string;
  kind: string;
  status: MemoryStatus;
  flagged: boolean;
  memoryId: string;
  [key: string]: unknown;
}

export interface MapNode {
  id: string;
  type: "memory";
  position: { x: number; y: number };
  data: MapNodeData;
}

export interface MapEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  /** depends_on edges propagate ripples; snapshot_of edges do not (ADR-0013). */
  propagates: boolean;
}

export interface MapGraph {
  nodes: MapNode[];
  edges: MapEdge[];
  /** The kinds drawn, in the vocabulary's order (for the legend). */
  kinds: string[];
}

const COLUMN_WIDTH = 260;
// A node is at most kind, two clamped label lines and a row of chips tall (globals.css);
// the chips can wrap to a second row when a flag joins the status.
const ROW_HEIGHT = 136;
/** The map's frame is about 1.6 times as wide as it is tall; the layout aims for that. */
const ASPECT = 1.6;
/** Space between two depth bands, wider than between the sub-columns of one band, so
 * "starting points → read from them → derived" stays readable after wrapping. */
const BAND_GAP = 120;

export function buildGraph(graph: GraphOut, vocabularyKinds: readonly string[] = []): MapGraph {
  const nodesById = new Map<string, MapNode>();
  for (const item of graph.nodes) {
    const { memory } = item;
    // I1 at the UI: a retired memory is never drawn, even if one were sent.
    if (nodesById.has(memory.id) || !isVisibleInLists(memory.status)) continue;
    nodesById.set(memory.id, {
      id: memory.id,
      type: "memory",
      position: { x: 0, y: 0 },
      data: {
        label: memory.content,
        kind: memory.kind,
        status: memory.status,
        flagged: item.flagged,
        memoryId: memory.id,
      },
    });
  }

  const edges: MapEdge[] = [];
  const seenEdges = new Set<string>();
  for (const link of graph.links) {
    // A link to a node that is not drawn (retired, say) would dangle; skip it.
    if (!nodesById.has(link.parent_id) || !nodesById.has(link.dependent_id)) continue;
    if (seenEdges.has(link.id)) continue;
    seenEdges.add(link.id);
    edges.push(edgeOf(link));
  }

  const nodes = [...nodesById.values()];
  const kinds = orderKinds(
    nodes.map((node) => node.data.kind),
    vocabularyKinds,
  );
  layoutByDepth(nodes, edges, kinds);
  return { nodes, edges, kinds };
}

function edgeOf(link: Link): MapEdge {
  return {
    id: link.id,
    source: link.parent_id,
    target: link.dependent_id,
    label: link.link_type,
    propagates: link.link_class === "depends_on",
  };
}

/** The distinct kinds present, in the vocabulary's order; kinds the vocabulary does not
 * name (or every kind, when it failed to load) follow alphabetically. */
export function orderKinds(present: readonly string[], vocabularyKinds: readonly string[]) {
  const distinct = [...new Set(present)];
  const known = vocabularyKinds.filter((kind) => distinct.includes(kind));
  const unknown = distinct.filter((kind) => !vocabularyKinds.includes(kind)).sort();
  return [...known, ...unknown];
}

/** Bands by dependency depth (a node sits in the band right of its deepest parent), so
 * every edge points left to right whatever the domain's kinds are. A band taller than
 * the map is wide wraps into sub-columns, so the whole graph is roughly as wide as it is
 * tall. Within a band, nodes follow their first parent's position, so facts read from
 * one source (an opening's fields) stay together beside it; then kind, then label, so
 * the map does not jump between reloads. */
function layoutByDepth(nodes: MapNode[], edges: MapEdge[], kinds: readonly string[]): void {
  const parentsOf = new Map<string, string[]>();
  for (const edge of edges) {
    parentsOf.set(edge.target, [...(parentsOf.get(edge.target) ?? []), edge.source]);
  }
  const depth = new Map<string, number>();
  const visiting = new Set<string>();
  function depthOf(id: string): number {
    const known = depth.get(id);
    if (known !== undefined) return known;
    // Links form a DAG; should a cycle ever arrive, cut it here rather than recurse forever.
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const parents = parentsOf.get(id) ?? [];
    const value = parents.length === 0 ? 0 : 1 + Math.max(...parents.map(depthOf));
    visiting.delete(id);
    depth.set(id, value);
    return value;
  }

  const bands = new Map<number, MapNode[]>();
  for (const node of nodes) {
    const band = depthOf(node.id);
    bands.set(band, [...(bands.get(band) ?? []), node]);
  }
  // Rows per sub-column so that width ~ ASPECT * height: rows ~ sqrt(n * W / (H * ASPECT)).
  const maxRows = Math.max(
    4,
    Math.ceil(Math.sqrt((nodes.length * COLUMN_WIDTH) / (ROW_HEIGHT * ASPECT))),
  );
  const rankOf = (kind: string) => kinds.indexOf(kind);
  const order = new Map<string, number>(); // placement order, read by the next band
  let x = 0;
  for (const band of [...bands.keys()].sort((p, q) => p - q)) {
    const members = bands.get(band) ?? [];
    const anchor = (node: MapNode) => {
      const placed = (parentsOf.get(node.id) ?? [])
        .map((id) => order.get(id))
        .filter((at): at is number => at !== undefined);
      return placed.length === 0 ? -1 : Math.min(...placed);
    };
    members.sort(
      (a, b) =>
        anchor(a) - anchor(b) ||
        rankOf(a.data.kind) - rankOf(b.data.kind) ||
        a.data.label.localeCompare(b.data.label) ||
        a.id.localeCompare(b.id),
    );
    const columns = Math.ceil(members.length / maxRows);
    const rows = Math.ceil(members.length / columns);
    members.forEach((node, index) => {
      const column = Math.floor(index / rows);
      node.position = { x: x + column * COLUMN_WIDTH, y: (index % rows) * ROW_HEIGHT };
      order.set(node.id, order.size);
    });
    x += columns * COLUMN_WIDTH + BAND_GAP;
  }
}
