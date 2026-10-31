"""InboundDispatcher (ADR-0076): every command, the unlinked refusal, links, answers,
forget, openings and the conversation path. Offline over the API harness."""

import asyncio
from datetime import timedelta

from ripple.agents.conversation import Citation, PendingQuestion
from ripple.core.errors import LLMUnavailableError
from ripple.core.models import Status, TriggerKind
from ripple.notify.inbound import dispatcher as d
from ripple.notify.inbound.keyboards import (
    answer_data,
    feedback_data,
    forget_data,
    keyboard_rows,
)
from tests.api.fakes import ScriptedOpeningParser, unparseable_opening
from tests.api.harness import Harness
from tests.builders import memory
from tests.notify.test_inbound_support import (
    CHAT,
    DASHBOARD,
    JD_TEXT,
    OTHER_CHAT,
    build,
    reply,
)

# ---- unlinked chats (I6) ---------------------------------------------------------


def test_dispatcher_start_from_an_unlinked_chat_explains_linking():
    bot = build()

    outcome = asyncio.run(bot.text("/start"))

    assert outcome.texts == [d.START_TEXT]
    assert outcome.path == "start_unlinked"


def test_dispatcher_unlinked_chat_gets_only_link_instructions_for_any_text():
    bot = build()

    outcome = asyncio.run(bot.text("my cgpa is 9.1"))

    assert outcome.texts == [d.UNLINKED_TEXT]
    assert bot.conversation.calls == []
    assert bot.harness.store.all_memories() == []


def test_dispatcher_unlinked_chat_commands_are_refused_except_link_and_start():
    bot = build()

    async def run():
        return [
            await bot.text(c) for c in ("/questions", "/forget x", "/export", "/opening " + JD_TEXT)
        ]

    outcomes = asyncio.run(run())

    assert all(o.texts == [d.UNLINKED_TEXT] for o in outcomes)
    assert bot.harness.opening_recorder.recorded == []


def test_dispatcher_unlinked_chat_button_tap_is_acknowledged_and_ignored():
    bot = build()

    async def run():
        user = await bot.user(chat_id=OTHER_CHAT)
        pending = await bot.pending(user)
        return pending, await bot.tap(answer_data(pending.id, "still_holds"), chat_id=CHAT)

    pending, outcome = asyncio.run(run())

    assert outcome.replies == () and outcome.ack is not None
    assert outcome.ack.text == d.LINK_FIRST
    assert asyncio.run(bot.memory(pending.id)).status is Status.PENDING_USER


# ---- /link -------------------------------------------------------------------------


def test_dispatcher_link_with_a_valid_code_links_the_chat_and_greets():
    bot = build()

    async def run():
        user = await bot.user(chat_id=None)
        code = await bot.link_code(user)
        outcome = await bot.text(f"/link {code.lower()}")  # case-insensitive
        return user, outcome, await bot.harness.user_store.get_user(user.id)

    user, outcome, linked = asyncio.run(run())

    assert outcome.path == "linked"
    assert outcome.texts[0].startswith(f"Linked. Hello {user.display_name}!")
    assert linked is not None and linked.telegram_chat_id == CHAT


def test_dispatcher_link_code_works_once():
    bot = build()

    async def run():
        user = await bot.user(chat_id=None)
        code = await bot.link_code(user)
        first = await bot.text(f"/link {code}")
        second = await bot.text(f"/link {code}", chat_id=OTHER_CHAT)
        return first, second

    first, second = asyncio.run(run())

    assert first.path == "linked"
    assert second.texts == [d.LINK_FAILED]


def test_dispatcher_link_code_expires_after_fifteen_minutes():
    bot = build()

    async def run():
        user = await bot.user(chat_id=None)
        code = await bot.link_code(user)
        bot.harness.clock.advance(timedelta(minutes=15, seconds=1))
        return await bot.text(f"/link {code}")

    assert asyncio.run(run()).texts == [d.LINK_FAILED]


