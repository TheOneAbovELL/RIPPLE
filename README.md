# Ripple

**Memory that knows what else to forget.** When a fact changes, Ripple updates every
belief an AI agent built on it.

Agents now remember and act for months. Their worst failure is not forgetting; it is
acting confidently on knowledge that has gone stale. When a student's CGPA rises, the
eligibility verdicts, recommendations and search criteria built on the old CGPA have
to change too. Most memory systems update the contradicted fact and leave its
dependents behind. Ripple makes dependencies between memories explicit, and when one
changes it re-examines exactly what rested on it.

The first product built on Ripple is a job-hunt assistant for engineering students.

## The idea in one paragraph
Deterministic code decides **which** memories a change affects; a language model decides
only **how** to fix each one. Every memory is linked to the memories it was derived from.
When a fact changes, the ripple engine walks those links wave by wave (graph traversal,
never an LLM call, invariant I3). Domain rules settle what they can compute, such as
eligibility from a CGPA and a cutoff. The model is asked only about the rest, and its
answer is validated against a schema before it touches memory (I4). Each affected
belief is kept, updated, retired, or turned into a question for the user, and every
state change leaves an audit record with its reason and evidence (I2).

```
 "My CGPA is now 8.6"
        │
        ▼
 ┌─────────────┐   new version    ┌──────────────────────────────────────────┐
 │   Intake    │ ───────────────▶ │ Ripple engine (deterministic, I3)        │
 │ detect +    │                  │  wave 1: eligibility (Acme, Beta), fit,  │
 │ link        │                  │          search criteria                 │
 └─────────────┘                  │  wave 2: what depended on those          │
                                  └───────────────┬──────────────────────────┘
                                                  │ one decision per belief
                                  ┌───────────────▼──────────────────────────┐
                                  │ Resolver chain: domain rules first,      │
                                  │ LLM fallback (schema-validated, I4)      │
                                  │ keep · update · retire · ask the student │
                                  └───────────────┬──────────────────────────┘
                                                  ▼
                              ChangeEvent with reasons + evidence (I2)
```

## What a student can do
- **Set up a profile from a resume.** Upload a PDF; every extracted fact is shown with
  the exact line it came from, and nothing enters memory until the student confirms it
  (I5: the agent never invents profile facts).
- **Add openings** by pasting a job description or forwarding a placement email, or let
  the Scout find them on allowed sources. Fields are parsed with their source spans.
- **See derived beliefs:** eligibility, fit with the JD lines it rests on, deadline
  reminders and search criteria, each with "why do you believe this?" one click away.
- **Say what changed** in plain words or as a structured fact, and watch the ripple:
  which beliefs were re-checked, wave by wave, and what happened to each.
- **Answer questions** Ripple parks when it should not guess, for example a CGPA on a
  4-point scale against 10-point cutoffs.
- **Get a daily digest and alerts** on Telegram for high-fit openings and close deadlines.
- **Inspect, edit and forget** any memory. Forgetting removes the whole version chain
  and cascades along dependencies (I7). Export or delete everything (FR-15).
- **Use it from other agents** through the MCP server (search, save, update, forget, explain).

Ripple never applies to a job or acts on an external site on the student's behalf (I6).

## Run it locally
Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/) and Node.js for the
dashboard build. Docker is not needed for development: Postgres with pgvector runs
embedded (ADR-0115).

```bash
uv sync
```

```bash
uv run python -m tools.local_run --seed-demo
```

This starts Postgres, applies the migrations, builds the dashboard if needed, serves
the dashboard and the API on one origin, creates a user, and prints the sign-in token.
`--seed-demo` adds a demo student whose profile has already rippled, so the first page
has something to show. Open the printed address and paste the token.

What needs a model key: resume parsing, job-description parsing, free-text statements
and the LLM fallback resolver call Anthropic's API (`ANTHROPIC_API_KEY`, models in
`config/llm.default.toml`). Structured profile facts, the rules, the ripple engine,
retrieval, the inspector, questions, the map, export and forget all work without one
(ADR-0116). When the model is unavailable, the API says so (503) and lists the
change events the nightly sweep will finish later. It never claims a ripple it did not
complete.

Run one scheduled worker job against the same database (prints messages when no
Telegram token is set):

```bash
uv run python -m ripple.worker.run_once nightly_sweep
```

Production runs as containers (API, worker, MCP, Postgres, Redis, Caddy):
`docker compose -f infra/docker-compose.yml --profile app up -d --build`. See
[docs/ops/](docs/ops/).

## Tests and checks

```bash
uv run pytest -m "not slow"
```

```bash
uv run python -m tools.embedded_pg test
```

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

```bash
cd apps/web && npm ci && npm run lint && npm test && npm run build
```

The second command runs the database suite against a throwaway embedded Postgres.
Behaviour scenarios replay a user's timeline and assert every memory's state after
each event (`tests/scenarios/*.yaml`). Each invariant I1–I8 has a named test
(`test_invariant_I<n>_...`).

## Evaluation
- **RippleBench**: synthetic, labelled timelines in three domains: jobs (v0), news and
  finance (v1). Ripple is compared with append-only, newest-wins and check-everything
  memory strategies, plus ablations. Report: [docs/results/benchmark.md](docs/results/benchmark.md).
- **Link finder** (contribution C1): a ModernBERT-base pair classifier, fine-tuned on CPU,
  that proposes typed dependency links from text and is evaluated against the rule
  linker, with cross-domain transfer. Report: [docs/results/link-finder.md](docs/results/link-finder.md).
- **Paper and thesis drafts**: [docs/paper/](docs/paper/). Every number in them is a
  macro rendered from `results/` (invariant I8, `uv run python -m paper.i8`).

Both reports state their limits up front: the benchmarks are synthetic with a scripted
oracle resolver, and the results come from an uncommitted tree. The real-model
comparison (H3) and the student pilot (C3) are not run yet; the reports give the exact
commands and protocol for each.

## Repository map
| Path | What lives there |
|---|---|
| `src/ripple/core` | Models, store protocol, ripple engine, intake, resolver chain. Domain-agnostic. |
| `src/ripple/storage` | PostgreSQL + pgvector store (SQLAlchemy 2 async), Alembic migrations |
| `src/ripple/linking` | Link finders: rules, LLM, trained model |
| `src/ripple/retrieval` | Validity-aware hybrid retrieval with graph expansion |
| `src/ripple/llm` | Provider router, schemas, versioned prompts: the only code that calls an LLM |
| `src/ripple/agents` | Conversation, Scout, Curator, Tailor |
| `src/ripple/domains/jobs` | The job-hunt adapter: vocabulary, rules, parsers, ranking |
| `src/ripple/{api,mcp_server,notify,worker}` | FastAPI, MCP server, Telegram, scheduled jobs |
| `apps/web` | Next.js dashboard (static export) |
| `bench/`, `training/`, `results/` | RippleBench, link-finder training, run outputs |
| `docs/` | Vision, requirements, architecture, data model, evaluation, ADRs, learning notes |

## Read more
[Vision and claims](docs/00-vision.md) · [Requirements](docs/01-requirements.md) ·
[Architecture](docs/02-architecture.md) · [Data model](docs/03-data-model.md) ·
[Evaluation protocol](docs/04-evaluation.md) · [Roadmap](docs/05-roadmap.md) ·
[Related work](docs/06-related-work.md) · [Decisions (ADRs)](docs/adr/README.md) ·
[How each module works](docs/learning/)

---
Final-year B.Tech project by **Omjee R Giri**.
