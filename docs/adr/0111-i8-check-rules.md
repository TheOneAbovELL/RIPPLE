# ADR-0111: The I8 check — what counts as a result number and how it is accepted
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-17)

## Context
I8 says every number in README, docs or paper traces to a file in results/. Read
literally that covers dates, ADR ids and port numbers; in practice the risk is a result
— an accuracy, a cost, a pass count — written into prose without a run behind it.
CLAUDE.md requires a named test per invariant. The docs are written by many parallel
sessions, so the check must catch new untraced numbers without forcing a rewrite of
every existing document today.

## Decision
1. **Scope.** README.md and every docs/**/*.md, except docs/paper/generated/ (written
   by `paper.numbers` from results/, ADR-0110).
2. **Claims.** After masking structural numbers — ISO dates and timestamps, years (not
   after a currency sign or slash, not before a quantity noun; "2026/2027" pairs only on
   lines without a result word), semantic versions, package pins with a dotted version
   glued to a name that is not a metric word,
   Python versions, ADR/FR/NFR/WS/IDEAS/phase/proposal/migration/wave/step/item/line/
   round/checkpoint/invariant ids (ranges joined only by dashes, never followed by a
   percentage), `#n`, claim and hypothesis ids C/H/Q/I, roadmap task ids, file names
   with a digit (matched per token), file:line (never before a percent sign), shas
   with a letter, lists of real HTTP status codes on lines about HTTP and without a
   result word, whole pytest progress lines, Markdown link targets, ordered-list
   markers —
   a claim is: a percentage; a fraction on a line with a result word; a decimal on a
   line with a metric word (inflections included); a currency amount; a multiplier
   ("N× faster"); a count of a metric noun (scenarios passed, checks failed,
   resolver/LLM calls, tokens, students, users, questions asked, stale
   recommendations), ranges included; a test-outcome count ("N passed"). A test-outcome
   count is *verification* when its line, or its whole paragraph, names a test runner
   (pytest, vitest, ruff, pyright, npm, a tests/ path, vitest's "Tests N passed",
   "in Ns") and holds no bench vocabulary (scenario, strategy names, suite names like
   finance_v1, bench.run, oracle, results/), or its line reports a runner-only outcome
   (xfailed, skipped, warnings, "N tests"); otherwise it is a metric count. In docs/paper/ outside generated/, every
   remaining digit is a claim, glued units and signs included (strict mode).
3. **Acceptance, in order.**
   a. a macro: `{{num:key}}` with a registered key, or `value<!--num:key-->` whose
      value equals the macro rendered from results/ at test time; an unknown key or a
      mismatched value is a violation that no rule can accept; references inside
      inline code document the syntax, are not checked, and do not hide their digits;
      categories `strict` and `macro` cannot be allow-listed;
   b. a citation: the claim's paragraph, list item, table row or heading names
      results/<run> (no `..`), and that run's report.md holds the claim's exact text
      with numeric boundaries, or — for a metric count — its metrics.json holds the
      number under the noun's top-level key ("N resolver calls" → `resolver_calls`).
      A citation does not require the cited run to pass ADR-0110's provenance checks:
      process records may describe uncommitted runs; the write-up uses macros;
   c. an allow-list category for named paths, each rule used or reported stale — one
      today: verification counts in process records (docs/DEVLOG.md, docs/plans/**),
      the pasted output of a command (CLAUDE.md "show real output"), not research
      results;
   d. an allow-list text entry: exact span, one path, a `context` substring that must
      be on the same line (so a later real result in the same file is not covered), a
      reason and a source — targets (H1's, the pilot size), example inputs, worked
      examples of a metric definition, code or config constants, versions;
   e. a known violation (path, exact span, count ≥ 1, reason) in
      paper/i8_known_violations.toml.
   Anything else fails `test_invariant_I8_every_result_number_in_docs_traces_to_results`.
4. **No silent rot.** An unused category or text entry, or a known violation found fewer
   times than listed, fails `test_invariant_I8_rule_files_have_no_stale_entries`. The
   generated files must equal a fresh render
   (`test_invariant_I8_generated_numbers_match_results`). Rule files are validated on
   load (required fields, `paths` a list, `count` ≥ 1).
5. **Ownership.** WS-17 lists violations it finds in other workstreams' documents and
   does not edit those documents; the coordinator fixes or accepts them.

## Alternatives considered
- **Flag every digit everywhere** — the literal reading; thousands of hits on dates, ids
  and code, an allow-list nobody maintains. Lost; kept as strict mode for docs/paper.
- **Treat test counts as violations** — more literal, but they are verification records
  with their command beside them; hundreds of entries would bury the real violations.
  Lost to a category scoped to process records and to lines that look like runner
  output. The author may delete the category rule to reverse this.
- **Citation by any number in the cited run's JSON** (the first version) — accepted
  "N checks failed" whenever any per-scenario field equalled N, and "M/T" whenever the
  report held a longer number ending in it ("1M/T"). Lost to exact bounded text or the
  noun's own key.
- **Citation on the same line only** — a wrapped bullet often names its folder on the
  next line. Lost to the block (paragraph, list item; table rows and headings alone).
- **Line-number keys for known violations** — every edit above a line in a shared
  document would break the test. Lost to (path, span, count).
- **An auto-baseline command that rewrites the violations file** — makes blessing a new
  violation one keystroke. Rejected; entries are written by hand with a reason.
- **LLM-based detection** — catches "doubled"; costs calls, non-deterministic, and
  tests may not call an LLM. Lost.

## Consequences
- The detector is a heuristic: a bare integer without a metric noun ("the run had 30")
  outside docs/paper — including bare cells of a Markdown results table — is not seen,
  and numbers in words never are. The outlines' strict mode and the macro scheme are the
  main defence for the write-up.
- Seven violations are listed today (see ws-17.md); new documents from parallel
  sessions fail the test until their numbers are traced, allow-listed or listed.

## Revisit if
False positives exceed a handful per wave, a real untraced result slips past the
detector, the author decides test counts should trace to results/ too, or the LaTeX
source lands (then `.tex` files join the scan).
