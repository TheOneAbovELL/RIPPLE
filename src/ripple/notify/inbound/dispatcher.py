"""What the bot answers to one update (ADR-0076). Pure decision, no sending.

`InboundDispatcher.handle(update)` returns an `Outcome`: replies addressed to the chat
that wrote and, for a button tap, the toast to acknowledge it. The channel delivers;
the dispatcher never holds a network client, so every path is tested without one.

Rules the code enforces, not the prose:
- An unlinked chat gets link instructions and nothing else (I6: the bot never acts for
  a chat it cannot tie to a user); `/link` is the one command it may use, rate-limited.
- A button's memory id is re-checked against the user and the memory's state on every
  tap; callback data is a hint, not an authorisation.
- Forget is two steps with a time limit: `/forget <id>` shows the memory, the tap must
  come within `confirmation_ttl`, and only then does `ripple.core.forget` run (I7).
- Every free-text message of a linked chat goes to the conversation agent, which is
  where I5 lives; the dispatcher adds the citation footer and never adds a claim.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from ripple.agents.conversation import ConversationReply
from ripple.api.contracts import OpeningUnparseableError
from ripple.api.services import Services
from ripple.core import answers
from ripple.core.answers import NotPendingError
from ripple.core.errors import LLMOutputInvalidError, LLMUnavailableError
from ripple.core.forget import forget
from ripple.core.models import ChangeEvent, DecisionAction, Memory, Status
from ripple.core.store import MemoryNotFoundError
from ripple.notify.inbound.errors import CallbackDataError
from ripple.notify.inbound.keyboards import (
    AnswerAction,
    FeedbackAction,
    ForgetAction,
    InlineKeyboard,
    decode_callback,
    forget_keyboard,
    question_keyboard,
)
from ripple.notify.inbound.ratelimit import RateLimiter
from ripple.notify.inbound.render import QuestionCard, render_reply
from ripple.notify.inbound.updates import IncomingCallback, IncomingText, IncomingUpdate
from ripple.pilot.feedback import (
    FeedbackKindMismatchError,
    FeedbackTargetNotFoundError,
    record_feedback,
)
from ripple.storage.feedback import FeedbackKind
from ripple.storage.users import User, UserStore, link_telegram

log = logging.getLogger("ripple.notify.inbound.dispatcher")

FEEDBACK_NOTED = "Noted."
FEEDBACK_APPLIED = "Noted. Ripple did not apply anywhere; this is for your records."
FEEDBACK_REPEAT = "Already noted."
FEEDBACK_GONE = "That item is no longer available."

LINK_ATTEMPT_LIMIT = 5
LINK_ATTEMPT_WINDOW = timedelta(minutes=10)
CONFIRMATION_TTL = timedelta(minutes=5)
MAX_QUESTION_CARDS = 10
OPENING_MIN_LENGTH = 200
OPENING_MIN_KEYWORDS = 2
OPENING_MIN_KEYWORDS_FORWARDED = 1
OPENING_KEYWORDS = (
    "job description",
    "responsibilities",
    "requirements",
    "qualifications",
    "eligibility",
    "eligible",
    "cgpa",
    "stipend",
    "ctc",
    "lpa",
    "apply by",
    "last date",
    "deadline",
    "internship",
    "intern",
    "hiring",
    "we are looking for",
    "role:",
    "location:",
    "position",
    "placement",
    "campus",
)

HELP_TEXT = "\n".join(
    [
        'Tell me facts ("my CGPA is 8.1"), ask me things, or paste a job description.',
        "Commands:",
        "/questions - things I need you to confirm",
        "/opening <text> - record a job description",
        "/forget <memory id> - delete a memory and everything built on it",
        "/export - where to download or delete all your data",
        "/help - this message",
    ]
)
UNLINKED_TEXT = (
    "This chat is not linked to a Ripple account yet, so I will not read or write "
    "anything for it. In the dashboard choose Telegram, get a link code and send it "
    "here as /link <code>. A code works once and expires after 15 minutes."
)
START_TEXT = (
    "Hi, I am Ripple. I keep your job-hunt memory consistent: when a fact changes, "
    "everything that depended on it is checked.\n\n" + UNLINKED_TEXT
)
LINK_USAGE = "Send /link followed by the code from the dashboard, for example /link 3F9A2C7B1D0E."
LINK_FAILED = (
    "That code is not valid, has expired or was already used. Make a new one in the "
    "dashboard and send it within 15 minutes."
)
LINK_RATE_LIMITED = "Too many link attempts from this chat. Wait 10 minutes and try again."
ALREADY_LINKED = (
    "This chat is already linked to {name}. To move it, delete the link in the dashboard first."
)
NO_QUESTIONS = "No open questions. I will ask here when a change makes me unsure about something."
QUESTIONS_INTRO = "I need you to confirm {count} thing(s):"
MORE_QUESTIONS = "{count} more in the dashboard."
QUESTION_GONE = "That question was already answered or the memory is gone."
NOT_YOURS = "I cannot find that memory."
CORRECTION_PROMPT = "Send the corrected value as your next message for:\n{content}"
CORRECTION_ACK = "Waiting for your correction"
FORGET_USAGE = (
    "Send /forget followed by the memory id (shown under each source and in the dashboard)."
)
FORGET_CONFIRM = (
    "Delete this memory, every earlier version of it and everything built on it? "
    "This cannot be undone.\n{content}"
)
FORGET_EXPIRED = "That confirmation has expired. Send /forget <memory id> again."
FORGET_DONE = "Deleted {count} memory record(s). They are gone for good."
FORGET_KEPT = "Kept. Nothing was deleted."
EXPORT_TEXT = "Export and deletion live in the dashboard, so you can see exactly what leaves: {url}"
OPENING_USAGE = "Paste the job description after /opening, or forward the message to me."
OPENING_RECORDED = (
    "Recorded opening: {summary} ({count} memory record(s)). Ask me about it any time."
)
OPENING_UNREADABLE = (
    "That did not read as a job description I can structure. Try /opening with the full text."
)
UNKNOWN_COMMAND = "I do not know that command.\n" + HELP_TEXT
MODEL_DOWN = (
    "I could not reach the model just now. Nothing was changed; please try again in a minute."
)
BUTTON_INVALID = "That button is no longer valid."
LINK_FIRST = "Link your account first: send /start"

_COMMAND = re.compile(r"^/([A-Za-z_]+)(?:@\w+)?(?:\s+|$)")


@dataclass(frozen=True)
class Reply:
    chat_id: int
    text: str
    keyboard: InlineKeyboard | None = None


@dataclass(frozen=True)
class CallbackAck:
    callback_id: str
    text: str | None = None


@dataclass(frozen=True)
class Outcome:
    replies: tuple[Reply, ...] = ()
    ack: CallbackAck | None = None
    path: str = ""  # which branch handled it; for logs and tests, never shown to the user

    @property
    def texts(self) -> list[str]:
        return [reply.text for reply in self.replies]


class Conversation(Protocol):
    """The agent's turn (ADR-0045); the dispatcher needs nothing else from it."""

    async def turn(
        self,
        user_id: str,
        message: str,
        *,
        message_id: str | None = None,
        trace_id: str | None = None,
    ) -> ConversationReply: ...