def test_dispatcher_link_without_a_code_shows_usage():
    bot = build()

    assert asyncio.run(bot.text("/link")).texts == [d.LINK_USAGE]


def test_dispatcher_link_attempts_are_rate_limited_per_chat_five_per_ten_minutes():
    bot = build()

    async def run():
        user = await bot.user(chat_id=None)
        attempts = [await bot.text("/link WRONG") for _ in range(6)]
        other_chat = await bot.text("/link WRONG", chat_id=OTHER_CHAT)
        bot.harness.clock.advance(timedelta(minutes=10))
        code = await bot.link_code(user)
        after_window = await bot.text(f"/link {code}")
        return attempts, other_chat, after_window

    attempts, other_chat, after_window = asyncio.run(run())

    assert [a.path for a in attempts] == ["link_failed"] * 5 + ["link_rate_limited"]
    assert attempts[-1].texts == [d.LINK_RATE_LIMITED]
    assert other_chat.path == "link_failed"
    assert after_window.path == "linked"


def test_dispatcher_link_from_an_already_linked_chat_is_refused():
    bot = build()

    async def run():
        user = await bot.user("Asha")
        other, _ = await bot.harness.user("Ravi")
        code = await bot.link_code(other)
        outcome = await bot.text(f"/link {code}")
        return user, outcome, await bot.harness.user_store.get_user(other.id)

    user, outcome, other = asyncio.run(run())

    assert outcome.texts == [d.ALREADY_LINKED.format(name=user.display_name)]
    assert other is not None and other.telegram_chat_id is None


# ---- help, export, unknown ----------------------------------------------------------


def test_dispatcher_help_and_start_for_a_linked_chat_list_the_commands():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/help"), await bot.text("/start")

    for outcome in asyncio.run(run()):
        assert outcome.texts == [d.HELP_TEXT]


def test_dispatcher_export_points_to_the_dashboard():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/export")

    outcome = asyncio.run(run())

    assert DASHBOARD in outcome.texts[0]
    assert outcome.path == "export"


def test_dispatcher_unknown_command_shows_help_without_calling_the_agent():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/frobnicate now")

    assert asyncio.run(run()).texts == [d.UNKNOWN_COMMAND]
    assert bot.conversation.calls == []


def test_parse_command_strips_the_bot_suffix_and_lowercases():
    assert d.parse_command("/Link@RippleBot  ABC123 ") == ("/link", "ABC123")
    assert d.parse_command("/questions") == ("/questions", "")
    assert d.parse_command("tell me /link things") == (None, "tell me /link things")
    assert d.parse_command("  plain text  ") == (None, "plain text")


# ---- /questions and answers ------------------------------------------------------------


def test_dispatcher_questions_with_nothing_pending_says_so():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/questions")

    assert asyncio.run(run()).texts == [d.NO_QUESTIONS]


def test_dispatcher_questions_lists_each_pending_memory_with_an_answer_keyboard():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        return pending, await bot.text("/questions")

    pending, outcome = asyncio.run(run())

    assert outcome.path == "questions"
    assert outcome.texts[0] == d.QUESTIONS_INTRO.format(count=1)
    card = outcome.replies[1]
    assert card.text.splitlines() == [
        f"Does this still hold? {pending.content}",
        "Why I ask: the cutoff may have changed",
        f"Memory {pending.id}",
    ]
    assert card.keyboard is not None
    assert keyboard_rows(card.keyboard) == [
        ["Still holds", "No longer"],
        ["Correct it"],
        ["Useful question", "Not useful"],
    ]


def test_dispatcher_questions_does_not_show_another_users_pending_memories():
    bot = build()

    async def run():
        await bot.user()
        other = await bot.user("Ravi", chat_id=OTHER_CHAT)
        await bot.pending(other)
        return await bot.text("/questions")

    assert asyncio.run(run()).texts == [d.NO_QUESTIONS]


