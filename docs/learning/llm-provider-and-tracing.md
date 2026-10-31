# ripple.llm: provider adapter, transport retries, prices, tracing
Written 2026-10-19 for WS-8 (ADR-0027, ADR-0018). Complements docs/learning/llm-router.md.

## 1. What it does
Turns the Router from a test-only component into one that can call a real model:
the Anthropic adapter transports requests, the Router retries transport failures with
backoff, prices usage only from configuration, and opens a tracing span per attempt.

## 2. Why it exists
Without a provider adapter the product cannot be used (Phase 2 exit: the author uses
it daily). ADR-0010 wanted one choke point for retries, fallback and cost; ADR-0018
wanted every step traced; I8 forbids invented numbers, so cost is config or None.

## 3. How it works
- `providers/anthropic.py`: builds one tool whose `input_schema` is the requested JSON
  schema and forces the model to call it (`tool_choice`), then serialises the tool
  call's input back to JSON text. The Router still validates (I4). A prose reply
  raises `LLMOutputInvalidError` so the Router retries rather than guessing. The SDK
  client comes from an injected factory; tests pass a fake object, so no key or
  network is needed.
- `config.py`: `RouterConfig.from_toml` loads config/llm.default.toml (or the file
  RIPPLE_LLM_CONFIG names). `prices` maps a model id to USD per million tokens with
  the source and date; `cost_for` returns None for an unpriced model.
- `router.py`: `_call_with_transport_retries` retries connection, timeout and rate
  limit errors on the same model with delays base × 2^n through an injectable sleeper,
  then the Router moves to the next configured model. Schema-invalid output still
  never escalates. Each attempt opens `llm.attempt`; each success `llm.complete`.
- `tracing.py`: `Tracer` protocol; `NoopTracer` default; `LoggingTracer` for
  structured logs. A Langfuse tracer is the planned third implementation.

## 4. Trade-offs
- Forced tool use over provider JSON modes: one code path for every provider; the
  cost is a tool declaration per call, which is small.
- Backoff in the Router, not the SDK: the SDK has its own retries, but owning them
  keeps attempt counts and spans honest and makes the behaviour provider-agnostic.
- Prices as config: the author must copy prices in with a date; the alternative,
  hard-coding, would silently rot and violate I8.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Model answers prose instead of the tool | test_anthropic_client_prose_reply_is_invalid_output_not_a_guess |
| Request shape drifts (system prompt, tool choice) | test_anthropic_client_forces_the_schema_tool_and_splits_system_prompt |
| Transient outage | test_router_retries_transport_errors_with_exponential_backoff, ...falls_back_after_transport_budget_is_spent |
| Invented cost | test_router_prices_usage_from_config_only, test_default_config_file_parses_and_names_only_configured_providers |
| Content in traces | test_router_emits_a_span_per_attempt_and_per_completion |

## 6. Interview questions
1. *Why does the adapter not validate?* One validator (the Router) means one I4 test.
2. *What happens on a rate limit?* Backoff retries on the same model, then fallback.
3. *Where do model ids live?* Config, never code; eval runs record the config.
4. *How is cost kept honest?* Only configured prices with a source; otherwise None.
5. *How do you test a provider without a key?* Inject a fake SDK object.

## 7. Exercise
Add a price for claude-haiku-5-5 to a copy of config/llm.default.toml, point
RIPPLE_LLM_CONFIG at it, and write a test asserting `cost_for` matches your arithmetic.
