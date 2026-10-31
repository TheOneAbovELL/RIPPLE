"""Offline doubles for the notify contracts: a scripted RecommendationSource, a static
UserDirectory and a Recommendation builder (tests.md: builders, not hand-written dicts).
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

from ripple.domains.jobs.vocabulary import Recommendation
from tests.fakes.clock import DEFAULT_START

CHAT = "chat-1001"


def recommendation(
    *,
    opening_id: str = "opening-1",
    title: str = "Software Engineer Intern",
    company: str = "Acme",
    eligible: bool = True,
    fit_score: float = 0.5,
    fit_reasons: Sequence[str] = ("JD line 3: 'Python, SQL' matches skills python, sql",),
    deadline: datetime | None = DEFAULT_START + timedelta(days=5),
    flagged: bool = False,
) -> Recommendation:
    return Recommendation(
        opening_memory_id=opening_id,
        title=title,
        company=company,
        eligible=eligible,
        fit_score=fit_score,
        fit_reasons=tuple(fit_reasons),
        deadline=deadline,
        flagged=flagged,
    )


class FakeRecommendationSource:
    """Returns a fixed ranking per user and records every call."""

    def __init__(self, by_user: dict[str, Sequence[Recommendation]] | None = None) -> None:
        self.by_user = dict(by_user or {})
        self.calls: list[tuple[str, datetime, int]] = []

    async def recommendations_for(
        self, user_id: str, *, now: datetime, limit: int = 10
    ) -> Sequence[Recommendation]:
        self.calls.append((user_id, now, limit))
        return list(self.by_user.get(user_id, ()))[:limit]


class FakeUserDirectory:
    def __init__(self, chats: dict[str, str | None]) -> None:
        self._chats = dict(chats)

    async def active_user_ids(self) -> Sequence[str]:
        return list(self._chats)

    async def telegram_chat_id(self, user_id: str) -> str | None:
        return self._chats.get(user_id)
