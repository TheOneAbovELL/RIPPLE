"""Errors the notify package raises on purpose (python.md: never bare RuntimeError)."""

from ripple.core.errors import RippleError


class NotifyError(RippleError):
    """Base class for delivery failures."""


class MessageTooLongError(NotifyError):
    """The rendered text exceeds the transport's limit; nothing was sent."""

    def __init__(self, length: int, limit: int) -> None:
        self.length = length
        self.limit = limit
        super().__init__(f"message of {length} characters exceeds the limit of {limit}")


class TelegramSendError(NotifyError):
    """The Bot API refused or did not answer a sendMessage call.

    The message carries the HTTP status and Telegram's description, never the token or
    the message text (python.md: no secrets or user content in logs).
    """

    def __init__(
        self,
        status_code: int | None,
        description: str,
        *,
        error_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.description = description
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(f"telegram sendMessage failed (http {status_code}): {description}")
