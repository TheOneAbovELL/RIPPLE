from datetime import timedelta

import pytest

from ripple.notify.contracts import AlertKind, Thresholds
from ripple.notify.render import (
    DIGEST_MAX_LENGTH,
    Alert,
    alert_kinds,
    alerts_for,
    render_alert,
    render_digest,
)
from tests.fakes.clock import DEFAULT_START
from tests.notify.fakes import recommendation

NOW = DEFAULT_START


def test_render_digest_lists_title_company_eligibility_fit_reasons_and_deadline():
    text = render_digest(
        [
            recommendation(
                fit_score=0.82,
                fit_reasons=("JD line 3: 'Python' matches skill python", "CGPA 7.6 >= cutoff 7.0"),
                deadline=NOW + timedelta(hours=49, minutes=50),
            )
        ],
        NOW,
    )
    assert text.splitlines() == [
        "Ripple digest for 2026-10-19",
        "",
        "1. Software Engineer Intern at Acme",
        "   Eligible: yes",
        "   Fit: 82%",
        "   - JD line 3: 'Python' matches skill python",
        "   - CGPA 7.6 >= cutoff 7.0",
        "   Deadline: 2026-10-21 10:50 UTC (49h left)",
    ]


@pytest.mark.parametrize(
    ("score", "shown"), [(0.57, "57%"), (0.29, "29%"), (0.58, "58%"), (1.0, "100%")]
)
def test_render_digest_fit_percent_matches_the_source_score_despite_float_noise(score, shown):
    assert f"   Fit: {shown}" in render_digest([recommendation(fit_score=score)], NOW)


def test_render_digest_marks_flagged_items_unconfirmed_and_ineligible_items_no():
    text = render_digest([recommendation(flagged=True, eligible=False)], NOW)
    assert "1. Software Engineer Intern at Acme [unconfirmed]" in text
    assert "   Eligible: no" in text


def test_render_digest_never_invents_a_deadline_when_none_is_known():
    text = render_digest([recommendation(deadline=None)], NOW)
    assert "   Deadline: not stated" in text
    assert "left" not in text


def test_render_digest_says_passed_for_an_expired_deadline():
    text = render_digest([recommendation(deadline=NOW - timedelta(hours=1))], NOW)
    assert "(passed)" in text


def test_render_digest_floors_hours_left_instead_of_rounding_up():
    text = render_digest([recommendation(deadline=NOW + timedelta(hours=1, minutes=59))], NOW)
    assert "(1h left)" in text


def test_render_digest_with_nothing_to_show_says_so():
    assert render_digest([], NOW) == "Ripple digest for 2026-10-19\n\nNo openings to show today."


def test_render_digest_numbers_items_in_ranking_order():
    text = render_digest(
        [
            recommendation(title="First", opening_id="a"),
            recommendation(title="Second", opening_id="b"),
        ],
        NOW,
    )
    assert text.index("1. First") < text.index("2. Second")


def test_render_digest_drops_trailing_items_to_stay_under_the_message_limit():
    long_reasons = tuple(f"JD line {i}: " + "x" * 200 for i in range(5))
    ranked = [
        recommendation(opening_id=str(i), title=f"Opening {i}", fit_reasons=long_reasons)
        for i in range(10)
    ]
    assert len(render_digest(ranked, NOW, max_length=10**6)) > DIGEST_MAX_LENGTH

    text = render_digest(ranked, NOW)

    assert len(text) <= DIGEST_MAX_LENGTH
    assert "1. Opening 0 at Acme" in text
    assert "10. Opening 9" not in text
    assert text.endswith("more not shown (message limit).")
    shown = text.count(" at Acme")
    assert f"{10 - shown} more not shown" in text


def test_render_digest_without_omissions_has_no_omission_line():
    assert "not shown" not in render_digest([recommendation()], NOW)


# ---- alert thresholds ----------------------------------------------------------------


def test_alert_kinds_high_fit_at_threshold():
    far = NOW + timedelta(days=10)
    kinds = alert_kinds(recommendation(fit_score=0.8, deadline=far), NOW, Thresholds(fit_alert=0.8))
    assert kinds == (AlertKind.HIGH_FIT,)


def test_alert_kinds_no_high_fit_just_below_threshold():
    far = NOW + timedelta(days=10)
    assert (
        alert_kinds(recommendation(fit_score=0.79, deadline=far), NOW, Thresholds(fit_alert=0.8))
        == ()
    )


def test_alert_kinds_deadline_at_the_48h_edge_is_inside_the_window():
    kinds = alert_kinds(recommendation(deadline=NOW + timedelta(hours=48)), NOW, Thresholds())
    assert kinds == (AlertKind.DEADLINE_SOON,)


def test_alert_kinds_deadline_just_beyond_48h_is_outside_the_window():
    deadline = NOW + timedelta(hours=48, seconds=1)
    assert alert_kinds(recommendation(deadline=deadline), NOW, Thresholds()) == ()


def test_alert_kinds_past_or_unknown_deadline_never_alerts():
    assert alert_kinds(recommendation(deadline=NOW - timedelta(seconds=1)), NOW, Thresholds()) == ()
    assert alert_kinds(recommendation(deadline=None), NOW, Thresholds()) == ()


def test_alert_kinds_reports_both_reasons_when_both_hold():
    kinds = alert_kinds(
        recommendation(fit_score=0.9, deadline=NOW + timedelta(hours=3)), NOW, Thresholds()
    )
    assert kinds == (AlertKind.HIGH_FIT, AlertKind.DEADLINE_SOON)


def test_alert_kinds_never_alert_on_flagged_openings():
    urgent = recommendation(fit_score=0.95, deadline=NOW + timedelta(hours=1), flagged=True)
    assert alert_kinds(urgent, NOW, Thresholds()) == ()


def test_alert_kinds_never_alert_on_ineligible_openings():
    urgent = recommendation(fit_score=0.95, deadline=NOW + timedelta(hours=1), eligible=False)
    assert alert_kinds(urgent, NOW, Thresholds()) == ()


def test_alerts_for_keeps_only_qualifying_openings_in_ranking_order():
    hot = recommendation(opening_id="hot", fit_score=0.9, deadline=NOW + timedelta(hours=30))
    cold = recommendation(opening_id="cold", fit_score=0.3, deadline=NOW + timedelta(days=9))
    assert alerts_for([cold, hot], NOW, Thresholds()) == [
        Alert(hot, (AlertKind.HIGH_FIT, AlertKind.DEADLINE_SOON))
    ]


def test_render_alert_explains_why_now_per_item():
    hot = recommendation(title="Hot", fit_score=0.9, deadline=NOW + timedelta(hours=30))
    text = render_alert([Alert(hot, (AlertKind.HIGH_FIT, AlertKind.DEADLINE_SOON))], NOW)
    assert text.startswith("Ripple alert\n\n1. Hot at Acme")
    assert "   Why now: high fit (90%); deadline in 30h" in text


def test_render_alert_lists_only_the_kinds_it_is_given():
    hot = recommendation(title="Hot", fit_score=0.9, deadline=NOW + timedelta(hours=30))
    text = render_alert([Alert(hot, (AlertKind.DEADLINE_SOON,))], NOW)
    assert "   Why now: deadline in 30h" in text
    assert "high fit" not in text


def test_render_alert_is_empty_when_nothing_qualifies():
    assert render_alert([], NOW) == ""
