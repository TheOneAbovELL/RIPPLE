import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { GraphOut, Link, Memory, VocabularyOut } from "@/api/types";
import { buildGraph, orderKinds } from "@/features/map/graph";
import { MapView } from "@/features/map/MapView";

import { deferred, fakeApi, listed, memory, renderSignedIn } from "./helpers";

// React Flow needs a real layout engine; in jsdom the test replaces it with a flat
// rendering of the nodes it was given, so the page's own output can still be checked.
// React Flow measures and fits in a real browser; here the mock records the props the map
// passes for that.
const flow = vi.hoisted(() => ({ props: {} as Record<string, unknown> }));

vi.mock("@xyflow/react", async () => {
  const React = await import("react");
  type Props = {
    nodes: { id: string; data: { label: string } }[];
    edges: {
      id: string;
      animated?: boolean;
      label?: string;
      className?: string;
      style?: { strokeDasharray?: string };
    }[];
    children?: React.ReactNode;
  };
  return {
    ReactFlow: (props: Props & Record<string, unknown>) => {
      flow.props = props;
      const { nodes, edges, children } = props;
      return React.createElement(
        "div",
        {
          "data-testid": "flow",
          "data-edges": edges.length,
          "data-animated": edges.filter((e) => e.animated).length,
          "data-dashed": edges.filter((e) => e.style?.strokeDasharray).length,
          "data-hover-labels": edges.filter((e) => e.className === "map-edge").length,
        },
        nodes.map((n) => React.createElement("span", { key: n.id }, n.data.label)),
        children,
      );
    },
    Background: () => null,
    Controls: () => null,
    Handle: () => null,
    Position: { Left: "left", Right: "right" },
  };
});

function link(parent: Memory, dependent: Memory, overrides: Partial<Link> = {}): Link {
  return {
    id: `link-${parent.id}-${dependent.id}`,
    parent_id: parent.id,
    dependent_id: dependent.id,
    link_type: "eligibility_of",
    link_class: "depends_on",
    created_by: "rule",
    created_at: "2026-10-20T09:00:00Z",
    confidence: 0.9,
    strength: 1,
    verified_at: null,
    ...overrides,
  };
}

const VOCABULARY: VocabularyOut = {
  domain: "jobs",
  kinds: ["fact", "derived", "opening", "application", "criteria"],
  attributes: ["cgpa", "skill"],
  link_types: [{ name: "eligibility_of", link_class: "depends_on" }],
  profile_subject: "student",
  profile_attributes: [],
};

