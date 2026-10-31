"""Inline keyboards and the callback-data codec (ADR-0076).

Telegram caps callback_data at 64 bytes, so a button carries a one-letter family, a
one-letter action and the memory id (a uuid4 string, 36 characters), nothing else.
The dispatcher re-checks ownership and state on every tap: callback data is a hint
from the client, never an authorisation.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ripple.notify.inbound.errors import CallbackDataError

MAX_CALLBACK_DATA_BYTES = 64

AnswerKind = Literal["still_holds", "no_longer_holds", "correction"]
ForgetChoice = Literal["confirm", "cancel"]
# Pilot feedback (ADR-0105); the values are ripple.storage.feedback.FeedbackKind's.
FeedbackChoice = Literal["saved", "applied", "dismissed", "question_useful", "question_not_useful"]

_ANSWER_CODES: dict[str, AnswerKind] = {
    "s": "still_holds",
    "n": "no_longer_holds",
    "c": "correction",
}
_ANSWER_LETTERS = {kind: code for code, kind in _ANSWER_CODES.items()}
_FORGET_CODES: dict[str, ForgetChoice] = {"y": "confirm", "n": "cancel"}
_FORGET_LETTERS = {choice: code for code, choice in _FORGET_CODES.items()}
_FEEDBACK_CODES: dict[str, FeedbackChoice] = {
    "s": "saved",
    "a": "applied",
    "d": "dismissed",
    "u": "question_useful",
    "n": "question_not_useful",
}
_FEEDBACK_LETTERS = {kind: code for code, kind in _FEEDBACK_CODES.items()}


@dataclass(frozen=True)
class Button:
    text: str
    callback_data: str

    def __post_init__(self) -> None:
        size = len(self.callback_data.encode("utf-8"))
        if size > MAX_CALLBACK_DATA_BYTES:
            raise CallbackDataError(f"callback data is {size} bytes; Telegram allows 64")


@dataclass(frozen=True)
class InlineKeyboard:
    rows: tuple[tuple[Button, ...], ...]

    def reply_markup(self) -> dict[str, list[list[dict[str, str]]]]:
        """The `reply_markup` object sendMessage takes."""
        return {
            "inline_keyboard": [
                [{"text": b.text, "callback_data": b.callback_data} for b in row]
                for row in self.rows
            ]
        }


@dataclass(frozen=True)
class AnswerAction:
    memory_id: str
    kind: AnswerKind


@dataclass(frozen=True)
class ForgetAction:
    memory_id: str
    choice: ForgetChoice


@dataclass(frozen=True)
class FeedbackAction:
    memory_id: str
    kind: FeedbackChoice


CallbackAction = AnswerAction | ForgetAction | FeedbackAction


def answer_data(memory_id: str, kind: AnswerKind) -> str:
    return f"a:{_ANSWER_LETTERS[kind]}:{memory_id}"


def forget_data(memory_id: str, choice: ForgetChoice) -> str:
    return f"f:{_FORGET_LETTERS[choice]}:{memory_id}"


def feedback_data(memory_id: str, kind: FeedbackChoice) -> str:
    return f"p:{_FEEDBACK_LETTERS[kind]}:{memory_id}"


def decode_callback(data: str) -> CallbackAction:
    """The action a button encodes; CallbackDataError for anything else."""
    parts = data.split(":", 2)
    if len(parts) != 3 or not parts[2]:
        raise CallbackDataError("callback data has the wrong shape")
    family, code, memory_id = parts
    if family == "a" and code in _ANSWER_CODES:
        return AnswerAction(memory_id, _ANSWER_CODES[code])
    if family == "f" and code in _FORGET_CODES:
        return ForgetAction(memory_id, _FORGET_CODES[code])
    if family == "p" and code in _FEEDBACK_CODES:
        return FeedbackAction(memory_id, _FEEDBACK_CODES[code])
    raise CallbackDataError("callback data names an unknown action")


def question_keyboard(memory_id: str) -> InlineKeyboard:
    return InlineKeyboard(
        (
            (
                Button("Still holds", answer_data(memory_id, "still_holds")),
                Button("No longer", answer_data(memory_id, "no_longer_holds")),
            ),
            (Button("Correct it", answer_data(memory_id, "correction")),),
            # Pilot metric "question usefulness" (docs/04, ADR-0105).
            (
                Button("Useful question", feedback_data(memory_id, "question_useful")),
                Button("Not useful", feedback_data(memory_id, "question_not_useful")),
            ),
        )
    )


def forget_keyboard(memory_id: str) -> InlineKeyboard:
    return InlineKeyboard(
        (
            (
                Button("Delete for good", forget_data(memory_id, "confirm")),
                Button("Keep it", forget_data(memory_id, "cancel")),
            ),
        )
    )


def keyboard_rows(keyboard: InlineKeyboard) -> Sequence[Sequence[str]]:
    """Button labels by row; for tests and logs."""
    return [[b.text for b in row] for row in keyboard.rows]