class ChatDirectory(Protocol):
    async def user_for_chat(self, chat_id: int) -> User | None: ...


class ScanningChatDirectory:
    """Chat lookup over `UserStore.list_users`.

    Linear in the number of users: fine for a pilot of fifteen, wrong past a few
    hundred. The handover requests `UserStore.user_for_telegram_chat(chat_id)` backed
    by an index; this class is the seam that swap replaces.
    """

    def __init__(self, user_store: UserStore) -> None:
        self._user_store = user_store

    async def user_for_chat(self, chat_id: int) -> User | None:
        for user in await self._user_store.list_users():
            if user.telegram_chat_id == chat_id:
                return user
        return None


@dataclass(frozen=True)
class _Pending:
    memory_id: str
    user_id: str
    at: datetime


def parse_command(text: str) -> tuple[str | None, str]:
    """("/link", "ABC") for a command, (None, text) otherwise; the bot suffix is dropped."""
    match = _COMMAND.match(text.strip())
    if match is None:
        return None, text.strip()
    return f"/{match.group(1).lower()}", text.strip()[match.end() :].strip()


def looks_like_opening(text: str, *, forwarded: bool) -> bool:
    """A cheap gate before the JD parser: long enough and job-shaped.

    A forwarded message needs one keyword, a pasted one two, so a long forwarded
    placement mail is recorded without a command while a long pasted story about an
    interview is answered by the agent.
    """
    if len(text) < OPENING_MIN_LENGTH:
        return False
    lowered = text.lower()
    hits = sum(1 for keyword in OPENING_KEYWORDS if keyword in lowered)
    needed = OPENING_MIN_KEYWORDS_FORWARDED if forwarded else OPENING_MIN_KEYWORDS
    return hits >= needed


