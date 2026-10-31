"""RippleBench v1, finance track (test only, H4): seeded theses whose assumptions break.

    uv run python -m bench.generate_finance            # writes bench/data/finance_v1/
    uv run python -m bench.generate_finance --check    # verifies the files match

SYNTHETIC and TEST ONLY (docs/04: "Finance track (test only)"; ADR-0101). Every
scenario is `test` with `held_out = "domain"`: the link finder never sees finance data
while training, so this track measures transfer (H4). Companies, tickers and people
are invented; the theses are a user's own notes, not advice (docs/00, "What we do NOT
claim"). Seven families, as in v0 and news:

changed (guidance_cut) · unchanged (peer_margin) · temporary (trading_halt) · chain
(ceo_departure) · ask (rate_edge) · snapshot (journal_entry) · forget (forget_holding).

Besides the scenarios the generator writes `pairs.jsonl`: labelled link pairs in the C5
format (bench/linkpairs.py), every one `Split.TEST` (ADR-0102), for WS-14's harness.
"""

import argparse
import random
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from bench.generate import ManifestEntry
from bench.linkpairs import LabelledPair, PairMemory, Provenance, Split, write_pairs
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
from ripple.domains.finance.vocabulary import (
    DOMAIN,
    MACRO_SUBJECT,
    CompanyAttribute,
    FinanceLinkType,
    Kind,
    MacroAttribute,
    company_subject,
    finance_registry,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "finance_v1"
PAIRS_FILE = "pairs.jsonl"
DEFAULT_SEED = 20261031
DEFAULT_PERSONAS = 5
GENERATOR_VERSION = 1
TRACK = "finance_v1"

NAMES = ("uma", "vikram", "wen", "xavier", "yamini", "zoya", "arjun", "bela", "chen", "divya")
# Invented companies and people; any resemblance to a real one is not intended.
COMPANIES = (
    ("ZNTH", "Zenith Looms", "textiles"),
    ("KRVL", "Korval Freight", "logistics"),
    ("MPLW", "Maplewood Pantry", "packaged food"),
    ("ORBX", "Orbix Fabworks", "chip packaging"),
    ("TALN", "Talon Railcar", "rolling stock"),
    ("VSTR", "Vestra Diagnostics", "lab testing"),
    ("QUIL", "Quillon Studios", "streaming"),
)
LEADERS = (
    "R. Okonjo",
    "M. Lindqvist",
    "S. Varadan",
    "J. Castellano",
    "T. Nakahara",
    "A. Mensforth",
)


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    margin: int  # operating margin, percent
    guidance: int  # revenue growth guidance, percent
    leader: str

    @property
    def subject(self) -> str:
        return company_subject(self.ticker)


@dataclass(frozen=True)
class Investor:
    id: str
    name: str
    policy_rate: float  # the (fictional) policy rate the theses were written under
    companies: tuple[Company, ...]

    def company(self, index: int) -> Company:
        return self.companies[index]


def make_personas(seed: int, count: int) -> list[Investor]:
    """Investor i depends on the seed and i only (as v0 personas do)."""
    if count > len(NAMES):
        raise ValueError(f"at most {len(NAMES)} personas; add names to NAMES for more")
    names = list(NAMES)
    random.Random(f"{seed}:names").shuffle(names)
    investors: list[Investor] = []
    for index, name in enumerate(names[:count]):
        rng = random.Random(f"{seed}:persona:{index}")
        picked = rng.sample(COMPANIES, 3)
        leaders = rng.sample(LEADERS, 3)
        companies = tuple(
            Company(
                ticker=ticker,
                name=company_name,
                sector=sector,
                margin=rng.randint(14, 32),
                guidance=rng.randint(8, 25),
                leader=leader,
            )
            for (ticker, company_name, sector), leader in zip(picked, leaders, strict=True)
        )
        investors.append(
            Investor(
                id=f"f{index}_{name}",
                name=name,
                policy_rate=round(rng.uniform(4.5, 5.6), 1),
                companies=companies,
            )
        )
    return investors


# ---- helpers ------------------------------------------------------------------------------


def _company_fact(
    company: Company, attribute: CompanyAttribute, value: str | int
) -> StructuredFact:
    return StructuredFact(subject=company.subject, attribute=attribute, value=value)


def _margin_memory(company: Company, margin: int | None = None) -> MemorySpec:
    value = company.margin if margin is None else margin
    return MemorySpec(
        kind=Kind.FACT,
        content=f"{company.ticker} operating margin is {value}%",
        structured=_company_fact(company, CompanyAttribute.MARGIN, value),
    )


def _thesis(company: Company) -> str:
    return (
        f"{company.ticker} thesis: {company.sector} leader "
        f"compounding on margins near {company.margin}%"
    )


def _floor(company: Company) -> int:
    return company.margin - 4


# ---- templates ----------------------------------------------------------------------------


def guidance_cut(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """changed: guidance is cut; the estimate and the thesis built on it re-derive."""
    company, other = investor.company(0), investor.company(1)
    new_guidance = max(1, company.guidance - rng.randint(5, 8))
    estimate = f"{company.ticker} revenue grows about {company.guidance}% next year"
    new_estimate = f"{company.ticker} revenue grows about {new_guidance}% next year"
    new_thesis = f"{company.ticker} thesis weakened: growth guided down to {new_guidance}%"
    return ScenarioSpec(
        name="",
        description=f"{company.name} cuts guidance; {investor.name}'s estimate and thesis follow.",
        memories={
            "guidance": MemorySpec(
                kind=Kind.FACT,
                content=f"{company.ticker} guides {company.guidance}% revenue growth",
                structured=_company_fact(company, CompanyAttribute.GUIDANCE, company.guidance),
            ),
            "estimate": MemorySpec(kind=Kind.DERIVED, content=estimate),
            "thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(company)),
            "other_margin": _margin_memory(other),
            "other_thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(other)),
        },
        links=[
            ["guidance", "estimate", FinanceLinkType.ESTIMATE_FROM],
            ["guidance", "thesis", FinanceLinkType.PREMISE_OF],
            ["other_margin", "other_thesis", FinanceLinkType.PREMISE_OF],
        ],
        resolutions={
            "estimate": [update_to("guidance", new_estimate)],
            "thesis": [update_to("guidance", new_thesis)],
        },
        events=[
            EventSpec(
                update="guidance",
                content=f"{company.ticker} guides {new_guidance}% revenue growth",
                structured=_company_fact(company, CompanyAttribute.GUIDANCE, new_guidance),
                expect={
                    "guidance": retired(1),
                    "guidance@latest": valid(2),
                    "estimate@latest": valid(2, new_estimate),
                    "thesis@latest": valid(2, new_thesis),
                    "other_thesis": valid(),
                    "other_margin": valid(),
                },
            )
        ],
    )


def peer_margin(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """unchanged: one company's margin moves; the other company's thesis and alert stay."""
    moved, other = investor.company(1), investor.company(2)
    new_margin = moved.margin + rng.choice((-3, -2, 2, 3))
    new_thesis = f"{moved.ticker} thesis: margins now {new_margin}%, re-checked"
    return ScenarioSpec(
        name="",
        description=f"{moved.name} reports a new margin; nothing about {other.name} changes.",
        memories={
            "margin": _margin_memory(moved),
            "thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(moved)),
            "other_margin": _margin_memory(other),
            "other_thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(other)),
            "other_alert": MemorySpec(
                kind=Kind.ALERT,
                content=f"look again if {other.ticker} margin falls below {_floor(other)}%",
            ),
        },
        links=[
            ["margin", "thesis", FinanceLinkType.PREMISE_OF],
            ["other_margin", "other_thesis", FinanceLinkType.PREMISE_OF],
            ["other_thesis", "other_alert", FinanceLinkType.ALERT_FOR],
        ],
        resolutions={"thesis": [update_to("margin", new_thesis)]},
        events=[
            EventSpec(
                update="margin",
                content=f"{moved.ticker} operating margin is {new_margin}%",
                structured=_company_fact(moved, CompanyAttribute.MARGIN, new_margin),
                expect={
                    "thesis@latest": valid(2, new_thesis),
                    "other_thesis": valid(),
                    "other_alert": valid(),
                    "other_margin": valid(),
                },
            )
        ],
    )


def trading_halt(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """temporary: trading is halted for N days, then resumes; nothing permanent.

    review -> plan uses the generic depends_on_fact on purpose: generic types are part
    of every registry, so the H4 pairs include one generic positive per persona.
    """
    company = investor.company(0)
    days = rng.randint(2, 15)
    return ScenarioSpec(
        name="",
        description=f"{company.name} is halted for {days} days pending a filing.",
        memories={
            "trading": MemorySpec(
                kind=Kind.FACT,
                content=f"{company.ticker} trades normally",
                structured=_company_fact(company, CompanyAttribute.TRADING_STATUS, "trading"),
            ),
            "review": MemorySpec(kind=Kind.ALERT, content=f"review {company.ticker} every Friday"),
            "plan": MemorySpec(
                kind=Kind.DERIVED, content=f"next {company.ticker} review covers the margin trend"
            ),
        },
        links=[
            ["trading", "review", FinanceLinkType.ALERT_FOR],
            ["review", "plan", "depends_on_fact"],
        ],
        resolutions={
            "review": [update_to("halt", "weekly review rescheduled around the halt")],
            "plan": [keep("halt", "the review topic does not depend on trading days")],
        },
        events=[
            EventSpec(
                new="halt",
                kind=Kind.FACT,
                content=f"{company.ticker} trading halted for {days} days pending a filing",
                valid_to_days=days,
                structured=_company_fact(company, CompanyAttribute.TRADING_STATUS, "halted"),
                links=[["halt", "review", "depends_on_time_period"]],
                expect={
                    "halt": Expectation(status=Status.VALID),
                    "review@latest": valid(2),
                    "trading": valid(),
                    "plan": valid(),
                },
            ),
            EventSpec(
                advance_days=days + 1,
                expect={
                    "halt": retired(),
                    "review@latest": valid(3),
                    "trading": valid(),
                    "plan": valid(),
                },
            ),
        ],
    )


def ceo_departure(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """chain: the leader leaves; assumption -> thesis -> alert, three hops."""
    company, other = investor.company(1), investor.company(2)
    successor = rng.choice([leader for leader in LEADERS if leader != company.leader])
    return ScenarioSpec(
        name="",
        description=(
            f"{company.leader} leaves {company.name}; the thesis built on the plan unwinds."
        ),
        memories={
            "leader": MemorySpec(
                kind=Kind.FACT,
                content=f"{company.leader} runs {company.name}",
                structured=_company_fact(company, CompanyAttribute.LEADERSHIP, company.leader),
            ),
            "assumption": MemorySpec(
                kind=Kind.ASSUMPTION,
                content=f"{company.leader}'s cost plan keeps {company.ticker} margins rising",
            ),
            "thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(company)),
            "alert": MemorySpec(
                kind=Kind.ALERT,
                content=f"look again if {company.ticker} margin falls below {_floor(company)}%",
            ),
            "other_margin": _margin_memory(other),
            "other_thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(other)),
        },
        links=[
            ["leader", "assumption", FinanceLinkType.PREMISE_OF],
            ["assumption", "thesis", FinanceLinkType.PREMISE_OF],
            ["thesis", "alert", FinanceLinkType.ALERT_FOR],
            ["other_margin", "other_thesis", FinanceLinkType.PREMISE_OF],
        ],
        resolutions={
            "assumption": [
                update_to("leader", f"{company.ticker} cost plan uncertain under {successor}")
            ],
            "thesis": [retire("leader")],
            "alert": [retire("leader")],
        },
        events=[
            EventSpec(
                update="leader",
                content=f"{successor} replaces {company.leader} at {company.name}",
                structured=_company_fact(company, CompanyAttribute.LEADERSHIP, successor),
                expect={
                    "assumption@latest": valid(2),
                    "thesis": retired(),
                    "alert": retired(),
                    "other_thesis": valid(),
                    "other_margin": valid(),
                },
            )
        ],
    )


def rate_edge(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """ask: the policy rate edges towards the line a thesis was written against."""
    company = investor.company(0)
    line = round(investor.policy_rate + 0.5, 1)
    new_rate = round(line - 0.1, 1)
    reply = rng.choice(("still_holds", "no_longer_holds", "correction"))
    thesis = f"{company.ticker} thesis holds while the policy rate stays below {line}%"
    alert_after = f"review {company.ticker} now: rate thesis under question"
    answer = EventSpec(answer="thesis", reply=reply)
    if reply == "still_holds":
        answer = answer.model_copy(update={"expect": {"thesis": valid(), "alert": valid()}})
    elif reply == "no_longer_holds":
        answer = answer.model_copy(
            update={"expect": {"thesis": retired(), "alert@latest": valid(2, alert_after)}}
        )
    else:
        corrected = f"{company.ticker} thesis holds while the policy rate stays below {line + 0.5}%"
        answer = answer.model_copy(
            update={
                "content": corrected,
                "expect": {
                    "thesis@latest": valid(2, corrected),
                    "alert@latest": valid(2, alert_after),
                },
            }
        )
    return ScenarioSpec(
        name="",
        description=f"The policy rate nears {investor.name}'s {line}% line ({reply}).",
        memories={
            "rate": MemorySpec(
                kind=Kind.FACT,
                content=f"policy rate is {investor.policy_rate}%",
                structured=StructuredFact(
                    subject=MACRO_SUBJECT,
                    attribute=MacroAttribute.POLICY_RATE,
                    value=investor.policy_rate,
                ),
            ),
            "thesis": MemorySpec(kind=Kind.THESIS, content=thesis),
            "alert": MemorySpec(kind=Kind.ALERT, content=f"review {company.ticker} monthly"),
        },
        links=[
            ["rate", "thesis", FinanceLinkType.PREMISE_OF],
            ["thesis", "alert", FinanceLinkType.ALERT_FOR],
        ],
        resolutions={
            "thesis": [
                ask(
                    "rate",
                    f"The policy rate is now {new_rate}%, just under your {line}% line. "
                    "Does your thesis still hold?",
                    "the new rate sits on the line the thesis names",
                )
            ],
            "alert": [update_to("thesis", alert_after)],
        },
        events=[
            EventSpec(
                update="rate",
                content=f"policy rate is {new_rate}%",
                structured=StructuredFact(
                    subject=MACRO_SUBJECT, attribute=MacroAttribute.POLICY_RATE, value=new_rate
                ),
                expect={
                    "thesis": Expectation(status=Status.PENDING_USER),
                    "alert": Expectation(status=Status.SUSPECT, version=1),
                },
            ),
            answer,
        ],
    )


def journal_entry(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """snapshot: a revised thesis re-arms its alert but never rewrites the journal."""
    company = investor.company(2)
    new_floor = _floor(company) - rng.choice((1, 2, 3))
    journal = f"2026-10-01: started following {company.ticker} on the margin thesis"
    new_alert = f"look again if {company.ticker} margin falls below {new_floor}%"
    return ScenarioSpec(
        name="",
        description=f"{investor.name} revises the {company.ticker} thesis; the journal keeps v1.",
        memories={
            "thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(company)),
            "journal": MemorySpec(kind=Kind.JOURNAL, content=journal),
            "alert": MemorySpec(
                kind=Kind.ALERT,
                content=f"look again if {company.ticker} margin falls below {_floor(company)}%",
            ),
        },
        links=[
            ["thesis", "journal", FinanceLinkType.JOURNALED_WITH],
            ["thesis", "alert", FinanceLinkType.ALERT_FOR],
        ],
        resolutions={
            "alert": [update_to("thesis", new_alert)],
            "journal": [keep("thesis", "a journal entry records the decision as it was made")],
        },
        events=[
            EventSpec(
                update="thesis",
                content=f"{company.ticker} thesis revised: margins can dip to {new_floor}%",
                expect={
                    "thesis": retired(),
                    "journal": valid(1, journal),
                    "alert@latest": valid(2, new_alert),
                },
            )
        ],
    )


def forget_holding(investor: Investor, rng: random.Random) -> ScenarioSpec:
    """forget: deleting a margin fact removes every version and the thesis built on it."""
    company, other = investor.company(0), investor.company(1)
    new_margin = company.margin + rng.choice((-2, 2))
    new_thesis = f"{company.ticker} thesis: margins now {new_margin}%, re-checked"
    return ScenarioSpec(
        name="",
        description=f"{investor.name} asks to forget {company.ticker} after one margin update.",
        memories={
            "margin": _margin_memory(company),
            "thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(company)),
            "other_margin": _margin_memory(other),
            "other_thesis": MemorySpec(kind=Kind.THESIS, content=_thesis(other)),
        },
        links=[
            ["margin", "thesis", FinanceLinkType.PREMISE_OF],
            ["other_margin", "other_thesis", FinanceLinkType.PREMISE_OF],
        ],
        resolutions={"thesis": [update_to("margin", new_thesis)]},
        events=[
            EventSpec(
                update="margin",
                content=f"{company.ticker} operating margin is {new_margin}%",
                structured=_company_fact(company, CompanyAttribute.MARGIN, new_margin),
                expect={"thesis@latest": Expectation(version=2)},
            ),
            EventSpec(
                forget="margin",
                expect={
                    "margin": Expectation(deleted=True),
                    "thesis": Expectation(deleted=True),
                    "other_margin": Expectation(status=Status.VALID),
                    "other_thesis": Expectation(status=Status.VALID),
                },
            ),
        ],
    )


TEMPLATES: Mapping[str, tuple[str, Template]] = {
    "guidance_cut": ("changed", guidance_cut),
    "peer_margin": ("unchanged", peer_margin),
    "trading_halt": ("temporary", trading_halt),
    "ceo_departure": ("chain", ceo_departure),
    "rate_edge": ("ask", rate_edge),
    "journal_entry": ("snapshot", journal_entry),
    "forget_holding": ("forget", forget_holding),
}

SPEC = TrackSpec(
    track=TRACK,
    domain=DOMAIN,
    module="bench.generate_finance",
    version=GENERATOR_VERSION,
    templates=TEMPLATES,
    test_only=True,
)


# ---- C5 pairs (ADR-0102) ------------------------------------------------------------------


def scenario_pairs(entry: ManifestEntry, spec: ScenarioSpec) -> list[LabelledPair]:
    """Every ordered pair of the scenario's memories, labelled from its links.

    Positive: a direct link written in the scenario (seeded or added by a `new` event).
    Negative: no direct link parent -> dependent. A pair whose dependent sits below the
    parent through a chain of links is left out: a correct linker writes only the
    direct edges, but "no link" would be a doubtful label for an indirect dependency.
    A reversed edge stays in as a negative, so direction is scored. Two facts about the
    same subject and attribute (trading vs halted) stay in as a negative too, noted:
    they contradict each other, which the change detector handles, not a link.
    """
    registry = finance_registry()
    memories: dict[str, PairMemory] = {
        alias: PairMemory(kind=m.kind, content=m.content, structured=m.structured)
        for alias, m in spec.memories.items()
    }
    links = [tuple(link) for link in spec.links]
    for event in spec.events:
        if event.new is not None and event.content is not None:
            memories[event.new] = PairMemory(
                kind=event.kind, content=event.content, structured=event.structured
            )
            links.extend(tuple(link) for link in event.links)
    direct = {(parent, dependent): link_type for parent, dependent, link_type in links}
    pairs: list[LabelledPair] = []
    for parent in memories:
        below = _reachable(parent, direct)
        for dependent in memories:
            if dependent == parent:
                continue
            link_type = direct.get((parent, dependent))
            if link_type is None and dependent in below:
                continue  # indirect dependency: no trustworthy label either way
            note = None
            if link_type is None and (dependent, parent) in direct:
                note = "reversed edge"
            elif link_type is None and _same_key(memories[parent], memories[dependent]):
                note = "same structured key"
            pairs.append(
                LabelledPair(
                    pair_id=f"{TRACK}:{spec.name}:{parent}>{dependent}",
                    track=TRACK,
                    domain=DOMAIN,
                    persona=entry.persona,
                    template=entry.template,
                    split=Split.TEST,
                    parent=memories[parent],
                    dependent=memories[dependent],
                    link_type=link_type,
                    link_class=registry.class_of(link_type) if link_type else None,
                    provenance=Provenance.SCENARIO,
                    note=note,
                )
            )
    return pairs


def _same_key(a: PairMemory, b: PairMemory) -> bool:
    return (
        a.structured is not None
        and b.structured is not None
        and (a.structured.subject, a.structured.attribute)
        == (b.structured.subject, b.structured.attribute)
    )


def _reachable(start: str, direct: Mapping[tuple[str, str], str]) -> set[str]:
    """Aliases below `start` through links of any class (a snapshot is a dependency too)."""
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for parent, dependent in direct:
            if parent == current and dependent not in seen:
                seen.add(dependent)
                frontier.append(dependent)
    return seen


def track_pairs(scenarios: Sequence[tuple[ManifestEntry, ScenarioSpec]]) -> list[LabelledPair]:
    """Pairs of every scenario, one per distinct (parent, dependent) text.

    Templates share background memories (another company's margin and thesis appear in
    several scenarios of a persona), so the same text pair recurs. Keeping each once
    stops template overlap from weighting the H4 score; the copy with the smallest
    pair_id is kept. Two copies with different labels would mean the templates
    contradict each other, and that is refused.
    """
    kept: dict[tuple[str, str], LabelledPair] = {}
    every = [pair for entry, spec in scenarios for pair in scenario_pairs(entry, spec)]
    for pair in sorted(every, key=lambda p: p.pair_id):
        key = (pair.parent.model_dump_json(), pair.dependent.model_dump_json())
        first = kept.setdefault(key, pair)
        if first.link_type != pair.link_type:
            raise ValueError(
                f"{first.pair_id} and {pair.pair_id} have the same texts but labels "
                f"{first.link_type!r} and {pair.link_type!r}"
            )
    return list(kept.values())


def pairs_text(scenarios: Sequence[tuple[ManifestEntry, ScenarioSpec]]) -> str:
    """The exact bytes `write_pairs` produces, so --check compares like for like."""
    pairs = track_pairs(scenarios)
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / PAIRS_FILE
        write_pairs(path, pairs)
        return path.read_text(encoding="utf-8")


def _pairs_file(scenarios: list[tuple[ManifestEntry, ScenarioSpec]]) -> dict[str, str]:
    return {PAIRS_FILE: pairs_text(scenarios)}


def generate(seed: int = DEFAULT_SEED, personas: int = DEFAULT_PERSONAS) -> Track:
    return assemble_track(SPEC, make_personas(seed, personas), seed, extra_files=_pairs_file)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the RippleBench v1 finance track")
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
    print(f"wrote {len(track.scenarios)} scenarios + manifest.json + {PAIRS_FILE} to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
