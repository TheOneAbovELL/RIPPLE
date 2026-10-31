# ADR-0117: The Anthropic adapter sends only arguments the pinned SDK accepts
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · Amends ADR-0010
(provider adapter request shape)

## Context
WS-20's live run found every model call failing: `POST /openings` answered 503
`LLMUnavailableError`. `AnthropicClient.complete` passed `temperature`, and the pinned
`anthropic==1.15.0` has no such argument on `AsyncMessages.create`, so the SDK raised
`TypeError` before any request left the machine. The unit tests used a fake SDK that
accepted any keyword, so nothing caught it. With the argument removed, a live probe
reached the API and was refused only by authentication (the key on this machine is
invalid), so the request shape is now accepted.

## Decision
1. The adapter no longer sends `temperature`. `CompletionRequest.temperature` stays in the
   provider-neutral request for adapters whose API takes it.
2. A test pins the contract to the installed SDK: the keyword arguments the adapter sends
   must be a subset of `inspect.signature(AsyncMessages.create)`. An SDK upgrade that
   drops or renames an argument fails this test offline instead of in production.

## Alternatives considered
- Pass `temperature` through `extra_body`: it sends a field the SDK dropped on purpose;
  current models may reject it, and determinism here already comes from the forced tool
  schema and I4 validation, not from sampling.
- Pin an older SDK that still takes `temperature`: the version was chosen with the
  models in config; downgrading for one argument trades a working client for an old one.

## Consequences
- Sampling uses the provider default. Decisions stay schema-bound and validated (I4);
  run-to-run variation of LLM answers is measured by the bench, not assumed away.
- tests/llm/test_anthropic_client.py::test_anthropic_client_sends_only_arguments_the_installed_sdk_accepts.
