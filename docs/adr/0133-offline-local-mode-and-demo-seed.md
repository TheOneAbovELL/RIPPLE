# ADR-0133: The demo seed writes through the real paths with a deterministic "ask" fallback
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · workstream: WS-20

## Context
The thesis demo must show a ripple on first open, identical with or without
`ANTHROPIC_API_KEY`, free, and produced by the engine rather than inserted. Since
ADR-0116 a structured profile fact is classified, linked and derived from without a
model; the model is still the resolver's fallback when every jobs rule declines.

## Decision
1. **The local server keeps the production wiring unchanged** (ADR-0132). A keyless
   run fails where production would (503) and the banner lists those features. (An
   earlier draft swapped stand-ins into the server; ADR-0116 made that unnecessary for
   structured facts, and a server that differs from production would prove less.)
2. **`--seed-demo`** builds the seed's runner and Intake from production's components
   (jobs rules, `ProfileDerivationObserver`, `StructuredFirstLinker` with
   `JobsStructureLinker` and `RuleLinker`, the permanent and multi-valued attribute
   sets) with three model seams replaced: the resolver fallback is `AskTheStudent`
   (asks, naming the belief and the change; never updates or retires), the prose
   linker is `RuleLinker`, and the change detector refuses anything but a permanent
   structured fact. It writes, all through the real paths:
   - seven profile facts with `Intake.ingest(profile_statement(...))`;
   - three openings with `OpeningRecorderAdapter.record` (`record_opening` plus
     `derive_for_opening`) from realistic JD texts with exact spans, deadlines 3, 9 and
     16 days ahead in IST;
   - CGPA 8.1 to 8.6: Beta Analytics (cutoff 8.5) is updated from not eligible to
     eligible, Acme (7.0) recomputed, the criteria updated;
   - "My college reports CGPA on a 4-point scale": the eligibility rule refuses to
     compare a 4-point CGPA with ten-point cutoffs (ADR-0034), so Acme's and Beta's
     eligibility are asked and their dependents parked; Gamma, without a cutoff, is
     kept. The profile is left inconsistent on purpose: it is the case Ripple is built
     to ask about rather than guess.
   Every state change has its ChangeEvent (pinned by a test that accounts for every
   version, retirement, ask and parked memory).

## Alternatives considered
- A fixture SQL dump: bypasses I2 and the engine; it would show data the engine never
  produced.
- Seeding through HTTP with a recorded FakeLLM: needs the test fakes at runtime and
  pretends a model ran.
- Stand-ins in the local server as well: a keyless run would look more capable than
  production; after ADR-0116 the gain was small.
- A parked question from an unparseable deadline ("to be announced"): realistic, but
  `parse_deadline` raises instead of returning unknown, so the reminder rule crashes
  rather than declines (reported in the WS-20 handover, request 3).

## Consequences
- Only the seed uses the stand-ins; the server, benchmarks and production never do.
- The demo dates are relative to the seed time, so deadlines stay in the future.

## Revisit if
A key is available on the demo machine (run the seed's statements through the real
model and compare), or the API grows a deterministic linker of its own.
