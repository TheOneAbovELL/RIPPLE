"""Integration adapters: the API's protocols over the jobs workstreams (checkpoint C2).

Each adapter is a thin seam, so the API tests keep using fakes and the real parsers,
recorder and recommender are exercised by their own suites. Written by the coordinator
from the WS-3 handover recipe.
"""

import asyncio

from ripple.api.contracts import OpeningWritten, ResumeParse, ResumeUnparseableError
from ripple.core.clock import Clock
from ripple.core.intake import Statement
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.domains.jobs.derive import derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.parsers import (
    UnparseableResumeError,
    candidate_to_statement,
    extract_text,
    parse_jd,
    parse_resume,
    strip_email_envelope,
)
from ripple.domains.jobs.vocabulary import CandidateFact, ParsedOpening
from ripple.llm.router import Router


class ResumeParserAdapter:
    def __init__(self, router: Router) -> None:
        self._router = router

    async def parse(self, pdf: bytes, *, source_ref: str) -> ResumeParse:
        try:
            text = await asyncio.to_thread(extract_text, pdf)  # pypdf is CPU-bound and sync
        except UnparseableResumeError as exc:
            raise ResumeUnparseableError(str(exc)) from exc
        return ResumeParse(text=text, facts=await parse_resume(self._router, text))


class CandidateStatementsAdapter:
    def statement_for(
        self, user_id: str, candidate: CandidateFact, *, source_ref: str
    ) -> Statement:
        return candidate_to_statement(candidate, user_id, source_ref, origin="inspector")


class OpeningParserAdapter:
    def __init__(self, router: Router) -> None:
        self._router = router

    async def parse(self, text: str, *, source_ref: str) -> ParsedOpening:
        # Forwarded placement emails carry headers and signatures; pasted JDs do not.
        body = strip_email_envelope(text) if source_ref.startswith("email:") else text
        return await parse_jd(self._router, body, source_ref)


class OpeningRecorderAdapter:
    """Records the opening (WS-1) and derives its beliefs so recommendations exist."""

    def __init__(self, store: Store, clock: Clock, runner: RippleRunner) -> None:
        self._store = store
        self._clock = clock
        self._runner = runner

    async def record(self, user_id: str, opening: ParsedOpening) -> OpeningWritten:
        recorded = await record_opening(
            self._store, self._clock, user_id, opening, self._runner, created_by="user"
        )
        derived = await derive_for_opening(
            self._store, self._clock, self._runner, recorded.anchor.id
        )
        beliefs = [b for b in (derived.eligibility, derived.fit, derived.reminder) if b]
        memory_ids = (
            recorded.anchor.id,
            *(f.id for f in recorded.fields),
            *(b.id for b in beliefs),
        )
        return OpeningWritten(
            opening_memory_id=recorded.anchor.id,
            memory_ids=memory_ids,
            event_id=recorded.event.id,
        )
