# bench v1: news and finance tracks, finance link pairs, STALE loader
Written 2026-10-31 (WS-15, wave B); seeds and metrics added the same day (WS-18).
Describes only code that exists. Read
docs/learning/bench.md first: v1 reuses the v0 runner, strategies and results format.

## 1. What it does
RippleBench v1 adds two tracks in the v0 scenario format: **news_v1** (stories that
develop or get corrected, and the summaries and briefings built on them) and
**finance_v1** (a user's theses whose assumptions break; test only). Both are generated
from seeded personas and seven templates, one per gold behaviour. The finance track also
ships labelled link pairs in the C5 format for the H4 transfer test. A STALE loader
reads a local copy of that external benchmark, or explains why it cannot.

The data is **synthetic**: invented places, incidents, companies and people. docs/04
asks for real news stories; section 4 is how you add them.

## 2. Why it exists
docs/04 names three RippleBench tracks plus STALE; docs/00 scopes news as benchmark only
and finance as an unseen-domain test (H4: does the link finder transfer?). ADR-0100
(adapters), ADR-0101 (tracks), ADR-0102 (finance pairs), ADR-0103 (STALE),
ADR-0104 (check_everything order).

## 3. How it works
- **Adapters** `src/ripple/domains/{news,finance}/vocabulary.py`: kinds, attributes,
  link types and `news_registry()` / `finance_registry()`. Each domain maps its types
  to depends_on or snapshot_of and has one snapshot type: news `shared_from` (what the
  reader already shared), finance `journaled_with` (a dated decision record).
- **Domain-aware runner** `bench/domains.py`: a scenario's `meta.domain` (default
  jobs) picks the registry; `ScenarioRunner` writes `Memory.domain` accordingly and
  `validate_scenario` reports a link type the domain does not know.
- **Track machinery** `bench/tracks.py`: `assemble_track(spec, personas, seed)`
  builds persona x template scenarios, splits them with the v0 rule (or holds out the
  whole domain when `test_only`), writes `manifest.json` with `content: synthetic`;
  `write_track` / `check_track` handle scenarios, manifest and extra files;
  `load_track(data_dir, split)` reads generated plus curated scenarios.
- **Generators** `bench/generate_news.py`, `bench/generate_finance.py`: personas
  (a reader following three stories; an investor with three fictional companies) and
  seven templates each. Mapping to v0 families:

  | family | jobs v0 | news v1 | finance v1 |
  |---|---|---|---|
  | changed | cgpa_rise | figure_revised | guidance_cut |
  | unchanged | deadline_moved | other_story_develops | peer_margin |
  | temporary | exam_block | road_closure | trading_halt |
  | chain | accepted_offer | attribution_retracted | ceo_departure |
  | ask | cutoff_unknown | conflicting_reports | rate_edge |
  | snapshot | resume_update | shared_note | journal_entry |
  | forget | forget_cgpa | forget_story | forget_holding |

- **Finance pairs** `generate_finance.scenario_pairs`: every ordered pair of memories
  in a scenario. A direct link is a positive (type and class from the registry); no
  direct link is a negative (a reversed edge or two facts about the same attribute are
  noted); an indirect dependency is left out; each distinct text pair is kept once
  (`track_pairs`). All `Split.TEST`, written with `bench.linkpairs.write_pairs` to
  `bench/data/finance_v1/pairs.jsonl`, hashed in the manifest.
- **STALE** `bench/stale.py`: `RIPPLE_STALE_PATH` -> file or folder of `.jsonl`;
  strict `StaleItem` records; `python -m bench.stale` prints counts.
- **Runs** `python -m bench.run --suite news_v1|finance_v1 --strategy <name>`.
  With `--generator-seeds 3` each track is regenerated in memory with seeds
  20261031–20261033 (ADR-0121; the first reproduces the checked-in files) and every
  run writes `memory_metrics` (ADR-0120). Seeded runs leave curated stories out.
  Results across all three tracks: docs/results/benchmark.md.

Commands:
```
uv run python -m bench.generate_news --check
uv run python -m bench.generate_finance --check
uv run python -m bench.run --suite news_v1 --strategy check_everything
RIPPLE_STALE_PATH=/data/stale uv run python -m bench.stale
```

