# Final delivery — everything buildable, built and verified (2026-10-31)
Written by the coordinator on the author's instruction of 2026-10-31: deliver the whole
project in this session, including the three [human] pieces (WaveEngine, metric
functions, training loop), which the author has now explicitly asked the collaborator
to implement (CLAUDE.md "Human-owned work": "unless explicitly asked").

## What cannot be delivered from a chat, and is not faked
- A pilot season with real students (C3's evidence) needs students, a season and the
  department's consent sign-off. Delivered instead: everything a pilot needs to start.
- Numbers from a real LLM (LLM linker accuracy and cost, LLM resolver on prose) need
  ANTHROPIC_API_KEY, which this machine does not have. Delivered: the code paths, tested
  offline, and the commands that produce those numbers once the key is set.
- A live deployment needs a server and DNS. Delivered: images, compose, Caddy, runbooks.
- Commits: CLAUDE.md forbids the collaborator to commit. The paper renders its numbers
  in draft mode until the author's first commit stamps the runs (ADR-0110).

## Done before the workstreams launched
- WaveEngine implemented (ADR-0013 contract); the 10 engine tests and 11 scenarios pass.
- Real Postgres with pgvector on this machine without Docker (pgserver, dev dependency,
  `uv run python -m tools.embedded_pg test`): the 72 slow tests pass live; a Windows
  event-loop bug in psycopg's async mode found and fixed (src/ripple/storage/loop.py).

## Workstreams (one shared checkout, file ownership as in wave B)
| WS | Name | Owns | ADRs |
|---|---|---|---|
| WS-18 | Metric functions and the full benchmark | bench/** (incl. bench/metrics.py bodies), tests/scenarios/test_bench_*.py, results/ (new runs), docs/learning/bench.md and bench-v1.md, docs/results/benchmark.md (new), ws-18.md | 0120–0124 |
| WS-19 | Trained link finder (ADR-0009) and the link-finder report | training/**, tests/training/**, src/ripple/linking/trained.py (new), tests/linking/test_trained*.py, results/ (linkpairs runs), docs/learning/link-finder-data.md, docs/results/link-finder.md (new), ws-19.md | 0125–0129 |
| WS-20 | Complete product: dashboard flows, design, local run | apps/web/**, tools/local_run.py (new), src/ripple/worker/run_once.py (new), tests/worker/test_run_once.py, tests/tools/**, docs/learning/dashboard.md, docs/learning/local-run.md (new), ws-20.md | 0130–0134 |
| WS-21 | Paper and thesis drafts (after WS-18 and WS-19 report) | docs/paper/**, paper/registry.py (macro additions), tests/paper/**, ws-21.md | 0135–0139 |
Coordinator: core, API, storage, CLAUDE.md, docs/00–06, ADR index, DEVLOG, roadmap,
tracker, tools/embedded_pg.py; ADRs 0115–0119. Contract changes go through handovers.
Dependencies: WS-19 may add PyTorch and transformers (CPU) with an ADR in its range,
exact pins, added with `uv add`; nobody else adds any.

## Acceptance (the whole project)
- Full fast suite, slow suite on embedded Postgres, ruff, format, pyright, dashboard
  lint/test/build all green.
- Benchmarks run for every strategy on smoke, v0, news_v1, finance_v1 with the metric
  functions; H1 and H2 readings written from those results with their caveats.
- A trained link finder exists, serves through the Linker protocol, and has a report:
  jobs test split and finance transfer (H4); H3's LLM comparison marked pending the key.
- A student can do every FR from the dashboard and Telegram; a developer runs the whole
  product locally with one command.
- Paper and thesis drafts with every number rendered from results/ (draft mode).