describe("buildGraph", () => {
  const cgpa = memory({ id: "fact-cgpa", content: "CGPA is 8.2" });
  const python = memory({ id: "skill-py", content: "Knows Python" });
  const opening = memory({ id: "open-1", kind: "opening", content: "SDE intern at Acme" });
  const eligible = memory({
    id: "der-1",
    kind: "derived",
    content: "Eligible for Acme",
    status: "SUSPECT",
  });
  const application = memory({ id: "app-1", kind: "application", content: "Applied to Acme" });

  it("draws every node the API returned and its links, parent to dependent", () => {
    const graph = buildGraph({
      nodes: [listed(cgpa), listed(python), listed(opening), listed(eligible, true)],
      links: [link(opening, eligible), link(cgpa, eligible)],
    });
    expect(graph.nodes.map((n) => n.id).sort()).toEqual([
      "der-1",
      "fact-cgpa",
      "open-1",
      "skill-py",
    ]);
    expect(graph.edges.map((e) => `${e.source}->${e.target}:${e.label}`).sort()).toEqual([
      "fact-cgpa->der-1:eligibility_of",
      "open-1->der-1:eligibility_of",
    ]);
  });

  it("skips a link whose other end is not among the nodes", () => {
    const graph = buildGraph({
      nodes: [listed(opening)],
      links: [link(opening, application, { link_type: "application_for" })],
    });
    expect(graph.edges).toEqual([]);
  });

  it("carries kind, status and the API's flag onto the node without deriving any", () => {
    const graph = buildGraph({ nodes: [listed(eligible, true), listed(opening)], links: [] });
    const node = graph.nodes.find((n) => n.id === "der-1")!;
    expect(node.data.kind).toBe("derived");
    expect(node.data.status).toBe("SUSPECT");
    expect(node.data.flagged).toBe(true);
    const unflagged = buildGraph({ nodes: [listed(eligible, false)], links: [] }).nodes[0]!;
    expect(unflagged.data.flagged).toBe(false);
  });

  it("marks snapshot links as not propagating", () => {
    const graph = buildGraph({
      nodes: [listed(opening), listed(application)],
      links: [link(opening, application, { link_class: "snapshot_of" })],
    });
    expect(graph.edges[0]!.propagates).toBe(false);
  });

  it("puts every dependent right of its parents and never overlaps two nodes", () => {
    const second = memory({ id: "open-2", kind: "opening", content: "Backend intern at Beta" });
    const graph = buildGraph(
      {
        nodes: [
          listed(cgpa),
          listed(opening),
          listed(second),
          listed(eligible),
          listed(application),
        ],
        links: [link(cgpa, eligible), link(opening, eligible), link(eligible, application)],
      },
      VOCABULARY.kinds,
    );
    const at = new Map(graph.nodes.map((n) => [n.id, n.position]));
    expect(at.get("fact-cgpa")!.x).toBeLessThan(at.get("der-1")!.x);
    expect(at.get("open-1")!.x).toBeLessThan(at.get("der-1")!.x);
    expect(at.get("der-1")!.x).toBeLessThan(at.get("app-1")!.x);
    const positions = graph.nodes.map((n) => `${n.position.x},${n.position.y}`);
    expect(new Set(positions).size).toBe(positions.length);
  });

  it("wraps a tall band into columns so the map has about the frame's shape", () => {
    // 3 sources, each read into 10 fields, and one belief per source: the shape of the
    // seeded demo that used to draw one column 30 nodes tall.
    const sources = [0, 1, 2].map((i) => memory({ id: `src-${i}`, kind: "opening" }));
    const fields = sources.flatMap((source, i) =>
      Array.from({ length: 10 }, (_, j) =>
        memory({ id: `f-${i}-${j}`, content: `field ${j}` }),
      ),
    );
    const beliefs = sources.map((_, i) => memory({ id: `b-${i}`, kind: "derived" }));
    const links = [
      ...fields.map((field, k) => link(sources[Math.floor(k / 10)]!, field)),
      ...beliefs.map((belief, i) => link(fields[i * 10]!, belief)),
    ];
    const graph = buildGraph(
      { nodes: [...sources, ...fields, ...beliefs].map((m) => listed(m)), links },
      ["fact", "derived", "opening"],
    );
    const xs = graph.nodes.map((n) => n.position.x);
    const ys = graph.nodes.map((n) => n.position.y);
    const width = Math.max(...xs) - Math.min(...xs) + 260;
    const height = Math.max(...ys) - Math.min(...ys) + 136;
    // About the frame's shape (1.6 : 1), not one tall column.
    expect(width / height).toBeGreaterThan(0.8);
    expect(width / height).toBeLessThan(3);
    // One source's fields stay together: their rows are contiguous within the band.
    const at = new Map(graph.nodes.map((n) => [n.id, n.position]));
    const firstSourceFields = fields.slice(0, 10).map((f) => at.get(f.id)!);
    const otherFields = fields.slice(10).map((f) => at.get(f.id)!);
    const key = (p: { x: number; y: number }) => p.x * 10000 + p.y;
    expect(Math.max(...firstSourceFields.map(key))).toBeLessThan(
      Math.min(...otherFields.map(key)),
    );
  });

  it("survives a cycle in the links instead of recursing forever", () => {
    const graph = buildGraph({
      nodes: [listed(opening), listed(eligible)],
      links: [link(opening, eligible), link(eligible, opening)],
    });
    const [first, second] = graph.nodes.map((n) => n.position);
    expect(first).not.toEqual(second);
  });

  it("draws a node or a link the API repeated only once", () => {
    const graph = buildGraph({
      nodes: [listed(opening), listed(opening), listed(eligible)],
      links: [link(opening, eligible), link(opening, eligible)],
    });
    expect(graph.nodes).toHaveLength(2);
    expect(graph.edges).toHaveLength(1);
  });

  it("orders the nodes of one column by the vocabulary's kinds, not alphabetically", () => {
    // Both are roots (column 0); "opening" sorts after "fact" alphabetically, and the
    // vocabulary here puts it first.
    const graph = buildGraph({ nodes: [listed(cgpa), listed(opening)], links: [] }, [
      "opening",
      "fact",
    ]);
    const at = new Map(graph.nodes.map((n) => [n.id, n.position]));
    expect(at.get("open-1")!.x).toBe(at.get("fact-cgpa")!.x);
    expect(at.get("open-1")!.y).toBeLessThan(at.get("fact-cgpa")!.y);
  });

  it("orders kinds by the vocabulary and puts unknown kinds last, alphabetically", () => {
    expect(
      orderKinds(["opening", "zeta", "fact", "alpha", "opening"], VOCABULARY.kinds),
    ).toEqual(["fact", "opening", "alpha", "zeta"]);
    expect(orderKinds(["opening", "fact"], [])).toEqual(["fact", "opening"]);
  });

  it("never draws a RETIRED memory or an edge to one (I1 at the UI)", () => {
    const retired = memory({
      id: "open-old",
      kind: "opening",
      content: "Closed opening",
      status: "RETIRED",
    });
    const graph = buildGraph({
      nodes: [listed(retired), listed(eligible)],
      links: [link(retired, eligible)],
    });
    expect(graph.nodes.map((n) => n.id)).toEqual(["der-1"]);
    expect(graph.edges).toEqual([]);
  });
});

