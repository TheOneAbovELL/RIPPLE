# ADR-0087: Openings map built from the inspector's `why` links, laid out by kind
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-12)

## Context
FR-13: openings, skills and applications as one live graph. The API has no graph
endpoint; `GET /memories/{id}` returns the parents of one memory (`why`, ADR-0042) and
`GET /memories` the visible rows. The frontend rule forbids business logic, so the map
may arrange and label but not decide.

## Decision
- **Data**: the page lists the visible memories once, keeps those whose kind is
  `opening`, `application` or `derived`, plus facts whose structured attribute is
  `skill`, then calls `GET /memories/{id}` for each kept memory and uses its `why`
  entries as edges (parent → dependent, labelled with `link_type`). A parent that was
  not in the kept set (a CGPA fact, say) is added as a plain fact node so no edge
  dangles. RETIRED memories are never drawn (I1).
- **Rendering**: `@xyflow/react` 12 with one custom node type showing the category
  label, the content as a link to the detail page, the status chip (colour and text)
  and the API's flag. `depends_on` edges are solid and animated (they propagate
  ripples); `snapshot_of` edges are dashed. Nodes are neither draggable nor
  connectable: positions are the layout's, and a drag on a controlled graph would only
  snap back.
- **Layout**: columns by category (skills and facts, openings, derived beliefs,
  applications), rows ordered by label, fixed spacing. Deterministic, no layout
  library, no position persisted.
- **Accessibility**: under the canvas a `<details>` lists the same nodes and edges as
  text ("Eligible for Acme *eligibility_of* SDE intern at Acme"), so keyboard and
  screen-reader users get the graph without dragging.
- **Contract request**: one `GET /graph` endpoint returning visible nodes and their
  links for the user would replace N+1 detail calls. The page is written so only the
  loader changes; the pure builder `src/features/map/graph.ts` keeps its tests.

## Alternatives considered
- Wait for `/graph` before building the map: leaves FR-13 unbuilt in the production
  pass for a performance concern that does not bite at pilot scale (tens of nodes).
  Lost.
- Read links from `GET /me/export`: returns every link including retired versions and
  resume candidates; filtering that on the client is business logic. Lost.
- dagre or elk for layout: better edges, one more dependency and a non-deterministic
  look between runs. Lost; revisit if maps grow past a screen.
- Infer skill nodes from content keywords: a client-side rule. Lost; the structured
  attribute is the API's word.

## Consequences
- N+1 requests per map load; acceptable for the pilot, replaced by `/graph` later.
- The map shows only what the inspector would show; a link the API hides (history
  depends_on) is hidden here too.

## Revisit if
`/graph` lands (swap the loader), or maps exceed a hundred nodes (layout library).
