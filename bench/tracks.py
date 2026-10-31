"""RippleBench v1 track machinery: split, manifest, files, curated stories (ADR-0101).

The v1 tracks (news_v1, finance_v1) are generated the way v0 is (bench/generate.py,
ADR-0061): seeded personas x template families, one scenario per pair, the v0 split
rule, a manifest with a data hash and a `--check` mode. What is new here:

- `test_only` tracks: the finance track is an unseen-domain test (H4, docs/04), so every
  scenario is `test` with `held_out = "domain"`; nothing in it may ever be trained on.
- `content`: every manifest says the scenarios are synthetic. docs/04 asks for real
  stories in the news track; until the author curates them the generated data stands in
  and says so.
- extra files (the finance C5 pairs) are written, hashed and checked with the scenarios.
- curated stories: hand-written scenarios in `<track>/curated/*.yaml` with a
  `meta.provenance` block (`CuratedProvenance`). They are never generated, never
  overwritten, always `test` and loaded beside the generated ones.
"""

import hashlib
import json
import random
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bench.domains import domain_of
from bench.generate import (
    SPLITS,
    Generated,
    ManifestEntry,
    check_data,
    data_hash,
    scenario_yaml,
    write_data,
)
from bench.scenario import (
    Expectation,
    ResolutionSpec,
    ScenarioSpec,
    load_scenario,
    validate_scenario,
)
from ripple.core.models import DecisionAction, Status

CURATED_DIR = "curated"
CURATED_SPLIT = "curated"
TRACK_SPLITS = (*SPLITS, CURATED_SPLIT)
SYNTHETIC_NOTE = (
    "synthetic: generated from templates with fictional names, places and companies; "
    "no real story, person or company is described"
)


class Persona(Protocol):
    @property
    def id(self) -> str: ...


Template = Callable[[Any, random.Random], ScenarioSpec]


@dataclass(frozen=True)
class TrackSpec:
    track: str  # news_v1, finance_v1
    domain: str  # the adapter whose link types the scenarios use
    module: str  # the generator module, recorded in the manifest
    version: int
    templates: Mapping[str, tuple[str, Template]]  # name -> (family, template)
    test_only: bool = False


@dataclass(frozen=True)
class Track:
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]]
    manifest: dict[str, Any]
    extra_files: dict[str, str] = field(default_factory=dict)  # file name -> exact text

    def as_generated(self) -> Generated:
        return Generated(scenarios=self.scenarios, manifest=self.manifest)


# ---- scripted-resolution and gold helpers shared by the v1 templates ---------------------


def update_to(
    trigger: str, content: str, reason: str = "re-derived from its parent"
) -> ResolutionSpec:
    return ResolutionSpec(
        trigger=trigger, action=DecisionAction.UPDATE, new_content=content, reason=reason
    )


def retire(
    trigger: str, reason: str = "no longer holds after its parent changed"
) -> ResolutionSpec:
    return ResolutionSpec(trigger=trigger, action=DecisionAction.RETIRE, reason=reason)


def keep(trigger: str, reason: str) -> ResolutionSpec:
    return ResolutionSpec(trigger=trigger, action=DecisionAction.KEEP, reason=reason)


def ask(trigger: str, question: str, reason: str) -> ResolutionSpec:
    return ResolutionSpec(
        trigger=trigger, action=DecisionAction.ASK, question=question, reason=reason
    )


def valid(version: int = 1, content: str | None = None) -> Expectation:
    return Expectation(status=Status.VALID, version=version, content=content)


def retired(version: int | None = None) -> Expectation:
    return Expectation(status=Status.RETIRED, version=version)


# ---- generation ---------------------------------------------------------------------------


