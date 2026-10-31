"""Conversation agent (ADR-0045, FR-10, FR-7): one LangGraph turn per user message.

    classify --intent--> tell             (Intake.ingest, origin "conversation")
                    --> answer           (retrieve -> claims with evidence ids -> reply)
                    --> answer_question  (ripple.core.answers)

The thread id is the user id, so the turn history survives between messages (ADR-0023).
Every model call goes through the Router with a schema (I4). An answer is assembled
from claims that cite memories retrieved this turn; a claim without such a citation is
dropped and the reply says so (I5). Flagged memories are rendered "(unconfirmed)" by
code. The graph has no tool that reaches outside memory (I6; see capabilities.py).
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from ripple.agents.capabilities import Capability
from ripple.agents.evidence import flagged_memories_block, retrieved_block, text_block
from ripple.core import answers
from ripple.core.answers import NotPendingError
from ripple.core.change_detection import ChangeKind
from ripple.core.clock import Clock
from ripple.core.intake import Intake, Statement
from ripple.core.models import ChangeEvent, DecisionAction, Memory, Status, StructuredFact
from ripple.core.retrieval_contract import RetrievedMemory, Retriever
from ripple.core.ripple import RippleRunner
from ripple.core.store import MemoryNotFoundError, Store
from ripple.llm.client import Message
from ripple.llm.prompts import load_prompt
from ripple.llm.router import Router
from ripple.llm.schemas.conversation import AnswerVerdict, Intent, IntentVerdict

log = logging.getLogger("ripple.agents.conversation")

TASK_INTENT = "intent"
TASK_ANSWER = "conversation"
PROMPT_VERSION = 1
RECENT_TURNS = 6

CAPABILITIES = frozenset(
    {
        Capability.LLM_COMPLETE,
        Capability.MEMORY_READ,
        Capability.MEMORY_RETRIEVE,
        Capability.MEMORY_WRITE_VIA_INTAKE,
        Capability.MEMORY_ANSWER_QUESTION,
    }
)

NOTHING_KNOWN = "I have nothing recorded about that yet. Tell me and I will remember it."
NOTHING_SUPPORTED = "I could not answer that from what you have told me so far."
UNCLEAR_QUESTION = "I could not tell which pending question that answers. Which one did you mean?"
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Citation:
    memory_id: str
    source_refs: tuple[str, ...]
    flagged: bool


@dataclass(frozen=True)
class PendingQuestion:
    """A memory the ripple parked in PENDING_USER; the user is asked whether it holds."""

    memory_id: str
    content: str
    reason: str


@dataclass(frozen=True)
class ConversationReply:
    intent: Intent
    text: str
    citations: tuple[Citation, ...] = ()
    # tell: the memory written (or the existing one when nothing changed).
    recorded_memory_id: str | None = None
    questions: tuple[PendingQuestion, ...] = ()
    # ask/plan: claims the model made without evidence it was shown (I5).
    dropped_claims: int = 0


@dataclass(frozen=True)
class Turn:
    message: str
    reply_text: str


def _recent(old: list[Turn], new: list[Turn]) -> list[Turn]:
    """Keep only what the classifier reads. Thread state is a second copy of user text
    outside the forget API (ADR-0045 consequences), so it stays bounded."""
    return (old + new)[-RECENT_TURNS:]


class ConversationState(TypedDict):
    user_id: str
    message: str
    message_id: str | None
    trace_id: str | None
    verdict: IntentVerdict | None
    reply: ConversationReply | None
    turns: Annotated[list[Turn], _recent]


class ConversationAgent:
    def __init__(
        self,
        *,
        store: Store,
        clock: Clock,
        router: Router,
        intake: Intake,
        retriever: Retriever,
        runner: RippleRunner,
        checkpointer: BaseCheckpointSaver,
        domain: str,
        fact_kind: str = "fact",
        k: int = 8,
        prompt_version: int = PROMPT_VERSION,
    ) -> None:
        self._store = store
        self._clock = clock
        self._router = router
        self._intake = intake
        self._retriever = retriever
        self._runner = runner
        self._domain = domain
        self._fact_kind = fact_kind
        self._k = k
        self.prompt_version = prompt_version
        self._intent_prompt = load_prompt("intent", prompt_version)
        self._answer_prompt = load_prompt("conversation", prompt_version)
        self.graph = self._build(checkpointer)

    # ---- public --------------------------------------------------------------

    @property
    def capabilities(self) -> frozenset[Capability]:
        return CAPABILITIES

    async def turn(
        self,
        user_id: str,
        message: str,
        *,
        message_id: str | None = None,
        trace_id: str | None = None,
    ) -> ConversationReply:
        state = await self.graph.ainvoke(
            {
                "user_id": user_id,
                "message": message,
                "message_id": message_id,
                "trace_id": trace_id,
                "verdict": None,
                "reply": None,
            },
            config=self.thread_config(user_id),
        )
        reply = state["reply"]
        assert reply is not None  # every branch sets it
        return reply

    @staticmethod
    def thread_config(user_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": user_id}}

    # ---- graph ---------------------------------------------------------------

    def _build(self, checkpointer: BaseCheckpointSaver) -> Any:
        builder = StateGraph(ConversationState)
        builder.add_node("classify", self._classify)
        builder.add_node("tell", self._tell)
        builder.add_node("answer", self._answer)
        builder.add_node("answer_question", self._answer_question)
        builder.add_edge(START, "classify")
        builder.add_conditional_edges(
            "classify",
            self._route,
            {"tell": "tell", "answer": "answer", "answer_question": "answer_question"},
        )
        for node in ("tell", "answer", "answer_question"):
            builder.add_edge(node, END)
        return builder.compile(checkpointer=checkpointer)

    @staticmethod
    def _route(state: ConversationState) -> Literal["tell", "answer", "answer_question"]:
        verdict = state["verdict"]
        assert verdict is not None
        if verdict.intent == "tell":
            return "tell"
        if verdict.intent == "answer_question":
            return "answer_question"
        return "answer"

    async def _classify(self, state: ConversationState) -> dict[str, Any]:
        pending = await self._pending(state["user_id"])
        recent = state["turns"][-RECENT_TURNS:]
        user = "\n\n".join(
            [
                f"Current date-time: {self._clock.now().isoformat()}",
                text_block("MESSAGE", state["message"]),
                text_block(
                    "RECENT TURNS (oldest first)",
                    "\n".join(f"student: {t.message}\nassistant: {t.reply_text}" for t in recent)
                    or "(none)",
                ),
                flagged_memories_block(
                    "PENDING QUESTIONS (memories waiting for the student's answer)",
                    [(m, True) for m in pending],
                ),
            ]
        )
        completion = await self._router.complete(
            TASK_INTENT,
            [
                Message(role="system", content=self._intent_prompt),
                Message(role="user", content=user),
            ],
            IntentVerdict,
            trace_id=state["trace_id"],
        )
        return {"verdict": completion.output}

    async def _tell(self, state: ConversationState) -> dict[str, Any]:
        verdict = state["verdict"]
        assert verdict is not None and verdict.statement is not None
        content, structured = self._grounded(
            verdict.statement, verdict.structured, state["message"], state["trace_id"]
        )
        statement = Statement(
            user_id=state["user_id"],
            domain=self._domain,
            kind=self._fact_kind,
            content=content,
            structured=structured,
            source_ref=state["message_id"],
            origin="conversation",
        )
        result = await self._intake.ingest(statement, trace_id=state["trace_id"])
        memory = result.memory
        match result.change_kind:
            case ChangeKind.UNCHANGED:
                text = f"That is already recorded: {memory.content}."
            case ChangeKind.UPDATE:
                text = f"Updated: {memory.content} (replaces the earlier version)."
            case ChangeKind.TEMPORARY:
                until = memory.valid_to.date().isoformat() if memory.valid_to else "later"
                text = f"Recorded until {until}: {memory.content}."
            case _:
                text = f"Recorded: {memory.content}."
        questions = await self._questions_from(result.event)
        reply = ConversationReply(
            intent="tell",
            text=_with_questions(text, questions),
            recorded_memory_id=memory.id,
            questions=questions,
        )
        return {"reply": reply, "turns": [Turn(state["message"], reply.text)]}

    async def _answer(self, state: ConversationState) -> dict[str, Any]:
        verdict = state["verdict"]
        assert verdict is not None
        intent: Intent = "plan" if verdict.intent == "plan" else "ask"
        hits = await self._retriever.search(
            state["user_id"],
            state["message"],
            k=self._k,
            include_flagged=True,
            expand_graph=True,
        )
        if not hits:
            # Honest and free: no evidence means no model call and no claims.
            reply = ConversationReply(intent=intent, text=NOTHING_KNOWN)
            return {"reply": reply, "turns": [Turn(state["message"], reply.text)]}
        user = "\n\n".join(
            [
                f"MODE: {intent}",
                f"Current date-time: {self._clock.now().isoformat()}",
                text_block("QUESTION", state["message"]),
                retrieved_block("EVIDENCE (the student's memories)", hits),
            ]
        )
        completion = await self._router.complete(
            TASK_ANSWER,
            [
                Message(role="system", content=self._answer_prompt),
                Message(role="user", content=user),
            ],
            AnswerVerdict,
            trace_id=state["trace_id"],
        )
        reply = _compose_answer(intent, completion.output, hits)
        if reply.dropped_claims:
            log.info(
                "dropped unsupported claims",
                extra={
                    "user_id": state["user_id"],
                    "dropped": reply.dropped_claims,
                    "trace_id": state["trace_id"],
                },
            )
        return {"reply": reply, "turns": [Turn(state["message"], reply.text)]}

    async def _answer_question(self, state: ConversationState) -> dict[str, Any]:
        verdict = state["verdict"]
        assert verdict is not None and verdict.memory_id is not None
        pending = {m.id: m for m in await self._pending(state["user_id"])}
        memory = pending.get(verdict.memory_id)
        if memory is None:
            # Schema-valid but not one of this user's open questions: refuse, write nothing.
            return self._unclear_question(state)
        trace_id = state["trace_id"]
        try:
            match verdict.answer:
                case "still_holds":
                    event = await answers.confirm_still_holds(
                        self._store, self._clock, memory.id, trace_id=trace_id
                    )
                    text = f"Thanks, kept: {memory.content}."
                case "no_longer_holds":
                    event = await answers.answer_no_longer_holds(
                        self._store, self._clock, self._runner, memory.id, trace_id=trace_id
                    )
                    text = f"Retired: {memory.content}."
                case _:
                    assert verdict.correction is not None  # enforced by IntentVerdict
                    content, structured = self._grounded(
                        verdict.correction, verdict.structured, state["message"], trace_id
                    )
                    event = await answers.answer_with_correction(
                        self._store,
                        self._clock,
                        self._runner,
                        memory.id,
                        content=content,
                        # None carries the old value over; a corrected structured fact
                        # must replace it, or content and value disagree.
                        structured=structured,
                        trace_id=trace_id,
                    )
                    text = f"Updated to: {content}."
        except NotPendingError:
            # Answered or swept between our read and the answers transaction.
            return self._unclear_question(state)
        questions = await self._questions_from(event)
        reply = ConversationReply(
            intent="answer_question",
            text=_with_questions(text, questions),
            recorded_memory_id=event.trigger_memory_id,
            questions=questions,
        )
        return {"reply": reply, "turns": [Turn(state["message"], reply.text)]}

    # ---- helpers -------------------------------------------------------------

    @staticmethod
    def _unclear_question(state: ConversationState) -> dict[str, Any]:
        reply = ConversationReply(intent="answer_question", text=UNCLEAR_QUESTION)
        return {"reply": reply, "turns": [Turn(state["message"], reply.text)]}

    @staticmethod
    def _grounded(
        text: str, structured: StructuredFact | None, message: str, trace_id: str | None
    ) -> tuple[str, StructuredFact | None]:
        """Model-written text and values may carry only numbers the student wrote (I5).

        The intent model restates the message. If the restatement or its structured
        value holds a number the message does not, the student's own words are
        recorded instead and the structured form is dropped. Prose without numbers
        passes unchanged.
        """
        claimed = _numbers(text)
        if structured is not None:
            value = structured.value
            if isinstance(value, int | float) and not isinstance(value, bool):
                claimed.add(float(value))
            elif isinstance(value, str):
                claimed |= _numbers(value)
        if claimed <= _numbers(message):
            return text, structured
        log.info(
            "ungrounded number in restatement; recording the message",
            extra={"trace_id": trace_id},
        )
        return message, None

    async def _pending(self, user_id: str) -> list[Memory]:
        return await self._store.memories_for_user(user_id, [Status.PENDING_USER])

    async def _questions_from(self, event: ChangeEvent | None) -> tuple[PendingQuestion, ...]:
        """Memories this event parked in PENDING_USER, as questions for the reply.

        The runner records the ask's reason but not its question text (Decision has
        no such field; contract request in the WS-4 handover), so the question is the
        memory's content plus that reason.
        """
        if event is None:
            return ()
        questions: list[PendingQuestion] = []
        for decision in event.decisions:
            if decision.action is not DecisionAction.ASK:
                continue
            try:
                memory = await self._store.get_memory(decision.memory_id)
            except MemoryNotFoundError:
                continue
            if memory.status is Status.PENDING_USER:
                questions.append(PendingQuestion(memory.id, memory.content, decision.reason))
        return tuple(questions)


def _numbers(text: str) -> set[float]:
    return {float(n) for n in _NUMBER.findall(text)}


def _with_questions(text: str, questions: Sequence[PendingQuestion]) -> str:
    if not questions:
        return text
    lines = [text, f"I need you to confirm {len(questions)} thing(s):"]
    lines.extend(f"- Does this still hold? {q.content} ({q.reason})" for q in questions)
    return "\n".join(lines)


def _compose_answer(
    intent: Intent, verdict: AnswerVerdict, hits: Sequence[RetrievedMemory]
) -> ConversationReply:
    """Keep claims that cite retrieved memories; drop and count the rest (I5)."""
    shown = {h.memory.id: h for h in hits}
    lines: list[str] = []
    citations: dict[str, Citation] = {}
    dropped = 0
    for claim in verdict.claims:
        cited = [shown[i] for i in dict.fromkeys(claim.evidence_ids) if i in shown]
        if not cited:
            dropped += 1
            continue
        unconfirmed = any(h.flagged for h in cited)
        lines.append(f"{claim.text} (unconfirmed)" if unconfirmed else claim.text)
        for h in cited:
            citations.setdefault(h.memory.id, Citation(h.memory.id, h.evidence, h.flagged))
    if not lines:
        lines.append(NOTHING_SUPPORTED)
    if dropped:
        lines.append(
            f"I left out {dropped} statement(s) I could not support from your recorded memory."
        )
    return ConversationReply(
        intent=intent,
        text="\n".join(lines),
        citations=tuple(citations.values()),
        dropped_claims=dropped,
    )
