# ripple.llm — the Router
Written 2026-10-19 for src/ripple/llm as it exists after Phase 0 task 0.6.

## 1. What it does
The Router is the only door between Ripple and any LLM. A caller names a task, hands
over messages and a Pydantic schema, and gets back either a validated object or an
exception. Providers are swapped by configuration, not by code.

## 2. Why it exists
ADR-0010 (one provider-agnostic router with structured outputs) and invariant I4 (LLM
output is parsed into a schema before use, never partially applied). NFR-1 needs tests
to run offline, so the same interface has a FakeLLM. NFR-2 and NFR-6 need cost and
latency per call, so the router is where they are measured.

## 3. How it works
- `client.py` defines `LLMClient`, a Protocol with one method, `complete(request)`,
  returning raw text plus token counts. Providers and `tests/fakes/llm.py` implement it.
- `config.py` holds `RouterConfig`: a task name maps to an ordered list of `ModelSpec`
  (primary first, then fallbacks) and a `max_retries` budget.
- `router.py`: `Router.complete(task, messages, schema)` walks the task's models. For
  each model `_complete_with` makes up to `1 + max_retries` attempts. Every attempt
  sends the schema's JSON schema and validates the reply with
  `schema.model_validate_json`. On failure it appends the model's own reply and a
  message naming the validation error, then asks again. Success returns a
  `Completion` with the object, attempts, latency and accumulated tokens. Exhausting
  the budget raises `LLMOutputInvalidError`, and that is final: a different provider
  is not more likely to fix malformed content. A provider that raises a transport
  error is skipped for the next model; when every model fails, `LLMUnavailableError`
  carries each failure.
- Logging uses stdlib `logging` with `extra` fields (task, model, attempts, latency,
  tokens, trace_id). Content is never logged.

## 4. Trade-offs
- Clients return text, not objects, so validation happens in one place. The cost is
  that a provider's native structured-output guarantee is not trusted, only used.
- Invalid output does not trigger fallback. If a cheap model keeps misformatting, the
  fix is configuration (a better primary), not silent escalation that hides cost.
- Retries re-send the whole conversation plus the bad answer, which costs tokens; the
  budget is small (default 2) for that reason.
- No cost table yet: `cost_usd` is None until provider adapters know prices (Phase 2).
  Wrong when: a run needs cost per call before then; use token counts.
- Usage (attempts, tokens, latency) accumulates across providers, so a primary that
  burned two attempts before raising still shows in the fallback's `Completion`.
  A call that raises counts as an attempt.
- No transport retries with backoff yet: a provider error moves straight to the next
  model (TODO in the module docstring, Phase 1).

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Output misses a field, then is fixed | test_router_retries_invalid_output_then_returns_valid |
| Output never valid | test_router_rejects_invalid_output_after_n_retries |
| Invalid output must not escalate to another provider | test_router_does_not_fall_back_on_invalid_output |
| Provider raises | test_router_falls_back_when_provider_raises |
| Every provider raises | test_router_raises_unavailable_when_every_provider_fails |
| Config names a provider with no client | test_router_refuses_config_with_unknown_provider |
| Tokens across attempts | test_router_accumulates_tokens_across_attempts |
| Tokens from a provider that failed before fallback | test_router_counts_tokens_from_failed_provider_before_fallback |
| Content leaking into logs | test_router_logs_every_attempt_without_content |

## 6. Interview questions
1. *Why validate in the router and not in each provider adapter?* One place to test I4;
   adapters stay dumb and interchangeable.
2. *Why does invalid output not fall back to the next provider?* Malformed content is a
   prompt or model-choice problem; escalating hides cost and makes behaviour depend on
   the failure path.
3. *How does a retry help the model?* It sees its own answer and the exact validation
   error (field and reason), the cheapest corrective signal.
4. *What does "never partially applied" mean here?* The caller only ever sees a fully
   validated object; there is no path that returns a dict with some fields filled.
5. *Where do eval numbers for cost come from?* From the `Completion` the router returns,
   recorded by the bench into results/, not from a dashboard (I8, ADR-0018).

## 7. Exercise
Write a FakeLLM script where the first reply is valid JSON of the wrong shape (an
array), and predict the error text the router sends back before running the test.
