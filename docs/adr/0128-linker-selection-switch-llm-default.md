# ADR-0128: The write-path linker is chosen by RIPPLE_LINKER; the LLM linker stays the default until H3 is judged
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-19)
Builds on ADR-0009 ("the trained model becomes the default if it meets H3"), ADR-0125,
ADR-0126.

## Context
A trained linker now exists and serves through the `Linker` protocol. ADR-0009 makes it
the default only if it meets H3: within 5 F1 points of the LLM linker at a fraction of
the cost. The LLM linker has not been scored (no ANTHROPIC_API_KEY on the build machine),
so H3 cannot be judged. Operators still need a way to try the trained linker.

## Decision
1. `ripple.linking.trained.select_linker(env, llm=..., registry=...)` reads
   `RIPPLE_LINKER` (`llm`, the default, or `trained`) and, for `trained`,
   `RIPPLE_TRAINED_LINKER_MODEL` (a model folder). Unknown values and a missing folder
   raise `ConfigurationError` at start-up; a model whose label space has a type the
   domain's registry lacks is refused.
2. The default stays `llm`. Switching the default to `trained` needs a new ADR citing an
   H3 result folder with both linkers scored on the same pair file.
3. torch and transformers are imported only when `trained` is selected (ADR-0125
   point 3).
4. The call site is the coordinator's: `src/ripple/api/wiring.py` (and the worker's
   wiring) build `LLMLinker(router, registry)` today; WS-19's handover asks for
   `select_linker(os.environ, llm=LLMLinker(router, registry), registry=registry)` there.

## Alternatives considered
- Make the trained linker the default now — ADR-0009's condition is unmet (unjudged);
  lost.
- A TOML entry in config/llm.default.toml — that file configures LLM providers; a
  linker that calls no LLM does not belong in it; lost.
- Run both linkers and union the proposals — doubles the LLM cost the trained linker is
  meant to save, and no measurement says it helps; lost for now.

## Consequences
- Until the wiring calls `select_linker`, the switch exists but has no effect in the API.
- Selecting `trained` in a container needs the `linkfinder` group installed (ADR-0125
  point 4) and the model folder mounted.

## Revisit if
H3 is judged (either way), or a second domain gets its own trained model (then the
switch needs one model folder per domain).
