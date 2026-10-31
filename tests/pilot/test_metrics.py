"""Pilot metrics over a constructed week with hand-derived answers (ADR-0106)."""

from ripple.pilot.metrics import (
    MIN_PUBLISHABLE_COHORT,
    TBD,
    positive_pairs,
    question_usefulness,
    questions_asked,
    saved_or_applied_share,
    week_metrics,
)
from ripple.pilot.weeks import parse_week
from ripple.storage.feedback import FeedbackKind
from tests.pilot.support import (
    ACCOUNTS,
    ASHA,
    CANONICAL,
    DELIVERIES,
    EVENTS,
    EXPECTED_ACTIVE,
    EXPECTED_ASKED,
    EXPECTED_FEEDBACK_COUNTS,
    EXPECTED_REACTIONS_WITHOUT_ALERT,
    EXPECTED_SHARE,
    EXPECTED_USEFULNESS,
    FEEDBACK,
    NOTE_SENTINEL,
    WEEK,
    alert,
    at,
    digest,
    fb,
)

ALL_EVENTS = [e for events in EVENTS.values() for e in events]
NEXT_WEEK = parse_week("2026-W46")


def metrics():
    return week_metrics(WEEK, ACCOUNTS, DELIVERIES, FEEDBACK, ALL_EVENTS, CANONICAL)


def test_week_metrics_saved_or_applied_share_matches_hand_count():
    share = metrics()["pilot_metrics"]["saved_or_applied_share"]
    assert (share["numerator"], share["denominator"], share["value"]) == EXPECTED_SHARE


def test_week_metrics_question_usefulness_matches_hand_count():
    usefulness = metrics()["pilot_metrics"]["question_usefulness"]
    assert (
        usefulness["numerator"],
        usefulness["denominator"],
        usefulness["value"],
    ) == EXPECTED_USEFULNESS


def test_week_metrics_counts_activity_inside_the_week_only():
    assert metrics()["activity"] == {
        "digests_sent": 5,
        "alerts_sent": {"deadline_soon": 2, "high_fit": 3},
        "feedback": EXPECTED_FEEDBACK_COUNTS,
        "recommendation_reactions_without_alert": EXPECTED_REACTIONS_WITHOUT_ALERT,
        "questions_asked": EXPECTED_ASKED,
    }


def test_week_metrics_cohort_counts_answers_as_activity_and_flags_small_weeks():
    assert metrics()["cohort"] == {
        "accounts": 5,
        "active_users": EXPECTED_ACTIVE,
        "publishable": False,
        "min_publishable_cohort": MIN_PUBLISHABLE_COHORT,
    }


def test_week_metrics_reports_unsupported_metrics_as_tbd_with_reason():
    pilot = metrics()["pilot_metrics"]
    for name in (
        "days_earlier_than_self_discovery",
        "stale_recommendation_rate",
        "self_reported_trust",
    ):
        assert pilot[name]["value"] == TBD
        assert pilot[name]["reason"]


def test_week_metrics_names_every_docs04_pilot_metric():
    # docs/04 "Pilot metrics": the five, in its order.
    assert list(metrics()["pilot_metrics"]) == [
        "saved_or_applied_share",
        "days_earlier_than_self_discovery",
        "stale_recommendation_rate",
        "question_usefulness",
        "self_reported_trust",
    ]


def test_week_metrics_contains_no_user_id_or_note():
    text = repr(metrics())
    for user_id in ACCOUNTS:
        assert repr(user_id) not in text
    assert NOTE_SENTINEL not in text


def test_week_metrics_empty_week_reports_tbd_not_zero():
    empty = week_metrics(parse_week("2027-W01"), ACCOUNTS, [], [], [])
    pilot = empty["pilot_metrics"]
    assert pilot["saved_or_applied_share"]["value"] == TBD
    assert pilot["question_usefulness"]["value"] == TBD
    assert empty["activity"]["digests_sent"] == 0


def test_saved_or_applied_share_ignores_digests():
    rate = saved_or_applied_share(WEEK, [digest(ASHA, 0)], [], {})
    assert (rate.numerator, rate.denominator) == (0, 0)


def test_saved_or_applied_share_excludes_reactions_without_alert():
    rate = saved_or_applied_share(
        WEEK, [], [fb(ASHA, "self-pasted", FeedbackKind.SAVED, at(1))], {}
    )
    assert (rate.numerator, rate.denominator) == (0, 0)


def test_saved_or_applied_share_counts_a_save_from_an_earlier_week():
    rate = saved_or_applied_share(
        NEXT_WEEK,
        [alert(ASHA, "o1", NEXT_WEEK.start)],
        [fb(ASHA, "o1", FeedbackKind.SAVED, at(1))],
        {},
    )
    assert (rate.numerator, rate.denominator) == (1, 1)


def test_saved_or_applied_share_joins_versions_of_one_opening():
    rate = saved_or_applied_share(
        WEEK, [alert(ASHA, "o1", at(0))], [fb(ASHA, "o1v2", FeedbackKind.SAVED, at(1))], CANONICAL
    )
    assert (rate.numerator, rate.denominator) == (1, 1)


def test_positive_pairs_saved_then_dismissed_is_not_positive():
    rows = [fb(ASHA, "o", FeedbackKind.SAVED, at(0)), fb(ASHA, "o", FeedbackKind.DISMISSED, at(1))]
    assert positive_pairs(WEEK, rows, {}) == set()


def test_positive_pairs_applied_survives_a_later_dismissal():
    rows = [
        fb(ASHA, "o", FeedbackKind.APPLIED, at(0)),
        fb(ASHA, "o", FeedbackKind.DISMISSED, at(1)),
    ]
    assert positive_pairs(WEEK, rows, {}) == {(ASHA, "o")}


def test_question_usefulness_first_rating_wins():
    # The store keeps the first row per kind, so useful → not useful → useful leaves
    # two rows; the first is the one rule that the third tap cannot contradict.
    rate = question_usefulness(
        WEEK,
        [
            fb(ASHA, "q", FeedbackKind.QUESTION_USEFUL, at(0)),
            fb(ASHA, "q", FeedbackKind.QUESTION_NOT_USEFUL, at(1)),
        ],
    )
    assert (rate.numerator, rate.denominator) == (1, 1)


def test_question_usefulness_skips_questions_first_rated_in_an_earlier_week():
    rate = question_usefulness(
        NEXT_WEEK,
        [
            fb(ASHA, "q", FeedbackKind.QUESTION_USEFUL, at(0)),
            fb(ASHA, "q", FeedbackKind.QUESTION_NOT_USEFUL, NEXT_WEEK.start),
        ],
    )
    assert (rate.numerator, rate.denominator) == (0, 0)


def test_questions_asked_ignores_events_outside_the_week():
    assert questions_asked(parse_week("2026-W44"), ALL_EVENTS) == 1  # bina's Sunday ask
