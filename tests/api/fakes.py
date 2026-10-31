"""Fakes for the API's injected contracts (tests.md: offline, scripted, recording).

In-memory UserStore and CandidateStore mirror the Postgres ones through the
contracts in tests/api/store_contracts.py. The parser, recorder and recommendation
fakes stand in for WS-1 and WS-2 until integration.
"""

from collections.abc import Sequence
from datetime import datetime

from ripple.api.contracts import (
    OpeningUnparseableError,
    OpeningWritten,
    ResumeParse,
    ResumeUnparseableError,
)
from ripple.core.change_detection import ChangeClassification, ChangeKind
from ripple.core.errors import LLMUnavailableError
from ripple.core.intake import Statement
from ripple.core.models import Memory, StructuredFact
from ripple.core.resolver import Resolution, ResolutionContext
from ripple.domains.jobs.vocabulary import (
    DOMAIN,
    PROFILE_SUBJECT,
    CandidateFact,
    Kind,
    ParsedField,
    ParsedOpening,
    Recommendation,
    TextSpan,
)
from ripple.storage.candidates import (
    CandidateAlreadyDecidedError,
    CandidateStatus,
    ResumeCandidate,
)
from ripple.storage.users import ApiToken, TelegramLinkCode, User

# ---- identity -------------------------------------------------------------------------


class InMemoryUserStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.tokens: dict[str, ApiToken] = {}
        self.codes: dict[str, TelegramLinkCode] = {}

    async def add_user(self, user: User) -> None:
        if user.id in self.users:
            raise ValueError(f"user {user.id!r} already exists")
        self.users[user.id] = user

    async def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    async def list_users(self) -> list[User]:
        return sorted(self.users.values(), key=lambda u: (u.created_at, u.id))

    async def replace_user(self, user: User) -> None:
        if user.id not in self.users:
            raise KeyError(user.id)
        self.users[user.id] = user

    async def delete_user(self, user_id: str) -> None:
        self.users.pop(user_id, None)
        self.tokens = {k: v for k, v in self.tokens.items() if v.user_id != user_id}
        self.codes = {k: v for k, v in self.codes.items() if v.user_id != user_id}

    async def add_token(self, token: ApiToken) -> None:
        if any(t.token_hash == token.token_hash for t in self.tokens.values()):
            raise ValueError("duplicate token hash")  # mirrors uq_api_tokens_token_hash
        self.tokens[token.id] = token

    async def user_for_token_hash(self, token_hash: str) -> User | None:
        for token in self.tokens.values():
            if token.token_hash == token_hash:
                return self.users.get(token.user_id)
        return None

    async def add_link_code(self, code: TelegramLinkCode) -> None:
        if code.code in self.codes:
            raise ValueError("duplicate link code")
        self.codes[code.code] = code

    async def get_link_code(self, code: str) -> TelegramLinkCode | None:
        return self.codes.get(code)

    async def replace_link_code(self, code: TelegramLinkCode) -> None:
        if code.code not in self.codes:
            raise KeyError(code.code)
        self.codes[code.code] = code


class InMemoryCandidateStore:
    def __init__(self) -> None:
        self.candidates: dict[str, ResumeCandidate] = {}

    async def add_candidates(self, candidates: list[ResumeCandidate]) -> None:
        for candidate in candidates:
            if candidate.id in self.candidates:
                raise ValueError(f"candidate {candidate.id!r} already exists")
            self.candidates[candidate.id] = candidate

    async def get_candidate(self, candidate_id: str) -> ResumeCandidate | None:
        return self.candidates.get(candidate_id)

    async def candidates_for_user(
        self, user_id: str, status: CandidateStatus | None = None
    ) -> list[ResumeCandidate]:
        return sorted(
            (
                c
                for c in self.candidates.values()
                if c.user_id == user_id and (status is None or c.status is status)
            ),
            key=lambda c: (c.created_at, c.id),
        )

    async def replace_candidate(
        self, candidate: ResumeCandidate, *, expected_status: CandidateStatus | None = None
    ) -> None:
        if candidate.id not in self.candidates:
            raise KeyError(candidate.id)
        current = self.candidates[candidate.id].status
        if expected_status is not None and current is not expected_status:
            raise CandidateAlreadyDecidedError(candidate.id, current)
        self.candidates[candidate.id] = candidate

    async def delete_for_user(self, user_id: str) -> None:
        self.candidates = {k: v for k, v in self.candidates.items() if v.user_id != user_id}


class FailingResolver:
    """Every provider down: what the Router raises when no model answers."""

    async def resolve(self, context: ResolutionContext) -> Resolution:
        raise LLMUnavailableError("resolver", ["fake: down"])


