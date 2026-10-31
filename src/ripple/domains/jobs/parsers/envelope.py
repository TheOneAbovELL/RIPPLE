"""Strip the envelope of a forwarded placement email before JD parsing (FR-2, ADR-0035).

Deterministic and conservative: header blocks, forward markers, quote prefixes, legal
disclaimers and closing signatures go; everything else stays. Cutting too much loses
a requirement, so header lines are only recognised at the top of the text or right
after a forward/reply marker, and a signature cut only applies when little text
follows the closing line.
"""

import re

_HEADER_LINE = re.compile(
    r"^(?:From|To|Cc|Bcc|Sent|Date|Subject|Reply-To|Message-ID|In-Reply-To|References|"
    r"Received|Return-Path|Content-Type|Content-Transfer-Encoding|MIME-Version|"
    r"Importance|X-[\w-]+)\s*:",
    re.IGNORECASE,
)
_FORWARD_MARKER = re.compile(
    r"^\s*(?:-{2,}\s*(?:Forwarded message|Original Message)\s*-{2,}|"
    r"Begin forwarded message:|FW:|Fwd:)\s*$",
    re.IGNORECASE,
)
_ON_WROTE = re.compile(r"^\s*On .{3,120}?wrote:\s*$", re.IGNORECASE)
_QUOTE_PREFIX = re.compile(r"^(?:\s*>)+\s?")
_CLOSING = re.compile(
    r"^\s*(?:thanks|thank you|thanks\s*(?:&|and)\s*regards|regards|best|best regards|"
    r"warm regards|kind regards|sincerely|cheers|yours (?:sincerely|faithfully))"
    r"[\s,.!]*$",
    re.IGNORECASE,
)
_SIGNATURE_DELIMITER = re.compile(r"^-- ?$")
_DISCLAIMER = re.compile(
    r"^\s*(?:disclaimer|confidentiality notice|this (?:e-?mail|message)[^.\n]{0,80}"
    r"(?:confidential|intended solely|intended only))",
    re.IGNORECASE,
)
_NOISE_LINE = re.compile(r"^\s*sent from my \w+", re.IGNORECASE)
_MAX_SIGNATURE_LINES = 10


def strip_email_envelope(text: str) -> str:
    lines = [_QUOTE_PREFIX.sub("", line) for line in text.replace("\r\n", "\n").split("\n")]
    lines = _drop_headers(lines)
    # The disclaimer goes first so a long one cannot push the closing line out of the
    # signature window.
    lines = _cut_disclaimer(lines)
    lines = _cut_signature(lines)
    body = "\n".join(line.rstrip() for line in lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _drop_headers(lines: list[str]) -> list[str]:
    """Remove header blocks: a run of Header: lines (plus wrapped continuations) at the
    top of the text or right after a forward/reply marker, and the marker itself.
    A "Date:" line in the middle of a JD body is content and stays."""
    kept: list[str] = []
    headers_allowed = True  # until the first body line
    in_headers = False
    for line in lines:
        if _FORWARD_MARKER.match(line) or _ON_WROTE.match(line) or _NOISE_LINE.match(line):
            headers_allowed = True
            in_headers = True
            continue
        if headers_allowed and _HEADER_LINE.match(line):
            in_headers = True
            continue
        if in_headers and line.strip() and line[:1].isspace():
            continue  # a wrapped header value
        in_headers = False
        if line.strip():
            headers_allowed = False
        kept.append(line)
    return kept


def _cut_signature(lines: list[str]) -> list[str]:
    """Cut from the last closing line or `--` delimiter when at most ten lines follow it."""
    lowest = max(0, len(lines) - _MAX_SIGNATURE_LINES - 1)
    for index in range(len(lines) - 1, lowest - 1, -1):
        line = lines[index]
        if _SIGNATURE_DELIMITER.match(line) or _CLOSING.match(line):
            return lines[:index]
    return lines


def _cut_disclaimer(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        if _DISCLAIMER.match(line):
            return lines[:index]
    return lines