describe("MapView", () => {
  const opening = memory({ id: "open-1", kind: "opening", content: "SDE intern at Acme" });
  const derived = memory({ id: "der-1", kind: "derived", content: "Eligible for Acme" });
  const graphOut: GraphOut = {
    nodes: [listed(opening), listed(derived)],
    links: [link(opening, derived)],
  };

  it("shows a loading status first", async () => {
    const pending = deferred<GraphOut>();
    renderSignedIn(
      <MapView />,
      fakeApi({
        getGraph: vi.fn(() => pending.promise),
        getVocabulary: vi.fn(async () => VOCABULARY),
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Loading the openings map");
    pending.resolve({ nodes: [], links: [] });
  });

  it("shows an empty message when there is nothing to map", async () => {
    renderSignedIn(
      <MapView />,
      fakeApi({
        getGraph: vi.fn(async () => ({ nodes: [], links: [] })),
        getVocabulary: vi.fn(async () => VOCABULARY),
      }),
    );
    expect(await screen.findByText(/No memories to map yet/)).toBeInTheDocument();
  });

  it("shows the API error", async () => {
    const api = fakeApi({
      getGraph: vi.fn(async () => Promise.reject(new ApiError(500, undefined))),
      getVocabulary: vi.fn(async () => VOCABULARY),
    });
    renderSignedIn(<MapView />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("status 500");
  });

  it("loads the whole graph in one call and renders it with its text list", async () => {
    const getGraph = vi.fn(async () => graphOut);
    const api = fakeApi({ getGraph, getVocabulary: vi.fn(async () => VOCABULARY) });
    renderSignedIn(<MapView />, api);
    const flow = await screen.findByTestId("flow");
    expect(getGraph).toHaveBeenCalledTimes(1);
    expect(api.getMemory).not.toHaveBeenCalled();
    expect(api.listMemories).not.toHaveBeenCalled();
    expect(flow).toHaveAttribute("data-edges", "1");
    const links = screen.getByRole("list", { name: "Map links" });
    expect(within(links).getByText(/Eligible for Acme/)).toHaveTextContent(
      "Eligible for Acme depends on SDE intern at Acme (eligibility_of)",
    );
    const nodes = screen.getByRole("list", { name: "Map nodes" });
    expect(nodes).toHaveTextContent("Opening: SDE intern at Acme");
    expect(nodes).toHaveTextContent("Derived: Eligible for Acme");
  });

  it("draws depends_on links solid and snapshot links dashed, as the legend says", async () => {
    const application = memory({ id: "app-1", kind: "application", content: "Applied" });
    const api = fakeApi({
      getGraph: vi.fn(async () => ({
        nodes: [listed(opening), listed(derived), listed(application)],
        links: [
          link(opening, derived),
          link(opening, application, { link_class: "snapshot_of", link_type: "sent_with" }),
        ],
      })),
      getVocabulary: vi.fn(async () => VOCABULARY),
    });
    renderSignedIn(<MapView />, api);
    const flow = await screen.findByTestId("flow");
    expect(flow).toHaveAttribute("data-animated", "0");
    expect(flow).toHaveAttribute("data-dashed", "1");
    expect(screen.getByRole("list", { name: "Map links" })).toHaveTextContent(
      "Applied is a snapshot of SDE intern at Acme (sent_with)",
    );
  });

  it("fits the whole graph into view after measurement, zooming out far enough", async () => {
    const api = fakeApi({
      getGraph: vi.fn(async () => ({ nodes: [listed({ content: "CGPA is 8.1" })], links: [] })),
      getVocabulary: vi.fn(async () => VOCABULARY),
    });
    renderSignedIn(<MapView />, api);
    await screen.findByTestId("flow");
    // React Flow runs a queued fitView once the nodes are measured; the default minZoom
    // (0.5) is what left a tall graph out of view, so both must allow 0.2.
    expect(flow.props.fitView).toBe(true);
    expect(flow.props.minZoom).toBe(0.2);
    expect(flow.props.fitViewOptions).toEqual({ padding: 0.08, minZoom: 0.2 });
  });

  it("keeps edge labels for hover and selection instead of drawing them all", async () => {
    const parent = memory({ content: "CGPA is 8.1" });
    const child = memory({ kind: "derived", content: "eligible" });
    const api = fakeApi({
      getGraph: vi.fn(async () => ({
        nodes: [listed(parent), listed(child)],
        links: [link(parent, child)],
      })),
      getVocabulary: vi.fn(async () => VOCABULARY),
    });
    renderSignedIn(<MapView />, api);
    expect(await screen.findByTestId("flow")).toHaveAttribute("data-hover-labels", "1");
    expect(screen.getByText(/hover or select an edge for its link type/)).toBeInTheDocument();
  });

  it("still draws the map when the vocabulary request fails", async () => {
    const api = fakeApi({
      getGraph: vi.fn(async () => graphOut),
      getVocabulary: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
    });
    renderSignedIn(<MapView />, api);
    expect(await screen.findByTestId("flow")).toHaveAttribute("data-edges", "1");
    expect(screen.getByRole("list", { name: "Map nodes" })).toHaveTextContent(
      "Opening: SDE intern at Acme",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
