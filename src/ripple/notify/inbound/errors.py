"""Errors the inbound channel raises on purpose (python.md: never bare RuntimeError)."""

from ripple.notify.errors import NotifyError


class TelegramCallError(NotifyError):
    """The Bot API refused or did not answer a method call.

    Carries the method, the HTTP status and Telegram's description; never the token,
    never the message text (python.md: no secrets or user content in logs).
    """

    def __init__(
        self,
        method: str,
        status_code: int | None,
        description: str,
        *,
        error_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.method = method
        self.status_code = status_code
        self.description = description
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(f"telegram {method} failed (http {status_code}): {description}")


class CallbackDataError(NotifyError):
    """Callback data that is not one Ripple's keyboards produced."""
