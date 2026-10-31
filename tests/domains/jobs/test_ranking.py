"""JobsRecommender (ADR-0032): eligible, urgent, fit, variety; flagged; never retired."""

from datetime import UTC, datetime, timedelta

from ripple.core.models import Status
from ripple.domains.jobs.derive import derive_for_opening
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.profile import record_profile_fact
from ripple.domains.jobs.ranking import JobsRecommender
from ripple.domains.jobs.vocabulary import ProfileAttribute, Recommendation
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


class Board:
    """A store with a profile (cgpa 7.9, batch 2027, python + pytorch) and openings."""

    def __init__(self) -> None:
        self.store, self.clock = InMemoryStore(), FakeClock(NOW - timedelta(days=7))
        self.runner = make_runner(self.store, self.clock)
        for attribute, value in (
            (ProfileAttribute.CGPA, 7.9),
            (ProfileAttribute.BATCH, 2027),
            (ProfileAttribute.SKILL, "Python"),
            (ProfileAttribute.SKILL, "PyTorch"),
        ):
            run(record_profile_fact(self.store, self.clock, self.runner, USER, attribute, value))

    def opening(
        self,
        company: str | None,
        *,
        cutoff: float | None = 7.8,
        batch: int | None = 2027,
        skills: tuple[str, ...] = ("Python", "PyTorch", "SQL"),
        deadline: datetime | None = NOW + timedelta(days=10),
        source_ref: str | None = None,
    ) -> str:
        parsed = parsed_acme(
            company=company,
            cutoff=cutoff,
            batch=batch,
            skills=skills,
            deadline=deadline.isoformat() if deadline else None,
            source_ref=source_ref or f"https://{(company or 'none').lower()}.example/jobs",
        )
        self.clock.advance(timedelta(minutes=1))
        recorded = run(record_opening(self.store, self.clock, USER, parsed, self.runner))
        run(derive_for_opening(self.store, self.clock, self.runner, recorded.anchor.id))
        return recorded.anchor.id

    def set_status(self, memory_id: str, status: Status) -> None:
        async def flip():
            async with self.store.transaction() as tx:
                memory = await tx.get_memory(memory_id)
                await tx.replace_memory(memory.model_copy(update={"status": status}))

        run(flip())

    def rank(self, *, now: datetime = NOW, limit: int = 10) -> list[Recommendation]:
        return list(
            run(JobsRecommender(self.store).recommendations_for(USER, now=now, limit=limit))
        )


def test_recommender_puts_eligible_openings_before_ineligible_ones_whatever_the_fit():
    board = Board()
    weak_but_eligible = board.opening("Acme", skills=("Rust", "Go"))
    strong_but_ineligible = board.opening("Globex", cutoff=9.5, skills=("Python", "PyTorch"))
    ranked = board.rank()
    assert [r.opening_memory_id for r in ranked] == [weak_but_eligible, strong_but_ineligible]
    assert [r.eligible for r in ranked] == [True, False]
    assert ranked[1].fit_score == 1.0 and ranked[0].fit_score == 0.0


def test_recommender_puts_a_deadline_within_48_hours_before_a_better_fit():
    board = Board()
    better_fit = board.opening("Acme", skills=("Python", "PyTorch"))
    urgent = board.opening("Globex", skills=("Python", "SQL"), deadline=NOW + timedelta(hours=30))
    assert [r.opening_memory_id for r in board.rank()] == [urgent, better_fit]


def test_recommender_orders_the_same_tier_by_fit_then_earliest_deadline():
    board = Board()
    low = board.opening("Acme", skills=("Python", "SQL", "Go"), deadline=NOW + timedelta(days=3))
    high = board.opening("Globex", skills=("Python", "PyTorch"), deadline=NOW + timedelta(days=9))
    later = board.opening("Initech", skills=("Python", "SQL"), deadline=NOW + timedelta(days=8))
    sooner = board.opening("Umbrella", skills=("Python", "SQL"), deadline=NOW + timedelta(days=4))
    assert [r.opening_memory_id for r in board.rank()] == [high, sooner, later, low]


def test_recommender_spreads_companies_within_a_tier():
    board = Board()
    acme_1 = board.opening("Acme", skills=("Python", "PyTorch"), source_ref="https://acme/1")
    acme_2 = board.opening("Acme", skills=("Python", "PyTorch", "SQL"), source_ref="https://acme/2")
    acme_3 = board.opening("Acme", skills=("Python", "SQL", "Go"), source_ref="https://acme/3")
    globex = board.opening("Globex", skills=("Python", "SQL", "Go"))
    assert [r.opening_memory_id for r in board.rank()] == [acme_1, globex, acme_2, acme_3]


def test_recommender_variety_never_lifts_an_ineligible_opening_above_an_eligible_one():
    board = Board()
    acme_1 = board.opening("Acme", source_ref="https://acme/1")
    acme_2 = board.opening("Acme", source_ref="https://acme/2")
    globex = board.opening("Globex", cutoff=9.9)
    assert [r.opening_memory_id for r in board.rank()] == [acme_1, acme_2, globex]


