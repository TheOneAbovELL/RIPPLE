# Architecture

## Principle
The graph decides scope; the LLM decides action (ADR-0003). The core engine is
domain-agnostic; domains plug in through adapters.

## Modules
| Module | Responsibility | May import |
|---|---|---|
| core | Models, Store interface, ripple engine, resolver interface, ChangeEvents | nothing in ripple except core |
| linking | Rule, LLM and trained linkers behind one Linker interface | core, llm |
| storage | SQLAlchemy tables, Alembic migrations, Postgres Store (ADR-0016) | core |
| retrieval | Validity-aware hybrid search, graph expansion, evidence fetch | core, storage |
| llm | Provider router, schemas, versioned prompts, FakeLLM | core |
| agents | LangGraph graphs: Conversation, Tailor; Scout as a plain loop (ADR-0072); Curator is the worker's sweep | everything above |
| domains/<name> | Schemas, link types, sources, rules for one domain | core, linking |
| api / mcp_server / notify / worker | Delivery | everything |

### How core stays domain-agnostic (ADR-0013)
Core defines two **link classes** with fixed behaviour: depends_on and snapshot_of
(table in docs/03-data-model.md), and two protocols it never implements: Linker and
Resolver. A domain adapter declares its link types and maps each to one class; the
write flow (agents / api) applies that mapping and rejects an unmapped type before
anything reaches core. Core validates only that link_class is one it knows. The engine,
the versioning code and the forget API only ever look at the class.

## Flows
1. Write (ripple.core.intake): statement → change detection (deterministic for structured
   facts, LLM for prose; ADR-0020) → new memory or new version → Linker proposes links
   → store (transaction) with its ChangeEvent → post-commit indexing (MemoryIndexer,
   retrieval keeps its lexical and dense indexes in step) → ripple.
2. Ripple (wave by wave, ADR-0013): a memory write (new fact, new version or expiry)
   is the trigger; its transaction also creates the ChangeEvent → engine takes the seed
   set (new version, or the retired memory) and emits wave 1 = dependents along
   depends_on links, no status filter, no LLM; they become SUSPECT and commit →
   Resolver decides keep / update / retire / ask per memory with retrieved evidence;
   the wave's decisions and state changes commit as one transaction appended to the
   ChangeEvent → only updated or retired memories seed the next wave; keep halts the
   branch; ask parks the memory in PENDING_USER and marks its subtree SUSPECT; a later
   answer starts a new ripple → repeat until an empty wave or the depth limit, then
   set completed_at. A failed commit rolls back to the last committed one; the sweep
   resumes ripples with no completed_at.
3. Read: query → hybrid search over VALID memories → graph expansion → evidence →
   agent answers with citations.
4. Scout loop: schedule or criteria change → fetch allowed sources → parse → dedupe →
   write flow → rank → notify.

## Agents
| Agent | Trigger | Permissions |
|---|---|---|
| Conversation | user message | read memory; write facts via write flow |
| Scout | daily; criteria change | plain loop over injected parts (ADR-0072); GET only through ripple.domains.jobs.sources (robots, terms, rate limits; ADR-0008); write openings |
| Curator | memory write; nightly sweep (expiry of valid_to, re-check of weak links FR-16, resume of ripples with no completed_at) | run ripples; ask user; commit |
| Tailor | on request | read only |

## RAG
Validity-aware (I1: VALID returned; SUSPECT and PENDING_USER only flagged; RETIRED
never), graph-expanded (1 hop by default, skipping history depends_on links whose
parent is superseded), evidence-cited.
Key metric: stale retrieval rate.

## Open (not yet decided; see docs/plans/phase-0.md)
- Identity and auth for a multi-user pilot (User entity, login, Telegram linking).
- Embedding model (Phase 3), LangGraph checkpointer (Phase 2), resume PDF parser
  (Phase 2): each needs an ADR before its first import. Observability, ORM and the job
  queue are decided in ADR-0016 to 0018.

## Security
- Retrieved text is untrusted: evidence only in user messages; injection defence in prompts.
- Allowed-sources registry for Scout (ADR-0008).
- Secrets only in env; never logged.

## Deployment
Docker Compose: api, worker, postgres(+pgvector), redis (ADR-0017), web. One VPS for
the pilot.
