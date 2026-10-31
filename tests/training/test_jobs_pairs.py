import json
from collections import Counter
from pathlib import Path

import pytest
from bench.linkpairs import PairMemory, Provenance, Split, read_pairs
from bench.scenario import load_scenario
from training.jobs_pairs import (
    NEGATIVE_RATIO,
    SOURCE_DIR,
    Claim,
    ClaimKind,
    PairKey,
    _Candidate,
    build_pairs,
    check,
    decontaminate,
    file_sha256,
    manifest_path,
    pairs_path,
    resolve,
)
from training.replay import scenario_snapshots

from ripple.domains.jobs.vocabulary import jobs_registry
from tests.training.support import pair


@pytest.fixture(scope="module")
def built():
    return build_pairs()


def _texts(snapshot, parent: str, dependent: str) -> tuple[str, str]:
    return snapshot.memories[parent].content, snapshot.memories[dependent].content


def test_jobs_pairs_checked_in_files_equal_a_fresh_generation(tmp_path: Path):
    assert check(pairs_path().parent, seed=20261031, ratio=NEGATIVE_RATIO, scratch=tmp_path) == []


def test_jobs_pairs_manifest_counts_and_hash_describe_the_file():
    manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    pairs = list(read_pairs(pairs_path()))
    assert manifest["file_sha256"] == file_sha256(pairs_path())
    assert manifest["counts"]["total"] == len(pairs)
    cells = Counter(f"{p.split}/{p.provenance}/{'link' if p.is_link else 'no_link'}" for p in pairs)
    assert manifest["counts"]["by_split_provenance_label"] == dict(cells)


def test_jobs_pairs_build_is_deterministic(built):
    again = build_pairs()
    assert [p.model_dump() for p in again.pairs] == [p.model_dump() for p in built.pairs]


def test_jobs_pairs_seed_moves_only_the_sampled_negatives(built):
    other = build_pairs(seed=7)
    positives = {p.pair_id for p in built.pairs if p.is_link}
    assert positives == {p.pair_id for p in other.pairs if p.is_link}
    assert {p.pair_id for p in built.pairs} != {p.pair_id for p in other.pairs}


def test_jobs_pairs_carry_both_generated_provenances_and_no_other(built):
    assert {p.provenance for p in built.pairs} == {Provenance.SCENARIO, Provenance.RULE}
    assert all(p.is_link for p in built.pairs if p.provenance is Provenance.RULE)


def test_jobs_pairs_keep_every_reversed_link_as_a_negative(built):
    by_texts = {(p.persona, p.parent.content, p.dependent.content): p for p in built.pairs}
    for positive in (p for p in built.pairs if p.is_link):
        reverse = by_texts.get(
            (positive.persona, positive.dependent.content, positive.parent.content)
        )
        assert reverse is not None and not reverse.is_link, positive.pair_id
        assert reverse.note == "reversed link"


def test_jobs_pairs_sample_negatives_at_the_ratio_to_positives(built):
    stats = built.stats["process"]
    assert isinstance(stats, dict)
    positives = (
        stats["rule_vs_scenario_agree"]
        + stats["rule_vs_scenario_missed"]
        + stats.get("rule_vs_scenario_disagree", 0)
        + stats.get("positives_rule_only", 0)
    )
    kept = stats["negatives_reversed_link"] + stats["negatives_sampled_other"]
    assert kept == NEGATIVE_RATIO * positives  # every v0 persona has enough negatives
    assert stats["negatives_available"] > kept


def test_snapshot_of_link_stays_on_the_resume_version_it_was_written_with():
    spec = load_scenario(SOURCE_DIR / "resume_update__p0_jay.yaml")
    seeded, after = scenario_snapshots(spec, jobs_registry())
    linked_before = {_texts(seeded, p, d): t for p, d, t in seeded.links}
    linked_after = {_texts(after, p, d): t for p, d, t in after.links}
    assert linked_before[("resume v1", "applied to initech with resume v1")] == "sent_with_resume"
    assert ("resume v2", "applied to initech with resume v1") not in linked_after
    # depends_on follows both endpoints to their new versions
    assert (
        linked_after[("resume v2", "highlight the new django work for hooli")] == "depends_on_fact"
    )


def test_snapshots_drop_retired_expired_and_forgotten_memories():
    registry = jobs_registry()
    offer = scenario_snapshots(load_scenario(SOURCE_DIR / "accepted_offer__p0_jay.yaml"), registry)
    assert "eligibility" in offer[0].memories and "eligibility" not in offer[-1].memories
    exams = scenario_snapshots(load_scenario(SOURCE_DIR / "exam_block__p0_jay.yaml"), registry)
    assert "exams" in exams[1].memories and "exams" not in exams[2].memories
    forget = scenario_snapshots(load_scenario(SOURCE_DIR / "forget_cgpa__p0_jay.yaml"), registry)
    assert {"cgpa", "eligibility"}.isdisjoint(forget[-1].memories)
    assert {"skill", "fit"} <= set(forget[-1].memories)


