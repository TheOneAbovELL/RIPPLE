# ADR-0027: Anthropic SDK as the first provider adapter; structured output via forced tool use
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
ADR-0010's Router validates JSON into schemas but had no real provider: every path ran
on FakeLLM. The product cannot be used by the author in February 2027 without one.
.env.example already carries ANTHROPIC_API_KEY and OPENAI_API_KEY.

## Decision
- Add the `anthropic` SDK (exact pin) and implement `ripple.llm.providers.anthropic.
  AnthropicClient` as the first `LLMClient`. Structured output is obtained by declaring
  one tool whose `input_schema` is the requested JSON schema and forcing
  `tool_choice` to it; the tool call's input is serialised back to JSON for the Router
  to validate (I4 unchanged: the Router still validates, the adapter only transports).
- Model ids come from config (RouterConfig), never from code; the default config
  file names Claude Haiku 5.5 for linker/change_detector/jd_parser and Claude Sonnet
  5.5 for resolver/conversation/tailor, to be revised by the Phase 3 cost measurements.
- Cost: `RouterConfig.prices` maps model id to USD per million input/output tokens;
  the adapter fills `cost_usd` only when a price is configured, otherwise None, so no
  number is invented (I8). Prices are recorded in config with their source and date.
- Transport retries: the Router retries a provider's transport errors with exponential
  backoff (configurable attempts and base delay, injectable sleeper) before falling
  back to the next model; schema-invalid output is still never retried across
  providers.
- The OpenAI adapter remains unbuilt (NotImplementedError naming the roadmap task)
  until a second provider is needed for fallback in the pilot.

## Alternatives considered
- Provider-native "JSON mode" / response_format — not uniform across providers;
  forced tool use is the documented structured-output path and keeps one code path.
- LangChain model wrappers — an extra abstraction layer over the Router we already
  own; ADR-0010 wanted one choke point. Lost.
- OpenAI first — the author's keys and the project's examples are Anthropic-first;
  either works behind the Router.

## Consequences
- Tests mock the SDK client object (dependency injection of a client factory); no
  network, no key needed. A `RIPPLE_LIVE_LLM=1` slow test is reserved for the author.
- The adapter is the only module importing `anthropic` (boundary test unchanged).

## Revisit if
The SDK's tool-use contract changes, or measured costs argue for different defaults.
