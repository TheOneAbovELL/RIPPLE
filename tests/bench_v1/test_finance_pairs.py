"""Finance C5 pairs (ADR-0102): test split only, labels follow the scenario links."""

from collections import Counter

import pytest
from bench.generate_finance import (
    DATA_DIR,
    PAIRS_FILE,
    TRACK,
    generate,
    pairs_text,
    scenario_pairs,
    track_pairs,
)
from bench.linkpairs import Provenance, Split, read_pairs
from bench.tracks import load_track

from ripple.core.models import LinkClass
from ripple.domains.finance.vocabulary import DOMAIN, finance_registry


@pytest.fixture(scope="module")
def scenarios():
    return load_track(DATA_DIR)


@pytest.fixture(scope="module")
def checked_in():
    return list(read_pairs(DATA_DIR / PAIRS_FILE))


def test_every_pair_is_test_split_scenario_labelled_finance(checked_in):
    assert checked_in
    assert {(p.split, p.track, p.domain, p.provenance) for p in checked_in} == {
        (Split.TEST, TRACK, DOMAIN, Provenance.SCENARIO)
    }


def test_the_checked_in_pairs_equal_a_fresh_generation():
    fresh = generate()  # from the seed, not from the checked-in scenarios
    assert pairs_text(fresh.scenarios) == (DATA_DIR / PAIRS_FILE).read_text(encoding="utf-8")


def test_each_text_pair_appears_once_with_one_label(checked_in):
    keys = [(p.parent.model_dump_json(), p.dependent.model_dump_json()) for p in checked_in]
    assert len(set(keys)) == len(keys)
    assert len({p.pair_id for p in checked_in}) == len(checked_in)


def test_the_file_keeps_every_distinct_link_of_the_scenarios(checked_in, scenarios):
    every = [p for entry, spec in scenarios for p in scenario_pairs(entry, spec)]
    assert {(p.parent, p.dependent, p.link_type) for p in every} == {
        (p.parent, p.dependent, p.link_type) for p in checked_in
    }


def test_two_copies_of_a_text_pair_with_different_labels_are_refused(scenarios):
    entry, spec = scenarios[0]
    parent, dependent, _ = spec.links[0]
    clash = spec.model_copy(
        update={"name": "clash", "links": [[parent, dependent, "alert_for"], *spec.links[1:]]}
    )
    with pytest.raises(ValueError, match="same texts but labels"):
        track_pairs([(entry, spec), (entry, clash)])


def test_every_scenario_link_is_exactly_one_positive_with_its_class(scenarios):
    registry = finance_registry()
    for entry, spec in scenarios:
        links = [*spec.links, *(link for event in spec.events for link in event.links)]
        positives = [p for p in scenario_pairs(entry, spec) if p.is_link]
        assert Counter((p.link_type, p.link_class) for p in positives) == Counter(
            (link[2], registry.class_of(link[2])) for link in links
        ), entry.name


def test_snapshot_links_are_labelled_snapshot_of(scenarios):
    journal = [
        p
        for entry, spec in scenarios
        if entry.template == "journal_entry"
        for p in scenario_pairs(entry, spec)
        if p.is_link and p.dependent.kind == "journal"
    ]
    assert journal and {p.link_class for p in journal} == {LinkClass.SNAPSHOT_OF}


def test_an_indirect_dependency_is_left_unlabelled(scenarios):
    # ceo_departure: leader -> assumption -> thesis -> alert. leader -> thesis is real
    # but indirect, so neither a link nor a "no link" label is trustworthy.
    entry, spec = next((e, s) for e, s in scenarios if e.template == "ceo_departure")
    ids = {p.pair_id for p in scenario_pairs(entry, spec)}
    assert f"{TRACK}:{spec.name}:leader>assumption" in ids
    assert f"{TRACK}:{spec.name}:leader>thesis" not in ids
    assert f"{TRACK}:{spec.name}:leader>alert" not in ids


def test_a_reversed_edge_is_a_negative_marked_as_such(scenarios):
    entry, spec = next((e, s) for e, s in scenarios if e.template == "ceo_departure")
    pairs = {p.pair_id: p for p in scenario_pairs(entry, spec)}
    reverse = pairs[f"{TRACK}:{spec.name}:assumption>leader"]
    assert not reverse.is_link and reverse.note == "reversed edge"
    unrelated = pairs[f"{TRACK}:{spec.name}:other_margin>thesis"]
    assert not unrelated.is_link and unrelated.note is None


def test_memories_added_by_an_event_take_part_in_pairs(scenarios):
    entry, spec = next((e, s) for e, s in scenarios if e.template == "trading_halt")
    halt = [p for p in scenario_pairs(entry, spec) if p.pair_id.endswith(":halt>review")]
    assert len(halt) == 1 and halt[0].link_type == "depends_on_time_period"
