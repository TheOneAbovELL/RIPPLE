"""STALE, the external benchmark, read from a local copy (ADR-0103).

    RIPPLE_STALE_PATH=/path/to/stale uv run python -m bench.stale    # summarise a local copy

Nothing here downloads anything: the author places the dataset on disk and points
`RIPPLE_STALE_PATH` at a .jsonl file or a folder of them. Unset, empty or missing, the
loader raises ConfigurationError naming the variable.

The record shape below is the one ADR-0103 declares; the session that wrote it was
offline and could not check it against the published release. Every field is strict
(`extra="forbid"`), so a release that differs fails loudly at load time with the
offending file and line, and the fix is a small converter, never a silent mis-mapping.

Whether STALE maps onto Ripple's memory API without adaptation is the docs/04 "Open"
question; ADR-0103 records why it stays open. No runner is built until it is answered.
"""

import argparse
import datetime as dt
import os
import sys
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ripple.core.errors import ConfigurationError

STALE_PATH_VAR = "RIPPLE_STALE_PATH"


class StaleTurn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class StaleSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1)
    date: dt.date
    turns: list[StaleTurn] = Field(min_length=1)


class StaleItem(BaseModel):
    """One test item: a dated multi-session history and a probe question whose right
    answer needs the later, implicitly conflicting statement, not the earlier one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(min_length=1)
    sessions: list[StaleSession] = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)  # the up-to-date answer
    stale_answer: str | None = None  # the answer the superseded statement would give
    conflict_type: str | None = None  # the release's own category label, kept verbatim
    evidence_session_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _session_ids_are_consistent(self) -> "StaleItem":
        ids = [session.session_id for session in self.sessions]
        if len(set(ids)) != len(ids):
            raise ValueError("session_id repeats within the item")
        unknown = set(self.evidence_session_ids) - set(ids)
        if unknown:
            raise ValueError(f"evidence_session_ids name unknown sessions {sorted(unknown)}")
        return self


class StaleFormatError(ConfigurationError):
    """The local copy does not have the shape ADR-0103 declares; write a converter."""


def stale_path_from_env(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    raw = env.get(STALE_PATH_VAR, "").strip()
    if not raw:
        raise ConfigurationError(
            f"{STALE_PATH_VAR} is not set; point it at a local copy of STALE "
            "(the bench never downloads it; ADR-0103)"
        )
    path = Path(raw)
    if not path.exists():
        raise ConfigurationError(f"{STALE_PATH_VAR}={raw!r} does not exist")
    return path


def stale_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files = sorted(path.glob("*.jsonl"))
    if not files:
        raise ConfigurationError(
            f"{STALE_PATH_VAR}={str(path)!r} holds no .jsonl files (subfolders are not read)"
        )
    return files


def iter_stale(path: Path) -> Iterator[StaleItem]:
    """Items in file order; the first malformed line stops the load with its location."""
    seen: set[str] = set()
    for file in stale_files(path):
        try:
            # utf-8-sig: a byte-order mark from a Windows editor is not a format error.
            lines = file.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError as exc:
            raise StaleFormatError(f"{file}: not UTF-8 text: {exc}") from exc
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                item = StaleItem.model_validate_json(line)
            except ValidationError as exc:
                raise StaleFormatError(
                    f"{file}:{number}: not in the ADR-0103 shape: {exc}"
                ) from exc
            if item.item_id in seen:
                raise StaleFormatError(f"{file}:{number}: duplicate item_id {item.item_id!r}")
            seen.add(item.item_id)
            yield item


def load_stale(environ: Mapping[str, str] | None = None) -> list[StaleItem]:
    path = stale_path_from_env(environ)
    items = list(iter_stale(path))
    if not items:
        raise StaleFormatError(f"{path}: no items; the .jsonl files are empty")
    return items


def summarise(items: Sequence[StaleItem]) -> dict[str, object]:
    """Counts only; reported so the author can check a local copy against the paper."""
    return {
        "items": len(items),
        "sessions": sum(len(item.sessions) for item in items),
        "turns": sum(len(s.turns) for item in items for s in item.sessions),
        "conflict_types": dict(
            sorted(Counter(item.conflict_type or "unlabelled" for item in items).items())
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    argparse.ArgumentParser(
        description=f"Summarise the local STALE copy at ${STALE_PATH_VAR}"
    ).parse_args(argv)
    try:
        items = load_stale()
    except ConfigurationError as exc:
        print(f"STALE not available: {exc}", file=sys.stderr)
        return 2
    for key, value in summarise(items).items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
