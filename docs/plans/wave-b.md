# Wave B — evaluation, pilot operations and write-up plumbing
Written 2026-10-31 by the coordinator under the autonomous mandate; launched the same
day on the author's "Start wave B". Parent plan: docs/plans/production-plan.md (wave B).
Tracker: docs/plans/parallel-execution.md. Closes at checkpoint C4.

## Ground truth at launch
Checkpoint C3 closed on 2026-10-26: 1346 passed, 31 xfailed (the author's WaveEngine and
metric functions), ruff and pyright clean, dashboard green. Still no commit, remote,
Docker or API key. Consequences for this wave:
- No Ripple-strategy numbers exist and none may be invented (I8). Every harness here
  writes results/ folders and reports "TBD (pending run)" where a [human] body or a
  live model is missing.
- No network from sessions: no dataset downloads, no real LLM, no real Telegram. Real
  data (news stories, STALE) is an author action, documented as such.
- No new dependency (no PyTorch, no matplotlib); needs go to the handover.

## Shared contract added for this wave
| Id | Contract | File | Consumers |
|---|---|---|---|
| C5 | Labelled link pairs: `LabelledPair`, `PairMemory`, `Provenance`, `Split`, `split_for`, `write_pairs`, `read_pairs` | bench/linkpairs.py (tested in tests/scenarios/test_linkpairs_contract.py) | WS-14, WS-15 |

## Workstreams
| WS | Name | Owns (create/edit) | ADRs | Migration |
|---|---|---|---|---|
| WS-14 | Link-finder data and evaluation harness | training/** (new package), tests/training/**, data under training/data/**, docs/learning/link-finder-data.md, docs/plans/parallel-execution/ws-14.md | 0090–0094 | — |
| WS-15 | RippleBench v1: news track, finance track, STALE adapter | bench/** except bench/linkpairs.py and the bodies in bench/metrics.py; bench/data/news_v1/**, bench/data/finance_v1/**; src/ripple/domains/news/**, src/ripple/domains/finance/**; tests/bench_v1/**, tests/domains/news/**, tests/domains/finance/**; docs/learning/bench-v1.md, ws-15.md | 0100–0104 | — |
| WS-16 | Pilot operations | src/ripple/pilot/** (new package), src/ripple/storage/feedback*.py, infra/migrations/versions/0009_pilot_feedback.py (down_revision "0006"), src/ripple/api/routers/feedback.py (new; the coordinator includes it in app.py), tests/pilot/**, tests/api/test_feedback*.py, tests/storage/test_feedback*.py, docs/pilot/**, docs/ops/runbook.md, docs/ops/incident.md, docs/learning/pilot-ops.md, ws-16.md | 0105–0109 | 0009 |
| WS-17 | Paper and thesis plumbing | paper/** (new package at the repo root), docs/paper/**, tests/paper/**, docs/learning/paper-plumbing.md, ws-17.md | 0110–0114 | — |

The four are independent: WS-14 and WS-15 meet only through C5; WS-16 and WS-17 read
results/ and the store but write neither. Migration ids 0007 and 0008 stay reserved for
the Scout and Telegram ledgers (IDEAS 11).

### WS-14 acceptance
- A deterministic generator turns RippleBench v0 scenarios into C5 pairs: positives from
  scenario links (SCENARIO) and structure rules (RULE, proposal 0002), negatives sampled
  from same-persona memories with no link; persona/template split from the v0 manifest.
- A leakage test: no test-split persona or template text appears in any train pair; the
  eval-auditor checklist from docs/04 applied and recorded.
- The 300-pair hand-check protocol (sampling, labelling sheet format, agreement report);
  the hand labels themselves are the author's.
- An evaluation harness that runs any `ripple.core.linking.Linker` over a pair file and
  writes results/<date>_linkpairs_<track>_<sha>/ with per-provenance confusion counts;
  baselines: the rule linker and the LLM linker on FakeLLM offline.
- The training loop stays [human]: interface, xfail(strict) tests and a learning-doc
  recipe, TODO(human) bodies.

### WS-15 acceptance
- Minimal news and finance domain adapters (kinds, link types mapped to core classes,
  vocabularies), each with the adapter tests the jobs one has.
- News track v1 and finance track v1 generators in the v0 scenario format, seeded,
  with manifests and the same split rule; content is synthetic and labelled as such
  until the author curates real stories (docs/04 says "real stories").
- Finance pairs in C5 format (test split only, H4).
- STALE: an adapter design and loader against a local path; with no dataset on disk it
  raises a ConfigurationError naming the variable; the mapping question in docs/04
  "Open" answered in an ADR from the published format, or left open with the reason.
- `bench.run` gains the new suites; baselines run on them and write results/.

### WS-16 acceptance
- Pilot feedback capture: a table (migration 0009), a store, and `POST /feedback`
  (saved, applied, dismissed, useful/not-useful question) with I1/I6 respected.
- A weekly report generator (`python -m ripple.pilot.report`) over the store, the
  delivery log and the feedback table, computing the docs/04 pilot metrics it can, with
  "TBD" for the rest; output under results/pilot/<week>/ (I8).
- Incident runbook, monitoring checklist, refined consent and onboarding drafts for the
  department; the bot buttons and dashboard controls for feedback go to the handover as
  requests (WS-10 and WS-12 files are not WS-16's).

### WS-17 acceptance
- docs/paper skeleton (paper and thesis outlines mapped to C1–C4 and H1–H4) where every
  number is a macro.
- `python -m paper.numbers` renders macros from results/ folders only, refusing a
  number without a source; figures as data files (CSV, pgfplots, SVG) with no new
  dependency.
- `test_invariant_I8_...`: every digit-bearing claim in README.md, docs/** and
  docs/paper/** is either a rendered macro, an allow-listed non-result (dates, versions,
  ADR numbers, FR ids) or flagged; the test ships with the current violations listed
  explicitly so it passes today and fails on new ones.

## Rules for every wave-B session
The round-1 rules in docs/plans/parallel-execution.md apply unchanged: read CLAUDE.md and
the docs first; edit only owned paths; contract changes go in the handover; own-path
lint, format, type check and tests; offline only; ADRs in your range as "Accepted under
the autonomous mandate", not indexed (the coordinator indexes); accepted ADRs are never
edited in place (amend with a new ADR); a learning doc per module; hand over in
docs/plans/parallel-execution/<ws>.md; never commit, push or run gh. `graphify query`
before the first grep or source read. uv is at ~/.local/bin.

## Checkpoint C4
Full suite, contract requests applied (app.py include for /feedback, bot and dashboard
feedback controls, any C5 change), ADR index, tracker, roadmap, DEVLOG, docs/04 update
if any new results exist, code review of the integration diff, A–G hand-over.
