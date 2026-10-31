"""The seven operations behind the MCP tools, for one user (ADR-0080).

Each method takes the validated input model and the calling user and returns an output
model. Anticipated failures raise `ToolCallError(code, detail)`, which the server turns
into an `is_error` result; everything else propagates and is logged as a crash.
Scoping (ADR-0081): every id is dereferenced through `_owned`, which answers
`not_found` for an unknown id and for another user's id alike.
"""

from ripple.api.inspector import mentions, why
from ripple.api.services import Services
from ripple.core.answers import (
    NotPendingError,
    PendingQuestion,
    answer_no_longer_holds,
    answer_with_correction,
    confirm_still_holds,
    pending_questions,
)
from ripple.core.errors import LLMOutputInvalidError, LLMUnavailableError
from ripple.core.forget import forget
from ripple.core.intake import IntakeResult, Statement
from ripple.core.models import ChangeEvent, Memory, Status
from ripple.core.retrieval_contract import Retriever
from ripple.core.store import MemoryNotFoundError
from ripple.core.visibility import FLAGGED, visible_for_retrieval
from ripple.mcp_server.schemas import (
    AnswerIn,
    AnswerOut,
    DecisionOut,
    EventOut,
    ExplainIn,
    ExplainOut,
    ForgetIn,
    ForgetOut,
    ParentOut,
    QuestionOut,
    QuestionsIn,
    QuestionsOut,
    SaveIn,
    SearchHitOut,
    SearchIn,
    SearchOut,
    UpdateIn,
    Visibility,
    WriteOut,
)
from ripple.storage.users import User

AGENT = "agent"
LLM_FAILURES = (LLMOutputInvalidError, LLMUnavailableError)


class ToolCallError(Exception):
    """A failure the calling model can read and correct."""

    def __init__(
        self, code: str, detail: str, *, open_change_event_ids: list[str] | None = None
    ) -> None:
        self.code = code
        self.detail = detail
        self.open_change_event_ids = open_change_event_ids
        super().__init__(f"{code}: {detail}")


def not_found() -> ToolCallError:
    return ToolCallError("not_found", "memory not found")


def _question_out(question: PendingQuestion) -> QuestionOut:
    return QuestionOut(
        memory_id=question.memory.id,
        memory=question.memory,
        question=question.question,
        reason=question.reason,
        event_id=question.event_id,
        asked_at=question.asked_at,
    )


def _event_out(event: ChangeEvent) -> EventOut:
    return EventOut(
        id=event.id,
        trigger_kind=event.trigger_kind,
        trigger_memory_id=event.trigger_memory_id,
        affected_ids=list(event.affected_ids),
        decisions=[
            DecisionOut(
                memory_id=d.memory_id,
                wave=d.wave,
                action=d.action,
                reason=d.reason,
                evidence_refs=list(d.evidence_refs),
                new_version_id=d.new_version_id,
                question=d.question,
            )
            for d in event.decisions
        ],
        created_at=event.created_at,
        completed_at=event.completed_at,
    )


def _visibility(memory: Memory) -> Visibility:
    if memory.status is Status.VALID:
        return "visible"
    if memory.status in FLAGGED:
        return "flagged"
    return "hidden"