def test_every_test_split_scenario_link_of_the_seeded_state_is_a_positive(built):
    labelled = {
        (p.persona, p.parent.content, p.dependent.content): p.link_type for p in built.pairs
    }
    manifest = json.loads((SOURCE_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in (e for e in manifest["scenarios"] if e["split"] == "test"):
        seeded = scenario_snapshots(load_scenario(SOURCE_DIR / entry["file"]), jobs_registry())[0]
        for parent, dependent, link_type in seeded.links:
            key = (entry["persona"], *_texts(seeded, parent, dependent))
            assert labelled.get(key) == link_type, key


def test_resolve_drops_a_rule_label_that_a_scenario_says_is_no_link():
    memory = PairMemory(kind="derived", content="x")
    other = PairMemory(kind="derived", content="y")
    key = PairKey("p0_jay", "a", "b")
    templates = frozenset({"exam_block"})
    candidate = _Candidate(
        memory,
        other,
        [
            Claim(ClaimKind.NO_LINK, Provenance.SCENARIO, templates),
            Claim(ClaimKind.LINK, Provenance.RULE, templates, "eligibility_of", "r"),
        ],
    )
    stats: Counter[str] = Counter()
    positives, negatives = resolve({key: candidate}, stats)
    assert (positives, negatives) == ([], [])
    assert stats["dropped_rule_vs_closed_world"] == 1


def test_resolve_files_a_scenario_link_a_rule_also_derives_under_rule():
    key = PairKey("p0_jay", "a", "b")
    templates = frozenset({"exam_block"})
    candidate = _Candidate(
        PairMemory(kind="fact", content="x"),
        PairMemory(kind="derived", content="y"),
        [
            Claim(ClaimKind.LINK, Provenance.SCENARIO, templates, "eligibility_of"),
            Claim(
                ClaimKind.LINK,
                Provenance.RULE,
                templates,
                "eligibility_of",
                "eligibility_from_cgpa",
            ),
        ],
    )
    [positive], _ = resolve({key: candidate}, Counter())
    assert positive.provenance is Provenance.RULE
    assert positive.note == "rule:eligibility_from_cgpa; scenario agrees"


def _candidate(*claims: Claim) -> dict[PairKey, _Candidate]:
    memories = (PairMemory(kind="fact", content="x"), PairMemory(kind="derived", content="y"))
    return {PairKey("p0_jay", "a", "b"): _Candidate(*memories, list(claims))}


TEMPLATES = frozenset({"exam_block"})


def test_resolve_keeps_the_scenario_type_when_a_rule_derives_another():
    stats: Counter[str] = Counter()
    [positive], _ = resolve(
        _candidate(
            Claim(ClaimKind.LINK, Provenance.SCENARIO, TEMPLATES, "depends_on_fact"),
            Claim(ClaimKind.LINK, Provenance.RULE, TEMPLATES, "eligibility_of", "r"),
        ),
        stats,
    )
    assert (positive.link_type, positive.provenance) == ("depends_on_fact", Provenance.SCENARIO)
    assert stats["rule_vs_scenario_disagree"] == 1


def test_resolve_drops_a_pair_two_snapshots_label_link_and_no_link():
    stats: Counter[str] = Counter()
    result = resolve(
        _candidate(
            Claim(ClaimKind.LINK, Provenance.SCENARIO, TEMPLATES, "depends_on_fact"),
            Claim(ClaimKind.NO_LINK, Provenance.SCENARIO, TEMPLATES),
        ),
        stats,
    )
    assert result == ([], [])
    assert stats["dropped_conflicting_scenario_labels"] == 1


def test_resolve_never_makes_a_transitive_pair_a_negative():
    stats: Counter[str] = Counter()
    result = resolve(
        _candidate(
            Claim(ClaimKind.INDIRECT, Provenance.SCENARIO, TEMPLATES),
            Claim(ClaimKind.NO_LINK, Provenance.SCENARIO, TEMPLATES),
        ),
        stats,
    )
    assert result == ([], [])
    assert stats["excluded_indirect"] == 1


def test_decontaminate_drops_train_pairs_with_test_texts_and_never_test_pairs():
    test_pair = pair("t")
    train_twin = pair(
        "r",
        split=Split.TRAIN,
        persona="p0_jay",
        template="exam_block",
        link_type=None,
        parent=test_pair.dependent,
        dependent=test_pair.parent,
    )
    other = PairMemory(kind="derived", content="unrelated")
    train_clean = pair(
        "c", split=Split.TRAIN, persona="p0_jay", template="exam_block", dependent=other
    )
    stats: Counter[str] = Counter()
    kept = decontaminate([test_pair, train_twin, train_clean], stats)
    assert [p.pair_id for p in kept] == ["t", "c"]
    assert stats["train_dropped_text_in_test"] == 1