def test_recommender_never_returns_an_opening_whose_anchor_is_retired():
    board = Board()
    open_id = board.opening("Acme")
    closed = board.opening("Globex")
    board.set_status(closed, Status.RETIRED)
    assert [r.opening_memory_id for r in board.rank()] == [open_id]


def test_recommender_flags_an_opening_whose_belief_or_field_is_suspect_or_pending():
    board = Board()
    acme = board.opening("Acme")
    globex = board.opening("Globex")
    initech = board.opening("Initech")
    acme_fit = next(
        m
        for m in board.store.all_memories()
        if m.structured
        and m.structured.subject == f"opening:{acme}"
        and m.structured.attribute == "fit_score"
    )
    globex_deadline = next(
        m
        for m in board.store.all_memories()
        if m.structured
        and m.structured.subject == f"opening:{globex}"
        and m.structured.attribute == "deadline"
    )
    board.set_status(acme_fit.id, Status.SUSPECT)
    board.set_status(globex_deadline.id, Status.PENDING_USER)
    flags = {r.opening_memory_id: r.flagged for r in board.rank()}
    assert flags == {acme: True, globex: True, initech: False}


def test_recommender_leaves_out_openings_whose_deadline_has_passed():
    board = Board()
    board.opening("Acme", deadline=NOW - timedelta(hours=1))
    live = board.opening("Globex")
    assert [r.opening_memory_id for r in board.rank()] == [live]


def test_recommender_treats_a_missing_eligibility_belief_as_not_eligible():
    store, clock = InMemoryStore(), FakeClock(NOW - timedelta(days=1))
    runner = make_runner(store, clock)
    # No CGPA on the profile: eligibility cannot be derived for a cutoff-bearing opening.
    recorded = run(record_opening(store, clock, USER, parsed_acme(), runner))
    run(derive_for_opening(store, clock, runner, recorded.anchor.id))
    ranked = run(JobsRecommender(store).recommendations_for(USER, now=NOW))
    assert [r.eligible for r in ranked] == [False]
    # Fit is still computed: zero overlap, every required skill reported as missing.
    assert ranked[0].fit_score == 0.0
    assert all(reason.startswith("missing ") for reason in ranked[0].fit_reasons)
    assert len(ranked[0].fit_reasons) == 3


def test_recommender_fills_title_company_deadline_and_cited_fit_reasons():
    board = Board()
    acme = board.opening("Acme")
    (r,) = board.rank()
    assert r.opening_memory_id == acme
    assert r.title == "Software Development Engineer Intern"
    assert r.company == "Acme"
    assert r.deadline == NOW + timedelta(days=10)
    assert r.fit_score == round(2 / 3, 4)
    assert r.fit_reasons == (
        'has Python: JD says "Required: Python, PyTorch, SQL"; profile says "knows Python"',
        'has PyTorch: JD says "Required: Python, PyTorch, SQL"; profile says "knows PyTorch"',
        'missing SQL: JD says "Required: Python, PyTorch, SQL"',
    )


def test_recommender_respects_the_limit_after_ranking():
    board = Board()
    for company in ("Acme", "Globex", "Initech"):
        board.opening(company)
    assert len(board.rank(limit=2)) == 2
    assert len(board.rank()) == 3


def test_recommender_returns_nothing_for_a_user_with_no_openings():
    board = Board()
    assert board.rank() == []
    assert run(JobsRecommender(board.store).recommendations_for("someone-else", now=NOW)) == []


def test_recommender_keeps_a_flagged_deadline_for_ordering_and_display():
    board = Board()
    acme = board.opening("Acme", deadline=NOW + timedelta(hours=20))
    board.opening("Globex", skills=("Python", "PyTorch"))
    deadline = next(
        m
        for m in board.store.all_memories()
        if m.structured
        and m.structured.subject == f"opening:{acme}"
        and m.structured.attribute == "deadline"
    )
    board.set_status(deadline.id, Status.SUSPECT)
    first = board.rank()[0]
    assert first.opening_memory_id == acme  # still urgent
    assert first.deadline == NOW + timedelta(hours=20) and first.flagged


def test_recommender_is_not_flagged_by_a_belief_it_does_not_use():
    board = Board()
    acme = board.opening("Acme")
    reminder = next(
        m
        for m in board.store.all_memories()
        if m.structured
        and m.structured.subject == f"opening:{acme}"
        and m.structured.attribute == "remind_at"
    )
    board.set_status(reminder.id, Status.SUSPECT)
    assert [r.flagged for r in board.rank()] == [False]


def test_recommender_does_not_spread_openings_without_a_company_as_one_employer():
    board = Board()
    a = board.opening(None, skills=("Python", "PyTorch"), source_ref="https://x/1")
    b = board.opening(None, skills=("Python", "PyTorch", "SQL"), source_ref="https://x/2")
    c = board.opening("Globex", skills=("Python", "PyTorch", "SQL"))
    assert [r.opening_memory_id for r in board.rank()] == [a, b, c]
