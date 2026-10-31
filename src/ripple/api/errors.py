"""Map Ripple's exceptions to HTTP statuses, once, at the app boundary.

Handlers raise core exceptions as they are; this module decides the status, so a
router never hand-rolls a 409 for a NotPendingError. Anything unmapped is a 500 and
stays loud (python.md: never swallow exceptions). A 5xx body names the error type but
not its message, which may quote a provider or a user's content.

An LLM failure can arrive after a write committed (Intake writes the memory, then the
ripple runs; the runner commits SUSPECT marks before the resolver answers). The body
then lists the user's open ChangeEvents so the client can tell what was committed; the
nightly sweep resumes them (ADR-0013).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ripple.api.contracts import OpeningUnparseableError, ResumeUnparseableError
from ripple.api.services import Services
from ripple.core.answers import NotPendingError
from ripple.core.errors import (
    ConfigurationError,
    InvariantViolationError,
    LLMOutputInvalidError,
    LLMUnavailableError,
)
from ripple.core.links import UnknownLinkTypeError
from ripple.core.store import ChangeEventNotFoundError, MemoryNotFoundError
from ripple.domains.jobs.openings import OpeningAlreadyRecordedError
from ripple.storage.users import User

log = logging.getLogger("ripple.api")

STATUS_FOR: dict[type[Exception], int] = {
    MemoryNotFoundError: 404,
    ChangeEventNotFoundError: 404,
    NotPendingError: 409,
    # The same JD source pasted twice: the opening already exists (FR-2).
    OpeningAlreadyRecordedError: 409,
    ResumeUnparseableError: 422,
    OpeningUnparseableError: 422,
    UnknownLinkTypeError: 422,
    LLMOutputInvalidError: 503,
    LLMUnavailableError: 503,
    InvariantViolationError: 500,
    ConfigurationError: 500,
}

LLM_FAILURES = (LLMOutputInvalidError, LLMUnavailableError)


def install_error_handlers(app: FastAPI) -> None:
    for exc_type, status in STATUS_FOR.items():
        app.add_exception_handler(exc_type, _handler(status))


def _handler(status: int):  # noqa: ANN202 - FastAPI's handler signature is untyped
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        name = type(exc).__name__
        if status < 500:
            return JSONResponse(status_code=status, content={"detail": str(exc), "error": name})
        log.error("request failed", extra={"error": name, "path": request.url.path})
        content: dict[str, object] = {"detail": f"{name}; see server logs", "error": name}
        if isinstance(exc, LLM_FAILURES):
            content["open_change_event_ids"] = await _open_event_ids(request)
        return JSONResponse(status_code=status, content=content)

    return handle


async def _open_event_ids(request: Request) -> list[str]:
    user = getattr(request.state, "user", None)
    services = getattr(request.app.state, "services", None)
    if not isinstance(user, User) or not isinstance(services, Services):
        return []
    return [event.id for event in await services.store.open_change_events(user.id)]
