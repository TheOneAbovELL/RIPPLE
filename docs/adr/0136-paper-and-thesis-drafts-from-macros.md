# ADR-0136: The paper and thesis drafts: macro-only sources, rendered copies, and what they may claim
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-21)

## Context
On 2026-10-31 the author asked for complete paper and thesis drafts. WS-17 left two
outlines (docs/paper/paper-outline.md, thesis-outline.md) and the macro pipeline
(ADR-0110, ADR-0111). WS-18 and WS-19 produced results:
- the benchmark grid with the scripted oracle and gold links;
- the trained link finder, against the rule linker, on jobs and on finance.
Three things are missing: the system the claims describe (a trained or LLM linker
feeding an LLM resolver), every LLM number (no valid key on this machine), and the pilot.
docs/paper/ is in strict I8 mode: any digit there is a claim. A reader also needs to see
the drafts with their numbers in place.

## Decision
1. **Sources are macro-only.** docs/paper/paper.md and docs/paper/thesis.md hold every
   number as `{{num:key}}`. The prose names the results/ folder a reading comes from
   where that helps, but a folder name never stands in for a macro. Targets and
   structural quantities are written in words ("at least nine tenths", "seven
   template families"). Results never are.
2. **Rendered copies.** `python -m paper.numbers` also writes generated/paper.md and
   generated/thesis.md (`--draft`: generated/draft/), with each macro replaced by its
   value, by "TBD (pending run)" or, for an unknown key, by a visible `??key`. They are
   generated files: never edited, checked by `--check` like the others, and excluded
   from the I8 scan with the rest of generated/.
3. **What the drafts claim.**
   - The measured evidence is the oracle namespace (ADR-0135). It is always labelled
     "scripted oracle and gold links". It tests the engine's semantics, not language
     understanding.
   - The system-level macros (`mem.*`, `h1.*`, `h2.*`, `h3.*`, model-backed
     `ablation.*`) appear beside the oracle ones and print TBD until their runs exist.
   - H1's accuracy half is reported as met by construction under the oracle. Its cost
     half is reported as not met on these small stores. H2 holds in direction only, and
     H4 is not supported. H3, the pilot (C3) and the hand check stay pending, each with
     the command or step that would produce it.
   - These caveats come from docs/results/benchmark.md and docs/results/link-finder.md
     and are repeated in the drafts, not softened.
4. **Related work** names only works that can be cited accurately:
   - agent memory systems: MemGPT/Letta, Mem0, Zep/Graphiti, A-MEM;
   - truth maintenance: Doyle's TMS, de Kleer's ATMS;
   - AGM belief revision;
   - knowledge editing: ROME, MEMIT, MQuAKE;
   - retrieval-augmented generation and its freshness problem.
   The 2026 works in docs/06 are cited as listed there. Where a venue or detail is
   uncertain, the text says "citation to verify". No number from another paper is
   quoted.
5. **The outlines stay** as the section-to-evidence map that
   `test_invariant_I8_outlines_cover_every_hypothesis_with_registered_macros` reads.
   The drafts follow them, except where the evidence that exists differs from what the
   outline expected. The oracle namespace and the held_out=both cell are recorded in
   ADR-0135.

## Alternatives considered
- **Write the drafts in LaTeX now.** The thesis template and the venue are not chosen.
  Markdown with the outlines' LaTeX comments converts later, and the I8 scan reads
  Markdown today.
- **Annotated values in the sources**, written as `VALUE<!--num:key-->`. The I8 check verifies
  them, but every re-run would make the sources stale. Placeholders plus a rendered copy
  keep the sources stable.
- **Leave the system-level macros out until they render.** The drafts would then hide
  what is pending. Showing "TBD (pending run)" beside the oracle reading keeps the gap
  visible.

## Consequences
- After a re-run, the drafts update by re-rendering; nobody edits a number.
- The camera-ready gate is still `paper.numbers --strict`. It fails while any macro the
  registry holds is refused, so the registry must shrink to what the final paper uses,
  or every run must exist, before submission.
