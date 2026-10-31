# ADR-0090: Jobs link pairs come from static scenario snapshots, with structure rules as a stratum
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-14)
Builds on ADR-0009 (trained link finder), ADR-0061 (v0 generator and split), proposal
0002 (silver labels), the C5 contract (bench/linkpairs.py).

## Context
Phase 4 needs labelled (parent, dependent) pairs to train and score link finders. The
only labelled source today is RippleBench v0 (ADR-0061). Its link list is exact for
the seeded state, but events create new versions (a raised CGPA, a moved deadline, a
re-derived belief) whose texts are also realistic linker inputs, and docs/03 fixes
how links follow versions. Proposal 0002 asks that structure-derivable links be
labelled by rule and stratified by provenance.

## Decision
1. `training/replay.py` replays every scenario statically (no engine, no LLM) into
   snapshots: the seeded state and the state after each event. Versioning follows
   docs/03 (depends_on links follow both endpoints to new versions; snapshot_of links
   hold only between the versions they were written between). A change ripples in
   waves as the WaveEngine contract says: update or retire passes it on, keep, ask or
   no answer stops the branch, depth capped at DEFAULT_MAX_DEPTH; the answer is the
   first resolution whose trigger matches (AliasResolver). Unrestated event fields
   carry over as in bench.scenario's runner. Retire, expiry and forget (cascading
   along depends_on) remove memories. A test checks every v0 scenario's own `expect`
   blocks against the replay.
2. Every ordered pair of memories that coexist in one snapshot is a candidate.
   Claims: a scenario link, a transitive dependency without a direct link
   (excluded: neither label is safe), or no link (inside one scenario the link list
   is complete, so this is a SCENARIO negative).
3. `training/structure_rules.py` derives eligibility_of (from a CGPA cutoff opening,
   and from CGPA when that company states a cutoff in the same snapshot),
   reminder_for (exact deadline date), criteria_from (CGPA value) and
   sent_with_resume (resume version) from structured parents and v0 surface forms.
   depends_on_fact and fit_of stay out of reach of rules by design. Rules run inside
   snapshots only.
4. Merging and provenance: claims merge on (persona, parent memory, dependent
   memory). A scenario link that a rule also derives, with the same type, is filed
   under **RULE** (note "rule:<name>; scenario agrees"); scenario links no v0 rule
   derives stay **SCENARIO**. RULE thus means "structure determines this link"; the
   SCENARIO positives are the links no v0 rule derives, which include the hidden
   depends_on_fact links and also structural links the rules miss on wording (the
   per-type table shows which). When a rule derives a *different* type from a
   scenario link, the scenario's type wins and `rule_vs_scenario_disagree` counts
   it. A rule label against a scenario's no-link claim, a link and a no-link claim
   from two snapshots, or two rule types are dropped and counted.
5. A pair seen under several templates names them all, sorted, joined with "+";
   it is train only when its persona and every template are train (`split_for`).
6. `pair_id` = `jobs_v0:<persona>:<sha256 of the two memories' JSON>[:16]`, stable
   for a fixed source and seed.
7. Output `training/data/jobs_v0_pairs.jsonl` (C5, via `write_pairs`) and
   `jobs_v0_pairs.manifest.json` (seed, ratio, source sha, test personas and
   templates, counts by split × provenance × label and by link type, prevalence per
   split, text-overlap counters, every process counter including zeros, file
   sha256); `--check` and a test prove the checked-in files equal a fresh generation.

## Alternatives considered
- Seeded state only — simplest, but drops every versioned text (CGPA 7.9, the new
  deadline, "resume v2" versus an application sent with v1, the best snapshot_of
  negative v0 has). Lost.
- Replaying through the real engine — the WaveEngine is the author's [human] task
  and the oracle resolutions already say what changes; static replay needs neither,
  and the expectation test keeps it honest.
- Scenario precedence over rules (RULE only for rule-only links) — v0 rules find no
  link the scenarios lack (`positives_rule_only` is 0 in the manifest), so the RULE
  stratum would be empty and the stratification proposal 0002 asks for would say
  nothing. Lost.
- Rules across a persona's scenarios on the seeded state — written first; on v0 it
  produced no claim, and a cross-scenario rule positive would have no reversed-link
  negative (its pair never shares a snapshot), breaking ADR-0091. Removed until a
  track needs it.
- Cross-scenario negatives within a persona — the persona's CGPA really is a parent
  of eligibility beliefs in other scenarios; the closed world holds only inside one
  scenario. Lost.

## Consequences
- The pair set is small and regular because v0 is (counts in
  training/data/jobs_v0_pairs.manifest.json); it exercises the protocol, not a model.
  Real training data needs v1 and LLM-labelled pairs (proposal 0002, Phase 4).
- RULE pairs are positives only; a RULE stratum's precision is undefined and the
  harness writes null (ADR-0093).
- Rules read v0 surface forms ("eligible for <company>", "remind ... before <date>");
  a v1 adapter with OpeningAttribute.COMPANY on openings should read structure instead.
- If docs/03 or the engine contract changes, training/replay.py must follow; the
  expectation test fails first.

## Revisit if
v1 or real JD text lands (rules must move from surface forms to structure), or the
hand check (ADR-0092) shows RULE labels below scenario labels in agreement.