def test_dispatcher_still_holds_tap_restores_the_memory_and_writes_an_event():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        outcome = await bot.tap(answer_data(pending.id, "still_holds"))
        return pending, outcome, await bot.memory(pending.id)

    pending, outcome, after = asyncio.run(run())

    assert after.status is Status.VALID
    assert outcome.texts == [f"Kept: {pending.content}"]
    assert outcome.ack is not None and outcome.ack.text is None
    events = [
        e for e in bot.harness.store.change_events() if e.trigger_kind is TriggerKind.USER_ANSWER
    ]
    assert len(events) == 1  # I2: the answer is a recorded ChangeEvent


def test_dispatcher_no_longer_holds_tap_retires_the_memory():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        outcome = await bot.tap(answer_data(pending.id, "no_longer_holds"))
        return pending, outcome, await bot.memory(pending.id)

    pending, outcome, after = asyncio.run(run())

    assert after.status is Status.RETIRED
    assert outcome.texts == [f"Retired: {pending.content}"]


def test_dispatcher_correction_tap_then_text_writes_a_new_version_without_the_agent():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        prompt = await bot.tap(answer_data(pending.id, "correction"))
        corrected = await bot.text("eligible for Acme (cutoff 7.0)")
        latest = await bot.harness.store.latest_version(pending.id)
        return pending, prompt, corrected, latest

    pending, prompt, corrected, latest = asyncio.run(run())

    assert prompt.texts == [d.CORRECTION_PROMPT.format(content=pending.content)]
    assert prompt.ack is not None and prompt.ack.text == d.CORRECTION_ACK
    assert corrected.path == "answer:correction"
    assert corrected.texts == ["Updated to: eligible for Acme (cutoff 7.0)"]
    assert latest.id != pending.id and latest.content == "eligible for Acme (cutoff 7.0)"
    assert latest.status is Status.VALID
    assert bot.conversation.calls == []


def test_dispatcher_pending_correction_is_cancelled_by_a_command():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        await bot.tap(answer_data(pending.id, "correction"))
        await bot.text("/help")
        outcome = await bot.text("eligible for Acme (cutoff 7.0)")
        return pending, outcome, await bot.memory(pending.id)

    _pending, outcome, after = asyncio.run(run())

    assert outcome.path.startswith("turn:")  # went to the agent, not the correction
    assert after.status is Status.PENDING_USER


def test_dispatcher_pending_correction_expires_after_the_confirmation_ttl():
    bot = build(confirmation_ttl=timedelta(minutes=5))

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        await bot.tap(answer_data(pending.id, "correction"))
        bot.harness.clock.advance(timedelta(minutes=6))
        return await bot.text("eligible for Acme (cutoff 7.0)")

    assert asyncio.run(run()).path.startswith("turn:")


def test_dispatcher_answer_tap_on_another_users_memory_changes_nothing():
    bot = build()

    async def run():
        await bot.user()
        other = await bot.user("Ravi", chat_id=OTHER_CHAT)
        pending = await bot.pending(other)
        outcome = await bot.tap(answer_data(pending.id, "no_longer_holds"))
        return outcome, await bot.memory(pending.id)

    outcome, after = asyncio.run(run())

    assert outcome.replies == () and outcome.ack is not None
    assert outcome.ack.text == d.NOT_YOURS
    assert after.status is Status.PENDING_USER


def test_dispatcher_answer_tap_on_a_memory_that_is_no_longer_pending_is_refused():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        await bot.tap(answer_data(pending.id, "still_holds"))
        return await bot.tap(answer_data(pending.id, "no_longer_holds"))  # stale button

    outcome = asyncio.run(run())

    assert outcome.ack is not None and outcome.ack.text == d.QUESTION_GONE
    assert outcome.replies == ()


