# ADR-0103: STALE is read from a local copy in a declared shape; the mapping question stays open
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-15, wave B)
Answers part of the docs/04 "Open" list: whether STALE's scenario format maps onto a
memory API without adaptation. Answer: **left open**, for the reason below.

## Context
docs/04 lists STALE (docs/06: "Benchmark of implicit memory conflicts",
arXiv 2605.06527v1) as the external benchmark "for comparability". Wave B is offline: no
download, no fetching of the paper. The only facts on hand are docs/06's one-line
description and the link. An honest answer to "does it map without adaptation?"
needs the release's actual record format, which this session cannot see.

## Decision
1. **The mapping question stays open.** It cannot be answered from a one-line
   description, and guessing would be an invented claim about someone else's
   benchmark. What *can* be said, and is recorded here as the analysis the author
   should test against the paper:
   - Ripple's bench checks memory **states** after each event (VALID/RETIRED/... per
     alias). Benchmarks of memory conflicts are commonly published as a dated
     conversation history plus probe questions with reference answers, i.e. they check
     **answers**, not states.
   - If STALE is of that kind, it does **not** map without adaptation. Three pieces are
     needed: (a) turning each user turn into statements through the write flow, which
     needs the LLM change detector and a Linker (ADR-0020), so it cannot run offline;
     (b) an answer step: retrieval (I1-aware) plus an answering model; (c) scoring the
     answer against the reference, with the judge-plus-human-sample protocol of docs/04.
     STALE then measures retrieval-level staleness (H2), not the state metrics.
   - If STALE instead labels memory states per event, the mapping is close to direct:
     sessions become `new`/`update` events and labels become expectations.
2. **Loader now, runner later.** `bench/stale.py` reads a local copy:
   `RIPPLE_STALE_PATH` names a `.jsonl` file or a folder of them; unset, empty or
   missing raises `ConfigurationError` naming the variable; nothing is downloaded.
3. **Declared shape, strict.** One JSON object per line: `item_id`; `sessions`
   (each `session_id`, ISO `date`, `turns` of `{role: user|assistant, content}`);
   `question`; `answer` (the up-to-date answer); optional `stale_answer`,
   `conflict_type` (the release's own label, verbatim) and `evidence_session_ids`.
   This is the collaborator's declared interchange shape for a history-plus-probe
   benchmark, **not verified against the release**. Models use `extra="forbid"`, so a
   release that differs fails at load time with file and line (`StaleFormatError`),
   and the author writes a small converter into this shape instead of the loader
   silently mis-reading fields.
4. A hand-written two-item fixture (tests/bench_v1/fixtures/stale/tiny.jsonl) tests the
   loader. It is not STALE data and is never reported as such.
5. `python -m bench.stale` prints counts of a local copy (items, sessions, turns,
   conflict types) so the author can check them against the paper. No STALE suite in
   `bench.run` until the mapping is decided; no result folder claims STALE numbers.

## Alternatives considered
- Answer "maps directly" and build a runner — would assert a format nobody here has
  read; a wrong mapping produces numbers that look comparable and are not. Lost (I8).
- Fetch the paper or dataset once — forbidden by the wave-B offline rule.
- No loader until the paper is read — leaves the author nothing to point at a copy and
  no test of the failure modes. Lost; the loader is cheap and its shape is explicit.
- A permissive loader (unknown fields ignored) — a renamed field would be silently
  dropped. Lost to strict validation.

## Consequences
- The author's action: read the STALE paper and release, place a copy locally, run
  `python -m bench.stale`; if it fails the declared shape, write a converter or amend
  this ADR's shape; then decide the mapping in the Phase 3 baseline ADR and close the
  docs/04 "Open" item.
- Until then the paper cites STALE as related work only; no comparability claim.

## Revisit if
The STALE release has been read (then supersede this ADR with the mapping decision),
or an answer-level harness exists for H2 that STALE can plug into.