## 4. Adding curated real stories (your data work)
Put each story in `bench/data/news_v1/curated/<slug>.yaml` (finance theses go in
`bench/data/finance_v1/curated/`). Same format as a generated scenario, plus
`meta.domain` and `meta.provenance`:

```yaml
name: curated_<slug>
description: one line on what developed or was corrected
meta:
  domain: news
  family: changed            # one of the seven families, or your own label
  provenance:
    kind: curated
    story: <slug>
    sources:                 # one per development the events encode
      - {url: "https://...", outlet: "...", published_on: 2026-05-01, retrieved_on: 2026-11-02}
      - {url: "https://...", outlet: "...", published_on: 2026-05-03, retrieved_on: 2026-11-02}
    curated_by: ORG
    curated_on: 2026-11-02
    text_policy: paraphrased # write claims in your own words; never paste article text
memories: {...}              # claims, summaries, briefings as they stood first
links: [...]                 # summarises / inferred_from / briefing_from / shared_from
resolutions: {...}           # what a correct resolver decides, by alias and trigger
events: [...]                # each development, with the expected state of every memory
```
Rules the loader enforces: provenance validates; the domain matches the track; the
scenario passes `validate_scenario`. Curated stories are always test (`held_out:
curated`), never overwritten by the generator, hashed separately in config.json
(`data.curated`), and selected alone with `--split curated`. Report curated and
synthetic numbers separately. The gold states are yours: decide them from the sources,
not from a model.

## 5. Trade-offs
- Synthetic templates make gold labels exact and runs deterministic, but they test
  semantics, not language; that is why the manifests say "synthetic".
- The three tracks mirror each other family by family, so baseline counts on news and
  finance coincide by construction. Compare tracks only after curated data exists.
- Pairs come from within one scenario: labels are certain, but negatives are easy
  (often different subjects). Harder negatives need cross-scenario sampling with a
  human check (ADR-0102).
- STALE's shape is declared, not verified (offline); strict validation turns a wrong
  guess into a loud error instead of wrong numbers.
- check_everything reads the graph to order its single wave parents first (ADR-0104),
  so its result no longer depends on alias spelling; its scope is still everything.

## 6. Failure modes and tests
| Failure | Test |
|---|---|
| a domain type maps to the wrong class / leaks across domains | tests/domains/{news,finance}/test_vocabulary.py |
| a correction rewrites a shared note or journal entry | test_a_correction_carries_..., test_a_thesis_update_carries_... |
| v1 split differs from v0's rule | test_assemble_track_splits_exactly_as_the_v0_generator_does |
| finance reaches a train split | test_a_test_only_track_holds_out_the_whole_domain, test_finance_train_split_is_refused, test_every_pair_is_test_split_... |
| checked-in data drifts | test_the_checked_in_track_matches_a_fresh_generation, test_the_checked_in_pairs_equal_a_fresh_generation |
| a persona name leaks into another track | test_v1_persona_names_never_appear_in_another_track |
| curated story without sources, or not declared paraphrased (copying itself is not detectable; the curator's declaration is checked) | test_a_curated_story_with_bad_provenance_is_refused |
| baseline outcome depends on alias names | test_check_everything_outcome_does_not_depend_on_alias_spelling |
| STALE missing or in another shape | tests/bench_v1/test_stale.py |
| ripple strategy claims numbers without the engine | test_finance_ripple_is_reported_not_runnable_... |

## 7. Interview questions
1. Why does finance have no train split, and how would a finance persona reaching
   training data inflate H4?
2. Why are indirect dependencies left out of the pairs instead of labelled "no link"?
3. What does `shared_from` being snapshot_of buy you in the news track? What breaks if
   it were depends_on?
4. Why does check_everything's member order change its result on the ask family, and
   why is parents-first the fair choice?
5. What would you need before claiming a STALE number is comparable with the paper's?

## 8. Exercise
Write one curated news story from two real reports of a story whose figure was revised
(follow section 4), run `uv run python -m bench.run --suite news_v1 --strategy
check_everything --split curated`, and explain each failed check in the report.
