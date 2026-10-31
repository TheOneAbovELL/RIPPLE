"""Labelled link pairs: the shared format for link-finder data and its evaluation (C5).

Coordinator-owned contract for wave B (docs/plans/wave-b.md). WS-14 generates pairs
for the jobs track and builds the training data and evaluation harness over them; WS-15
generates the finance track (test only, H4) in the same format so one harness scores
both. Nothing here trains or scores; it only fixes the shape and the split rule.

A pair is (parent memory, dependent memory) with the link a correct linker would write
between them, or no link. Direction follows docs/03: parent -> dependent, the dependent
is re-examined when the parent changes. Memories are carried as text plus optional
structure, never as store ids, so a pair file is self-contained and leaks nothing about
the store it came from.
"""

import json
from collections.abc import Iterable, Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ripple.core.models import LinkClass, StructuredFact


class Provenance(StrEnum):
    """Where a label came from (proposal 0002); evaluation is stratified by it."""

    RULE = "rule"  # derivable from structure (eligibility_of, criteria_from, ...)
    SCENARIO = "scenario"  # a link written in a RippleBench scenario file
    LLM = "llm"  # an LLM labeller's answer, schema-validated (I4)
    HUMAN = "human"  # hand-checked; the 300-pair gold set (ADR-0009)


class Split(StrEnum):
    TRAIN = "train"
    TEST = "test"


class PairMemory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)
    structured: StructuredFact | None = None


class LabelledPair(BaseModel):
    """One candidate edge and its label. `link_type` None means "no link"."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pair_id: str = Field(min_length=1)  # stable across regenerations of the same seed
    track: str = Field(min_length=1)  # jobs_v0, jobs_v1, news_v1, finance_v1
    domain: str = Field(min_length=1)  # the adapter whose link types label it
    persona: str = Field(min_length=1)
    template: str = Field(min_length=1)
    split: Split
    parent: PairMemory
    dependent: PairMemory
    link_type: str | None = None
    link_class: LinkClass | None = None
    provenance: Provenance
    labeller: str | None = None  # model id and prompt version for LLM, initials for human
    note: str | None = None

    @model_validator(mode="after")
    def _link_type_and_class_together(self) -> "LabelledPair":
        if (self.link_type is None) != (self.link_class is None):
            raise ValueError("link_type and link_class are set together or not at all")
        if self.provenance in (Provenance.LLM, Provenance.HUMAN) and not self.labeller:
            raise ValueError(f"a {self.provenance} label names its labeller")
        return self

    @property
    def is_link(self) -> bool:
        return self.link_type is not None


def split_for(persona_is_train: bool, template_is_train: bool) -> Split:
    """docs/04: split by persona and template, never by item. A pair is train only when
    both its persona and its template are train; everything else is test."""
    return Split.TRAIN if persona_is_train and template_is_train else Split.TEST


def write_pairs(path: Path, pairs: Iterable[LabelledPair]) -> int:
    """JSON Lines, one pair per line, sorted by pair_id so regeneration diffs cleanly."""
    ordered = sorted(pairs, key=lambda p: p.pair_id)
    seen: set[str] = set()
    for pair in ordered:
        if pair.pair_id in seen:
            raise ValueError(f"duplicate pair_id {pair.pair_id!r}")
        seen.add(pair.pair_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as out:
        for pair in ordered:
            out.write(json.dumps(pair.model_dump(mode="json"), sort_keys=True) + "\n")
    return len(ordered)


def read_pairs(path: Path) -> Iterator[LabelledPair]:
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, start=1):
            if line.strip():
                try:
                    yield LabelledPair.model_validate_json(line)
                except ValueError as exc:
                    raise ValueError(f"{path}:{number}: {exc}") from exc
