"""Jobs rule resolvers (ADR-0031): pure, deterministic, cite their parents."""

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from ripple.core.models import DecisionAction, Memory, Status
from ripple.core.resolver import ResolutionContext, ResolverChain
from ripple.domains.jobs.beliefs import (
    compute_criteria,
    compute_eligibility,
    compute_fit,
    compute_reminder,
)
from ripple.domains.jobs.rules import (
    CriteriaRule,
    EligibilityRule,
    FitRule,
    OpeningFieldRule,
    ReminderRule,
    jobs_rules,
)
from ripple.domains.jobs.schemas import OpeningView, ProfileView, anchor_structured
from ripple.domains.jobs.vocabulary import (
    PROFILE_SUBJECT,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
    opening_subject,
)
from tests.builders import derived, fact, memory
from tests.domains.jobs.helpers import RefusingResolver, run

ANCHOR = memory(kind=Kind.OPENING, content="SDE Intern at Acme", created_by="scout")
SUBJECT = opening_subject(ANCHOR.id)


def opening_fact(attribute: str, value: str | int | float | bool, content: str) -> Memory:
    return fact(SUBJECT, attribute, value, content=content, created_by="scout")


def profile(attribute: str, value: str | int | float | bool) -> Memory:
    return fact(PROFILE_SUBJECT, attribute, value)


CUTOFF = opening_fact(OpeningAttribute.CGPA_CUTOFF, 7.8, "Minimum CGPA: 7.8")
REQ_BATCH = opening_fact(OpeningAttribute.BATCH, 2027, "Eligible batch: 2027")
REQ_PY = opening_fact(OpeningAttribute.REQUIRED_SKILL, "Python", "Required: Python, SQL")
REQ_SQL = opening_fact(OpeningAttribute.REQUIRED_SKILL, "SQL", "Required: Python, SQL")
DEADLINE = opening_fact(
    OpeningAttribute.DEADLINE, "2026-11-05T09:00:00+00:00", "Apply by 2026-11-05T09:00:00+00:00"
)
CGPA_76 = profile(ProfileAttribute.CGPA, 7.6)
CGPA_79 = profile(ProfileAttribute.CGPA, 7.9)
BATCH_2027 = profile(ProfileAttribute.BATCH, 2027)
SKILL_PY = profile(ProfileAttribute.SKILL, "python")


def belief_memory(parents: Sequence[Memory], compute, **overrides) -> Memory:
    """The derived memory exactly as derivation would have written it from `parents`."""
    view = OpeningView.from_memories(ANCHOR, parents)
    belief = compute(ProfileView.from_memories(parents), view)
    assert belief is not None
    return derived(belief.content, structured=belief.structured, kind=belief.kind, **overrides)


def context(memory: Memory, parents: Sequence[Memory], trigger: Memory | None = None):
    return ResolutionContext(
        trigger=trigger or (parents[-1] if parents else memory),
        memory=memory,
        parents=parents,
        wave=1,
    )


# ---- EligibilityRule ------------------------------------------------------------------


def test_eligibility_rule_keeps_when_recomputation_matches_and_cites_parents():
    parents = [ANCHOR, CGPA_76, CUTOFF, BATCH_2027, REQ_BATCH]
    eligibility = belief_memory(parents, compute_eligibility)
    resolution = EligibilityRule().resolve(context(eligibility, parents))
    assert resolution is not None and resolution.action is DecisionAction.KEEP
    assert set(resolution.evidence_refs) == {m.id for m in parents}


