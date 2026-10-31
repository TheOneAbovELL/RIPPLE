# ADR-0088: API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields
Status: Accepted under the autonomous mandate · Date: 2026-10-26 · Amends ADR-0087
(map loading, content and layout), ADR-0086 (valid_to read-only) and ADR-0042 (edit
body) · checkpoint C3

## Context
The WS-12 handover listed five requests the dashboard worked around: the map made one
detail request per node; the edit form could not change `valid_to` although FR-12 says
"edit (content, valid_to)"; the kind filter hardcoded the jobs vocabulary; every `id`
in the generated client was optional because the core models give it a default
factory; and `next dev` on another port could not call the API.

## Decision
1. `GET /graph` returns the user's visible memories (the I1 boundary of GET /memories:
   no RETIRED rows, `flagged` on SUSPECT and PENDING_USER) and the links whose two ends
   are both visible. A named test, test_invariant_I1_graph_never_returns_retired_nodes_or_links_to_them,
   pins the boundary.
2. `EditIn.valid_to`: omitted keeps the old value, explicit null makes the belief
   permanent, a timestamp sets its end (the nightly sweep then expires it, ADR-0015).
   The router distinguishes "omitted" from "null" through `model_fields_set`.
3. `GET /vocabulary` returns the domain, the adapter's kinds and attributes
   (`Services.vocabulary`, a `DomainVocabulary`, jobs by default) and the registry's
   link types with their core class.
4. `Memory` and `Link` set `json_schema_serialization_defaults_required=True`, so the
   OpenAPI output schema marks every field required (serialisation always emits them).
   Input validation is unchanged.
5. `create_app(cors_origins=...)` adds CORSMiddleware for the given origins only;
   `RIPPLE_CORS_ORIGINS` sets them in development. Production passes none (same origin
   behind Caddy, ADR-0029).
6. `tests/api/test_openapi_snapshot.py` fails when apps/web/openapi.json drifts from the
   live schema.

## Alternatives considered
- A graph built client-side from detail calls (status quo): N+1 requests and the I1
  rule enforced by the client's choice of endpoints rather than one server boundary.
- A separate `PUT /memories/{id}/valid_to`: a second write path that would ripple
  separately from a content edit the user made in the same form.
- Hardcoded vocabulary in the dashboard: makes the inspector a jobs-only tool while
  core and the API are domain-agnostic (ADR-0013).
- Marking ids required with a custom schema hook per model: more code for the same
  effect as one Pydantic setting.

## Consequences
- The routes table in tests/api/test_invariants_api.py gains GET /graph and
  GET /vocabulary (read-only; I6 unaffected).
- The dashboard adopted all of it at C3 (docs/plans/parallel-execution/ws-12.md): the map
  loads `GET /graph` once and now draws every visible memory, laid out by dependency
  depth rather than by a fixed list of kinds (amends ADR-0087's content and layout); the
  edit form offers keep, set and clear for `valid_to` (amends ADR-0086's read-only
  note); the kind filter reads `GET /vocabulary` and degrades to "any kind" if it fails.
