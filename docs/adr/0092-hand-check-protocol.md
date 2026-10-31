# ADR-0092: The 300-pair hand check is stratified, blind, keyed and re-drawn at report time
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-14)
Builds on ADR-0009 ("300 hand-checked"), proposal 0002 (agreement by provenance),
docs/04 ("LLM judge calibrated on a human-labelled sample; report agreement").

## Context
ADR-0009 names 300 hand-checked pairs as the gold set; docs/04 asks for agreement
reported with both scores. The hand labels are the author's. What is needed is a
protocol that makes those 300 labels measure something: which pairs, what the
labeller sees, how agreement is computed, and how a reader knows the sheet was not
hand-picked.

## Decision
1. **Sampling** (`training.handcheck.sample_for_handcheck`): strata = split ×
   provenance × label. Each stratum gets min(size, 10) first (the minimums win if
   they alone exceed the total), the rest of the 300 is shared in proportion to
   remaining size by largest remainder; seeded (`{seed}:handcheck`, default
   20261031), then shuffled across strata.
2. **Sheet** (CSV, `SHEET_COLUMNS`): row number, both memories (kind, content,
   structured as "subject / attribute = value"), then `human_link_type` (a registered
   type or "none"), `sure` (yes/no), `labeller` (initials), `comment`. No pair_id (it
   names the persona and so the split), no silver label, provenance or note:
   labelling is blind.
3. **Key file** `<sheet>.key.json`: pair file path and sha256, n, seed, the
   allocation and the row -> pair_id list. The report re-draws the sample from n and
   seed and refuses a sheet whose rows are not that sample, or whose pair file
   changed; everything is checked before the results folder is created.
4. **Reading**: a blank row is pending; a row with a label but no labeller, an
   unknown type, `sure` not yes/no, or a duplicated or unknown row number is refused
   with its row number, never guessed. A byte-order mark (spreadsheet "CSV UTF-8")
   is accepted.
5. **Report** (`python -m training.handcheck report`): results/<date>_handcheck_<track>_<sha>/
   with config.json (pair file and sheet sha256, sample n/seed/allocation, labelled
   and pending counts, labellers), metrics.json, report.md and gold_pairs.jsonl.
   Per overall, provenance, stratum and "sure only": n, both-link, both-none, each
   disagreement direction, detection agreement, Cohen's kappa on link/no-link (null
   when one class only), type agreement among both-link.
6. **Gold set**: gold_pairs.jsonl holds the checked pairs as HUMAN provenance
   (`labeller` = initials, note = "silver <provenance>:<type>[; unsure]").

## Alternatives considered
- Simple random 300 — on v0 the RULE and train strata would get a handful each; lost.
- Showing the silver label for confirm/reject — faster, but anchors the labeller and
  inflates agreement; lost.
- pair_id on the sheet — simplest join, but it carries the persona; lost for the key file.
- Kappa only, or raw agreement only — kappa is undefined or misleading at extreme
  prevalence, raw agreement hides chance; both are reported.
- An xlsx sheet — needs a dependency; CSV opens in any editor.

## Consequences
- On v0 the whole pair file is not much larger than the sample (manifest counts); the
  protocol is ready, but the 300 that matter are from the LLM-labelled Phase 4 set.
- One labeller gives silver-versus-human agreement, not inter-annotator agreement
  (the report says so); a second labeller on a subset is the author's call.
- The memories' text still shows which template family a pair comes from; full
  blindness to split is not possible with readable pairs.

## Revisit if
A second labeller joins (add inter-annotator kappa) or the LLM-labelled set arrives
(add LLM as a provenance stratum, already representable in C5).
