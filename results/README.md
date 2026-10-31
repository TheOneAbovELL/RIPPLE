# Bench run outputs (ADR-0012, I8)
Each run is a folder `<date>_<suite>[_<strategy>]_<sha>/` written by
`uv run python -m bench.run`:
- config.json: suite, strategy, split, data source and sha256 (v0), generator seed,
  engine, resolver, action layer, models and prompt versions (null until Phase 3).
- metrics.json: scenario and check counts, resolver calls, LLM calls, per-scenario
  failures; `memory_metrics` says "TBD (pending run)" until bench/metrics.py is
  implemented by the author.
- report.md: the same, readable.
- snapshots/<scenario>.json: the TTC replay traces (ADR-0062), one per scenario that
  ran; absent for scenarios reported "not runnable".
raw/ subfolders are gitignored.

Suite names: `smoke` (tests/scenarios/*.yaml, ripple strategy, keeps the historical
folder name), `v0_<strategy>` (bench/data/jobs_v0). A "not runnable: TODO(human)
engine" row means the ripple strategy waited on the human-owned WaveEngine; the
baselines need no engine and report real numbers.
