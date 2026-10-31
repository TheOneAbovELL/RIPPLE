"""RippleBench v0, jobs track: seeded personas x event templates -> scenario files (ADR-0061).

    uv run python -m bench.generate            # writes bench/data/jobs_v0/
    uv run python -m bench.generate --check    # verifies the files match a fresh generation

Every scenario is a tests/scenarios-format YAML (bench/scenario.py) with gold states
after every event, so the same runner and the same checks serve the smoke suite and
the bench. Generation is deterministic: the same seed and persona count produce
byte-identical files. The split is by persona and by template, never by item
(docs/04-evaluation.md): a scenario is `train` only when both its persona and its
template are train; `held_out` says which half is unseen. The strict test set is the
unseen-persona x unseen-template corner. manifest.json records all of it plus a hash
of the data so a results/ run can cite the exact data version (I8).

Seven template families, one per gold behaviour the engine must show:
changed · unchanged · temporary · chain · ask · snapshot · forget. Each template is a
function of the persona and a per-(seed, persona, template) random stream, so a new
persona never changes an existing persona's scenarios.
"""

import argparse
import hashlib
import json
import random
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from bench.scenario import (
    EventSpec,
    Expectation,
    MemorySpec,
    ResolutionSpec,
    ScenarioSpec,
    load_scenario,
    validate_scenario,
)
from ripple.core.models import DecisionAction, Status, StructuredFact
from ripple.domains.jobs.vocabulary import (
    PROFILE_SUBJECT,
    JobsLinkType,
    Kind,
    OpeningAttribute,
    ProfileAttribute,
    opening_subject,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "jobs_v0"
DEFAULT_SEED = 20261019
DEFAULT_PERSONAS = 5
GENERATOR_VERSION = 1
TRACK = "jobs_v0"

NAMES = ("asha", "bharat", "chitra", "dev", "esha", "farhan", "gauri", "harsh", "ira", "jay")
BRANCHES = ("CSE", "ECE", "IT", "EE", "ME")
SKILLS = ("python", "pytorch", "django", "react", "rust", "go", "sql", "kubernetes")
COMPANIES = ("acme", "globex", "initech", "umbrella", "hooli", "vandelay", "wonka", "stark")
ROLE_TYPES = ("internship", "full_time")


@dataclass(frozen=True)
class Opening:
    company: str
    title: str
    cgpa_cutoff: float
    deadline: str  # ISO 8601 with timezone, OpeningAttribute.DEADLINE
    required_skill: str
    role_type: str

    @property
    def alias(self) -> str:
        return f"{self.company}_opening"


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    cgpa: float
    batch: int
    branch: str
    skills: tuple[str, ...]
    openings: tuple[Opening, ...]  # [0] cutoff above cgpa, [1] below, [2] far above

    def opening(self, index: int) -> Opening:
        return self.openings[index]


# ---- personas --------------------------------------------------------------------------


def make_personas(seed: int, count: int) -> list[Persona]:
    """Persona i depends on the seed and i only, so raising `count` adds personas
    without changing the ones already generated."""
    if count > len(NAMES):
        raise ValueError(f"at most {len(NAMES)} personas; add names to NAMES for more")
    names = list(NAMES)
    random.Random(f"{seed}:names").shuffle(names)
    personas: list[Persona] = []
    for index, name in enumerate(names[:count]):
        rng = random.Random(f"{seed}:persona:{index}")
        cgpa = round(rng.uniform(6.6, 8.6), 1)
        companies = rng.sample(COMPANIES, 3)
        skills = tuple(rng.sample(SKILLS, 3))
        cutoffs = (round(cgpa + 0.2, 1), round(cgpa - 0.5, 1), round(cgpa + 0.8, 1))
        openings = tuple(
            Opening(
                company=company,
                title=f"{company.capitalize()} SDE {_role_word(role)}",
                cgpa_cutoff=cutoff,
                deadline=f"2026-{rng.randint(11, 12):02d}-{rng.randint(1, 28):02d}T23:59:00+05:30",
                required_skill=rng.choice([s for s in SKILLS if s not in skills]),
                role_type=role,
            )
            for company, cutoff, role in zip(
                companies, cutoffs, ("internship", "internship", "full_time"), strict=True
            )
        )
        personas.append(
            Persona(
                id=f"p{index}_{name}",
                name=name,
                cgpa=cgpa,
                batch=rng.choice((2027, 2028)),
                branch=rng.choice(BRANCHES),
                skills=skills,
                openings=openings,
            )
        )
    return personas


# ---- template helpers ------------------------------------------------------------------


def _role_word(role: str) -> str:
    return "intern" if role == "internship" else "engineer"


def _profile(attribute: ProfileAttribute, value: str | int | float | bool) -> StructuredFact:
    return StructuredFact(subject=PROFILE_SUBJECT, attribute=attribute, value=value)


def _opening_fact(
    opening: Opening, attribute: OpeningAttribute, value: str | int | float | bool
) -> StructuredFact:
    return StructuredFact(subject=opening_subject(opening.alias), attribute=attribute, value=value)


def _opening_memory(
    opening: Opening, attribute: OpeningAttribute = OpeningAttribute.CGPA_CUTOFF
) -> MemorySpec:
    if attribute is OpeningAttribute.DEADLINE:
        content = f"{opening.title}: deadline {opening.deadline[:10]}"
        value: str | float = opening.deadline
    else:
        content = f"{opening.title}: CGPA cutoff {opening.cgpa_cutoff}"
        value = opening.cgpa_cutoff
    return MemorySpec(
        kind=Kind.OPENING, content=content, structured=_opening_fact(opening, attribute, value)
    )


def _cgpa_memory(persona: Persona) -> MemorySpec:
    return MemorySpec(
        kind=Kind.FACT,
        content=f"CGPA is {persona.cgpa}",
        structured=_profile(ProfileAttribute.CGPA, persona.cgpa),
    )


def _update(alias: str, content: str, reason: str = "re-derived from its parent") -> ResolutionSpec:
    return ResolutionSpec(
        trigger=alias, action=DecisionAction.UPDATE, new_content=content, reason=reason
    )


def _retire(alias: str, reason: str = "no longer holds after its parent changed") -> ResolutionSpec:
    return ResolutionSpec(trigger=alias, action=DecisionAction.RETIRE, reason=reason)


def _keep(alias: str, reason: str) -> ResolutionSpec:
    return ResolutionSpec(trigger=alias, action=DecisionAction.KEEP, reason=reason)


def _valid(version: int = 1) -> Expectation:
    return Expectation(status=Status.VALID, version=version)


Template = Callable[[Persona, random.Random], ScenarioSpec]


# ---- templates --------------------------------------------------------------------------


def cgpa_rise(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """changed: a CGPA rise crosses one cutoff; eligibility and criteria re-derive."""
    opening = persona.opening(0)
    new_cgpa = round(opening.cgpa_cutoff + rng.choice((0.1, 0.2, 0.3)), 1)
    return ScenarioSpec(
        name="",
        description=f"{persona.name}'s CGPA rises past the {opening.company} cutoff.",
        memories={
            "cgpa": _cgpa_memory(persona),
            opening.alias: _opening_memory(opening),
            "eligibility": MemorySpec(
                kind=Kind.DERIVED,
                content=f"not eligible for {opening.company} "
                f"({persona.cgpa} < {opening.cgpa_cutoff})",
            ),
            "criteria": MemorySpec(
                kind=Kind.CRITERIA, content=f"search openings with cutoff <= {persona.cgpa}"
            ),
        },
        links=[
            ["cgpa", "eligibility", JobsLinkType.ELIGIBILITY_OF],
            [opening.alias, "eligibility", JobsLinkType.ELIGIBILITY_OF],
            ["cgpa", "criteria", JobsLinkType.CRITERIA_FROM],
        ],
        resolutions={
            "eligibility": [
                _update(
                    "cgpa", f"eligible for {opening.company} ({new_cgpa} >= {opening.cgpa_cutoff})"
                )
            ],
            "criteria": [_update("cgpa", f"search openings with cutoff <= {new_cgpa}")],
        },
        events=[
            EventSpec(
                update="cgpa",
                content=f"CGPA is {new_cgpa}",
                structured=_profile(ProfileAttribute.CGPA, new_cgpa),
                expect={
                    "cgpa": Expectation(status=Status.RETIRED, version=1),
                    "cgpa@latest": Expectation(
                        status=Status.VALID, version=2, content=f"CGPA is {new_cgpa}"
                    ),
                    "eligibility@latest": Expectation(
                        status=Status.VALID,
                        version=2,
                        content=f"eligible for {opening.company} "
                        f"({new_cgpa} >= {opening.cgpa_cutoff})",
                    ),
                    "criteria@latest": Expectation(status=Status.VALID, version=2),
                    opening.alias: _valid(),
                },
            )
        ],
    )


def deadline_moved(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """unchanged: one opening's deadline moves; the other opening's beliefs stay put."""
    moved, other = persona.opening(1), persona.opening(2)
    new_day = rng.randint(15, 28)
    new_deadline = f"2026-12-{new_day:02d}T23:59:00+05:30"
    return ScenarioSpec(
        name="",
        description=f"{moved.company} extends its deadline; nothing about {other.company} changes.",
        memories={
            moved.alias: _opening_memory(moved, OpeningAttribute.DEADLINE),
            f"{moved.company}_reminder": MemorySpec(
                kind=Kind.DERIVED, content=f"remind two days before {moved.deadline[:10]}"
            ),
            other.alias: _opening_memory(other, OpeningAttribute.DEADLINE),
            f"{other.company}_reminder": MemorySpec(
                kind=Kind.DERIVED, content=f"remind two days before {other.deadline[:10]}"
            ),
            "cgpa": _cgpa_memory(persona),
            f"{other.company}_eligibility": MemorySpec(
                kind=Kind.DERIVED, content=f"eligible for {other.company}"
            ),
        },
        links=[
            [moved.alias, f"{moved.company}_reminder", JobsLinkType.REMINDER_FOR],
            [other.alias, f"{other.company}_reminder", JobsLinkType.REMINDER_FOR],
            ["cgpa", f"{other.company}_eligibility", JobsLinkType.ELIGIBILITY_OF],
            [other.alias, f"{other.company}_eligibility", JobsLinkType.ELIGIBILITY_OF],
        ],
        resolutions={
            f"{moved.company}_reminder": [
                _update(moved.alias, f"remind two days before {new_deadline[:10]}")
            ],
        },
        events=[
            EventSpec(
                update=moved.alias,
                content=f"{moved.title}: deadline {new_deadline[:10]}",
                structured=_opening_fact(moved, OpeningAttribute.DEADLINE, new_deadline),
                expect={
                    f"{moved.company}_reminder@latest": Expectation(
                        status=Status.VALID,
                        version=2,
                        content=f"remind two days before {new_deadline[:10]}",
                    ),
                    f"{other.company}_reminder": _valid(),
                    f"{other.company}_eligibility": _valid(),
                    other.alias: _valid(),
                    "cgpa": _valid(),
                },
            )
        ],
    )


def exam_block(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """temporary: exams block availability for N days, then expire; nothing permanent."""
    opening = persona.opening(1)
    days = rng.randint(14, 45)
    return ScenarioSpec(
        name="",
        description=f"{persona.name} is busy with exams for {days} days.",
        memories={
            "looking": MemorySpec(
                kind=Kind.FACT,
                content="actively looking for internships",
                structured=_profile(ProfileAttribute.LOOKING, True),
            ),
            "availability": MemorySpec(kind=Kind.DERIVED, content="available for interviews"),
            "reminder": MemorySpec(
                kind=Kind.DERIVED, content=f"remind about the {opening.company} interview slot"
            ),
        },
        links=[
            ["looking", "availability", "depends_on_fact"],
            ["availability", "reminder", JobsLinkType.REMINDER_FOR],
        ],
        resolutions={
            "availability": [_update("exams", "availability recomputed around the exam block")],
            "reminder": [_keep("exams", "the slot is after the exams either way")],
        },
        events=[
            EventSpec(
                new="exams",
                kind=Kind.FACT,
                content=f"busy with exams for the next {days} days",
                valid_to_days=days,
                structured=_profile(ProfileAttribute.AVAILABILITY, "exams"),
                links=[["exams", "availability", "depends_on_time_period"]],
                expect={
                    "exams": Expectation(status=Status.VALID),
                    "availability@latest": Expectation(status=Status.VALID, version=2),
                    "looking": _valid(),
                    "reminder": _valid(),
                },
            ),
            EventSpec(
                advance_days=days + 1,
                expect={
                    "exams": Expectation(status=Status.RETIRED),
                    "availability@latest": Expectation(status=Status.VALID, version=3),
                    "looking": _valid(),
                    "reminder": _valid(),
                },
            ),
        ],
    )


def accepted_offer(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """chain: offer -> availability -> eligibility -> recommendation; full-time untouched."""
    summer, fulltime = persona.opening(1), persona.opening(2)
    giver = rng.choice([c for c in COMPANIES if c not in {summer.company, fulltime.company}])
    return ScenarioSpec(
        name="",
        description=f"{persona.name} accepts a {giver} summer offer; a three-hop chain retires.",
        memories={
            "offer": MemorySpec(
                kind=Kind.FACT,
                content="no summer offer accepted",
                structured=_profile(ProfileAttribute.ACCEPTED_OFFER, "none"),
            ),
            "availability": MemorySpec(kind=Kind.DERIVED, content="available for summer 2027"),
            "eligibility": MemorySpec(
                kind=Kind.DERIVED, content=f"eligible for {summer.company} summer internship"
            ),
            "recommendation": MemorySpec(
                kind=Kind.DERIVED, content=f"apply to {summer.company} summer internship"
            ),
            "batch": MemorySpec(
                kind=Kind.FACT,
                content=f"batch {persona.batch}",
                structured=_profile(ProfileAttribute.BATCH, persona.batch),
            ),
            "fulltime": MemorySpec(
                kind=Kind.DERIVED, content=f"apply to {fulltime.company} full-time {persona.batch}"
            ),
        },
        links=[
            ["offer", "availability", "depends_on_fact"],
            ["availability", "eligibility", JobsLinkType.ELIGIBILITY_OF],
            ["eligibility", "recommendation", "depends_on_fact"],
            ["batch", "fulltime", JobsLinkType.ELIGIBILITY_OF],
        ],
        resolutions={
            "availability": [_update("offer", f"not available for summer 2027 ({giver} offer)")],
            "eligibility": [_retire("offer")],
            "recommendation": [_retire("offer")],
        },
        events=[
            EventSpec(
                update="offer",
                content=f"accepted {giver} summer 2027 offer",
                structured=_profile(ProfileAttribute.ACCEPTED_OFFER, f"{giver}_summer_2027"),
                expect={
                    "availability@latest": Expectation(status=Status.VALID, version=2),
                    "eligibility": Expectation(status=Status.RETIRED),
                    "recommendation": Expectation(status=Status.RETIRED),
                    "fulltime": _valid(),
                    "batch": _valid(),
                },
            )
        ],
    )


def cutoff_unknown(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """ask: a small CGPA change leaves eligibility uncertain; the user answers."""
    opening = persona.opening(0)
    new_cgpa = round(persona.cgpa + 0.1, 1)
    reply = rng.choice(("still_holds", "no_longer_holds", "correction"))
    answer = EventSpec(answer="eligibility", reply=reply)
    if reply == "still_holds":
        answer = answer.model_copy(
            update={"expect": {"eligibility": _valid(), "recommendation": _valid()}}
        )
    elif reply == "no_longer_holds":
        answer = answer.model_copy(
            update={
                "expect": {
                    "eligibility": Expectation(status=Status.RETIRED),
                    "recommendation@latest": Expectation(
                        status=Status.VALID, version=2, content=f"apply to {opening.company}"
                    ),
                }
            }
        )
    else:
        answer = answer.model_copy(
            update={
                "content": f"eligible for {opening.company} (cutoff lowered to {new_cgpa})",
                "expect": {
                    "eligibility@latest": Expectation(
                        status=Status.VALID,
                        version=2,
                        content=f"eligible for {opening.company} (cutoff lowered to {new_cgpa})",
                    ),
                    "recommendation@latest": Expectation(
                        status=Status.VALID, version=2, content=f"apply to {opening.company}"
                    ),
                },
            }
        )
    return ScenarioSpec(
        name="",
        description=(
            f"{persona.name}'s CGPA edges up; the {opening.company} cutoff is unclear ({reply})."
        ),
        memories={
            "cgpa": _cgpa_memory(persona),
            opening.alias: _opening_memory(opening),
            "eligibility": MemorySpec(
                kind=Kind.DERIVED, content=f"not eligible for {opening.company}"
            ),
            "recommendation": MemorySpec(kind=Kind.DERIVED, content=f"skip {opening.company}"),
        },
        links=[
            ["cgpa", "eligibility", JobsLinkType.ELIGIBILITY_OF],
            [opening.alias, "eligibility", JobsLinkType.ELIGIBILITY_OF],
            ["eligibility", "recommendation", "depends_on_fact"],
        ],
        resolutions={
            "eligibility": [
                ResolutionSpec(
                    trigger="cgpa",
                    action=DecisionAction.ASK,
                    question=f"Is the {opening.company} cutoff still {opening.cgpa_cutoff}?",
                    reason="the new CGPA sits on the cutoff",
                )
            ],
            "recommendation": [_update("eligibility", f"apply to {opening.company}")],
        },
        events=[
            EventSpec(
                update="cgpa",
                content=f"CGPA is {new_cgpa}",
                structured=_profile(ProfileAttribute.CGPA, new_cgpa),
                expect={
                    "eligibility": Expectation(status=Status.PENDING_USER),
                    "recommendation": Expectation(status=Status.SUSPECT, version=1),
                },
            ),
            answer,
        ],
    )


def resume_update(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """snapshot: a new resume version re-tailors but never rewrites a sent application."""
    applied, target = persona.opening(1), persona.opening(2)
    project = rng.choice(persona.skills)
    return ScenarioSpec(
        name="",
        description=(
            f"{persona.name} uploads resume v2; the {applied.company} application keeps v1."
        ),
        memories={
            "resume": MemorySpec(
                kind=Kind.FACT,
                content="resume v1",
                structured=_profile(ProfileAttribute.RESUME, "v1"),
            ),
            "application": MemorySpec(
                kind=Kind.APPLICATION, content=f"applied to {applied.company} with resume v1"
            ),
            "tailoring": MemorySpec(
                kind=Kind.DERIVED, content=f"highlight the {project} project for {target.company}"
            ),
        },
        links=[
            ["resume", "application", JobsLinkType.SENT_WITH_RESUME],
            ["resume", "tailoring", "depends_on_fact"],
        ],
        resolutions={
            "tailoring": [
                _update("resume", f"highlight the new {project} work for {target.company}")
            ],
            "application": [_keep("resume", "a sent application is a historical record")],
        },
        events=[
            EventSpec(
                update="resume",
                content="resume v2",
                structured=_profile(ProfileAttribute.RESUME, "v2"),
                expect={
                    "resume": Expectation(status=Status.RETIRED),
                    "application": Expectation(
                        status=Status.VALID,
                        version=1,
                        content=f"applied to {applied.company} with resume v1",
                    ),
                    "tailoring@latest": Expectation(status=Status.VALID, version=2),
                },
            )
        ],
    )


def forget_cgpa(persona: Persona, rng: random.Random) -> ScenarioSpec:
    """forget: deleting the CGPA removes every version and every belief derived from it."""
    opening, other = persona.opening(0), persona.opening(1)
    skill = rng.choice(persona.skills)
    new_cgpa = round(opening.cgpa_cutoff + 0.1, 1)
    return ScenarioSpec(
        name="",
        description=f"{persona.name} asks to forget the CGPA after one change to it.",
        memories={
            "cgpa": _cgpa_memory(persona),
            "eligibility": MemorySpec(
                kind=Kind.DERIVED, content=f"not eligible for {opening.company}"
            ),
            "skill": MemorySpec(
                kind=Kind.FACT,
                content=f"knows {skill}",
                structured=_profile(ProfileAttribute.SKILL, skill),
            ),
            "fit": MemorySpec(kind=Kind.DERIVED, content=f"fit for {other.company}"),
        },
        links=[
            ["cgpa", "eligibility", JobsLinkType.ELIGIBILITY_OF],
            ["skill", "fit", JobsLinkType.FIT_OF],
        ],
        resolutions={"eligibility": [_update("cgpa", f"eligible for {opening.company}")]},
        events=[
            EventSpec(
                update="cgpa",
                content=f"CGPA is {new_cgpa}",
                structured=_profile(ProfileAttribute.CGPA, new_cgpa),
                expect={"eligibility@latest": Expectation(version=2)},
            ),
            EventSpec(
                forget="cgpa",
                expect={
                    "cgpa": Expectation(deleted=True),
                    "eligibility": Expectation(deleted=True),
                    "skill": Expectation(status=Status.VALID),
                    "fit": Expectation(status=Status.VALID),
                },
            ),
        ],
    )


TEMPLATES: Mapping[str, tuple[str, Template]] = {
    "cgpa_rise": ("changed", cgpa_rise),
    "deadline_moved": ("unchanged", deadline_moved),
    "exam_block": ("temporary", exam_block),
    "accepted_offer": ("chain", accepted_offer),
    "cutoff_unknown": ("ask", cutoff_unknown),
    "resume_update": ("snapshot", resume_update),
    "forget_cgpa": ("forget", forget_cgpa),
}


# ---- generation ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestEntry:
    file: str
    name: str
    persona: str
    template: str
    family: str
    split: str  # train | test
    held_out: str  # none | persona | template | both


@dataclass(frozen=True)
class Generated:
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]]
    manifest: dict[str, Any]


def build_scenario(persona: Persona, template: str, seed: int) -> ScenarioSpec:
    family, make = TEMPLATES[template]
    rng = random.Random(f"{seed}:{persona.id}:{template}")
    spec = make(persona, rng)
    return spec.model_copy(
        update={
            "name": f"{template}__{persona.id}",
            "meta": {
                "track": TRACK,
                "persona": persona.id,
                "template": template,
                "family": family,
                "seed": seed,
            },
        }
    )


def generate(seed: int = DEFAULT_SEED, personas: int = DEFAULT_PERSONAS) -> Generated:
    people = make_personas(seed, personas)
    split_rng = random.Random(f"{seed}:split")
    test_personas = set(split_rng.sample([p.id for p in people], max(1, personas * 2 // 5)))
    test_templates = set(split_rng.sample(sorted(TEMPLATES), 2))
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]] = []
    for persona in people:
        for template, (family, _) in TEMPLATES.items():
            spec = build_scenario(persona, template, seed)
            problems = validate_scenario(spec)
            if problems:
                raise ValueError(f"{spec.name}: {problems}")
            unseen = (persona.id in test_personas, template in test_templates)
            held_out = {
                (False, False): "none",
                (True, False): "persona",
                (False, True): "template",
                (True, True): "both",
            }[unseen]
            entry = ManifestEntry(
                file=f"{spec.name}.yaml",
                name=spec.name,
                persona=persona.id,
                template=template,
                family=family,
                split="train" if held_out == "none" else "test",
                held_out=held_out,
            )
            scenarios.append((entry, spec))
    documents = {entry.file: scenario_yaml(spec) for entry, spec in scenarios}
    manifest = {
        "track": TRACK,
        "generator": {"module": "bench.generate", "version": GENERATOR_VERSION},
        "seed": seed,
        "personas": {
            "all": [p.id for p in people],
            "train": sorted(p.id for p in people if p.id not in test_personas),
            "test": sorted(test_personas),
        },
        "templates": {
            "all": {name: family for name, (family, _) in TEMPLATES.items()},
            "train": sorted(t for t in TEMPLATES if t not in test_templates),
            "test": sorted(test_templates),
        },
        "split_rule": (
            "train = train persona AND train template; everything else is test; "
            "held_out names the unseen half; strict test = both"
        ),
        "data_sha256": data_hash(documents),
        "scenarios": [asdict(entry) for entry, _ in scenarios],
    }
    return Generated(scenarios=scenarios, manifest=manifest)


def scenario_yaml(spec: ScenarioSpec) -> str:
    data = spec.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def data_hash(documents: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(documents):
        digest.update(name.encode("utf-8"))
        digest.update(documents[name].encode("utf-8"))
    return digest.hexdigest()


def write_data(generated: Generated, out_dir: Path) -> list[Path]:
    """Write the track. Only files a previous manifest in `out_dir` lists are replaced;
    a directory holding scenario files without a manifest (tests/scenarios, say) is
    refused rather than overwritten."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    existing = sorted(path.name for path in out_dir.glob("*.yaml"))
    if existing and not manifest_path.exists():
        raise FileExistsError(
            f"{out_dir} holds {len(existing)} scenario files but no manifest.json; "
            "refusing to overwrite hand-written scenarios"
        )
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for stale in previous.get("scenarios", []):
            (out_dir / stale["file"]).unlink(missing_ok=True)
    written: list[Path] = []
    for entry, spec in generated.scenarios:
        path = out_dir / entry.file
        path.write_text(scenario_yaml(spec), encoding="utf-8")
        written.append(path)
    manifest_path.write_text(json.dumps(generated.manifest, indent=2) + "\n", encoding="utf-8")
    written.append(manifest_path)
    return written


def check_data(generated: Generated, out_dir: Path) -> list[str]:
    """Differences between the files on disk and a fresh generation; empty when in sync."""
    problems: list[str] = []
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"{manifest_path} is missing"]
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    if on_disk != generated.manifest:
        problems.append("manifest.json differs from a fresh generation")
    for entry, spec in generated.scenarios:
        path = out_dir / entry.file
        if not path.exists():
            problems.append(f"{entry.file} is missing")
        elif path.read_text(encoding="utf-8") != scenario_yaml(spec):
            problems.append(f"{entry.file} differs from a fresh generation")
    expected = {entry.file for entry, _ in generated.scenarios}
    problems.extend(
        f"{path.name} is not in the manifest"
        for path in out_dir.glob("*.yaml")
        if path.name not in expected
    )
    return problems


# ---- loader ------------------------------------------------------------------------------


SPLITS = ("all", "train", "test", "strict_test")


def load_manifest(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    return json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))


def load_jobs_v0(
    split: str = "all", data_dir: Path = DATA_DIR
) -> list[tuple[ManifestEntry, ScenarioSpec]]:
    """Scenarios of the track, in manifest order, filtered by split."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; choose one of {', '.join(SPLITS)}")
    manifest = load_manifest(data_dir)
    loaded: list[tuple[ManifestEntry, ScenarioSpec]] = []
    for raw in manifest["scenarios"]:
        entry = ManifestEntry(**raw)
        if split == "train" and entry.split != "train":
            continue
        if split == "test" and entry.split != "test":
            continue
        if split == "strict_test" and entry.held_out != "both":
            continue
        loaded.append((entry, load_scenario(data_dir / entry.file)))
    return loaded


# ---- cli ----------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the RippleBench v0 jobs track")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--personas", type=int, default=DEFAULT_PERSONAS)
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--check", action="store_true", help="verify the files on disk instead of writing"
    )
    args = parser.parse_args(argv)
    generated = generate(args.seed, args.personas)
    if args.check:
        problems = check_data(generated, args.out)
        for problem in problems:
            print(f"  {problem}")
        print(f"{args.out}: {'in sync' if not problems else f'{len(problems)} problem(s)'}")
        return 0 if not problems else 1
    written = write_data(generated, args.out)
    print(f"wrote {len(written) - 1} scenarios + manifest.json to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