class ScriptedDetector:
    """Classifies every prose statement the same way; structured facts never reach it."""

    def __init__(self, classification: ChangeClassification | None = None) -> None:
        self._classification = classification or ChangeClassification(
            kind=ChangeKind.NEW, reason="scripted"
        )
        self.calls = 0

    async def classify(
        self, content: str, structured: StructuredFact | None, candidates: Sequence[Memory]
    ) -> ChangeClassification:
        self.calls += 1
        return self._classification


# ---- WS-2 stand-ins -------------------------------------------------------------------


def span(text: str, start: int = 0) -> TextSpan:
    return TextSpan(start=start, end=start + len(text), text=text)


def candidate_fact(
    attribute: str, value: str | int | float | bool, text: str, *, confidence: float = 0.9
) -> CandidateFact:
    return CandidateFact(
        attribute=attribute,
        value=value,
        span=span(text),
        confidence=confidence,
        content=f"{attribute} is {value}",
    )


class ScriptedResumeParser:
    """Returns the scripted facts over a text in which their spans resolve: by default
    the span texts joined by newlines, each fact's span re-based onto that text."""

    def __init__(
        self, *facts: CandidateFact, error: Exception | None = None, text: str | None = None
    ) -> None:
        self._error = error
        self.calls: list[tuple[bytes, str]] = []
        if text is None:
            self.text, self._facts = _rebase_spans(facts)
        else:
            self.text, self._facts = text, list(facts)

    async def parse(self, pdf: bytes, *, source_ref: str) -> ResumeParse:
        self.calls.append((pdf, source_ref))
        if self._error is not None:
            raise self._error
        return ResumeParse(text=self.text, facts=list(self._facts))


NEWLINE = chr(10)  # a literal escape here was mangled twice by shell tooling; chr is unambiguous


def _rebase_spans(facts: Sequence[CandidateFact]) -> tuple[str, list[CandidateFact]]:
    lines: list[str] = []
    rebased: list[CandidateFact] = []
    offset = 0
    for fact in facts:
        lines.append(fact.span.text)
        rebased.append(
            CandidateFact(
                attribute=fact.attribute,
                value=fact.value,
                span=span(fact.span.text, offset),
                confidence=fact.confidence,
                content=fact.content,
            )
        )
        offset += len(fact.span.text) + 1  # the joining newline
    return NEWLINE.join(lines), rebased


def unparseable_resume() -> ResumeUnparseableError:
    return ResumeUnparseableError("no text layer")


class SimpleCandidateStatements:
    """Mirrors WS-2's candidate_to_statement: a profile fact, source_ref plus the span."""

    def statement_for(
        self, user_id: str, candidate: CandidateFact, *, source_ref: str
    ) -> Statement:
        return Statement(
            user_id=user_id,
            domain=DOMAIN,
            kind=Kind.FACT,
            content=candidate.content or f"{candidate.attribute} is {candidate.value}",
            structured=StructuredFact(
                subject=PROFILE_SUBJECT, attribute=candidate.attribute, value=candidate.value
            ),
            source_ref=f"{source_ref}#{candidate.span.start}-{candidate.span.end}",
            created_by="user",
            confidence=1.0,
        )


class ScriptedOpeningParser:
    def __init__(self, fields: Sequence[ParsedField] = (), *, error: Exception | None = None):
        self._fields = tuple(fields)
        self._error = error
        self.calls: list[tuple[str, str]] = []

    async def parse(self, text: str, *, source_ref: str) -> ParsedOpening:
        self.calls.append((text, source_ref))
        if self._error is not None:
            raise self._error
        return ParsedOpening(
            source_ref=source_ref,
            raw_text=text,
            fields=self._fields,
            summary="Intern at Acme",
        )


def unparseable_opening() -> OpeningUnparseableError:
    return OpeningUnparseableError("not a job description")


class RecordingOpeningRecorder:
    def __init__(self) -> None:
        self.recorded: list[tuple[str, ParsedOpening]] = []

    async def record(self, user_id: str, opening: ParsedOpening) -> OpeningWritten:
        self.recorded.append((user_id, opening))
        return OpeningWritten(
            opening_memory_id="opening-1", memory_ids=("opening-1", "req-1"), event_id="event-1"
        )


class ScriptedRecommendations:
    def __init__(self, *recommendations: Recommendation) -> None:
        self._recommendations = list(recommendations)
        self.calls: list[tuple[str, datetime, int]] = []

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]:
        self.calls.append((user_id, now, limit))
        return self._recommendations[:limit]
