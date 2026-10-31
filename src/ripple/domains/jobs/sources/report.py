"""What a scouting run produced, per source and per user (ADR-0072).

Kept beside the sources rather than in the agent so the agents package needs no
stdlib time module (tests/agents/test_invariants_agents.py allows it a short import
list) and so the worker job can type its return value without importing the agent.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

SCOUT_LEASE_TTL = timedelta(minutes=45)  # longer than the cron slot's 30-minute timeout


def scout_lease_key(user_id: str) -> str:
    return f"scout:{user_id}"


@dataclass
class SourceCount:
    candidates: int = 0  # items the listing offered this run (capped)
    new: int = 0  # openings recorded
    duplicates: int = 0  # already held or already seen
    filtered: int = 0  # parsed, but outside the criteria or not a JD
    refused: int = 0  # we may not fetch it: off-host link, robots, login (ADR-0008)
    errors: int = 0  # fetch, parse or write failures (details in ScoutReport.errors)


@dataclass(frozen=True)
class ScoutError:
    source_id: str
    url: str | None
    message: str


@dataclass
class ScoutReport:
    user_id: str
    started_at: datetime
    criteria_content: str | None = None  # the criteria memory's content, when one was used
    per_source: dict[str, SourceCount] = field(default_factory=dict)
    errors: list[ScoutError] = field(default_factory=list)
    recorded_anchor_ids: list[str] = field(default_factory=list)
    finished_at: datetime | None = None

    @property
    def candidates(self) -> int:
        return sum(c.candidates for c in self.per_source.values())

    @property
    def new(self) -> int:
        return sum(c.new for c in self.per_source.values())

    @property
    def duplicates(self) -> int:
        return sum(c.duplicates for c in self.per_source.values())

    @property
    def filtered(self) -> int:
        return sum(c.filtered for c in self.per_source.values())

    @property
    def refused(self) -> int:
        return sum(c.refused for c in self.per_source.values())


@dataclass
class ScoutRunReport:
    """What the scout_run job returns: one ScoutReport per user it reached."""

    by_user: dict[str, ScoutReport] = field(default_factory=dict)
    skipped_leased: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
