"""The 300-pair hand-check protocol (ADR-0009, ADR-0092): sample, label blind, compare.

    uv run python -m training.handcheck sample --out training/data/handcheck_jobs_v0.csv
    # the author fills human_link_type, sure and labeller in the CSV
    uv run python -m training.handcheck report --sheet training/data/handcheck_jobs_v0.csv

Sampling is stratified by split, provenance and label so every stratum the evaluation
reports gets checked, seeded, and shuffled across strata so the labeller cannot read
the stratum from the row order. The sheet shows a row number and the two memories,
nothing else: no pair_id (it names the persona), no link type, provenance or note.
The row -> pair_id key goes to a separate file (<sheet>.key.json) with the seed, size
and pair file hash, and the report re-draws the sample to prove the sheet is it. The
hand labels themselves are the author's; nothing here writes one.
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from bench.linkpairs import LabelledPair, PairMemory, Provenance, read_pairs, write_pairs
from bench.run import RESULTS_DIR, git_short_sha

from ripple.core.links import LinkTypeRegistry
from ripple.domains.jobs.vocabulary import jobs_registry
from training.jobs_pairs import REPO_ROOT, file_sha256, pairs_path

DEFAULT_SAMPLE = 300
DEFAULT_SEED = 20261031
MIN_PER_STRATUM = 10  # a stratum smaller than this is checked whole
NO_LINK = "none"
SHEET_COLUMNS = (
    "row",
    "parent_kind",
    "parent_content",
    "parent_structured",
    "dependent_kind",
    "dependent_content",
    "dependent_structured",
    "human_link_type",  # a registered link type, or "none"; empty = not labelled yet
    "sure",  # yes | no
    "labeller",  # initials
    "comment",
)


class SheetError(ValueError):
    """A sheet or key the protocol cannot accept; the message names the row or file."""


def stratum(pair: LabelledPair) -> str:
    return f"{pair.split}/{pair.provenance}/{'link' if pair.is_link else 'no_link'}"


def allocate(sizes: dict[str, int], total: int, minimum: int = MIN_PER_STRATUM) -> dict[str, int]:
    """Each stratum gets min(size, minimum) first; the rest of `total` is shared in
    proportion to the remaining sizes by largest remainder, so the result is exact
    and deterministic. When the minimums alone exceed `total`, the minimums win: a
    stratum is never left unchecked."""
    if total >= sum(sizes.values()):
        return dict(sizes)
    take = {name: min(size, minimum) for name, size in sizes.items()}
    left = total - sum(take.values())
    if left <= 0:
        return take
    spare = {name: sizes[name] - take[name] for name in sizes}
    pool = sum(spare.values())
    shares = {name: left * spare[name] / pool for name in sizes}
    for name in sizes:
        take[name] += int(shares[name])
    remainder = left - sum(int(s) for s in shares.values())
    by_fraction = sorted(sizes, key=lambda n: (-(shares[n] - int(shares[n])), n))
    for name in by_fraction[:remainder]:
        take[name] += 1
    return take


def _groups(pairs: Sequence[LabelledPair]) -> dict[str, list[LabelledPair]]:
    groups: dict[str, list[LabelledPair]] = defaultdict(list)
    for pair in sorted(pairs, key=lambda p: p.pair_id):
        groups[stratum(pair)].append(pair)
    return groups


def sample_for_handcheck(
    pairs: Sequence[LabelledPair], n: int = DEFAULT_SAMPLE, *, seed: int = DEFAULT_SEED
) -> list[LabelledPair]:
    groups = _groups(pairs)
    quota = allocate({name: len(group) for name, group in groups.items()}, n)
    rng = random.Random(f"{seed}:handcheck")
    chosen: list[LabelledPair] = []
    for name in sorted(groups):
        chosen.extend(rng.sample(groups[name], quota[name]))
    rng.shuffle(chosen)
    return chosen


def _structured(memory: PairMemory) -> str:
    s = memory.structured
    return "" if s is None else f"{s.subject} / {s.attribute} = {s.value}"


def key_path(sheet: Path) -> Path:
    return sheet.with_name(sheet.name + ".key.json")


def _display(path: Path) -> str:
    resolved = path.resolve()
    return (
        resolved.relative_to(REPO_ROOT).as_posix()
        if resolved.is_relative_to(REPO_ROOT)
        else resolved.as_posix()
    )


def write_sheet(
    sheet: Path, pairs_file: Path, *, n: int = DEFAULT_SAMPLE, seed: int = DEFAULT_SEED
) -> int:
    """Draw the sample and write the blind sheet plus its key file; returns the row count."""
    pairs = list(read_pairs(pairs_file))
    chosen = sample_for_handcheck(pairs, n, seed=seed)
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row, pair in enumerate(chosen, start=1):
            writer.writerow(
                {
                    "row": row,
                    "parent_kind": pair.parent.kind,
                    "parent_content": pair.parent.content,
                    "parent_structured": _structured(pair.parent),
                    "dependent_kind": pair.dependent.kind,
                    "dependent_content": pair.dependent.content,
                    "dependent_structured": _structured(pair.dependent),
                    "human_link_type": "",
                    "sure": "",
                    "labeller": "",
                    "comment": "",
                }
            )
    groups = _groups(pairs)
    key = {
        "pairs_file": _display(pairs_file),
        "pairs_sha256": file_sha256(pairs_file),
        "n": n,
        "seed": seed,
        "allocation": allocate({k: len(v) for k, v in groups.items()}, n),
        "rows": [pair.pair_id for pair in chosen],
    }
    key_path(sheet).write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return len(chosen)


def read_key(sheet: Path) -> dict[str, object]:
    path = key_path(sheet)
    if not path.exists():
        raise SheetError(f"{path.name} is missing: the sheet cannot be joined to its pairs")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_key(key: dict[str, object], pairs_file: Path, pairs: Sequence[LabelledPair]) -> None:
    """The sheet must be the seeded sample of this pair file, not a hand-picked one."""
    if key.get("pairs_sha256") != file_sha256(pairs_file):
        raise SheetError("the sheet was drawn from another version of the pair file")
    n, seed = key.get("n"), key.get("seed")
    if not isinstance(n, int) or not isinstance(seed, int):
        raise SheetError("the key file records no integer n and seed")
    expected = [p.pair_id for p in sample_for_handcheck(pairs, n, seed=seed)]
    if key.get("rows") != expected:
        raise SheetError(f"the sheet's rows are not the seeded sample (n={n}, seed={seed})")


@dataclass(frozen=True)
class HandLabel:
    pair_id: str
    link_type: str | None  # None = the labeller says no link
    sure: bool
    labeller: str
    comment: str


def read_sheet(sheet: Path, registry: LinkTypeRegistry) -> tuple[list[HandLabel], int]:
    """Labelled rows, and how many rows are still blank. A half-filled row is an error,
    not a guess: a label without its labeller cannot enter the gold set. Accepts the
    byte-order mark spreadsheet programs add to "CSV UTF-8"."""
    rows = read_key(sheet).get("rows")
    if not isinstance(rows, list):
        raise SheetError(f"{key_path(sheet).name} has no rows list")
    labels: list[HandLabel] = []
    pending = 0
    seen: set[int] = set()
    known = registry.known_types()
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            where = f"{sheet.name} row {row.get('row')}"
            try:
                number = int(row.get("row") or "")
            except ValueError as exc:
                raise SheetError(f"{where}: row is not a number") from exc
            if number in seen or not 1 <= number <= len(rows):
                raise SheetError(f"{where}: duplicated or unknown row")
            seen.add(number)
            answer = (row.get("human_link_type") or "").strip()
            labeller = (row.get("labeller") or "").strip()
            sure = (row.get("sure") or "").strip().lower()
            if not answer and not labeller and not sure:
                pending += 1
                continue
            if not answer or not labeller:
                raise SheetError(f"{where}: human_link_type and labeller are both required")
            if answer != NO_LINK and answer not in known:
                raise SheetError(f"{where}: {answer!r} is not a link type or {NO_LINK!r}")
            if sure not in ("yes", "no"):
                raise SheetError(f"{where}: sure must be yes or no")
            labels.append(
                HandLabel(
                    pair_id=str(rows[number - 1]),
                    link_type=None if answer == NO_LINK else answer,
                    sure=sure == "yes",
                    labeller=labeller,
                    comment=(row.get("comment") or "").strip(),
                )
            )
    return labels, pending


# ---- agreement ------------------------------------------------------------------------


@dataclass
class Agreement:
    n: int = 0
    both_link: int = 0
    both_none: int = 0
    silver_only: int = 0  # silver says link, human says none
    human_only: int = 0
    type_match: int = 0  # among both_link

    def add(self, silver: str | None, human: str | None) -> None:
        self.n += 1
        if silver is not None and human is not None:
            self.both_link += 1
            self.type_match += int(silver == human)
        elif silver is not None:
            self.silver_only += 1
        elif human is not None:
            self.human_only += 1
        else:
            self.both_none += 1

    def as_dict(self) -> dict[str, object]:
        observed = None if self.n == 0 else (self.both_link + self.both_none) / self.n
        return {
            "n": self.n,
            "both_link": self.both_link,
            "both_none": self.both_none,
            "silver_link_human_none": self.silver_only,
            "silver_none_human_link": self.human_only,
            "detection_agreement": observed,
            "detection_kappa": self.kappa(),
            "type_agreement_when_both_link": (
                None if self.both_link == 0 else self.type_match / self.both_link
            ),
        }

    def kappa(self) -> float | None:
        """Cohen's kappa on link / no-link; None when chance agreement is total (one
        class only), where kappa is undefined."""
        if self.n == 0:
            return None
        observed = (self.both_link + self.both_none) / self.n
        silver_link = (self.both_link + self.silver_only) / self.n
        human_link = (self.both_link + self.human_only) / self.n
        expected = silver_link * human_link + (1 - silver_link) * (1 - human_link)
        return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(
    pairs: Sequence[LabelledPair], labels: Sequence[HandLabel]
) -> dict[str, dict[str, object]]:
    by_id = {p.pair_id: p for p in pairs}
    missing = [label.pair_id for label in labels if label.pair_id not in by_id]
    if missing:
        raise SheetError(f"sheet names pairs not in the pair file: {missing[:5]}")
    table: dict[str, Agreement] = defaultdict(Agreement)
    for label in labels:
        pair = by_id[label.pair_id]
        for key in ("overall", f"provenance={pair.provenance}", f"stratum={stratum(pair)}"):
            table[key].add(pair.link_type, label.link_type)
        if label.sure:
            table["overall_sure_only"].add(pair.link_type, label.link_type)
    return {key: table[key].as_dict() for key in sorted(table)}


def gold_pairs(
    pairs: Sequence[LabelledPair], labels: Sequence[HandLabel], registry: LinkTypeRegistry
) -> list[LabelledPair]:
    """The hand-checked pairs as HUMAN-provenance C5 pairs (the gold set), with the silver
    label kept in the note so the disagreement stays visible."""
    by_id = {p.pair_id: p for p in pairs}
    gold: list[LabelledPair] = []
    for label in labels:
        silver = by_id[label.pair_id]
        gold.append(
            silver.model_copy(
                update={
                    "link_type": label.link_type,
                    "link_class": None
                    if label.link_type is None
                    else registry.class_of(label.link_type),
                    "provenance": Provenance.HUMAN,
                    "labeller": label.labeller,
                    "note": f"silver {silver.provenance}:{silver.link_type or NO_LINK}"
                    + ("" if label.sure else "; unsure"),
                }
            )
        )
    return gold


def write_report(
    pairs_file: Path,
    sheet: Path,
    *,
    registry: LinkTypeRegistry,
    results_root: Path = RESULTS_DIR,
) -> Path:
    """Everything is checked before anything is written, so a bad sheet leaves no
    half-written results folder."""
    pairs = list(read_pairs(pairs_file))
    key = read_key(sheet)
    verify_key(key, pairs_file, pairs)
    labels, pending = read_sheet(sheet, registry)
    table = agreement(pairs, labels)
    gold = gold_pairs(pairs, labels, registry)
    track = sorted({p.track for p in pairs})
    sha = git_short_sha()
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    base = results_root / f"{today}_handcheck_{'_'.join(track)}_{sha}"
    run_dir, counter = base, 1
    while run_dir.exists():
        counter += 1
        run_dir = base.with_name(f"{base.name}_{counter}")
    run_dir.mkdir(parents=True)
    config = {
        "suite": "handcheck",
        "data": {"pairs_file": _display(pairs_file), "pairs_sha256": file_sha256(pairs_file)},
        "sheet": _display(sheet),
        "sheet_sha256": file_sha256(sheet),
        "sample": {"n": key["n"], "seed": key["seed"], "allocation": key["allocation"]},
        "labelled": len(labels),
        "pending": pending,
        "labellers": sorted({label.labeller for label in labels}),
        "git_sha": sha,
        "run_at": datetime.now(tz=UTC).isoformat(),
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    write_pairs(run_dir / "gold_pairs.jsonl", gold)
    lines = [
        f"# Hand-check agreement: {', '.join(track)}",
        "",
        f"{len(labels)} labelled, {pending} pending. Silver = the generated label; "
        "human = the author's blind label. One labeller: this is silver-versus-human "
        "agreement, not inter-annotator agreement.",
        "",
        "| stratum | n | agreement | kappa | silver link, human none | silver none, human link "
        "| type agreement |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, cell in table.items():
        lines.append(
            f"| {name} | {cell['n']} | {_fmt(cell['detection_agreement'])} "
            f"| {_fmt(cell['detection_kappa'])} | {cell['silver_link_human_none']} "
            f"| {cell['silver_none_human_link']} | {_fmt(cell['type_agreement_when_both_link'])} |"
        )
    (run_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


def _fmt(value: object) -> str:
    return "n/a" if value is None else f"{float(str(value)):.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The 300-pair hand-check protocol.")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="write a blind labelling sheet and its key")
    sample.add_argument("--pairs", type=Path, default=pairs_path())
    sample.add_argument("--n", type=int, default=DEFAULT_SAMPLE)
    sample.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sample.add_argument("--out", type=Path, required=True)
    report = commands.add_parser("report", help="agreement of the sheet with the silver labels")
    report.add_argument("--pairs", type=Path, default=pairs_path())
    report.add_argument("--sheet", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "sample":
        count = write_sheet(args.out, args.pairs, n=args.n, seed=args.seed)
        print(f"wrote {count} rows to {args.out} and the key to {key_path(args.out).name}")
        return 0
    run_dir = write_report(args.pairs, args.sheet, registry=jobs_registry())
    print(f"wrote {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
