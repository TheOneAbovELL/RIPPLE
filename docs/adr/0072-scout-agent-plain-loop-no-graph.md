# ADR-0072: The Scout is a plain loop over injected parts, fetching only through the sources package
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-9)

## Context
docs/02 lists the Scout among the LangGraph agents (ADR-0005) with the permissions
"fetch allowed sources; write openings". FR-8 asks for a daily run and a run on a
search-criteria change. I5 forbids invented facts, I6 forbids acting on an external
site, and the agents package already has an invariant test that scans its imports: no
HTTP client, no delivery package, a short stdlib allowlist. The question is the shape
of the agent, where the HTTP client lives, how criteria reach it, and how the two
triggers are wired.

## Decision
1. **A plain class, not a graph.** `ScoutAgent.run_for_user(user_id)` is a loop with
   no decision a model makes: fetch → extract → dedupe → parse → filter → record. The
   only model call is `parse_jd` (WS-2, ADR-0035), already schema-validated and
   span-checked. A LangGraph graph would add a checkpointer and node plumbing to a
   function with no branch worth resuming. The Conversation and Tailor agents keep
   their graphs; ADR-0005 is narrowed, not reversed: graphs are for agents whose next
   step depends on model output.
2. **The agent never imports an HTTP client.** It receives a `SourceFetcher`
   (`ripple.domains.jobs.sources`), which is the only code that sends requests:
   GET only, to the registered host only, after robots.txt, at the source's rate (the
   slower of the registry's limit and robots' `Crawl-delay`), with ETag / Last-Modified
   revalidation, exponential backoff on 429 / 5xx / transport errors, no retry on 4xx,
   same-host redirects only, cookies cleared before every request, 401 / 403 / 407 and
   `WWW-Authenticate` refused outright. `sources.wiring.open_fetcher` builds the real
   client; the agents import scan keeps passing without exceptions.
3. **Criteria come from the user's VALID `criteria` memory** (the one `derive_criteria`
   writes, ADR-0031), parsed back from its content into `ScoutCriteria` (cgpa, batch,
   skills). The filter is narrow: a JD whose stated cutoff exceeds the CGPA, or whose
   stated batches exclude the student's, is not recorded; a JD that states neither
   passes, and eligibility is decided later from facts. A SUSPECT or PENDING_USER
   criteria is not used (the Scout does not act on a belief under question); no criteria
   means no filter, so a new user still gets openings.
4. **Per-source isolation, per-candidate isolation.** A source's failure is counted and
   the next source runs; a candidate's failure (refused fetch, failed fetch, parser
   rejection, adapter validation) is counted with its URL and the next candidate runs.
   Only failures outside any source (the store, the criteria read) propagate, so the
   worker job can isolate the user. The cap `max_candidates_per_source` (25) bounds
   model calls per source per run.
5. **Two triggers.** The daily run is `worker.jobs.scout_run`: one lease per user
   (`scout:<user id>`, 45 minutes, longer than the cron slot's timeout), failures
   isolated and raised at the end as `JobFailedForUsersError`, the agent built per run
   from the environment (registry file, Router config) and its client closed afterwards.
   The criteria-change run goes through the `ScoutTrigger` protocol
   (`on_criteria_changed(user_id)`): `ImmediateScoutTrigger` runs in-process,
   `EnqueueingScoutTrigger` hands the user id to a queue. `event_changed_criteria(store,
   event)` tells the caller whether a completed ChangeEvent touched a criteria memory
   (its trigger is one, or an UPDATE decision is on one). The hook point is the
   coordinator's: the write flow or `RippleRunner` completion calls it; the single-user
   worker job is registered by WS-6 (handover).
6. **Source refs and provenance.** Every recorded opening has `source_ref`
   `scout:<source id>:<canonical url>` and `created_by = "scout"`; every field memory's
   content is the page's own words at a span into the text the parser saw (I5, tested
   by `test_invariant_I5_scout_records_only_parsed_fields_with_spans_into_the_page_text`).

## Alternatives considered
- A LangGraph graph with fetch / parse / record nodes: uniform with the other agents,
  but no node's successor depends on a model, and the checkpointer would persist page
  bodies for no resume benefit. Lost.
- Letting the agent own an `httpx.AsyncClient`: simplest wiring, but it fails the
  agents import scan and puts the one network capability next to the memory-writing
  code. Lost; the fetcher is injected.
- Hard filter on skills too: a JD asking for one skill the student lacks would vanish;
  fit (ADR-0031) is the right place for a graded answer. Lost.
- Running the Scout synchronously inside the API request that changed the criteria:
  blocks a user request on remote fetches. Lost; the enqueueing trigger is the
  production shape, the immediate one is for development.

## Consequences
- The Scout's cost per night is bounded by sources × cap model calls, and by the
  dedupe (ADR-0071) usually far fewer.
- docs/02's agents table should read "Scout: plain loop (no graph), fetch via sources
  package" once the coordinator updates it; the permissions column is unchanged.
- The agents package gains no new `Capability`; a `source.fetch` capability is
  requested in the handover so the Scout can declare what it does like the others.
- Two WS-6 tests that asserted `scout_run` raises `NotImplementedError` now fail by
  design and need their replacement (handover).

## Revisit if
A source needs pagination or search parameters per criteria (then the hint grows a
query template and the loop grows a page cursor), or the pilot needs the Scout to close
openings it no longer finds (an opening lifecycle decision, WS-1 handover open problem).
