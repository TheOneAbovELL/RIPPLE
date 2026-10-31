from ripple.core.models import Status
from ripple.domains.jobs.openings import record_opening
from ripple.domains.jobs.sources.dedupe import (
    InMemoryScoutLedger,
    OpeningDeduplicator,
    canonical_of_source_ref,
    scout_source_ref,
)
from ripple.domains.jobs.vocabulary import OpeningAttribute, ParsedField, ParsedOpening, TextSpan
from tests.builders import fact
from tests.domains.jobs.helpers import USER, make_runner, parsed_acme, run
from tests.fakes.clock import FakeClock
from tests.fakes.store import InMemoryStore

CANONICAL = "https://careers.acme.example/jobs/42"


def _dedupe(store: InMemoryStore | None = None):
    store = store or InMemoryStore()
    ledger = InMemoryScoutLedger()
    return OpeningDeduplicator(store, ledger), store, ledger


def test_scout_source_ref_round_trips_the_canonical_url():
    ref = scout_source_ref("acme", CANONICAL)
    assert ref == f"scout:acme:{CANONICAL}"
    assert canonical_of_source_ref(ref) == CANONICAL
    assert canonical_of_source_ref("paste:1") is None
    assert canonical_of_source_ref(None) is None


def test_known_url_is_false_for_a_fresh_user_and_true_once_remembered():
    dedupe, _, _ = _dedupe()
    assert run(dedupe.known_url(USER, CANONICAL)) is False
    run(dedupe.remember(USER, CANONICAL, FakeClock().now()))
    assert run(dedupe.known_url(USER, CANONICAL)) is True
    assert run(dedupe.known_url("someone-else", CANONICAL)) is False  # per user


def test_known_url_finds_an_opening_the_scout_recorded_before_even_with_an_empty_ledger():
    store, clock = InMemoryStore(), FakeClock()
    parsed = parsed_acme(source_ref=scout_source_ref("acme", CANONICAL))
    run(record_opening(store, clock, USER, parsed, make_runner(store, clock)))
    dedupe, _, _ = _dedupe(store)  # a new process: the ledger is empty
    assert run(dedupe.known_url(USER, CANONICAL)) is True


def test_known_url_still_counts_a_retired_opening_as_known():
    store, clock = InMemoryStore(), FakeClock()
    parsed = parsed_acme(source_ref=scout_source_ref("acme", CANONICAL))
    recorded = run(record_opening(store, clock, USER, parsed, make_runner(store, clock)))

    async def retire():
        async with store.transaction() as tx:
            await tx.replace_memory(recorded.anchor.model_copy(update={"status": Status.RETIRED}))

    run(retire())
    dedupe, _, _ = _dedupe(store)
    assert run(dedupe.known_url(USER, CANONICAL)) is True


def test_known_url_matches_a_source_url_field_of_a_pasted_opening():
    store, clock = InMemoryStore(), FakeClock()
    raw = "Apply at https://Careers.Acme.Example/jobs/42/?utm_source=x today"
    url_text = "https://Careers.Acme.Example/jobs/42/?utm_source=x"
    start = raw.index(url_text)
    parsed = ParsedOpening(
        source_ref="paste:1",
        raw_text=raw,
        fields=(
            ParsedField(OpeningAttribute.TITLE, "SDE Intern", TextSpan(0, 5, "Apply")),
            ParsedField(
                OpeningAttribute.SOURCE_URL,
                url_text,
                TextSpan(start, start + len(url_text), url_text),
            ),
        ),
        summary="SDE Intern",
    )
    run(record_opening(store, clock, USER, parsed, make_runner(store, clock)))
    dedupe, _, _ = _dedupe(store)
    assert run(dedupe.known_url(USER, CANONICAL)) is True


def test_known_fingerprint_matches_the_title_and_company_of_a_held_opening():
    store, clock = InMemoryStore(), FakeClock()
    run(record_opening(store, clock, USER, parsed_acme(), make_runner(store, clock)))
    dedupe, _, _ = _dedupe(store)
    assert run(
        dedupe.known_fingerprint(USER, "ACME Pvt Ltd", "software development engineer intern")
    )
    assert run(dedupe.known_fingerprint(USER, "Acme", "Data Scientist")) is False


def test_known_fingerprint_ignores_facts_that_are_not_opening_fields():
    store = InMemoryStore()

    async def write():
        async with store.transaction() as tx:
            await tx.add_memory(fact("student", "skill", "Python"))

    run(write())
    dedupe, _, _ = _dedupe(store)
    assert run(dedupe.known_fingerprint(USER, "Acme", "Python")) is False


def test_remember_marks_the_url_and_the_fingerprint_in_the_ledger():
    dedupe, _, ledger = _dedupe()
    at = FakeClock().now()
    run(dedupe.remember(USER, CANONICAL, at, company="Acme", title="SDE Intern"))
    assert set(ledger.entries) == {
        (USER, f"url:{CANONICAL}"),
        (USER, "fp:acme|sde intern"),
    }
    assert run(dedupe.known_fingerprint(USER, "Acme", "SDE Intern")) is True
