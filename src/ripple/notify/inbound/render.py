"""Plain-text rendering of agent replies and question cards for Telegram (ADR-0076).

The agent already decides what may be said (claims with retrieved evidence, I5) and
marks claims on doubted memories "(unconfirmed)". This module only lays it out: the
reply text, then a numbered footer with the memory id behind each citation so the
student can open it in the dashboard inspector. No parse_mode: nothing to escape.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from ripple.agents.conversation import ConversationReply
from ripple.notify.telegram import MAX_TEXT_LENGTH

UNCONFIRMED = "(unconfirmed)"
SOURCES_HEADER = "Sources:"


@dataclass(frozen=True)
class QuestionCard:
    """One pending question as the chat shows it; the keyboard is attached by the dispatcher."""

    memory_id: str
    content: str
    question: str
    reason: str

    def text(self) -> str:
        lines = [self.question]
        if self.question.strip() != self.content.strip() and self.content not in self.question:
            lines.append(self.content)
        if self.reason:
            lines.append(f"Why I ask: {self.reason}")
        lines.append(f"Memory {self.memory_id}")
        return "\n".join(lines)


def render_reply(reply: ConversationReply) -> str:
    """The agent's text plus a `[n] <memory id>` footer, flagged ids marked unconfirmed."""
    if not reply.citations:
        return reply.text
    footer = [SOURCES_HEADER]
    for number, citation in enumerate(reply.citations, start=1):
        line = f"[{number}] {citation.memory_id}"
        if citation.flagged:
            line += f" {UNCONFIRMED}"
        footer.append(line)
    return "\n".join([reply.text, "", *footer])


def split_text(text: str, limit: int = MAX_TEXT_LENGTH) -> list[str]:
    """Pieces no longer than `limit`, cut at line breaks when possible, never empty."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit + 1)
        if cut <= 0:
            cut = limit
        piece, rest = rest[:cut], rest[cut:].lstrip("\n")
        if piece:
            pieces.append(piece)
    if rest:
        pieces.append(rest)
    return pieces


def numbered(items: Sequence[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))
