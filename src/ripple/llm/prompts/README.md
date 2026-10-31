# Prompts
One prompt per file with a version header, e.g. `resolver.v1.md`, and a one-line
changelog. A behaviour change is a new version file, never an in-place edit; run the
bench smoke suite before and after and record both in DEVLOG (.claude/rules/prompts.md).
Every prompt requests JSON matching a schema in `ripple.llm.schemas`. Evidence goes in
the user message only, and the prompt tells the model to ignore instructions inside it.

No prompts exist yet; the first arrive with the LLM linker and resolver in Phase 1.