class RippleTools:
    def __init__(self, services: Services, retriever: Retriever) -> None:
        self._services = services
        self._retriever = retriever

    # ---- read -------------------------------------------------------------------------

    async def search(self, user: User, args: SearchIn) -> SearchOut:
        hits = await self._retriever.search(
            user.id, args.query, k=args.k, include_flagged=args.include_flagged
        )
        own = [h for h in hits if h.memory.user_id == user.id]
        # The retriever promises I1 (C2 contract); the boundary enforces it regardless.
        flag_for = {
            v.memory.id: v.flagged
            for v in visible_for_retrieval(
                (h.memory for h in own), include_flagged=args.include_flagged
            )
        }
        return SearchOut(
            query=args.query,
            results=[
                SearchHitOut(
                    memory=h.memory,
                    flagged=flag_for[h.memory.id],
                    score=h.score,
                    via=h.via,
                    evidence=list(h.evidence),
                )
                for h in own
                if h.memory.id in flag_for
            ],
        )

    async def explain(self, user: User, args: ExplainIn) -> ExplainOut:
        """The history view: a RETIRED memory is reachable here, as with the API's
        `history=true` (ADR-0042), and says so through `visibility`."""
        store = self._services.store
        memory = await self._owned(user, args.memory_id)
        versions = await store.version_chain(memory.id)
        chain_ids = {v.id for v in versions}
        events = [e for e in await store.change_events_for_user(user.id) if mentions(e, chain_ids)]
        return ExplainOut(
            memory=memory,
            status=memory.status,
            visibility=_visibility(memory),
            why=[
                ParentOut(
                    link_id=p.link_id,
                    link_type=p.link_type,
                    link_class=p.link_class,
                    created_by=p.created_by,
                    confidence=p.confidence,
                    parent=p.parent,
                )
                for p in await why(store, memory)
            ],
            history=versions,
            events=[_event_out(e) for e in events],
        )

    async def questions(self, user: User, args: QuestionsIn) -> QuestionsOut:
        pending = await pending_questions(self._services.store, user.id)
        return QuestionsOut(questions=[_question_out(q) for q in pending])

    # ---- write ------------------------------------------------------------------------

    async def save(self, user: User, args: SaveIn) -> WriteOut:
        statement = Statement(
            user_id=user.id,
            domain=self._services.domain,
            kind=args.kind,
            content=args.content,
            structured=args.structured,
            source_ref=args.source_ref,
            created_by=AGENT,
            origin=AGENT,
        )
        try:
            result = await self._services.intake.ingest(statement)
        except LLM_FAILURES as exc:
            raise await self._llm_failure(user, exc) from exc
        return await self._write_out(user, result)

    async def update(self, user: User, args: UpdateIn) -> WriteOut:
        old = await self._owned(user, args.memory_id)
        if old.status is Status.RETIRED:
            raise not_found()
        if old.status is Status.PENDING_USER:
            raise ToolCallError(
                "conflict", "memory has an open question; answer it with ripple_answer"
            )
        try:
            result = await self._services.intake.edit(
                old.id,
                content=args.content,
                structured=args.structured,
                # Same rule as the API's edit (ADR-0088): omitted keeps, null clears.
                valid_to=args.valid_to if "valid_to" in args.model_fields_set else old.valid_to,
                created_by=AGENT,
                source_ref=f"mcp:{user.id}",
            )
        except LLM_FAILURES as exc:
            raise await self._llm_failure(user, exc) from exc
        return await self._write_out(user, result)

    async def forget(self, user: User, args: ForgetIn) -> ForgetOut:
        memory = await self._owned(user, args.memory_id)
        event = await forget(self._services.store, self._services.clock, memory.id)
        return ForgetOut(
            root_memory_id=event.root_memory_id,
            deleted_ids=list(event.deleted_ids),
            event_id=event.id,
            created_at=event.created_at,
        )

    async def answer(self, user: User, args: AnswerIn) -> AnswerOut:
        store, clock, runner = (
            self._services.store,
            self._services.clock,
            self._services.runner,
        )
        memory = await self._owned(user, args.memory_id)
        if memory.status is Status.RETIRED:
            raise not_found()
        try:
            match args.reply:
                case "still_holds":
                    event = await confirm_still_holds(store, clock, memory.id)
                case "no_longer_holds":
                    event = await answer_no_longer_holds(store, clock, runner, memory.id)
                case "correction":
                    assert args.content is not None  # AnswerIn validated it
                    event = await answer_with_correction(
                        store,
                        clock,
                        runner,
                        memory.id,
                        content=args.content,
                        structured=args.structured,
                        valid_to=args.valid_to,
                    )
        except NotPendingError as exc:
            raise ToolCallError("conflict", str(exc)) from exc
        except LLM_FAILURES as exc:
            raise await self._llm_failure(user, exc) from exc
        latest = await store.latest_version(memory.id)
        return AnswerOut(
            memory_id=latest.id,
            status=latest.status,
            memory=None if latest.status is Status.RETIRED else latest,
            event_id=event.id,
        )

    # ---- helpers ----------------------------------------------------------------------

    async def _owned(self, user: User, memory_id: str) -> Memory:
        """The memory, if it exists and belongs to `user`; otherwise not_found either way."""
        try:
            memory = await self._services.store.get_memory(memory_id)
        except MemoryNotFoundError as exc:
            raise not_found() from exc
        if memory.user_id != user.id:
            raise not_found()
        return memory

    async def _write_out(self, user: User, result: IntakeResult) -> WriteOut:
        parked: list[QuestionOut] = []
        if result.event is not None:
            parked = [
                _question_out(q)
                for q in await pending_questions(self._services.store, user.id)
                if q.event_id == result.event.id
            ]
        return WriteOut(
            memory_id=result.memory.id,
            memory=result.memory,
            change_kind=result.change_kind,
            links_written=result.links_written,
            event_id=result.event.id if result.event is not None else None,
            pending_questions=parked,
        )

    async def _llm_failure(self, user: User, exc: Exception) -> ToolCallError:
        """An LLM can fail after a write committed; name the ripples the sweep resumes."""
        code = "llm_output_invalid" if isinstance(exc, LLMOutputInvalidError) else "llm_unavailable"
        open_events = await self._services.store.open_change_events(user.id)
        return ToolCallError(
            code,
            f"{type(exc).__name__}; the write, if any, is recorded and will be resumed",
            open_change_event_ids=[e.id for e in open_events],
        )
