"""Exceptions raised across Ripple.

Every module raises these rather than bare ValueError/RuntimeError (python.md), so
callers can distinguish an invariant breach from an unavailable provider. New
exception types are added here when the code that raises them is built, not before.
"""


class RippleError(Exception):
    """Base class for every error Ripple raises on purpose."""


class ConfigurationError(RippleError):
    """Ripple was wired with a missing or inconsistent setting (config, env, registry)."""


class InvalidObjectError(RippleError, ValueError):
    """A core dataclass (resolution, proposal, classification) was built inconsistently."""


class InvariantViolationError(RippleError):
    """An invariant I1-I8 (CLAUDE.md) would be broken; the operation was refused."""


class LLMOutputInvalidError(RippleError):
    """The LLM never produced output matching the requested schema within the retry budget (I4)."""

    def __init__(self, task: str, attempts: int, last_error: str) -> None:
        self.task = task
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"task {task!r}: invalid output after {attempts} attempt(s): {last_error}")


class LLMUnavailableError(RippleError):
    """Every configured provider for a task failed before producing any output."""

    def __init__(self, task: str, failures: list[str]) -> None:
        self.task = task
        self.failures = failures
        super().__init__(f"task {task!r}: all providers failed: {failures}")
