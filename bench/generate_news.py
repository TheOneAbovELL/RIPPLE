"""RippleBench v1, news track: seeded readers x story templates -> scenarios (ADR-0101).

    uv run python -m bench.generate_news            # writes bench/data/news_v1/
    uv run python -m bench.generate_news --check    # verifies the files match

SYNTHETIC. docs/04 asks for real stories that developed or were corrected; until the
author curates them (bench/data/news_v1/curated/, docs/learning/bench-v1.md) this track
uses invented places and incidents, and the manifest says so. The generated stories
exercise the same seven gold behaviours as v0, in news terms:

changed (figure_revised) · unchanged (other_story_develops) · temporary
(road_closure) · chain (attribution_retracted) · ask (conflicting_reports) · snapshot
(shared_note) · forget (forget_story).

A reader persona follows three stories. A claim is what outlets report; a summary
repeats claims; a briefing is what the reader is told; a shared note is what the
reader already passed on, and a correction never rewrites it (shared_from is
snapshot_of).
"""

import argparse
import random
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from bench.scenario import EventSpec, Expectation, MemorySpec, ScenarioSpec
from bench.tracks import (
    Template,
    Track,
    TrackSpec,
    ask,
    assemble_track,
    check_track,
    keep,
    retire,
    retired,
    update_to,
    valid,
    write_track,
)
from ripple.core.models import Status, StructuredFact
from ripple.domains.news.vocabulary import (
    DOMAIN,
    READER_SUBJECT,
    Kind,
    NewsLinkType,
    ReaderAttribute,
    StoryAttribute,
    story_subject,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "news_v1"
DEFAULT_SEED = 20261031
DEFAULT_PERSONAS = 5
GENERATOR_VERSION = 1
TRACK = "news_v1"

NAMES = ("kavya", "leo", "meera", "nikhil", "omar", "priya", "quinn", "ravi", "sana", "tara")
# Invented towns; any resemblance to a real place is not intended.
PLACES = ("riverton", "larkspur", "eastmere", "hollowbay", "kestrel", "duncliff", "ashgrove")
OUTLETS = ("the Courier", "Valley Wire", "the Ledger", "Metro Desk", "the Gazette")


@dataclass(frozen=True)
class Incident:
    kind: str  # what happened
    figure_noun: str  # what the reported number counts
    causes: tuple[str, ...]  # candidate attributions
    closure: str  # the temporary restriction it brings


INCIDENTS = (
    Incident(
        "bridge collapse", "people injured", ("the contractor", "flood damage"), "the bridge road"
    ),
    Incident(
        "factory fire", "workers evacuated", ("faulty wiring", "a gas leak"), "the industrial road"
    ),
    Incident(
        "data breach",
        "accounts exposed",
        ("a phishing campaign", "a misconfigured server"),
        "the council portal",
    ),
    Incident(
        "power outage",
        "homes without power",
        ("a substation fault", "storm damage"),
        "the ring road",
    ),
    Incident(
        "ferry accident",
        "passengers rescued",
        ("engine failure", "the operator"),
        "the harbour route",
    ),
    Incident(
        "warehouse flood", "tonnes of grain lost", ("a burst main", "heavy rain"), "the depot road"
    ),
)


@dataclass(frozen=True)
class Story:
    place: str
    incident: Incident
    figure: int
    cause: str
    outlet: str

    @property
    def alias(self) -> str:
        return f"{self.place}_claim"

    @property
    def title(self) -> str:
        return f"{self.place.capitalize()} {self.incident.kind}"

    def figure_claim(self, figure: int, outlet: str | None = None) -> str:
        return f"{outlet or self.outlet}: {figure} {self.incident.figure_noun} in the {self.title}"

    def summary(self, figure: int) -> str:
        return f"{self.title}: {figure} {self.incident.figure_noun}"


@dataclass(frozen=True)
class Reader:
    id: str
    name: str
    region: str
    stories: tuple[Story, ...]  # three distinct places and incidents

    def story(self, index: int) -> Story:
        return self.stories[index]


def make_personas(seed: int, count: int) -> list[Reader]:
    """Reader i depends on the seed and i only (as v0 personas do)."""
    if count > len(NAMES):
        raise ValueError(f"at most {len(NAMES)} personas; add names to NAMES for more")
    names = list(NAMES)
    random.Random(f"{seed}:names").shuffle(names)
    readers: list[Reader] = []
    for index, name in enumerate(names[:count]):
        rng = random.Random(f"{seed}:persona:{index}")
        places = rng.sample(PLACES, 3)
        incidents = rng.sample(INCIDENTS, 3)
        stories = tuple(
            Story(
                place=place,
                incident=incident,
                figure=rng.randint(8, 240),
                cause=rng.choice(incident.causes),
                outlet=rng.choice(OUTLETS),
            )
            for place, incident in zip(places, incidents, strict=True)
        )
        readers.append(Reader(id=f"n{index}_{name}", name=name, region=places[0], stories=stories))
    return readers


# ---- helpers ------------------------------------------------------------------------------


def _story_fact(story: Story, attribute: StoryAttribute, value: str | int) -> StructuredFact:
    return StructuredFact(subject=story_subject(story.place), attribute=attribute, value=value)


def _figure_memory(story: Story) -> MemorySpec:
    return MemorySpec(
        kind=Kind.CLAIM,
        content=story.figure_claim(story.figure),
        structured=_story_fact(story, StoryAttribute.FIGURE, story.figure),
    )


def _summary_memory(story: Story) -> MemorySpec:
    return MemorySpec(kind=Kind.SUMMARY, content=story.summary(story.figure))


def _revised(story: Story, rng: random.Random) -> int:
    """A revision large enough to matter and never equal to the first figure."""
    delta = max(2, story.figure // rng.choice((3, 4, 5)))
    return story.figure + delta if rng.random() < 0.5 else max(1, story.figure - delta)


# ---- templates ----------------------------------------------------------------------------


def figure_revised(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """changed: an outlet revises the figure; summary and briefing re-derive."""
    story, other = reader.story(0), reader.story(1)
    new_figure = _revised(story, rng)
    briefing = f"today: {story.summary(story.figure)}; {other.summary(other.figure)}"
    new_briefing = f"today: {story.summary(new_figure)}; {other.summary(other.figure)}"
    return ScenarioSpec(
        name="",
        description=(
            f"{story.outlet} revises the {story.title} figure; {reader.name}'s briefing follows."
        ),
        memories={
            "claim": _figure_memory(story),
            "summary": _summary_memory(story),
            "other_claim": _figure_memory(other),
            "other_summary": _summary_memory(other),
            "briefing": MemorySpec(kind=Kind.BRIEFING, content=briefing),
        },
        links=[
            ["claim", "summary", NewsLinkType.SUMMARISES],
            ["other_claim", "other_summary", NewsLinkType.SUMMARISES],
            ["summary", "briefing", NewsLinkType.BRIEFING_FROM],
            ["other_summary", "briefing", NewsLinkType.BRIEFING_FROM],
        ],
        resolutions={
            "summary": [update_to("claim", story.summary(new_figure))],
            "briefing": [update_to("claim", new_briefing)],
        },
        events=[
            EventSpec(
                update="claim",
                content=story.figure_claim(new_figure),
                structured=_story_fact(story, StoryAttribute.FIGURE, new_figure),
                expect={
                    "claim": retired(1),
                    "claim@latest": valid(2, story.figure_claim(new_figure)),
                    "summary@latest": valid(2, story.summary(new_figure)),
                    "briefing@latest": valid(2, new_briefing),
                    "other_summary": valid(),
                    "other_claim": valid(),
                },
            )
        ],
    )


def other_story_develops(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """unchanged: one story resolves; the other story's summary and analysis stay put."""
    moved, other = reader.story(1), reader.story(2)
    verdict = rng.choice(("repairs approved", "inquiry opened", "compensation agreed"))
    return ScenarioSpec(
        name="",
        description=(
            f"The {moved.title} story moves on ({verdict}); nothing about {other.title} changes."
        ),
        memories={
            "outcome": MemorySpec(
                kind=Kind.CLAIM,
                content=f"{moved.title}: no decision yet",
                structured=_story_fact(moved, StoryAttribute.OUTCOME, "pending"),
            ),
            "summary": MemorySpec(kind=Kind.SUMMARY, content=f"{moved.title}: awaiting a decision"),
            "other_claim": _figure_memory(other),
            "other_summary": _summary_memory(other),
            "other_analysis": MemorySpec(
                kind=Kind.DERIVED, content=f"{other.title} is the larger story this week"
            ),
        },
        links=[
            ["outcome", "summary", NewsLinkType.SUMMARISES],
            ["other_claim", "other_summary", NewsLinkType.SUMMARISES],
            ["other_claim", "other_analysis", NewsLinkType.INFERRED_FROM],
        ],
        resolutions={"summary": [update_to("outcome", f"{moved.title}: {verdict}")]},
        events=[
            EventSpec(
                update="outcome",
                content=f"{moved.title}: {verdict}",
                structured=_story_fact(moved, StoryAttribute.OUTCOME, verdict),
                expect={
                    "summary@latest": valid(2, f"{moved.title}: {verdict}"),
                    "other_summary": valid(),
                    "other_analysis": valid(),
                    "other_claim": valid(),
                },
            )
        ],
    )


def road_closure(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """temporary: a closure tied to a story lasts N days, then expires."""
    story = reader.story(0)
    days = rng.randint(3, 21)
    return ScenarioSpec(
        name="",
        description=f"{story.incident.closure} near {story.place} closes for {days} days.",
        memories={
            "region": MemorySpec(
                kind=Kind.FACT,
                content=f"reader lives in {reader.region}",
                structured=StructuredFact(
                    subject=READER_SUBJECT, attribute=ReaderAttribute.REGION, value=reader.region
                ),
            ),
            "travel_advice": MemorySpec(
                kind=Kind.DERIVED, content=f"no travel disruption expected around {reader.region}"
            ),
            "briefing": MemorySpec(
                kind=Kind.BRIEFING, content=f"local briefing for {reader.region}: travel section"
            ),
        },
        links=[
            ["region", "travel_advice", "depends_on_fact"],
            ["travel_advice", "briefing", NewsLinkType.BRIEFING_FROM],
        ],
        resolutions={
            "travel_advice": [update_to("closure", "travel advice recomputed around the closure")],
            "briefing": [keep("closure", "the travel section reads the advice live")],
        },
        events=[
            EventSpec(
                new="closure",
                kind=Kind.CLAIM,
                content=f"{story.incident.closure} closed for {days} days after the {story.title}",
                valid_to_days=days,
                structured=_story_fact(story, StoryAttribute.CLOSURE, "closed"),
                links=[["closure", "travel_advice", "depends_on_time_period"]],
                expect={
                    "closure": Expectation(status=Status.VALID),
                    "travel_advice@latest": valid(2),
                    "region": valid(),
                    "briefing": valid(),
                },
            ),
            EventSpec(
                advance_days=days + 1,
                expect={
                    "closure": retired(),
                    "travel_advice@latest": valid(3),
                    "region": valid(),
                    "briefing": valid(),
                },
            ),
        ],
    )


def attribution_retracted(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """chain: blame is withdrawn; analysis -> follow-up -> briefing item, three hops."""
    story, other = reader.story(1), reader.story(2)
    cause = story.cause
    reason = rng.choice(("the investigation is still open", "new evidence emerged"))
    return ScenarioSpec(
        name="",
        description=(
            f"Officials withdraw the blame on {cause} for the {story.title}; a chain unwinds."
        ),
        memories={
            "attribution": MemorySpec(
                kind=Kind.CLAIM,
                content=f"officials blame {cause} for the {story.title}",
                structured=_story_fact(story, StoryAttribute.ATTRIBUTION, cause),
            ),
            "analysis": MemorySpec(kind=Kind.DERIVED, content=f"{cause} caused the {story.title}"),
            "follow_up": MemorySpec(
                kind=Kind.DERIVED, content=f"follow inspections linked to {cause}"
            ),
            "briefing_item": MemorySpec(
                kind=Kind.BRIEFING, content=f"briefing: {cause} blamed for the {story.title}"
            ),
            "other_claim": _figure_memory(other),
            "other_summary": _summary_memory(other),
        },
        links=[
            ["attribution", "analysis", NewsLinkType.INFERRED_FROM],
            ["analysis", "follow_up", NewsLinkType.INFERRED_FROM],
            ["follow_up", "briefing_item", NewsLinkType.BRIEFING_FROM],
            ["other_claim", "other_summary", NewsLinkType.SUMMARISES],
        ],
        resolutions={
            "analysis": [update_to("attribution", f"cause of the {story.title} not established")],
            "follow_up": [retire("attribution")],
            "briefing_item": [retire("attribution")],
        },
        events=[
            EventSpec(
                update="attribution",
                content=f"officials withdraw the blame on {cause}: {reason}",
                structured=_story_fact(story, StoryAttribute.ATTRIBUTION, "unknown"),
                expect={
                    "analysis@latest": valid(2),
                    "follow_up": retired(),
                    "briefing_item": retired(),
                    "other_summary": valid(),
                    "other_claim": valid(),
                },
            )
        ],
    )


def conflicting_reports(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """ask: a second outlet reports a different figure; the reader decides.

    The second report is written as a new version of the figure claim (the latest
    reported figure), so the first outlet's figure is retired at once; only the summary
    waits for the reader. A curated story where both reports must stay live would add
    the second outlet's claim as a `new` memory instead.
    """
    story = reader.story(0)
    second = next(o for o in OUTLETS if o != story.outlet)
    conflicting = _revised(story, rng)
    reply = rng.choice(("still_holds", "no_longer_holds", "correction"))
    answer = EventSpec(answer="summary", reply=reply)
    briefing_after = f"briefing: {story.title}, figure disputed"
    if reply == "still_holds":
        answer = answer.model_copy(update={"expect": {"summary": valid(), "briefing": valid()}})
    elif reply == "no_longer_holds":
        answer = answer.model_copy(
            update={
                "expect": {
                    "summary": retired(),
                    "briefing@latest": valid(2, briefing_after),
                }
            }
        )
    else:
        corrected = story.summary(conflicting)
        answer = answer.model_copy(
            update={
                "content": corrected,
                "expect": {
                    "summary@latest": valid(2, corrected),
                    "briefing@latest": valid(2, briefing_after),
                },
            }
        )
    return ScenarioSpec(
        name="",
        description=f"{second} contradicts {story.outlet} on the {story.title} figure ({reply}).",
        memories={
            "claim": _figure_memory(story),
            "summary": _summary_memory(story),
            "briefing": MemorySpec(
                kind=Kind.BRIEFING, content=f"briefing: {story.summary(story.figure)}"
            ),
        },
        links=[
            ["claim", "summary", NewsLinkType.SUMMARISES],
            ["summary", "briefing", NewsLinkType.BRIEFING_FROM],
        ],
        resolutions={
            "summary": [
                ask(
                    "claim",
                    f"{story.outlet} says {story.figure}, {second} says {conflicting}; "
                    "which should your summary use?",
                    "two outlets disagree and neither has corrected",
                )
            ],
            "briefing": [update_to("summary", briefing_after)],
        },
        events=[
            EventSpec(
                update="claim",
                content=story.figure_claim(conflicting, second),
                structured=_story_fact(story, StoryAttribute.FIGURE, conflicting),
                expect={
                    "summary": Expectation(status=Status.PENDING_USER),
                    "briefing": Expectation(status=Status.SUSPECT, version=1),
                },
            ),
            answer,
        ],
    )


def shared_note(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """snapshot: a correction re-summarises but never rewrites what was already shared."""
    story = reader.story(2)
    new_figure = _revised(story, rng)
    shared = f"shared with the study group: {story.summary(story.figure)}"
    return ScenarioSpec(
        name="",
        description=f"{reader.name} shared the {story.title} figure before it was corrected.",
        memories={
            "claim": _figure_memory(story),
            "shared": MemorySpec(kind=Kind.SHARED, content=shared),
            "summary": _summary_memory(story),
        },
        links=[
            ["claim", "shared", NewsLinkType.SHARED_FROM],
            ["claim", "summary", NewsLinkType.SUMMARISES],
        ],
        resolutions={
            "summary": [update_to("claim", story.summary(new_figure))],
            "shared": [keep("claim", "a shared note is a record of what was said then")],
        },
        events=[
            EventSpec(
                update="claim",
                content=story.figure_claim(new_figure),
                structured=_story_fact(story, StoryAttribute.FIGURE, new_figure),
                expect={
                    "claim": retired(),
                    "shared": valid(1, shared),
                    "summary@latest": valid(2, story.summary(new_figure)),
                },
            )
        ],
    )


def forget_story(reader: Reader, rng: random.Random) -> ScenarioSpec:
    """forget: deleting a claim removes every version and every summary built on it."""
    story, other = reader.story(0), reader.story(1)
    new_figure = _revised(story, rng)
    return ScenarioSpec(
        name="",
        description=f"{reader.name} asks to forget the {story.title} after one revision.",
        memories={
            "claim": _figure_memory(story),
            "summary": _summary_memory(story),
            "other_claim": _figure_memory(other),
            "other_summary": _summary_memory(other),
        },
        links=[
            ["claim", "summary", NewsLinkType.SUMMARISES],
            ["other_claim", "other_summary", NewsLinkType.SUMMARISES],
        ],
        resolutions={"summary": [update_to("claim", story.summary(new_figure))]},
        events=[
            EventSpec(
                update="claim",
                content=story.figure_claim(new_figure),
                structured=_story_fact(story, StoryAttribute.FIGURE, new_figure),
                expect={"summary@latest": Expectation(version=2)},
            ),
            EventSpec(
                forget="claim",
                expect={
                    "claim": Expectation(deleted=True),
                    "summary": Expectation(deleted=True),
                    "other_claim": Expectation(status=Status.VALID),
                    "other_summary": Expectation(status=Status.VALID),
                },
            ),
        ],
    )


TEMPLATES: Mapping[str, tuple[str, Template]] = {
    "figure_revised": ("changed", figure_revised),
    "other_story_develops": ("unchanged", other_story_develops),
    "road_closure": ("temporary", road_closure),
    "attribution_retracted": ("chain", attribution_retracted),
    "conflicting_reports": ("ask", conflicting_reports),
    "shared_note": ("snapshot", shared_note),
    "forget_story": ("forget", forget_story),
}

SPEC = TrackSpec(
    track=TRACK,
    domain=DOMAIN,
    module="bench.generate_news",
    version=GENERATOR_VERSION,
    templates=TEMPLATES,
)


def generate(seed: int = DEFAULT_SEED, personas: int = DEFAULT_PERSONAS) -> Track:
    return assemble_track(SPEC, make_personas(seed, personas), seed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the RippleBench v1 news track")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--personas", type=int, default=DEFAULT_PERSONAS)
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    args = parser.parse_args(argv)
    track = generate(args.seed, args.personas)
    if args.check:
        problems = check_track(track, args.out)
        for problem in problems:
            print(f"  {problem}")
        print(f"{args.out}: {'in sync' if not problems else f'{len(problems)} problem(s)'}")
        return 0 if not problems else 1
    write_track(track, args.out)
    print(f"wrote {len(track.scenarios)} scenarios + manifest.json to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