def test_dispatcher_answer_tap_with_garbage_callback_data_is_refused():
    bot = build()

    async def run():
        await bot.user()
        return await bot.tap("not-a-button")

    outcome = asyncio.run(run())

    assert outcome.ack is not None and outcome.ack.text == d.BUTTON_INVALID


# ---- /forget -----------------------------------------------------------------------


def test_dispatcher_forget_asks_for_confirmation_with_the_memory_content():
    bot = build()

    async def run():
        user = await bot.user()
        fact = memory(content="knows Rust", user_id=user.id)
        await bot.seed(fact)
        return fact, await bot.text(f"/forget {fact.id}")

    fact, outcome = asyncio.run(run())

    assert outcome.path == "forget_asked"
    assert outcome.texts == [d.FORGET_CONFIRM.format(content="knows Rust")]
    assert outcome.replies[0].keyboard is not None
    assert keyboard_rows(outcome.replies[0].keyboard) == [["Delete for good", "Keep it"]]
    assert asyncio.run(bot.memory(fact.id)).content == "knows Rust"  # nothing deleted yet


def test_dispatcher_forget_confirmed_deletes_through_the_forget_api():
    bot = build()

    async def run():
        user = await bot.user()
        fact = memory(content="knows Rust", user_id=user.id)
        await bot.seed(fact)
        await bot.text(f"/forget {fact.id}")
        return fact, await bot.tap(forget_data(fact.id, "confirm"))

    fact, outcome = asyncio.run(run())

    assert outcome.path == "forget_done"
    assert outcome.texts == [d.FORGET_DONE.format(count=1)]
    assert bot.harness.store.all_memories() == []
    [event] = bot.harness.store.forget_events()
    assert event.deleted_ids == [fact.id]  # I7: a ForgetEvent records what left


def test_dispatcher_forget_cancelled_keeps_the_memory():
    bot = build()

    async def run():
        user = await bot.user()
        fact = memory(content="knows Rust", user_id=user.id)
        await bot.seed(fact)
        await bot.text(f"/forget {fact.id}")
        return fact, await bot.tap(forget_data(fact.id, "cancel"))

    fact, outcome = asyncio.run(run())

    assert outcome.texts == [d.FORGET_KEPT]
    assert [m.id for m in bot.harness.store.all_memories()] == [fact.id]


def test_dispatcher_forget_confirmation_expires_after_the_ttl():
    bot = build(confirmation_ttl=timedelta(minutes=5))

    async def run():
        user = await bot.user()
        fact = memory(content="knows Rust", user_id=user.id)
        await bot.seed(fact)
        await bot.text(f"/forget {fact.id}")
        bot.harness.clock.advance(timedelta(minutes=5, seconds=1))
        return fact, await bot.tap(forget_data(fact.id, "confirm"))

    fact, outcome = asyncio.run(run())

    assert outcome.texts == [d.FORGET_EXPIRED]
    assert [m.id for m in bot.harness.store.all_memories()] == [fact.id]


def test_dispatcher_forget_confirm_without_a_request_deletes_nothing():
    bot = build()

    async def run():
        user = await bot.user()
        fact = memory(content="knows Rust", user_id=user.id)
        await bot.seed(fact)
        return fact, await bot.tap(forget_data(fact.id, "confirm"))

    fact, outcome = asyncio.run(run())

    assert outcome.texts == [d.FORGET_EXPIRED]
    assert [m.id for m in bot.harness.store.all_memories()] == [fact.id]


def test_dispatcher_forget_of_another_users_memory_is_not_found():
    bot = build()

    async def run():
        await bot.user()
        fact = memory(content="knows Rust", user_id="someone-else")
        await bot.seed(fact)
        return await bot.text(f"/forget {fact.id}")

    assert asyncio.run(run()).texts == [d.NOT_YOURS]


def test_dispatcher_forget_without_an_id_shows_usage():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/forget")

    assert asyncio.run(run()).texts == [d.FORGET_USAGE]


# ---- openings ----------------------------------------------------------------------


