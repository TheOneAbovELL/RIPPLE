"""Tracing hook for LLM calls and ripple steps (ADR-0018, NFR-6).

A Tracer opens spans around work and receives attributes when they close. The Router
and the agents call it; nothing in core does. Two implementations ship now: NoopTracer
(default) and LoggingTracer (structured stdlib logs). LangfuseTracer (ADR-0028) is the
third: it sends spans to Langfuse through an injected client, so tests never touch the
network and the protocol is the seam callers depend on.
"""

import logging
import os
import time
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

log = logging.getLogger("ripple.llm.tracing")

Attributes = dict[str, str | int | float | bool | None]


@dataclass
class Span:
    name: str
    attributes: Attributes = field(default_factory=dict)
    started: float = field(default_factory=time.perf_counter)

    def set(self, **attributes: str | int | float | bool | None) -> None:
        self.attributes.update(attributes)

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)


class Tracer(Protocol):
    def span(
        self, name: str, **attributes: str | int | float | bool | None
    ) -> AbstractContextManager[Span]:
        """Open a span; attributes may be added on the returned Span before it closes."""
        ...


class NoopTracer:
    @contextmanager
    def span(self, name: str, **attributes: str | int | float | bool | None) -> Iterator[Span]:
        yield Span(name, dict(attributes))


class LoggingTracer:
    """Emits one INFO record per span with its attributes and duration; never content."""

    def __init__(self, logger: logging.Logger = log) -> None:
        self._log = logger

    @contextmanager
    def span(self, name: str, **attributes: str | int | float | bool | None) -> Iterator[Span]:
        span = Span(name, dict(attributes))
        try:
            yield span
        except Exception as exc:
            span.set(error_type=type(exc).__name__)
            raise
        finally:
            self._log.info(
                "span", extra={"span": name, "elapsed_ms": span.elapsed_ms, **span.attributes}
            )


# ---- Langfuse (ADR-0028) ------------------------------------------------------------

ENV_PUBLIC_KEY = "LANGFUSE_PUBLIC_KEY"
ENV_SECRET_KEY = "LANGFUSE_SECRET_KEY"
ENV_HOST = "LANGFUSE_HOST"


class LangfuseObservationLike(Protocol):
    def update(self, **kwargs: Any) -> Any: ...

    def end(self, **kwargs: Any) -> Any: ...


class LangfuseLike(Protocol):
    """The slice of langfuse.Langfuse the tracer uses."""

    def start_observation(self, *, name: str, **kwargs: Any) -> LangfuseObservationLike: ...

    def flush(self) -> Any: ...

    def shutdown(self) -> Any: ...


class LangfuseTracer:
    """Spans become Langfuse observations; attributes travel as metadata, never content."""

    def __init__(self, client: LangfuseLike) -> None:
        self._client = client

    @contextmanager
    def span(self, name: str, **attributes: str | int | float | bool | None) -> Iterator[Span]:
        span = Span(name, dict(attributes))
        observation = self._client.start_observation(name=name, metadata=dict(attributes))
        try:
            yield span
        except Exception as exc:
            span.set(error_type=type(exc).__name__)
            observation.update(metadata=dict(span.attributes), level="ERROR")
            raise
        finally:
            observation.update(metadata={**span.attributes, "elapsed_ms": span.elapsed_ms})
            observation.end()

    def flush(self) -> None:
        self._client.flush()

    def shutdown(self) -> None:
        self._client.shutdown()


def tracer_from_env(env: Mapping[str, str] | None = None) -> Tracer:
    """Langfuse when all three LANGFUSE_* variables are set; otherwise structured logs.

    Tracing is never on the critical path: a missing key degrades to LoggingTracer and
    says so once at startup.
    """
    env = os.environ if env is None else env
    public, secret, host = (
        env.get(k, "").strip() for k in (ENV_PUBLIC_KEY, ENV_SECRET_KEY, ENV_HOST)
    )
    if not (public and secret and host):
        log.info("tracing: LANGFUSE_* not fully set; using LoggingTracer")
        return LoggingTracer()
    from langfuse import Langfuse  # the only import of the SDK in Ripple

    client = Langfuse(public_key=public, secret_key=secret, base_url=host)
    # The SDK's signature is wider than the slice we call; the cast records that.
    return LangfuseTracer(cast(LangfuseLike, client))
