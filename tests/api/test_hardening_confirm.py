"""Atomic candidate confirm (ADR-0043 follow-up, WS-3 open problem m6).

Two confirms of one candidate used to both pass the pending check and both write. The
store's conditional replace is the arbiter now: the second one raises and the API
answers 409. ConditionalReplaceContract runs here against the in-memory store and,
under the slow marker, in tests/storage/test_hardening_uploads_postgres.py.
"""

import asyncio

import pytest

from ripple.storage.candidates import (
    CandidateAlreadyDecidedError,
    CandidateStatus,
    CandidateStore,
    ResumeCandidate,
)
from tests.api.fakes import InMemoryCandidateStore, ScriptedResumeParser, candidate_fact
from tests.api.harness import Harness, body
from tests.api.store_contracts import _candidate
from tests.fakes.clock import DEFAULT_START

PDF = b"%PDF-1.4 test"


def _decided(row: ResumeCandidate, status: CandidateStatus) -> ResumeCandidate:
    return row.model_copy(
        update={"status": status, "decided_at": DEFAULT_START, "memory_id": "mem-1"}
    )


class ConditionalReplaceContract:
    @pytest.fixture
    def owner(self) -> str:
        return "student-1"

    def test_replace_with_expected_status_writes_when_the_row_still_has_it(
        self, candidate_store: CandidateStore, owner: str
    ):
        row = _candidate(owner)
        asyncio.run(candidate_store.add_candidates([row]))
        decided = _decided(row, CandidateStatus.CONFIRMED)
        asyncio.run(
            candidate_store.replace_candidate(decided, expected_status=CandidateStatus.PENDING)
        )
        assert asyncio.run(candidate_store.get_candidate(row.id)) == decided

    def test_second_decision_on_a_stale_read_raises_and_changes_nothing(
        self, candidate_store: CandidateStore, owner: str
    ):
        row = _candidate(owner)
        asyncio.run(candidate_store.add_candidates([row]))
        # Both requests read the row while it was pending ...
        confirmed = _decided(row, CandidateStatus.CONFIRMED)
        rejected = _decided(row, CandidateStatus.REJECTED).model_copy(update={"memory_id": None})
        asyncio.run(
            candidate_store.replace_candidate(confirmed, expected_status=CandidateStatus.PENDING)
        )
        # ... and the loser finds it decided.
        with pytest.raises(CandidateAlreadyDecidedError) as info:
            asyncio.run(
                candidate_store.replace_candidate(rejected, expected_status=CandidateStatus.PENDING)
            )
        assert info.value.actual is CandidateStatus.CONFIRMED
        assert info.value.candidate_id == row.id
        assert asyncio.run(candidate_store.get_candidate(row.id)) == confirmed

    def test_replace_without_an_expectation_still_overwrites(
        self, candidate_store: CandidateStore, owner: str
    ):
        row = _candidate(owner)
        asyncio.run(candidate_store.add_candidates([row]))
        asyncio.run(candidate_store.replace_candidate(_decided(row, CandidateStatus.CONFIRMED)))
        asyncio.run(candidate_store.replace_candidate(_decided(row, CandidateStatus.REJECTED)))
        found = asyncio.run(candidate_store.get_candidate(row.id))
        assert found is not None and found.status is CandidateStatus.REJECTED


class TestInMemoryConditionalReplace(ConditionalReplaceContract):
    @pytest.fixture
    def candidate_store(self) -> InMemoryCandidateStore:
        return InMemoryCandidateStore()


# ---- the API race ---------------------------------------------------------------------


class _YieldingCandidateStore(InMemoryCandidateStore):
    """Yields to the event loop on every read, so two requests interleave the way two
    uvicorn workers would: both see the candidate pending before either writes."""

    async def get_candidate(self, candidate_id: str):
        await asyncio.sleep(0)
        return await super().get_candidate(candidate_id)


def _race_harness() -> Harness:
    h = Harness.build(resume_parser=ScriptedResumeParser(candidate_fact("cgpa", 7.6, "CGPA 7.6")))
    yielding = _YieldingCandidateStore()
    object.__setattr__(h.services, "candidate_store", yielding)
    h.candidate_store = yielding
    return h


def test_two_concurrent_confirms_yield_one_success_one_409_and_one_memory():
    h = _race_harness()

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            uploaded = body(
                await c.post(
                    "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
                )
            )
            candidate_id = uploaded["candidates"][0]["id"]
            first, second = await asyncio.gather(
                c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers),
                c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers),
            )
        return user, first, second

    user, first, second = asyncio.run(run())
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    loser = first if first.status_code == 409 else second
    assert body(loser)["detail"] == "candidate already confirmed"
    assert len([m for m in h.store.all_memories() if m.user_id == user.id]) == 1
    confirmed = asyncio.run(
        h.candidate_store.candidates_for_user(user.id, CandidateStatus.CONFIRMED)
    )
    assert len(confirmed) == 1 and confirmed[0].memory_id == h.store.all_memories()[0].id


def test_confirm_racing_a_reject_leaves_the_first_decision_standing():
    h = _race_harness()

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            uploaded = body(
                await c.post(
                    "/resume", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=headers
                )
            )
            candidate_id = uploaded["candidates"][0]["id"]
            rejected, confirmed = await asyncio.gather(
                c.post(f"/resume/candidates/{candidate_id}/reject", headers=headers),
                c.post(f"/resume/candidates/{candidate_id}/confirm", headers=headers),
            )
        return user, rejected, confirmed

    user, rejected, confirmed = asyncio.run(run())
    assert {rejected.status_code, confirmed.status_code} == {200, 409}
    rows = asyncio.run(h.candidate_store.candidates_for_user(user.id, None))
    winner = "rejected" if rejected.status_code == 200 else "confirmed"
    assert [r.status.value for r in rows] == [winner]
