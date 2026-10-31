# docs/paper — outlines and rendered numbers
Owner: WS-17 (wave B), for the author. ADR-0110 (macro scheme), ADR-0111 (I8 check).

## What is here
- `paper-outline.md` — the conference paper, section by section, mapped to C1–C4,
  H1–H4, the baselines, ablations and pilot metrics of docs/04-evaluation.md.
- `thesis-outline.md` — the B.Tech thesis (May 2028), chapter by chapter, same mapping.
- `paper.md` and `thesis.md` — the written drafts (ADR-0136), numbers as macros only.
- `generated/` — written by `uv run python -m paper.numbers`; never edited by hand:
  `numbers.tex` (LaTeX macros), `numbers.json` (values, provenance, refusal reasons),
  `numbers.md` (the same as a table), `figures/` (CSV, pgfplots `.dat`, SVG), and
  `paper.md` / `thesis.md`, the drafts with every macro replaced by its value.

## How a number gets into the write-up
A number is never typed. It is a macro from `paper/registry.py`:

| Where | Write | Renders as |
|---|---|---|
| Markdown outline | `{{num:h1.accuracy_ratio}}` | the macro name; the value lives in generated/numbers.md |
| Markdown with the value shown | `VALUE<!--num:oracle.v0.check_everything.pass_share-->` | the value; the I8 test checks it against results/ |
| LaTeX | `\rnum{h1.accuracy_ratio}` after `\input{generated/numbers.tex}` | the value, or **TBD (pending run)** |
| pgfplots | `\pgfplotstableread{generated/figures/baselines_v0.dat}` | `nan` where a macro is refused |

A macro is rendered only from results/ run folders that pass the provenance checks
(ADR-0110): config.json and metrics.json present, a clean commit, a complete run, models
pinned and prompt versions recorded when a model was used, no newer run of the same
macro failing the checks, and no disagreement between runs of one configuration;
headline numbers also need recorded models and at least three run seeds (docs/04
Protocol), and a derived number or a figure needs all its runs to agree on everything
but the field being compared. Anything else is refused and prints "TBD (pending run)"
with the reason in numbers.json. Today every run in results/ is uncommitted, so every
macro is refused by default; `--draft` relaxes only the clean-commit gate (headline
numbers included, ADR-0135) and writes generated/draft/, marked DRAFT. Read the drafts
there: generated/draft/paper.md and generated/draft/thesis.md.

## Commands
- Render: `uv run python -m paper.numbers`
- Check the generated files are current: `uv run python -m paper.numbers --check`
- Camera-ready gate (fails while any macro is refused): `uv run python -m paper.numbers --strict`
- Development view, uncommitted runs allowed, written to `generated/draft/` and marked
  DRAFT: `uv run python -m paper.numbers --draft`
- I8 report over README.md and docs/: `uv run python -m paper.i8` (`--all` lists accepted claims)
- The test: `uv run pytest tests/paper`

## Adding a number
1. Add a `MacroSpec` (or `DerivedSpec`) to `paper/registry.py`: folder pattern, config
   filter, JSON path, format, headline flag, the claims it supports.
2. Run the producer (bench, linker harness, pilot report) so a results/ folder holds it.
3. `uv run python -m paper.numbers`, then reference the macro.

## LaTeX-ready structure
Every heading in the outlines carries its LaTeX command and label in an HTML comment,
for example a comment holding `\section{Introduction}\label{sec:intro}`. Tables are
specified as rows × macros so that each cell becomes one `\rnum{}`. No section numbers
are typed: LaTeX numbers them.
