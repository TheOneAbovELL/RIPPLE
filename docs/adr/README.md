# Architecture Decision Records
Accepted ADRs are never edited; they are superseded by new ones.
Workstream ADR ranges (docs/plans/parallel-execution.md): WS-1 0030-0034, WS-2 0035-0039,
WS-3 0040-0044, WS-4 0045-0049, WS-5 0050-0054, WS-6 0055-0059, WS-7 0060-0064, WS-8 0065-0069,
WS-9 0070-0074, WS-10 0075-0079, WS-11 0080-0084, WS-12 0085-0089, WS-14 0090-0094, WS-13 0095-0099, WS-15 0100-0104, WS-16 0105-0109, WS-17 0110-0114.

| # | Title | Status |
|---|---|---|
| 0001 | Record decisions as ADRs | Accepted |
| 0002 | Job hunting is the primary domain | Accepted |
| 0003 | The graph decides scope; the LLM decides action | Accepted · amended by 0013 |
| 0004 | PostgreSQL + pgvector with in-process traversal | Accepted · amended by 0013 |
| 0005 | LangGraph for agents; core stays framework-free | Accepted |
| 0006 | Expose memory tools over MCP | Accepted |
| 0007 | Retire, never silently delete | Accepted · amended by 0013 |
| 0008 | The human applies; allowed sources only | Accepted |
| 0009 | A trained small model for link finding | Accepted |
| 0010 | Provider-agnostic LLM router with structured outputs | Accepted; Anthropic request shape amended by 0117 |
| 0011 | Python tooling: uv, ruff, pyright, pytest | Accepted |
| 0012 | Evaluation-first development | Accepted |
| 0013 | Wave-by-wave ripple over core link classes | Accepted; wave order amended by 0119 (a memory waits for every affected parent) |
| 0014 | Memory versions are rows; dependency links are copied to the new version | Accepted |
| 0015 | Every change is a memory write; temporary facts self-expire | Accepted |
| 0016 | SQLAlchemy 2 (async, psycopg) + Alembic, in a storage package outside core | Accepted |
| 0017 | Background jobs with arq on Redis | Accepted |
| 0018 | Observability with Langfuse over OpenTelemetry; structured logging until then | Accepted |
| 0019 | Rule-first resolution | Accepted |
| 0020 | Change detection: deterministic for structured facts, LLM for prose | Accepted; permanent structured facts amended by 0116 |
| 0021 | Scenario files are YAML, parsed with PyYAML | Accepted |
| 0022 | Web API stack: FastAPI, uvicorn, httpx, python-multipart | Accepted |
| 0023 | LangGraph dependency and Postgres checkpointer | Accepted |
| 0024 | Resume parsing: pypdf text extraction, LLM structuring, user confirmation | Accepted |
| 0025 | Notifications: Telegram Bot API over httpx; email deferred | Accepted |
| 0026 | Retrieval is lexical-first behind an Embedder contract; dense model decided at integration | Accepted |
| 0027 | Anthropic SDK as the first provider adapter; structured output via forced tool use | Accepted |
| 0030 | An opening is one anchor memory plus one structured fact per field | Accepted |
| 0031 | Jobs rule resolvers recompute derived beliefs from their parents | Accepted; points 1 and 5 amended by 0034 |
| 0032 | Ranking openings: eligible, then urgent, then fit, then variety; flagged, never retired | Accepted |
| 0035 | Parsers: LLM extraction with deterministic span, value and date validation | Accepted |
| 0040 | Identity for the pilot: admin-created users, hashed bearer tokens, one-time Telegram link codes | Accepted |
| 0041 | API composition: `create_app(services)`, a `Services` object, environment-only wiring | Accepted |
| 0042 | Inspector endpoints: I1 at the boundary, history on request, edits go straight to versioning | Accepted; edit body amended by 0088 |
| 0043 | Resume candidates live in their own table until the user decides | Accepted; amended by 0096 |
| 0044 | Export everything, delete through forget, keep the deletion audit | Accepted |
| 0045 | Conversation agent: one LangGraph turn, strict intent, evidence-only answers | Accepted |
| 0046 | Tailor agent: read-only, picks from id-validated candidates | Accepted |
| 0050 | Lexical scoring (BM25 / PostgreSQL FTS), reciprocal rank fusion and one-hop graph expansion for retrieval | Accepted |
| 0055 | Digest and alert policy: thresholds, rendering, what never alerts | Accepted |
| 0056 | Worker jobs are idempotent per user; sweeps hold a per-user lease; UTC schedule | Accepted; amended by 0095, 0099 |
| 0060 | Baseline memory strategies behind one MemoryStrategy protocol | Accepted; member order amended by 0104; config keys by 0122 |
| 0061 | RippleBench v0 jobs track is generated from seeded personas and templates | Accepted |
| 0062 | Time-to-consistency replay harness with per-event snapshots | Accepted |
| 0063 | Metric definitions for RippleBench v0 (interfaces; bodies are [human]) | Accepted; bodies implemented by 0120 at the author's request; wording amended by 0123 |
| 0028 | Langfuse tracer implemented now behind the Tracer protocol | Accepted |
| 0029 | Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups | Accepted |
| 0070 | Allowed-sources registry: a YAML file validated into Pydantic, terms note required | Accepted |
| 0071 | Scout dedupe by canonical URL, then (company, title) fingerprint, with a seen ledger | Accepted |
| 0072 | The Scout is a plain loop over injected parts, fetching only through the sources package | Accepted; points 3-4 amended by 0073 |
| 0034 | CGPA is compared with a cutoff only on one scale; otherwise the rules defer | Accepted (amends 0031) |
| 0073 | Scout refusals are counted apart from errors; criteria parse only the gates | Accepted (amends 0072) |
| 0075 | Telegram inbound: a strict subset of the Update type, private chats only, drops counted | Accepted |
| 0076 | Telegram dispatcher: commands, link flow, keyboards for answers, two-step forget, agent for the rest | Accepted |
| 0077 | Telegram delivery: secret-token webhook into the API, at-most-once by update_id, long polling for development only | Accepted; wiring amended by 0078 |
| 0078 | The Telegram channel is hosted in the API's lifespan; Services carries the shared parts | Accepted (amends 0077, 0082) |
| 0079 | Event observers on the runner; a criteria change queues a per-user Scout run | Accepted; derivation observer added by 0116 |
| 0080 | MCP server on the SDK's low-level Server, explicit Pydantic tool schemas, seven tools | Accepted |
| 0081 | MCP identity: one bearer token per connection, hashed through ADR-0040, bound per request | Accepted |
| 0082 | MCP transports: stdio for local clients, stateless streamable HTTP for the VPS, one wiring | Accepted; point 3 amended by 0078 |
| 0085 | Dashboard stack: Next.js static export, openapi-typescript client, Vitest | Accepted |
| 0086 | Dashboard pages, token session in sessionStorage, query-string routing | Accepted; valid_to note amended by 0088 |
| 0087 | Openings map built from the inspector's why links, laid out by kind | Accepted; loading, content and layout amended by 0088; vocabulary by 0118 |
| 0088 | API additions for the dashboard: /graph, /vocabulary, editable valid_to, required output fields | Accepted (amends 0086, 0087, 0042) |
| 0095 | A Postgres delivery log keyed by (user, kind, key) makes digests and alerts survive restarts | Accepted (amends 0056) |
| 0096 | Candidate decisions are a compare-and-set on status, so a double confirm cannot write twice | Accepted (amends 0043) |
| 0097 | The text layer of every resume upload is stored so span references resolve | Accepted |
| 0098 | API boundary hardening: token-bucket write limits, health probes, request ids with JSON logs, security headers and a body cap | Accepted |
| 0099 | The runner holds a per-ChangeEvent lease while it drives an event | Accepted |
| 0090 | Jobs link pairs come from static scenario snapshots, with structure rules as a stratum | Accepted |
| 0091 | Negatives at 3 per positive with every reversed link kept; train decontaminated against test | Accepted |
| 0092 | The 300-pair hand check is stratified, blind, keyed and re-drawn at report time | Accepted |
| 0093 | Link finders are scored per pair with opaque ids, stratified by provenance and held-out cell | Accepted; transfer mode amended by 0127 |
| 0094 | The training loop is an interface with a fixed data view; the loop is the author's | Accepted; loop implemented by 0126 at the author's request |
| 0100 | Minimal news and finance adapters are vocabularies mapped onto the core link classes | Accepted |
| 0101 | RippleBench v1 news and finance tracks are generated, synthetic and labelled so | Accepted |
| 0102 | Finance link pairs for H4 come from the finance_v1 scenarios, test split only | Accepted |
| 0103 | STALE is read from a local copy in a declared shape; the mapping question stays open | Accepted |
| 0104 | check_everything applies its one wave parents first | Accepted (amends 0060) |
| 0105 | Pilot feedback is one row per (student, memory, kind), first statement wins | Accepted |
| 0106 | The weekly pilot report computes two docs/04 metrics and marks three TBD | Accepted |
| 0107 | Three incident severities and a daily monitoring check for a one-operator pilot | Accepted |
| 0110 | Paper and thesis numbers are registered macros rendered from results/ | Accepted |
| 0111 | The I8 check: what counts as a result number and how it is accepted | Accepted |
| 0115 | Embedded Postgres with pgvector for development and the local slow suite | Accepted |
| 0116 | Structured facts are classified, linked and derived from without a model | Accepted (amends 0020, 0031, 0079); permanence keyed by 0140 |
| 0117 | The Anthropic adapter sends only arguments the pinned SDK accepts (no temperature) | Accepted (amends 0010) |
| 0118 | Profile vocabulary, an events feed and the final-delivery integration fixes | Accepted (amends 0087, 0131, 0134; wires 0128); events and specs amended by 0140 |
| 0119 | A memory is resolved after every affected parent of it (waves follow depth) | Accepted (amends 0013) |
| 0120 | Metric bodies, pooled suite aggregation and a retrieval probe in the replay | Accepted (implements 0063) |
| 0121 | "Three seeds" means three generator seeds, one results folder per seed | Accepted (settles 0110 point 8) |
| 0122 | Offline ablations, the linker and ablation keys, and counted LLM calls | Accepted (amends 0060, 0062) |
| 0123 | A row a version behind gold is stale; a repeated gold keeps the TTC window open | Accepted (amends 0063 wording) |
| 0125 | The trained link finder fine-tunes ModernBERT-base on CPU; torch and transformers in a linkfinder group | Accepted |
| 0126 | Link-finder training recipe, artifact folder, and the served linker in ripple.linking.trained | Accepted (amends 0094) |
| 0127 | Link-finder evaluation: a transfer mode for H4, CPU cost per call, and a three-seed summary | Accepted (amends 0093) |
| 0128 | The write-path linker is chosen by RIPPLE_LINKER; the LLM linker stays the default until H3 is judged | Accepted; wired by 0118 |
| 0130 | Dashboard information architecture and visual system | Accepted |
| 0131 | Student write flows in the dashboard (Telegram link, resume, openings, statements) | Accepted; point 6 amended by 0118 |
| 0132 | One-command local run of the whole product | Accepted |
| 0133 | The demo seed writes through the real paths with a deterministic "ask" fallback | Accepted |
| 0134 | Run one worker job locally without Redis | Accepted; wiring amended by 0118 |
| 0140 | Hardening of the final integration after code review | Accepted (amends 0116, 0118) |