def assemble_track(
    spec: TrackSpec,
    personas: Sequence[Persona],
    seed: int,
    extra_files: Callable[[list[tuple[ManifestEntry, ScenarioSpec]]], dict[str, str]] | None = None,
) -> Track:
    """Every persona x template, validated, split and hashed.

    The split draws from `random.Random(f"{seed}:split")` exactly as v0 does (two of
    five personas and two templates held out), so the rule is the same across tracks;
    tests/bench_v1 proves it against bench.generate.generate.
    """
    ids = [p.id for p in personas]
    if spec.test_only:
        test_personas, test_templates = set(ids), set(spec.templates)
    else:
        split_rng = random.Random(f"{seed}:split")
        test_personas = set(split_rng.sample(ids, max(1, len(ids) * 2 // 5)))
        test_templates = set(split_rng.sample(sorted(spec.templates), 2))
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]] = []
    for persona in personas:
        for template, (family, make) in spec.templates.items():
            scenario = _build(spec, persona, template, family, make, seed)
            problems = validate_scenario(scenario)
            if problems:
                raise ValueError(f"{scenario.name}: {problems}")
            held_out = (
                "domain"
                if spec.test_only
                else _held_out(persona.id in test_personas, template in test_templates)
            )
            entry = ManifestEntry(
                file=f"{scenario.name}.yaml",
                name=scenario.name,
                persona=persona.id,
                template=template,
                family=family,
                split="train" if held_out == "none" else "test",
                held_out=held_out,
            )
            scenarios.append((entry, scenario))
    extras = extra_files(scenarios) if extra_files else {}
    documents = {entry.file: scenario_yaml(s) for entry, s in scenarios}
    manifest: dict[str, Any] = {
        "track": spec.track,
        "domain": spec.domain,
        "content": "synthetic",
        "content_note": SYNTHETIC_NOTE,
        "generator": {"module": spec.module, "version": spec.version},
        "seed": seed,
        "personas": {
            "all": ids,
            "train": sorted(i for i in ids if i not in test_personas),
            "test": sorted(test_personas),
        },
        "templates": {
            "all": {name: family for name, (family, _) in spec.templates.items()},
            "train": sorted(t for t in spec.templates if t not in test_templates),
            "test": sorted(test_templates),
        },
        "split_rule": (
            "test only: the whole track is an unseen domain (H4); held_out = domain"
            if spec.test_only
            else "train = train persona AND train template; everything else is test; "
            "held_out names the unseen half; strict test = both"
        ),
        "curated": (
            f"hand-written real-story scenarios go in {CURATED_DIR}/ with meta.provenance "
            "(bench/tracks.py CuratedProvenance); always test; not covered by data_sha256"
        ),
        "data_sha256": data_hash(documents),
        "extra_files": {name: _sha256(text) for name, text in sorted(extras.items())},
        "scenarios": [asdict(entry) for entry, _ in scenarios],
    }
    return Track(scenarios=scenarios, manifest=manifest, extra_files=extras)


def _build(
    spec: TrackSpec, persona: Persona, template: str, family: str, make: Template, seed: int
) -> ScenarioSpec:
    rng = random.Random(f"{seed}:{persona.id}:{template}")
    scenario = make(persona, rng)
    return scenario.model_copy(
        update={
            "name": f"{template}__{persona.id}",
            "meta": {
                "track": spec.track,
                "domain": spec.domain,
                "content": "synthetic",
                "persona": persona.id,
                "template": template,
                "family": family,
                "seed": seed,
            },
        }
    )


def _held_out(persona_unseen: bool, template_unseen: bool) -> str:
    return {
        (False, False): "none",
        (True, False): "persona",
        (False, True): "template",
        (True, True): "both",
    }[(persona_unseen, template_unseen)]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_track(track: Track, out_dir: Path) -> list[Path]:
    """Scenarios and manifest through bench.generate.write_data (same refusal rules),
    then the extra files. The curated/ folder is never touched."""
    written = write_data(track.as_generated(), out_dir)
    for name, text in track.extra_files.items():
        path = out_dir / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check_track(track: Track, out_dir: Path) -> list[str]:
    problems = check_data(track.as_generated(), out_dir)
    for name, text in track.extra_files.items():
        path = out_dir / name
        if not path.exists():
            problems.append(f"{name} is missing")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"{name} differs from a fresh generation")
    return problems


# ---- curated real stories -----------------------------------------------------------------


class CuratedSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str = Field(pattern=r"^https?://\S+$")
    outlet: str = Field(min_length=1)
    published_on: date
    retrieved_on: date

    @model_validator(mode="after")
    def _retrieved_after_published(self) -> "CuratedSource":
        if self.retrieved_on < self.published_on:
            raise ValueError("retrieved_on is before published_on")
        return self