def test_dispatcher_opening_command_parses_and_records_through_services():
    bot = build()

    async def run():
        user = await bot.user()
        return user, await bot.text(f"/opening {JD_TEXT}")

    user, outcome = asyncio.run(run())

    assert outcome.path == "opening_command"
    [(text, source_ref)] = bot.harness.opening_parser.calls
    assert text == JD_TEXT and source_ref.startswith(f"telegram:{CHAT}:")
    [(recorded_user, parsed)] = bot.harness.opening_recorder.recorded
    assert recorded_user == user.id and parsed.raw_text == JD_TEXT
    assert outcome.texts == [d.OPENING_RECORDED.format(summary="Intern at Acme", count=2)]
    assert bot.conversation.calls == []


def test_dispatcher_opening_command_without_text_shows_usage():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text("/opening")

    assert asyncio.run(run()).texts == [d.OPENING_USAGE]


def test_dispatcher_pasted_job_description_is_detected_without_a_command():
    bot = build()

    async def run():
        await bot.user()
        return await bot.text(JD_TEXT)

    assert asyncio.run(run()).path == "opening_detected"
    assert len(bot.harness.opening_recorder.recorded) == 1


def test_dispatcher_forwarded_long_text_needs_only_one_job_keyword():
    bot = build()
    one_keyword = ("We are hiring for our Bengaluru office. " * 6).strip()  # > 200 chars, "hiring"

    async def run():
        await bot.user()
        pasted = await bot.text(one_keyword)
        forwarded = await bot.text(one_keyword, forwarded=True)
        return pasted, forwarded

    pasted, forwarded = asyncio.run(run())

    assert pasted.path.startswith("turn:")
    assert forwarded.path == "opening_detected"


def test_dispatcher_short_or_unjoblike_text_goes_to_the_agent():
    bot = build()
    story = ("I had a long day preparing for the interview and I think it went well " * 4).strip()

    async def run():
        await bot.user()
        return await bot.text("internship stipend?"), await bot.text(story)

    for outcome in asyncio.run(run()):
        assert outcome.path.startswith("turn:")
    assert bot.harness.opening_recorder.recorded == []


def test_dispatcher_unparseable_opening_is_reported_not_recorded():
    harness = Harness.build(opening_parser=ScriptedOpeningParser(error=unparseable_opening()))
    bot = build(harness=harness)

    async def run():
        await bot.user()
        return await bot.text(f"/opening {JD_TEXT}")

    assert asyncio.run(run()).texts == [d.OPENING_UNREADABLE]
    assert bot.harness.opening_recorder.recorded == []


# ---- conversation ------------------------------------------------------------------


def test_dispatcher_free_text_goes_to_the_agent_with_user_id_and_message_ref():
    bot = build()

    async def run():
        user = await bot.user()
        return user, await bot.text("what do you know about me?")

    user, outcome = asyncio.run(run())

    [(user_id, message, message_id)] = bot.conversation.calls
    assert user_id == user.id and message == "what do you know about me?"
    assert message_id is not None and message_id.startswith(f"telegram:{CHAT}:")
    assert outcome.texts == ["echo: what do you know about me?"]
    assert outcome.path == "turn:ask"


def test_dispatcher_renders_agent_citations_as_a_numbered_footer():
    scripted = reply(
        "Your CGPA is 7.6.\nEligible for Acme (unconfirmed)",
        citations=(Citation("mem-cgpa", ("resume:1",), False), Citation("mem-elig", (), True)),
    )
    bot = build()
    bot.conversation._replies.append(scripted)  # pyright: ignore[reportPrivateUsage]

    async def run():
        await bot.user()
        return await bot.text("am I eligible for Acme?")

    outcome = asyncio.run(run())

    assert outcome.texts == [
        "Your CGPA is 7.6.\nEligible for Acme (unconfirmed)\n\n"
        "Sources:\n[1] mem-cgpa\n[2] mem-elig (unconfirmed)"
    ]


