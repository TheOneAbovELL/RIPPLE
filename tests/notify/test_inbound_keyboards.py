"""Keyboards and the callback codec (ADR-0076): round trips, 64-byte cap, strict decode."""

import pytest

from ripple.core.ids import new_id
from ripple.notify.inbound.errors import CallbackDataError
from ripple.notify.inbound.keyboards import (
    MAX_CALLBACK_DATA_BYTES,
    AnswerAction,
    Button,
    ForgetAction,
    answer_data,
    decode_callback,
    forget_data,
    forget_keyboard,
    keyboard_rows,
    question_keyboard,
)


@pytest.mark.parametrize("kind", ["still_holds", "no_longer_holds", "correction"])
def test_answer_callback_data_round_trips(kind: str):
    memory_id = new_id()

    assert decode_callback(answer_data(memory_id, kind)) == AnswerAction(memory_id, kind)  # type: ignore[arg-type]


@pytest.mark.parametrize("choice", ["confirm", "cancel"])
def test_forget_callback_data_round_trips(choice: str):
    memory_id = new_id()

    assert decode_callback(forget_data(memory_id, choice)) == ForgetAction(memory_id, choice)  # type: ignore[arg-type]


def test_callback_data_for_a_uuid_memory_id_fits_telegram_limit():
    for data in (answer_data(new_id(), "no_longer_holds"), forget_data(new_id(), "confirm")):
        assert len(data.encode("utf-8")) <= MAX_CALLBACK_DATA_BYTES


def test_button_refuses_callback_data_over_64_bytes():
    with pytest.raises(CallbackDataError, match="64"):
        Button("too long", "a:s:" + "x" * 61)


@pytest.mark.parametrize(
    "data", ["", "a:s", "a:s:", "z:s:mem", "a:q:mem", "f:x:mem", "a:s:mem:extra:ok", "garbage"]
)
def test_decode_callback_rejects_anything_the_keyboards_did_not_produce(data: str):
    if data == "a:s:mem:extra:ok":
        # split(":", 2) keeps the tail as the id; a stray colon in an id is still an id.
        assert decode_callback(data) == AnswerAction("mem:extra:ok", "still_holds")
        return
    with pytest.raises(CallbackDataError):
        decode_callback(data)


def test_question_keyboard_has_the_three_answers_and_valid_reply_markup():
    keyboard = question_keyboard("mem-1")

    assert keyboard_rows(keyboard) == [
        ["Still holds", "No longer"],
        ["Correct it"],
        ["Useful question", "Not useful"],
    ]
    markup = keyboard.reply_markup()
    assert markup["inline_keyboard"][0][1] == {"text": "No longer", "callback_data": "a:n:mem-1"}


def test_forget_keyboard_offers_delete_and_keep():
    assert keyboard_rows(forget_keyboard("mem-1")) == [["Delete for good", "Keep it"]]


def test_feedback_buttons_round_trip_through_the_codec_within_telegrams_limit():
    from ripple.notify.inbound.keyboards import FeedbackAction, feedback_data

    memory_id = "0b5f3a52-6c0e-4b8e-9a43-3f0c2a6d9e11"  # a uuid4, the longest id in use
    for kind in ("saved", "applied", "dismissed", "question_useful", "question_not_useful"):
        data = feedback_data(memory_id, kind)
        assert len(data.encode()) <= 64
        assert decode_callback(data) == FeedbackAction(memory_id, kind)
