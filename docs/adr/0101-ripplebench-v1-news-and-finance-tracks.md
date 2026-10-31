# ADR-0101: RippleBench v1 news and finance tracks are generated, synthetic and labelled so
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-15, wave B)

## Context
docs/04: the news track is "real stories that developed or were corrected; labelled
downstream summaries"; the finance track is "test only"; every item has a stable id and
the split is by persona and template, never by item. The wave-B rules forbid network
access, so no real story can be collected in this session, and I8 forbids presenting
invented data as real. v0 (ADR-0061) already has a seeded generator, a split rule and a
`--check` mode. The scenario runner (bench/scenario.py) wrote every memory as a jobs
memory with the jobs link registry.

## Decision
1. `bench/generate_news.py` and `bench/generate_finance.py` generate 5 personas x 7
   templates = 35 scenarios each (seed 20261031), one template per v0 gold family:
   changed, unchanged, temporary, chain, ask, snapshot, forget. Same YAML format,
   same validation, same per-(seed, persona, template) random streams as v0.
2. `bench/tracks.py` holds what both share: `assemble_track` with the v0 split rule
   (a test proves it reproduces `bench.generate.generate`'s split), a `test_only`
   mode, `write_track` / `check_track` (scenarios, manifest and extra files such as
   pairs.jsonl), `load_track(data_dir, split)`.
3. **Synthetic, and said so.** Every manifest carries `content: synthetic` and a
   `content_note`; every scenario's meta carries `content: synthetic`; results
   config.json repeats it and report.md opens with a "Data: synthetic" line (v0 runs
   are labelled synthetic too). Until the first commit every run's git sha is
   "uncommitted", so config.json also records `source_sha256`, a hash of the bench
   and ripple sources that ran. Places, incidents, companies and people are invented.
4. **Finance is test only.** Every finance scenario is `split: test`,
   `held_out: domain`; manifest train lists are empty; `bench.run` refuses
   `--split train` for finance_v1; `strict_test` includes `held_out: domain`.
5. **Curated real stories, later, by the author.** Hand-written scenarios go in
   `bench/data/<track>/curated/*.yaml` with `meta.domain` and a `meta.provenance`
   block validated by `CuratedProvenance`: kind "curated", story slug, one or more
   sources (url, outlet, published_on, retrieved_on), curated_by, curated_on and
   `text_policy: paraphrased` (no article text copied). Curated scenarios are never
   generated or overwritten, named by a plain slug that no other scenario of the
   track uses, always `test` (`held_out: curated`), loaded with
   `--split all|test|curated`, and hashed separately (config.json `data.curated`).
6. **Domain-aware runner.** A scenario names its domain in `meta.domain` (default jobs,
   so smoke and v0 files are unchanged); `bench/domains.py` maps it to the adapter's
   registry; Memory.domain follows; `validate_scenario` reports a link type the domain
   does not know instead of failing mid-seed.
7. `bench.run --suite news_v1|finance_v1` runs every strategy and records track,
   domain, content label, data and extra-file hashes and curated digest.

## Alternatives considered
- Wait for real stories before building the track — honest but leaves H2–H4 without
  a harness until the author curates; the generated track tests the plumbing and the
  semantics now and is labelled synthetic. Lost on schedule, not on honesty.
- LLM-written stories — more natural prose, but non-deterministic, gold labels need a
  human check, and no LLM is allowed offline. Lost (as in ADR-0061).
- A separate scenario format for news (article + downstream summaries as text pairs) —
  closer to docs/04's wording, but a second runner and no shared baselines. Lost; a
  curated story fits the existing format (claims, summaries, briefings, events).
- Copying the v0 generate() split code — simpler, but two copies of the rule can drift.
  Lost to `assemble_track` plus an equivalence test; bench/generate.py is untouched.

## Consequences
- Results on these tracks measure the engine and the write/ripple semantics in new
  vocabularies, not language understanding; reports must say "synthetic".
- The three tracks mirror each other family by family, so baseline counts on news and
  finance coincide with each other by construction; that is expected, not a finding.
- The StubActionLayer recommends only jobs openings, so recommendation snapshots on
  v1 tracks are empty; action-level metrics on v1 need a domain action layer first.
- Curated stories are the author's [human] data work: sourcing, paraphrasing, gold
  states. docs/learning/bench-v1.md gives the recipe.

## Revisit if
Curated stories exist (then report curated and synthetic separately), or the link
finder needs prose richer than the templates give.