class CuratedProvenance(BaseModel):
    """`meta.provenance` of a hand-written real-story scenario.

    Labels stay the curator's: the expected states are written by a person reading the
    sources, never by a model. Content is paraphrased; article text is not copied.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["curated"]
    story: str = Field(min_length=1)  # a short slug for the real story
    sources: list[CuratedSource] = Field(min_length=1)  # every development cited
    curated_by: str = Field(min_length=1)  # initials
    curated_on: date
    text_policy: Literal["paraphrased"]  # no verbatim article text in the scenario

    @model_validator(mode="after")
    def _curated_after_retrieval(self) -> "CuratedProvenance":
        if any(source.retrieved_on > self.curated_on for source in self.sources):
            raise ValueError("curated_on is before a source's retrieved_on")
        return self


# A curated name becomes a snapshot file name in results/; keep it a plain slug.
CURATED_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def load_curated(
    data_dir: Path, domain: str, track: str
) -> list[tuple[ManifestEntry, ScenarioSpec]]:
    """Curated scenarios of a track, sorted by file name; a bad one is an error, not a skip."""
    folder = data_dir / CURATED_DIR
    loaded: list[tuple[ManifestEntry, ScenarioSpec]] = []
    for path in sorted(folder.glob("*.yaml")) if folder.is_dir() else []:
        try:
            spec = load_scenario(path)
        except (ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"{path}: not a valid scenario: {exc}") from exc
        if not CURATED_NAME.match(spec.name):
            raise ValueError(f"{path}: name {spec.name!r} must match {CURATED_NAME.pattern}")
        if spec.meta.get("track", track) != track:
            raise ValueError(f"{path}: meta.track must be {track!r}")
        if spec.meta.get("content", "curated") != "curated":
            raise ValueError(
                f"{path}: a curated scenario cannot be labelled {spec.meta['content']!r}"
            )
        if "provenance" not in spec.meta:
            raise ValueError(f"{path}: curated scenario needs meta.provenance")
        try:
            CuratedProvenance.model_validate(spec.meta["provenance"])
        except ValueError as exc:
            raise ValueError(f"{path}: invalid meta.provenance: {exc}") from exc
        if domain_of(spec.meta) != domain:
            raise ValueError(f"{path}: meta.domain must be {domain!r}")
        problems = validate_scenario(spec)
        if problems:
            raise ValueError(f"{path}: {problems}")
        loaded.append(
            (
                ManifestEntry(
                    file=f"{CURATED_DIR}/{path.name}",
                    name=spec.name,
                    persona=str(spec.meta.get("persona", "curated")),
                    template=str(spec.meta.get("template", "curated")),
                    family=str(spec.meta.get("family", "curated")),
                    split="test",
                    held_out=CURATED_SPLIT,
                ),
                spec,
            )
        )
    return loaded


def curated_digest(data_dir: Path) -> dict[str, object]:
    folder = data_dir / CURATED_DIR
    files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
    documents = {path.name: path.read_text(encoding="utf-8") for path in files}
    return {"count": len(files), "sha256": data_hash(documents) if files else None}


# ---- loader -------------------------------------------------------------------------------


def load_track_manifest(data_dir: Path) -> dict[str, Any]:
    return json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))


def load_track(data_dir: Path, split: str = "all") -> list[tuple[ManifestEntry, ScenarioSpec]]:
    """Generated scenarios in manifest order, then curated ones, filtered by split."""
    if split not in TRACK_SPLITS:
        raise ValueError(f"unknown split {split!r}; choose one of {', '.join(TRACK_SPLITS)}")
    manifest = load_track_manifest(data_dir)
    loaded: list[tuple[ManifestEntry, ScenarioSpec]] = []
    if split != CURATED_SPLIT:
        for raw in manifest["scenarios"]:
            entry = ManifestEntry(**raw)
            if split == "train" and entry.split != "train":
                continue
            if split == "test" and entry.split != "test":
                continue
            if split == "strict_test" and entry.held_out not in ("both", "domain"):
                continue
            loaded.append((entry, load_scenario(data_dir / entry.file)))
    if split in ("all", "test", CURATED_SPLIT):
        curated = load_curated(data_dir, manifest["domain"], manifest["track"])
        taken = {raw["name"] for raw in manifest["scenarios"]}
        for entry, _ in curated:
            if entry.name in taken:
                # Two runs of one name would share a snapshot file in results/ (I8).
                raise ValueError(f"{data_dir / entry.file}: name {entry.name!r} is already used")
            taken.add(entry.name)
        loaded.extend(curated)
    return loaded
