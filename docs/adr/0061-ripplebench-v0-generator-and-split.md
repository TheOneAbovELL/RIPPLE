# ADR-0061: RippleBench v0 jobs track is generated from seeded personas and templates
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-7)

## Context
docs/04-evaluation.md: the jobs track simulates students over a placement season,
labels every event with the exact expected state of every memory, gives every item a
stable id and splits train/test by persona and template, never by item. Phase 3 asks
for ~30 scenarios. Hand-writing them invites inconsistency and item-level leakage
into link-finder training (Phase 4).

## Decision
1. bench/generate.py builds personas (name, CGPA, batch, branch, skills, three
   openings with cutoffs and deadlines) from `random.Random(f"{seed}:persona:{i}")`,
   so persona i never changes when more personas are added, and seven template
   families, one per gold behaviour: changed (cgpa_rise), unchanged (deadline_moved),
   temporary (exam_block), chain (accepted_offer), ask (cutoff_unknown), snapshot
   (resume_update), forget (forget_cgpa). Each template draws its variation from
   `random.Random(f"{seed}:{persona}:{template}")`.
2. Output is the scenario format of bench/scenario.py (ADR-0021), one file per
   persona × template in bench/data/jobs_v0/, validated by `validate_scenario` before
   writing. Default seed 20261019, five personas: 35 scenarios, 175 gold checks.
3. manifest.json records seed, generator version, persona and template splits
   (two test personas, two test templates, both drawn from the seed), each
   scenario's split and `held_out` (none | persona | template | both), and a sha256
   over all files. `train` = train persona AND train template; everything else is
   `test`; `strict_test` = both unseen. `python -m bench.generate --check` and a test
   verify the checked-in files equal a fresh generation.
4. Scripted resolutions carry a `trigger` alias: the oracle answer applies only when
   the ripple was started by that memory. This keeps check_everything honest (it
   pays for every re-check but a re-check under an unrelated trigger keeps) without
   writing the gold decision into memories that should not change.
5. The root row of every alias uses the alias as its id, so traces are readable and
   the baselines' wave order is deterministic.

## Alternatives considered
- Hand-written YAML per scenario (the smoke suite's approach) — readable, but 30+
  files drift and persona/template metadata would be free text. Kept for the smoke
  suite only.
- LLM-generated scenarios — more varied prose, but non-deterministic and the gold
  labels would need checking by hand. Lost for v0; a candidate for v1 prose fields.
- Split by item (random 70/30) — standard but leaks personas and templates into
  training (eval-auditor item 1). Rejected by docs/04.

## Consequences
- The data is small and regular; v0 measures engine and semantics, not language.
  Missing-link and multi-parent cases are v1 items (noted in IDEAS via the
  coordinator).
- A template change changes every persona's file for that template; the manifest
  hash makes that visible in results/ configs.
- Expected strategy outcomes are tested: check_everything matches gold except in the
  ask family (subtree flagging needs the graph); append_only fails every family.

## Revisit if
v1 adds the news track or real-text openings, or the link finder's training set
needs a split finer than persona × template.