def test_dispatcher_questions_raised_by_a_tell_become_cards_with_keyboards():
    scripted = reply(
        "Recorded: CGPA is 7.9.",
        intent="tell",
        questions=(PendingQuestion("mem-elig", "eligible for Acme", "cutoff may differ"),),
    )
    bot = build()
    bot.conversation._replies.append(scripted)  # pyright: ignore[reportPrivateUsage]

    async def run():
        await bot.user()
        return await bot.text("my cgpa went up to 7.9")

    outcome = asyncio.run(run())

    assert outcome.texts[0] == "Recorded: CGPA is 7.9."
    card = outcome.replies[1]
    assert card.text.splitlines()[0] == "Does this still hold? eligible for Acme"
    assert card.keyboard is not None
    assert card.keyboard.rows[0][0].callback_data == answer_data("mem-elig", "still_holds")


def test_dispatcher_model_outage_is_reported_without_a_traceback_to_the_user():
    bot = build()
    bot.conversation.fail_with = LLMUnavailableError("intent", ["fake: down"])

    async def run():
        await bot.user()
        return await bot.text("hello?")

    outcome = asyncio.run(run())

    assert outcome.texts == [d.MODEL_DOWN]
    assert outcome.path == "turn_model_down"


def test_dispatcher_every_reply_is_addressed_to_the_chat_that_wrote():
    bot = build()

    async def run():
        user = await bot.user()
        await bot.user("Ravi", chat_id=OTHER_CHAT)
        pending = await bot.pending(user)
        outcomes = [
            await bot.text("/questions"),
            await bot.tap(answer_data(pending.id, "still_holds")),
            await bot.text("hello"),
            await bot.text("/export", chat_id=OTHER_CHAT),
        ]
        return outcomes

    outcomes = asyncio.run(run())

    assert {r.chat_id for o in outcomes[:3] for r in o.replies} == {CHAT}
    assert {r.chat_id for r in outcomes[3].replies} == {OTHER_CHAT}


# ---- pilot feedback (ADR-0105) ------------------------------------------------------


def test_dispatcher_question_usefulness_tap_records_feedback_once():
    bot = build()

    async def run():
        user = await bot.user()
        pending = await bot.pending(user)
        first = await bot.tap(feedback_data(pending.id, "question_useful"))
        again = await bot.tap(feedback_data(pending.id, "question_useful"))
        rows = await bot.harness.services.feedback_store.feedback_for_user(user.id)
        return first, again, rows

    first, again, rows = asyncio.run(run())

    assert first.ack is not None and first.ack.text == d.FEEDBACK_NOTED
    assert again.ack is not None and again.ack.text == d.FEEDBACK_REPEAT
    assert [r.kind.value for r in rows] == ["question_useful"]
    assert first.replies == () and again.replies == ()


def test_dispatcher_applied_tap_says_nothing_was_applied_anywhere():
    from ripple.domains.jobs.vocabulary import Kind

    bot = build()

    async def run():
        user = await bot.user()
        job = memory(content="SDE intern at Acme", kind=Kind.OPENING, user_id=user.id)
        await bot.seed(job)
        return await bot.tap(feedback_data(job.id, "applied"))

    outcome = asyncio.run(run())

    assert outcome.ack is not None and outcome.ack.text == d.FEEDBACK_APPLIED


def test_dispatcher_feedback_tap_on_another_users_memory_records_nothing():
    bot = build()

    async def run():
        await bot.user()
        other = await bot.user("Ravi", chat_id=OTHER_CHAT)
        pending = await bot.pending(other)
        outcome = await bot.tap(feedback_data(pending.id, "question_useful"))
        rows = await bot.harness.services.feedback_store.feedback_for_user(other.id)
        return outcome, rows

    outcome, rows = asyncio.run(run())

    assert outcome.ack is not None and outcome.ack.text == d.FEEDBACK_GONE
    assert rows == []
