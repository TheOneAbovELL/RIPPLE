# ADR-0122: Offline ablations, the `linker` and `ablation` keys, and counted LLM calls
Status: Accepted under the autonomous mandate · Date: 2026-10-31 (WS-18)
Amends the run-config shape of ADR-0060/0062 (new keys only; nothing removed).

## Context
docs/04 lists five ablations: without graph, LLM linker instead of trained, without
Curator, without evidence retrieval, without ask-user. paper/registry.py reads
`ablation` and `linker` from config.json (main ripple runs must say `ablation: null`;
the headline ripple runs are expected to say `linker: "trained"`) and treats
`models: null` as missing provenance while accepting `models: {}` only when
metrics.json carries `llm_calls`. bench.run wrote `llm_calls: 0` as a literal, no
`ablation` and no `linker`.

## Decision
1. **Two ablations run offline**, as `--strategy ripple --ablation <name>`:
   - `no_graph`: Ripple without a dependency graph to scope by re-checks every VALID
     memory after each write. That is check_everything's scope by construction, so the
     ablation reuses that strategy (`NoGraphRippleStrategy`) under the ripple name; its
     numbers equal check_everything's, and a test asserts it on every smoke scenario.
     The graph is still read for the parents-first order (ADR-0104), as in the baseline.
   - `no_ask_user`: every ASK the resolver returns becomes a KEEP (`NoAskResolver`): a
     system without ask-user keeps the belief it cannot settle, unflagged. Later answer
     events then fail as they do for the baselines (recorded errors, not crashes).
   The other three need a real LLM (llm_linker), the Curator agent with a model
   (no_curator) or the tailor's evidence path with a model (no_evidence); they are not
   built and are reported as not run.
2. **`ablation`** (null or the name) is written to config.json and metrics.json; the
   folder name gains `_<ablation>`; the resolver description gains ", asks replaced by
   keeps (no_ask_user)" while keeping its "scripted oracle" prefix.
3. **`linker: "scenario"`** for every bench run, with `linker_details`: links are
   written from the scenario file (the gold graph, created_by human); no link finder
   runs. The paper's headline ripple macros match `linker: "trained"` and therefore do
   not pick these runs up: correct, since a gold graph is not the system C1 claims.
4. **`llm_calls` is counted**: each resolver exposes `llm_calls` and bench.run sums
   them. The scripted oracle (`AliasResolver`) calls no model, so the sum is 0 and
   `llm_calls_note` says that `resolver_calls` is the number of calls an LLM resolver
   would have made. An LLM resolver plugged in later reports its own count.
5. **`models: {}` and `prompt_versions: {}`** replace `null`: "none used", confirmed by
   `llm_calls`, instead of "not recorded".

## Alternatives considered
- **no_graph as "ripple with every link removed"** — measures what the graph adds to
  accuracy (it would behave like newest_wins), but that answers a question the
  baselines already answer, and the task brief for WS-18 asked for check_everything-style
  scope. Lost; noted as a possible second reading in the report.
- **no_ask_user as RETIRE or as a guessed UPDATE** — retire throws away a belief that
  may still hold; an ask carries no content to update with. Lost; KEEP is what a store
  without questions does.
- **Write `llm_calls = resolver_calls`** — would make the oracle look like an LLM run and
  trip the paper's "called an LLM but names no model" check. Lost.
- **`linker: "trained"` because the gold graph is "perfect linking"** — would let the
  paper print oracle-graph numbers as the trained system's. Lost on I8.

## Consequences
- The ablation table in docs/results/benchmark.md has two runnable rows; three rows say
  "not run (needs an LLM)".
- `no_graph` adds no information beyond check_everything on the oracle; it exists so the
  ablation family is complete and a future LLM resolver run fills it.
- The paper's ablation macros (ripple, split test, `ablation` set) can read these runs
  once a commit stamps them and the seed counter reads generator seeds (ADR-0121).
- The headline memory macros need either a trained-linker run or a registry edit that
  admits `linker: "scenario"` for oracle-labelled macros (request to WS-21).

## Revisit if
An LLM resolver or the trained linker runs in the bench (then fill the other three
ablations and add a linker switch), or core changes how an ask parks a subtree.
