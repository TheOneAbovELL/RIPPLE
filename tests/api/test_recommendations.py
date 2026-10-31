"""GET /recommendations: read-only pass-through of the RecommendationSource."""

import asyncio
from datetime import timedelta

from ripple.domains.jobs.vocabulary import Recommendation
from tests.api.fakes import ScriptedRecommendations
from tests.api.harness import Harness, body
from tests.fakes.clock import DEFAULT_START


def _recommendation(title: str, flagged: bool = False) -> Recommendation:
    return Recommendation(
        opening_memory_id=f"opening-{title}",
        title=title,
        company="Acme",
        eligible=True,
        fit_score=0.8,
        fit_reasons=("asks for Python; you list Python",),
        deadline=DEFAULT_START + timedelta(days=3),
        flagged=flagged,
    )


def test_recommendations_are_returned_for_the_user_at_the_clock_time():
    source = ScriptedRecommendations(
        _recommendation("SDE Intern"), _recommendation("Data Intern", True)
    )
    h = Harness.build(recommendations=source)

    async def run():
        user, headers = await h.user()
        async with h.client() as c:
            default = await c.get("/recommendations", headers=headers)
            one = await c.get("/recommendations", params={"limit": 1}, headers=headers)
            too_many = await c.get("/recommendations", params={"limit": 99}, headers=headers)
        return user, default, one, too_many

    user, default, one, too_many = asyncio.run(run())
    out = body(default)["recommendations"]
    assert [(r["title"], r["flagged"]) for r in out] == [
        ("SDE Intern", False),
        ("Data Intern", True),
    ]
    assert out[0]["fit_reasons"] == ["asks for Python; you list Python"]
    assert len(body(one)["recommendations"]) == 1
    assert too_many.status_code == 422
    assert source.calls[0] == (user.id, DEFAULT_START, 10)
