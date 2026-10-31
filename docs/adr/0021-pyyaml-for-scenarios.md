# ADR-0021: Scenario files are YAML, parsed with PyYAML
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
CLAUDE.md specifies scenario tests as tests/scenarios/<name>.yaml: initial memories,
events in order, expected states after each event. The bench smoke suite (ADR-0012)
replays the same files. Python's standard library has no YAML parser.

## Decision
Add `pyyaml` (runtime, exact pin) and `types-pyyaml` (dev, for pyright). Scenario
files are loaded with `yaml.safe_load` only. The same loader serves tests/ and bench/.

## Alternatives considered
- JSON scenarios with the standard library — no dependency, but no comments and
  noisy quoting for a file the author will hand-edit for months. Lost on readability.
- TOML (stdlib tomllib) — fine for config, awkward for ordered lists of events with
  nested expectations. Lost.
- ruamel.yaml — round-trip editing we do not need. Lost.

## Consequences
- One small, ubiquitous dependency; `safe_load` keeps arbitrary-object loading off.
- Scenario schema is validated by the runner into Pydantic models, so a typo fails
  loudly rather than silently passing.

## Revisit if
Scenario files need generation at scale (Phase 3/4), where a Python builder may
replace hand-written YAML; the loader stays for hand-written cases.