class InboundDispatcher:
    def __init__(
        self,
        *,
        services: Services,
        conversation: Conversation,
        chats: ChatDirectory,
        rate_limiter: RateLimiter,
        dashboard_url: str,
        link_attempt_limit: int = LINK_ATTEMPT_LIMIT,
        link_attempt_window: timedelta = LINK_ATTEMPT_WINDOW,
        confirmation_ttl: timedelta = CONFIRMATION_TTL,
    ) -> None:
        self._services = services
        self._conversation = conversation
        self._chats = chats
        self._rate_limiter = rate_limiter
        self._dashboard_url = dashboard_url
        self._link_attempt_limit = link_attempt_limit
        self._link_attempt_window = link_attempt_window
        self._confirmation_ttl = confirmation_ttl
        # Per-chat short-lived state for the two multi-step flows. Per process: a
        # restart forgets a pending forget or correction, which only costs a retry.
        self._pending_forgets: dict[int, _Pending] = {}
        self._pending_corrections: dict[int, _Pending] = {}

    # ---- entry -----------------------------------------------------------------

    async def handle(self, update: IncomingUpdate) -> Outcome:
        user = await self._chats.user_for_chat(update.chat_id)
        if isinstance(update, IncomingCallback):
            outcome = await self._callback(update, user)
        else:
            outcome = await self._text(update, user)
        log.info(
            "telegram update handled",
            extra={
                "update_id": update.update_id,
                "user_id": user.id if user else None,
                "path": outcome.path,
                "replies": len(outcome.replies),
            },
        )
        return outcome

    # ---- text ------------------------------------------------------------------

    async def _text(self, update: IncomingText, user: User | None) -> Outcome:
        command, args = parse_command(update.text)
        if user is None:
            if command == "/start":
                return self._one(update.chat_id, START_TEXT, path="start_unlinked")
            if command == "/link":
                return await self._link(update, args)
            return self._one(update.chat_id, UNLINKED_TEXT, path="unlinked_refused")

        if command is not None:
            # A command ends any half-finished correction; the student changed topic.
            self._pending_corrections.pop(update.chat_id, None)
            return await self._command(update, user, command, args)

        pending = self._fresh(self._pending_corrections, update.chat_id, user)
        if pending is not None:
            self._pending_corrections.pop(update.chat_id, None)
            return await self._correct(update.chat_id, user, pending.memory_id, update.text)

        if looks_like_opening(update.text, forwarded=update.forwarded):
            return await self._opening(update, user, update.text, path="opening_detected")
        return await self._turn(update, user)

    async def _command(self, update: IncomingText, user: User, command: str, args: str) -> Outcome:
        chat_id = update.chat_id
        match command:
            case "/start" | "/help":
                return self._one(chat_id, HELP_TEXT, path="help")
            case "/link":
                return self._one(
                    chat_id, ALREADY_LINKED.format(name=user.display_name), path="already_linked"
                )
            case "/questions":
                return await self._questions(chat_id, user)
            case "/forget":
                return await self._forget_request(chat_id, user, args)
            case "/export":
                return self._one(
                    chat_id, EXPORT_TEXT.format(url=self._dashboard_url), path="export"
                )
            case "/opening":
                if not args:
                    return self._one(chat_id, OPENING_USAGE, path="opening_usage")
                return await self._opening(update, user, args, path="opening_command")
            case _:
                return self._one(chat_id, UNKNOWN_COMMAND, path="unknown_command")

    async def _link(self, update: IncomingText, code: str) -> Outcome:
        chat_id = update.chat_id
        allowed = await self._rate_limiter.allow(
            f"telegram-link:{chat_id}", self._link_attempt_limit, self._link_attempt_window
        )
        if not allowed:
            log.warning("link attempts rate-limited", extra={"update_id": update.update_id})
            return self._one(chat_id, LINK_RATE_LIMITED, path="link_rate_limited")
        if not code:
            return self._one(chat_id, LINK_USAGE, path="link_usage")
        user = await link_telegram(
            self._services.user_store, code.strip().upper(), chat_id, self._services.clock.now()
        )
        if user is None:
            return self._one(chat_id, LINK_FAILED, path="link_failed")
        log.info("telegram chat linked", extra={"user_id": user.id})
        return self._one(
            chat_id, f"Linked. Hello {user.display_name}!\n\n{HELP_TEXT}", path="linked"
        )

    async def _questions(self, chat_id: int, user: User) -> Outcome:
        pending = await answers.pending_questions(self._services.store, user.id)
        if not pending:
            return self._one(chat_id, NO_QUESTIONS, path="questions_none")
        replies = [Reply(chat_id, QUESTIONS_INTRO.format(count=len(pending)))]
        for question in pending[:MAX_QUESTION_CARDS]:
            card = QuestionCard(
                question.memory.id, question.memory.content, question.question, question.reason
            )
            replies.append(Reply(chat_id, card.text(), question_keyboard(question.memory.id)))
        if len(pending) > MAX_QUESTION_CARDS:
            replies.append(
                Reply(chat_id, MORE_QUESTIONS.format(count=len(pending) - MAX_QUESTION_CARDS))
            )
        return Outcome(tuple(replies), path="questions")

    async def _forget_request(self, chat_id: int, user: User, memory_id: str) -> Outcome:
        if not memory_id:
            return self._one(chat_id, FORGET_USAGE, path="forget_usage")
        memory = await self._owned(user, memory_id)
        if memory is None:
            return self._one(chat_id, NOT_YOURS, path="forget_not_found")
        self._pending_forgets[chat_id] = _Pending(memory.id, user.id, self._services.clock.now())
        return Outcome(
            (
                Reply(
                    chat_id,
                    FORGET_CONFIRM.format(content=memory.content),
                    forget_keyboard(memory.id),
                ),
            ),
            path="forget_asked",
        )

    async def _opening(self, update: IncomingText, user: User, text: str, *, path: str) -> Outcome:
        services = self._services
        try:
            parsed = await services.opening_parser.parse(text, source_ref=update.source_ref)
        except OpeningUnparseableError:
            return self._one(update.chat_id, OPENING_UNREADABLE, path="opening_unreadable")
        except (LLMUnavailableError, LLMOutputInvalidError):
            log.exception("opening parse failed", extra={"user_id": user.id})
            return self._one(update.chat_id, MODEL_DOWN, path="opening_model_down")
        written = await services.opening_recorder.record(user.id, parsed)
        return self._one(
            update.chat_id,
            OPENING_RECORDED.format(summary=parsed.summary, count=len(written.memory_ids)),
            path=path,
        )

    async def _turn(self, update: IncomingText, user: User) -> Outcome:
        try:
            reply = await self._conversation.turn(
                user.id, update.text, message_id=update.source_ref
            )
        except (LLMUnavailableError, LLMOutputInvalidError):
            log.exception("conversation turn failed", extra={"user_id": user.id})
            return self._one(update.chat_id, MODEL_DOWN, path="turn_model_down")
        replies = [Reply(update.chat_id, render_reply(reply))]
        for question in reply.questions:
            card = QuestionCard(
                question.memory_id,
                question.content,
                f"Does this still hold? {question.content}",
                question.reason,
            )
            replies.append(
                Reply(update.chat_id, card.text(), question_keyboard(question.memory_id))
            )
        return Outcome(tuple(replies), path=f"turn:{reply.intent}")

    # ---- callbacks -------------------------------------------------------------

    async def _callback(self, update: IncomingCallback, user: User | None) -> Outcome:
        ack = CallbackAck(update.callback_id)
        if user is None:
            return Outcome(
                ack=CallbackAck(update.callback_id, LINK_FIRST), path="callback_unlinked"
            )
        try:
            action = decode_callback(update.data)
        except CallbackDataError:
            return Outcome(
                ack=CallbackAck(update.callback_id, BUTTON_INVALID), path="callback_invalid"
            )
        if isinstance(action, ForgetAction):
            return await self._forget_decision(update, user, action, ack)
        if isinstance(action, FeedbackAction):
            return await self._feedback(update, user, action)
        return await self._answer(update, user, action, ack)

    async def _answer(
        self, update: IncomingCallback, user: User, action: AnswerAction, ack: CallbackAck
    ) -> Outcome:
        chat_id = update.chat_id
        memory = await self._owned(user, action.memory_id)
        if memory is None:
            return Outcome(ack=CallbackAck(ack.callback_id, NOT_YOURS), path="answer_not_found")
        if memory.status is not Status.PENDING_USER:
            return Outcome(
                ack=CallbackAck(ack.callback_id, QUESTION_GONE), path="answer_not_pending"
            )
        services = self._services
        if action.kind == "correction":
            self._pending_corrections[chat_id] = _Pending(memory.id, user.id, services.clock.now())
            return Outcome(
                (Reply(chat_id, CORRECTION_PROMPT.format(content=memory.content)),),
                CallbackAck(ack.callback_id, CORRECTION_ACK),
                path="answer_correction_prompt",
            )
        try:
            if action.kind == "still_holds":
                event = await answers.confirm_still_holds(services.store, services.clock, memory.id)
                text = f"Kept: {memory.content}"
            else:
                event = await answers.answer_no_longer_holds(
                    services.store, services.clock, services.runner, memory.id
                )
                text = f"Retired: {memory.content}"
        except NotPendingError:
            return Outcome(ack=CallbackAck(ack.callback_id, QUESTION_GONE), path="answer_raced")
        replies = [Reply(chat_id, text), *await self._follow_up_cards(chat_id, event)]
        return Outcome(tuple(replies), ack, path=f"answer:{action.kind}")

    async def _correct(self, chat_id: int, user: User, memory_id: str, content: str) -> Outcome:
        services = self._services
        try:
            event = await answers.answer_with_correction(
                services.store, services.clock, services.runner, memory_id, content=content
            )
        except (MemoryNotFoundError, NotPendingError):
            return self._one(chat_id, QUESTION_GONE, path="correction_raced")
        replies = [
            Reply(chat_id, f"Updated to: {content}"),
            *await self._follow_up_cards(chat_id, event),
        ]
        return Outcome(tuple(replies), path="answer:correction")

    async def _forget_decision(
        self, update: IncomingCallback, user: User, action: ForgetAction, ack: CallbackAck
    ) -> Outcome:
        chat_id = update.chat_id
        pending = self._fresh(self._pending_forgets, chat_id, user)
        self._pending_forgets.pop(chat_id, None)
        if action.choice == "cancel":
            return Outcome((Reply(chat_id, FORGET_KEPT),), ack, path="forget_cancelled")
        if pending is None or pending.memory_id != action.memory_id:
            return Outcome((Reply(chat_id, FORGET_EXPIRED),), ack, path="forget_expired")
        if await self._owned(user, action.memory_id) is None:
            return Outcome((Reply(chat_id, NOT_YOURS),), ack, path="forget_not_found")
        event = await forget(self._services.store, self._services.clock, action.memory_id)
        log.info(
            "memories forgotten from telegram",
            extra={"user_id": user.id, "deleted": len(event.deleted_ids)},
        )
        return Outcome(
            (Reply(chat_id, FORGET_DONE.format(count=len(event.deleted_ids))),),
            ack,
            path="forget_done",
        )

    async def _feedback(
        self, update: IncomingCallback, user: User, action: FeedbackAction
    ) -> Outcome:
        """Pilot feedback (ADR-0105) through the same rules as POST /feedback; a toast,
        no message, and nothing acted on anywhere (I6)."""
        services = self._services
        try:
            _, created = await record_feedback(
                services.store,
                services.feedback_store,
                services.clock,
                user_id=user.id,
                target_memory_id=action.memory_id,
                kind=FeedbackKind(action.kind),
            )
        except FeedbackTargetNotFoundError:
            return Outcome(ack=CallbackAck(update.callback_id, FEEDBACK_GONE), path="feedback_gone")
        except FeedbackKindMismatchError:
            # Only a forged or stale button gets here; nothing worth telling the student.
            log.warning("feedback kind does not fit its target", extra={"user_id": user.id})
            return Outcome(ack=CallbackAck(update.callback_id), path="feedback_mismatch")
        if not created:
            text = FEEDBACK_REPEAT
        elif action.kind == "applied":
            text = FEEDBACK_APPLIED
        else:
            text = FEEDBACK_NOTED
        return Outcome(ack=CallbackAck(update.callback_id, text), path="feedback")

    # ---- helpers ---------------------------------------------------------------

    @staticmethod
    def _one(chat_id: int, text: str, *, path: str) -> Outcome:
        return Outcome((Reply(chat_id, text),), path=path)

    async def _owned(self, user: User, memory_id: str) -> Memory | None:
        """The memory if it is this user's; None otherwise, without saying which."""
        try:
            memory = await self._services.store.get_memory(memory_id)
        except MemoryNotFoundError:
            return None
        return memory if memory.user_id == user.id else None

    def _fresh(self, table: dict[int, _Pending], chat_id: int, user: User) -> _Pending | None:
        pending = table.get(chat_id)
        if pending is None or pending.user_id != user.id:
            return None
        if self._services.clock.now() - pending.at > self._confirmation_ttl:
            return None
        return pending

    async def _follow_up_cards(self, chat_id: int, event: ChangeEvent) -> Sequence[Reply]:
        """Memories this answer's ripple parked in PENDING_USER, as new question cards."""
        cards: list[Reply] = []
        for decision in event.decisions:
            if decision.action is not DecisionAction.ASK:
                continue
            try:
                memory = await self._services.store.get_memory(decision.memory_id)
            except MemoryNotFoundError:
                continue
            if memory.status is Status.PENDING_USER:
                card = QuestionCard(
                    memory.id,
                    memory.content,
                    decision.question or f"Does this still hold? {memory.content}",
                    decision.reason,
                )
                cards.append(Reply(chat_id, card.text(), question_keyboard(memory.id)))
        return cards
