"""Reply rendering (ADR-0076): citation footer, unconfirmed marks, chunking."""

import pytest

from ripple.agents.conversation import Citation
from ripple.notify.inbound.render import QuestionCard, render_reply, split_text
from tests.notify.test_inbound_support import reply


def test_render_reply_without_citations_is_the_agent_text_alone():
    assert render_reply(reply("Recorded: CGPA is 7.6.", intent="tell")) == "Recorded: CGPA is 7.6."


def test_render_reply_numbers_citations_in_a_footer_with_memory_ids():
    text = render_reply(
        reply(
            "Your CGPA is 7.6.\nYou know SQL.",
            citations=(
                Citation("mem-cgpa", ("resume:1#3-9",), flagged=False),
                Citation("mem-sql", (), flagged=False),
            ),
        )
    )

    assert text.splitlines() == [
        "Your CGPA is 7.6.",
        "You know SQL.",
        "",
        "Sources:",
        "[1] mem-cgpa",
        "[2] mem-sql",
    ]


def test_render_reply_marks_flagged_citations_unconfirmed():
    text = render_reply(
        reply(
            "Eligible for Acme (unconfirmed)",
            citations=(Citation("mem-elig", (), flagged=True),),
        )
    )

    assert text.splitlines()[-1] == "[1] mem-elig (unconfirmed)"


def test_question_card_shows_question_reason_and_memory_id():
    card = QuestionCard(
        "mem-1", "eligible for Acme", "Does this still hold? eligible for Acme", "cutoff moved"
    )

    assert card.text().splitlines() == [
        "Does this still hold? eligible for Acme",
        "Why I ask: cutoff moved",
        "Memory mem-1",
    ]


def test_question_card_adds_the_content_when_the_question_does_not_quote_it():
    card = QuestionCard("mem-1", "eligible for Acme", "Is this still right?", "")

    assert card.text().splitlines() == ["Is this still right?", "eligible for Acme", "Memory mem-1"]


def test_split_text_returns_short_text_whole():
    assert split_text("hello", limit=10) == ["hello"]


def test_split_text_cuts_at_line_breaks_when_it_can():
    pieces = split_text("line one\nline two\nline three", limit=18)

    assert pieces == ["line one\nline two", "line three"]
    assert all(len(p) <= 18 for p in pieces)


def test_split_text_hard_cuts_a_single_long_line():
    pieces = split_text("x" * 25, limit=10)

    assert pieces == ["x" * 10, "x" * 10, "x" * 5]


def test_split_text_rejects_a_limit_below_one():
    with pytest.raises(ValueError, match="limit"):
        split_text("x", limit=0)
