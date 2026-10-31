"""Errors the parsers raise on purpose (python.md: specific exceptions, never bare ones)."""

from ripple.core.errors import RippleError


class UnparseableResumeError(RippleError):
    """The PDF has no text layer, is damaged or encrypted; OCR is out of scope (ADR-0024)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"resume cannot be parsed: {reason}")