def test_eligibility_rule_updates_when_the_cgpa_crosses_the_cutoff():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    assert eligibility.structured is not None and eligibility.structured.value is False
    resolution = EligibilityRule().resolve(context(eligibility, [ANCHOR, CGPA_79, CUTOFF]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == "eligible for SDE Intern at Acme: CGPA 7.9 >= cutoff 7.8"
    assert resolution.new_structured is not None and resolution.new_structured.value is True
    assert set(resolution.evidence_refs) == {ANCHOR.id, CGPA_79.id, CUTOFF.id}


def test_eligibility_rule_treats_an_equal_cgpa_as_eligible():
    cgpa = profile(ProfileAttribute.CGPA, 7.8)
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    resolution = EligibilityRule().resolve(context(eligibility, [ANCHOR, cgpa, CUTOFF]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == "eligible for SDE Intern at Acme: CGPA 7.8 >= cutoff 7.8"


def test_eligibility_rule_batch_mismatch_makes_it_not_eligible_despite_the_cgpa():
    parents_ok = [ANCHOR, CGPA_79, CUTOFF, BATCH_2027, REQ_BATCH]
    eligibility = belief_memory(parents_ok, compute_eligibility)
    batch_2028 = profile(ProfileAttribute.BATCH, 2028)
    resolution = EligibilityRule().resolve(
        context(eligibility, [ANCHOR, CGPA_79, CUTOFF, batch_2028, REQ_BATCH])
    )
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == (
        "not eligible for SDE Intern at Acme: CGPA 7.9 >= cutoff 7.8; "
        "batch 2028 is not required batch 2027"
    )


def test_eligibility_rule_returns_none_when_the_profile_cgpa_is_missing():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    assert EligibilityRule().resolve(context(eligibility, [ANCHOR, CUTOFF])) is None


def test_eligibility_rule_returns_none_when_the_cgpa_parent_is_retired_without_successor():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    gone = CGPA_76.model_copy(update={"status": Status.RETIRED})
    assert EligibilityRule().resolve(context(eligibility, [ANCHOR, gone, CUTOFF])) is None


def test_eligibility_rule_handles_a_cutoff_that_was_removed_from_the_opening():
    # The cutoff fact retired (JD re-parsed without one): no constraint is left to check.
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    gone = CUTOFF.model_copy(update={"status": Status.RETIRED})
    resolution = EligibilityRule().resolve(context(eligibility, [ANCHOR, CGPA_76, gone]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert "no CGPA cutoff or batch restriction stated" in (resolution.new_content or "")


def test_eligibility_rule_retires_when_the_opening_anchor_is_retired():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    closed = ANCHOR.model_copy(update={"status": Status.RETIRED})
    resolution = EligibilityRule().resolve(context(eligibility, [closed, CGPA_76, CUTOFF]))
    assert resolution is not None and resolution.action is DecisionAction.RETIRE
    assert resolution.evidence_refs == (closed.id,)


def test_eligibility_rule_ignores_memories_it_does_not_own():
    parents = [ANCHOR, CGPA_76, CUTOFF]
    fit = belief_memory([ANCHOR, REQ_PY, SKILL_PY], compute_fit)
    assert EligibilityRule().resolve(context(fit, parents)) is None
    assert EligibilityRule().resolve(context(CGPA_76, [ANCHOR])) is None
    assert EligibilityRule().resolve(context(derived("free text"), parents)) is None


def test_eligibility_rule_returns_none_without_its_anchor_among_the_parents():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    assert EligibilityRule().resolve(context(eligibility, [CGPA_76, CUTOFF])) is None


# ---- FitRule ----------------------------------------------------------------------


def test_fit_rule_updates_the_score_when_a_required_skill_is_learned():
    fit = belief_memory([ANCHOR, REQ_PY, REQ_SQL, SKILL_PY], compute_fit)
    assert fit.structured is not None and fit.structured.value == 0.5
    sql = profile(ProfileAttribute.SKILL, "SQL")
    resolution = FitRule().resolve(context(fit, [ANCHOR, REQ_PY, REQ_SQL, SKILL_PY, sql]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_structured is not None and resolution.new_structured.value == 1.0
    assert '- has SQL: JD says "Required: Python, SQL"; profile says "student skill is SQL"' in (
        resolution.new_content or ""
    )
    assert set(resolution.evidence_refs) == {ANCHOR.id, REQ_PY.id, REQ_SQL.id, SKILL_PY.id, sql.id}


def test_fit_rule_keeps_when_an_unrelated_skill_is_added():
    fit = belief_memory([ANCHOR, REQ_PY, REQ_SQL, SKILL_PY], compute_fit)
    rust = profile(ProfileAttribute.SKILL, "Rust")
    resolution = FitRule().resolve(context(fit, [ANCHOR, REQ_PY, REQ_SQL, SKILL_PY, rust]))
    assert resolution is not None and resolution.action is DecisionAction.KEEP


def test_fit_rule_returns_none_when_the_required_skills_are_gone():
    fit = belief_memory([ANCHOR, REQ_PY, SKILL_PY], compute_fit)
    assert FitRule().resolve(context(fit, [ANCHOR, SKILL_PY])) is None


# ---- ReminderRule -------------------------------------------------------------------


def test_reminder_rule_updates_when_the_deadline_moves():
    reminder = belief_memory([ANCHOR, DEADLINE], lambda _p, o: compute_reminder(o))
    moved = opening_fact(
        OpeningAttribute.DEADLINE, "2026-11-19T09:00:00+00:00", "Apply by 2026-11-19T09:00:00+00:00"
    )
    resolution = ReminderRule().resolve(context(reminder, [ANCHOR, moved]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_structured is not None
    assert datetime.fromisoformat(str(resolution.new_structured.value)) == datetime(
        2026, 11, 17, 9, 0, tzinfo=UTC
    )
    assert resolution.new_valid_to is None
    assert set(resolution.evidence_refs) == {ANCHOR.id, moved.id}


def test_reminder_rule_keeps_when_the_deadline_is_unchanged():
    reminder = belief_memory([ANCHOR, DEADLINE], lambda _p, o: compute_reminder(o))
    resolution = ReminderRule().resolve(context(reminder, [ANCHOR, DEADLINE]))
    assert resolution is not None and resolution.action is DecisionAction.KEEP


def test_reminder_rule_returns_none_without_a_deadline_parent():
    reminder = belief_memory([ANCHOR, DEADLINE], lambda _p, o: compute_reminder(o))
    assert ReminderRule().resolve(context(reminder, [ANCHOR])) is None


# ---- CriteriaRule -------------------------------------------------------------------


def _criteria(parents: Sequence[Memory]) -> Memory:
    belief = compute_criteria(ProfileView.from_memories(parents))
    assert belief is not None
    return derived(belief.content, structured=belief.structured, kind=belief.kind)


def test_criteria_rule_updates_the_cutoff_clause_when_the_cgpa_changes():
    criteria = _criteria([CGPA_76, BATCH_2027])
    resolution = CriteriaRule().resolve(context(criteria, [CGPA_79, BATCH_2027]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == "search openings with cgpa_cutoff <= 7.9; batch 2027"
    assert set(resolution.evidence_refs) == {CGPA_79.id, BATCH_2027.id}


def test_criteria_rule_returns_none_when_every_profile_parent_is_gone():
    criteria = _criteria([CGPA_76])
    gone = CGPA_76.model_copy(update={"status": Status.RETIRED})
    assert CriteriaRule().resolve(context(criteria, [gone])) is None
    assert CriteriaRule().resolve(context(CGPA_76, [])) is None


# ---- OpeningFieldRule ----------------------------------------------------------------


def test_opening_field_rule_keeps_a_field_while_its_anchor_is_valid():
    resolution = OpeningFieldRule().resolve(context(CUTOFF, [ANCHOR]))
    assert resolution is not None and resolution.action is DecisionAction.KEEP
    assert resolution.evidence_refs == (ANCHOR.id,)


def test_opening_field_rule_retires_a_field_when_its_anchor_is_retired():
    closed = ANCHOR.model_copy(update={"status": Status.RETIRED})
    resolution = OpeningFieldRule().resolve(context(CUTOFF, [closed]))
    assert resolution is not None and resolution.action is DecisionAction.RETIRE


def test_opening_field_rule_ignores_profile_facts_and_beliefs():
    assert OpeningFieldRule().resolve(context(CGPA_76, [ANCHOR])) is None
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    assert OpeningFieldRule().resolve(context(eligibility, [ANCHOR, CGPA_76, CUTOFF])) is None


def test_opening_field_rule_returns_none_when_the_anchor_is_pending_user():
    pending = ANCHOR.model_copy(update={"status": Status.PENDING_USER})
    assert OpeningFieldRule().resolve(context(CUTOFF, [pending])) is None


# ---- chain ---------------------------------------------------------------------------


def test_jobs_rules_has_one_rule_per_belief_kind_in_a_fixed_order():
    assert [type(r) for r in jobs_rules()] == [
        OpeningFieldRule,
        EligibilityRule,
        FitRule,
        ReminderRule,
        CriteriaRule,
    ]


def test_resolver_chain_with_jobs_rules_never_reaches_the_fallback_for_a_rule_case():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    fallback = RefusingResolver()
    chain = ResolverChain(jobs_rules(), fallback=fallback)  # type: ignore[arg-type]
    resolution = run(chain.resolve(context(eligibility, [ANCHOR, CGPA_79, CUTOFF])))
    assert resolution.action is DecisionAction.UPDATE
    assert fallback.contexts == []


def test_resolver_chain_falls_back_when_no_jobs_rule_applies():
    fallback = RefusingResolver()
    chain = ResolverChain(jobs_rules(), fallback=fallback)  # type: ignore[arg-type]
    with pytest.raises(AssertionError):
        run(chain.resolve(context(derived("Acme is a good place to work"), [ANCHOR])))
    assert len(fallback.contexts) == 1


def _owned_contexts():
    """One context per rule that the rule itself decides (never None)."""
    reminder = belief_memory([ANCHOR, DEADLINE], lambda _p, o: compute_reminder(o))
    return [
        (OpeningFieldRule(), context(CUTOFF, [ANCHOR])),
        (
            EligibilityRule(),
            context(
                belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility),
                [ANCHOR, CGPA_79, CUTOFF],
            ),
        ),
        (
            FitRule(),
            context(
                belief_memory([ANCHOR, REQ_PY, SKILL_PY], compute_fit), [ANCHOR, REQ_PY, SKILL_PY]
            ),
        ),
        (ReminderRule(), context(reminder, [ANCHOR, DEADLINE])),
        (CriteriaRule(), context(_criteria([CGPA_76]), [CGPA_79])),
    ]


@pytest.mark.parametrize(("rule", "ctx"), _owned_contexts(), ids=lambda x: type(x).__name__)
def test_jobs_rules_are_deterministic_across_calls(rule, ctx):
    first = rule.resolve(ctx)
    assert first is not None
    assert first == rule.resolve(ctx)


@pytest.mark.parametrize("status", [Status.SUSPECT, Status.PENDING_USER])
def test_eligibility_rule_defers_when_the_profile_parent_is_in_doubt(status):
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    doubtful = CGPA_79.model_copy(update={"status": status})
    assert EligibilityRule().resolve(context(eligibility, [ANCHOR, doubtful, CUTOFF])) is None


def test_eligibility_rule_defers_when_an_opening_field_is_pending_user():
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    pending = CUTOFF.model_copy(update={"status": Status.PENDING_USER})
    assert EligibilityRule().resolve(context(eligibility, [ANCHOR, CGPA_79, pending])) is None


def test_eligibility_rule_reads_a_field_that_is_suspect_only_in_its_anchors_wave():
    # Wave 1 of an anchor edit holds the fields and the beliefs together; the field is
    # SUSPECT but kept by OpeningFieldRule in the same wave, so its value stands.
    eligibility = belief_memory([ANCHOR, CGPA_76, CUTOFF], compute_eligibility)
    in_wave = CUTOFF.model_copy(update={"status": Status.SUSPECT})
    resolution = EligibilityRule().resolve(context(eligibility, [ANCHOR, CGPA_79, in_wave]))
    assert resolution is not None and resolution.action is DecisionAction.UPDATE
    assert resolution.new_content == "eligible for SDE Intern at Acme: CGPA 7.9 >= cutoff 7.8"


@pytest.mark.parametrize("status", [Status.SUSPECT, Status.PENDING_USER])
def test_fit_rule_defers_when_a_skill_parent_is_in_doubt(status):
    fit = belief_memory([ANCHOR, REQ_PY, REQ_SQL, SKILL_PY], compute_fit)
    doubtful = SKILL_PY.model_copy(update={"status": status})
    assert FitRule().resolve(context(fit, [ANCHOR, REQ_PY, REQ_SQL, doubtful])) is None


def test_criteria_rule_defers_when_a_profile_parent_is_in_doubt():
    criteria = _criteria([CGPA_76, BATCH_2027])
    doubtful = BATCH_2027.model_copy(update={"status": Status.PENDING_USER})
    assert CriteriaRule().resolve(context(criteria, [CGPA_79, doubtful])) is None


def test_opening_field_rule_follows_a_new_version_of_the_anchor():
    keyed = ANCHOR.model_copy(update={"structured": anchor_structured(ANCHOR.id, "https://acme")})
    v2 = keyed.model_copy(update={"id": "anchor-v2", "version": 2, "supersedes_id": ANCHOR.id})
    resolution = OpeningFieldRule().resolve(context(CUTOFF, [v2]))
    assert resolution is not None and resolution.action is DecisionAction.KEEP
