"""Router: the only path from Ripple to an LLM (ADR-0010, ADR-0027).

Guarantees:
- I4: the caller receives a validated Pydantic object or an exception, never raw text
  and never a partially valid object. Invalid output is retried with the validation
  error shown to the model, then rejected.
- Transport errors (connection, timeout, rate limit) are retried on the same model with
  exponential backoff, then the next configured model is tried. Schema-invalid output
  never escalates to another provider.
- Usage (attempts, tokens, cost) accumulates across every attempt and provider of one
  call, so results/ records what was really spent (I8). Cost comes only from configured
  prices.
- Every attempt is logged and traced with model, latency and token counts, never with
  content (ADR-0018).
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from ripple.core.errors import ConfigurationError, LLMOutputInvalidError, LLMUnavailableError
from ripple.llm.client import CompletionRequest, CompletionResult, LLMClient, Message
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.tracing import NoopTracer, Tracer

log = logging.getLogger("ripple.llm.router")

Sleeper = Callable[[float], Awaitable[None]]


class Completion[OutputT: BaseModel](BaseModel):
    output: OutputT
    model: str
    provider: str
    attempts: int
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None


@dataclass
class _Usage:
    """Accumulated across every attempt and every provider of one complete() call."""

    started: float
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None

    def add(self, input_tokens: int, output_tokens: int, cost_usd: float | None) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        if cost_usd is not None:
            self.cost_usd = (self.cost_usd or 0.0) + cost_usd

    def latency_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)


class Router:
    def __init__(
        self,
        config: RouterConfig,
        clients: Mapping[str, LLMClient],
        *,
        tracer: Tracer | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._config = config
        self._clients = clients
        self._tracer: Tracer = tracer or NoopTracer()
        self._sleep: Sleeper = sleeper or asyncio.sleep
        for specs in config.tasks.values():
            for spec in specs:
                if spec.provider not in clients:
                    raise ConfigurationError(f"no client registered for provider {spec.provider!r}")

    @property
    def tracer(self) -> Tracer:
        """The tracer every call reports to; the process flushes it at shutdown."""
        return self._tracer

    async def complete[OutputT: BaseModel](
        self,
        task: str,
        messages: list[Message],
        schema: type[OutputT],
        *,
        trace_id: str | None = None,
    ) -> Completion[OutputT]:
        usage = _Usage(started=time.perf_counter())
        failures: list[str] = []
        for spec in self._config.models_for(task):
            try:
                return await self._complete_with(spec, task, messages, schema, trace_id, usage)
            except LLMOutputInvalidError:
                # Invalid output is a content problem, not a transport one; a different
                # provider is not more likely to fix it, so stop here (I4: reject).
                raise
            except Exception as exc:  # provider adapters may raise anything
                failures.append(f"{spec.provider}/{spec.model}: {type(exc).__name__}: {exc}")
                log.warning(
                    "llm provider failed",
                    extra={
                        "task": task,
                        "provider": spec.provider,
                        "model": spec.model,
                        "error_type": type(exc).__name__,
                        "trace_id": trace_id,
                    },
                    exc_info=exc,
                )
        raise LLMUnavailableError(task, failures)

    async def _complete_with[OutputT: BaseModel](
        self,
        spec: ModelSpec,
        task: str,
        messages: list[Message],
        schema: type[OutputT],
        trace_id: str | None,
        usage: _Usage,
    ) -> Completion[OutputT]:
        client = self._clients[spec.provider]
        conversation = list(messages)
        last_error = ""
        max_attempts = 1 + self._config.max_retries
        for attempt in range(1, max_attempts + 1):
            request = CompletionRequest(
                model=spec.model,
                messages=conversation,
                json_schema=schema.model_json_schema(),
            )
            result = await self._call_with_transport_retries(client, request, spec, task, usage)
            cost = result.cost_usd
            if cost is None:
                cost = self._config.cost_for(spec.model, result.input_tokens, result.output_tokens)
            usage.add(result.input_tokens, result.output_tokens, cost)
            attempt_log = {
                "task": task,
                "provider": spec.provider,
                "model": spec.model,
                "attempt": attempt,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "trace_id": trace_id,
            }
            try:
                output = schema.model_validate_json(result.text)
            except ValidationError as exc:
                # Covers "not JSON at all" too: pydantic reports it as a json_invalid error.
                last_error = _summarise(exc)
                log.info("llm attempt", extra={**attempt_log, "valid": False})
            else:
                log.info("llm attempt", extra={**attempt_log, "valid": True})
                latency_ms = usage.latency_ms()
                with self._tracer.span(
                    "llm.complete",
                    task=task,
                    provider=spec.provider,
                    model=spec.model,
                    attempts=usage.attempts,
                    latency_ms=latency_ms,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    trace_id=trace_id,
                ):
                    pass
                log.info(
                    "llm completion",
                    extra={
                        "task": task,
                        "provider": spec.provider,
                        "model": spec.model,
                        "attempts": usage.attempts,
                        "latency_ms": latency_ms,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "trace_id": trace_id,
                    },
                )
                return Completion(
                    output=output,
                    model=spec.model,
                    provider=spec.provider,
                    attempts=usage.attempts,
                    latency_ms=latency_ms,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_usd=usage.cost_usd,
                )
            # Show the model what was wrong and ask again; the original messages stay.
            conversation = [
                *conversation,
                Message(role="assistant", content=result.text),
                Message(
                    role="user",
                    content=(
                        "Your previous answer did not match the required JSON schema: "
                        f"{last_error}. Reply again with only JSON matching the schema."
                    ),
                ),
            ]
        raise LLMOutputInvalidError(task, usage.attempts, last_error)

    async def _call_with_transport_retries(
        self,
        client: LLMClient,
        request: CompletionRequest,
        spec: ModelSpec,
        task: str,
        usage: _Usage,
    ) -> CompletionResult:
        """One model call, retried on transport failure with exponential backoff."""
        budget = self._config.transport_retries
        for transport_attempt in range(budget + 1):
            # A call that raises still counts as an attempt: it cost latency and a slot.
            usage.attempts += 1
            with self._tracer.span(
                "llm.attempt", task=task, provider=spec.provider, model=spec.model
            ) as span:
                try:
                    result = await client.complete(request)
                except LLMOutputInvalidError:
                    raise
                except Exception as exc:
                    span.set(error_type=type(exc).__name__)
                    if transport_attempt >= budget:
                        raise
                    delay = self._config.backoff_base_seconds * (2**transport_attempt)
                    log.info(
                        "llm transport retry",
                        extra={
                            "task": task,
                            "provider": spec.provider,
                            "model": spec.model,
                            "error_type": type(exc).__name__,
                            "delay_seconds": delay,
                        },
                    )
                    await self._sleep(delay)
                    continue
                span.set(input_tokens=result.input_tokens, output_tokens=result.output_tokens)
                return result
        raise AssertionError("unreachable: the loop returns or raises")


def _summarise(exc: ValidationError) -> str:
    # pydantic's full error object is verbose; the model needs field and reason only.
    parts = [f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors()]
    return json.dumps(parts)
