"""Named invariant tests for the Telegram inbound channel (CLAUDE.md I5, I6)."""

import asyncio
import json

import httpx

from ripple.notify.inbound.channel import TelegramChannel
from ripple.notify.inbound.keyboards import answer_data
from ripple.notify.inbound.ledger import InMemoryUpdateLedger
from ripple.notify.inbound.render import SOURCES_HEADER
from ripple.notify.inbound.telegram import (
    ALLOWED_METHODS,
    METHOD_ANSWER_CALLBACK,
    METHOD_GET_UPDATES,
    METHOD_SEND_MESSAGE,
    METHOD_SET_WEBHOOK,
    TelegramBotApi,
)
from tests.agents.wiring import claims, conversation_agent, intent
from tests.builders import fact
from tests.fakes.clock import FakeClock
from tests.fakes.llm import FakeLLM
from tests.fakes.retriever import ScriptedRetriever, hit
from tests.notify.test_inbound_support import (
    CHAT,
    JD_TEXT,
    OTHER_CHAT,
    build,
    raw_callback_update,
    raw_text_update,
)
from tests.notify.test_inbound_telegram_api import TOKEN

# ---- I6 ------------------------------------------------------------------------------


def test_invariant_I6_bot_calls_only_allowed_methods_and_only_the_writing_chat():
    """A scripted session (link, questions, answer, opening, chat, forget) drives the real
    Bot API client over a mock transport: every outbound call is one of four methods and
    every message goes to the chat that wrote, never to another user's chat."""
    seen: list[tuple[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content)
        seen.append((method, payload.get("chat_id")))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": len(seen)}})

    api = TelegramBotApi(
        TOKEN, FakeClock(), client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    bot = build()
    channel = TelegramChannel(dispatcher=bot.dispatcher, sender=api, ledger=InMemoryUpdateLedger())

    async def run():
        user = await bot.user(chat_id=None)
        await bot.user("Ravi", chat_id=OTHER_CHAT)
        code = await bot.link_code(user)
        pending = await bot.pending(user)
        updates = [
            raw_text_update("/start", update_id=1),
            raw_text_update(f"/link {code}", update_id=2),
            raw_text_update("/questions", update_id=3),
            raw_callback_update(answer_data(pending.id, "still_holds"), update_id=4),
            raw_text_update(JD_TEXT, update_id=5, forwarded=True),
            raw_text_update("what do you know about me?", update_id=6),
            raw_text_update("/export", update_id=7),
            raw_text_update("/forget nope", update_id=8),
        ]
        for raw in updates:
            await channel.receive(raw)

    asyncio.run(run())

    assert seen, "the session produced no outbound calls"
    assert {method for method, _ in seen} <= ALLOWED_METHODS
    assert {chat for method, chat in seen if method == METHOD_SEND_MESSAGE} == {CHAT, str(CHAT)}
    assert OTHER_CHAT not in {chat for _, chat in seen}
    assert {
        METHOD_SEND_MESSAGE,
        METHOD_ANSWER_CALLBACK,
        METHOD_GET_UPDATES,
        METHOD_SET_WEBHOOK,
    } == ALLOWED_METHODS


def test_invariant_I6_unlinked_chat_cannot_trigger_any_write():
    bot = build()

    async def run():
        for text in ("my cgpa is 9.9", "/opening " + JD_TEXT, "/forget x", "/questions"):
            await bot.text(text)
        await bot.tap(answer_data("any", "no_longer_holds"))

    asyncio.run(run())

    assert bot.harness.store.all_memories() == []
    assert bot.harness.store.change_events() == []
    assert bot.harness.opening_recorder.recorded == []
    assert bot.conversation.calls == []


# ---- I5 ------------------------------------------------------------------------------


def test_invariant_I5_replies_never_carry_claims_without_a_retrieved_citation():
    """The real conversation agent behind the dispatcher: the model invents two claims;
    the rendered Telegram reply shows only the cited one, lists exactly the retrieved
    memory in the footer and discloses the drop (agent's dropped_claims)."""
    harness_bot = build()
    store, clock = harness_bot.harness.store, harness_bot.harness.clock

    async def run():
        user = await harness_bot.user()
        cgpa = fact("student", "cgpa", 7.6, user_id=user.id)
        await harness_bot.seed(cgpa)
        llm = FakeLLM(
            intent("ask"),
            claims(
                ("Your CGPA is 7.6.", [cgpa.id]),
                ("You interned at Google for two years.", []),
                ("You won a hackathon.", ["not-retrieved"]),
            ),
        )
        agent = conversation_agent(store, clock, llm, ScriptedRetriever(hit(cgpa)))
        bot = build(conversation=agent, harness=harness_bot.harness)
        return cgpa, await bot.text("what do you know about me?")

    cgpa, outcome = asyncio.run(run())

    [text] = outcome.texts
    assert "Google" not in text and "hackathon" not in text
    body, footer = text.split(f"\n\n{SOURCES_HEADER}\n")
    assert body.splitlines() == [
        "Your CGPA is 7.6.",
        "I left out 2 statement(s) I could not support from your recorded memory.",
    ]
    assert footer.splitlines() == [f"[1] {cgpa.id}"]
