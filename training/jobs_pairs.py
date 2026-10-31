"""RippleBench v0 → C5 labelled link pairs for the jobs track (ADR-0090, ADR-0091).

    uv run python -m training.jobs_pairs          # write the pair file and its manifest
    uv run python -m training.jobs_pairs --check  # exit 1 if the checked-in files differ

Each scenario is replayed statically into snapshots (training/replay.py: the seeded
state, then the state after every event, with the versioning and wave rules of docs/03
and the engine contract). No engine runs.

Every ordered pair of distinct memories that coexist in a snapshot gets claims:
a scenario link (SCENARIO positive), a structure-rule link (RULE, proposal 0002), a
transitive dependency with no direct link (excluded: neither label is safe), or no
link (a SCENARIO negative: inside one scenario the link list is complete). Claims
merge by (persona, parent, dependent); contradictions are dropped and counted, except
a rule type differing from a scenario link's type, where the scenario wins.
Negatives are sampled to a fixed ratio (ADR-0091), pairs are split with
`split_for`, and a train pair whose texts equal a test pair's texts is dropped.
"""

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import permutations
from pathlib import Path

from bench.linkpairs import LabelledPair, PairMemory, Provenance, Split, split_for, write_pairs
from bench.scenario import ScenarioSpec, load_scenario

from ripple.core.links import LinkTypeRegistry
from ripple.domains.jobs.vocabulary import DOMAIN, jobs_registry
from training.leakage import TEMPLATE_JOIN, leakage_problems
from training.replay import scenario_snapshots
from training.structure_rules import label_by_structure

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "bench" / "data" / "jobs_v0"
OUTPUT_DIR = REPO_ROOT / "training" / "data"
TRACK = "jobs_v0"
GENERATOR_VERSION = 1
DEFAULT_SEED = 20261031
NEGATIVE_RATIO = 3  # sampled negatives per positive, per persona (ADR-0091)
# Written to the manifest even when zero, so "none happened" is a recorded fact.
PROCESS_COUNTERS = (
    "candidate_pairs",
    "dropped_conflicting_rule_labels",
    "dropped_conflicting_scenario_labels",
    "dropped_rule_vs_closed_world",
    "excluded_indirect",
    "negatives_available",
    "negatives_reversed_link",
    "negatives_sampled_other",
    "positives_rule_only",
    "rule_vs_scenario_agree",
    "rule_vs_scenario_disagree",
    "rule_vs_scenario_missed",
    "train_dropped_text_in_test",
)


def pairs_path(output_dir: Path = OUTPUT_DIR) -> Path:
    return output_dir / f"{TRACK}_pairs.jsonl"


def manifest_path(output_dir: Path = OUTPUT_DIR) -> Path:
    return output_dir / f"{TRACK}_pairs.manifest.json"


# ---- claims and labels ------------------------------------------------------------


class ClaimKind(StrEnum):
    LINK = "link"
    NO_LINK = "no_link"
    INDIRECT = "indirect"  # a transitive dependency with no direct link


@dataclass(frozen=True)
class Claim:
    kind: ClaimKind
    provenance: Provenance
    templates: frozenset[str]
    link_type: str | None = None
    rule: str | None = None


@dataclass(frozen=True)
class PairKey:
    persona: str
    parent: str  # PairMemory JSON, so equal texts and structure merge
    dependent: str


@dataclass
class _Candidate:
    parent: PairMemory
    dependent: PairMemory
    claims: list[Claim] = field(default_factory=list)


def _memory_key(memory: PairMemory) -> str:
    return memory.model_dump_json()


def _ancestor_pairs(links: Iterable[tuple[str, str, str]]) -> set[tuple[str, str]]:
    children: dict[str, set[str]] = defaultdict(set)
    for parent, dependent, _ in links:
        children[parent].add(dependent)
    reachable: set[tuple[str, str]] = set()
    for start in list(children):
        stack = list(children[start])
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            reachable.add((start, node))
            stack.extend(children.get(node, ()))
    return reachable


@dataclass
class PairBuild:
    pairs: list[LabelledPair]
    stats: dict[str, object]


def collect_candidates(
    scenarios: Sequence[ScenarioSpec], registry: LinkTypeRegistry
) -> dict[PairKey, _Candidate]:
    candidates: dict[PairKey, _Candidate] = {}

    def claim(persona: str, parent: PairMemory, dependent: PairMemory, item: Claim) -> None:
        key = PairKey(persona, _memory_key(parent), _memory_key(dependent))
        candidates.setdefault(key, _Candidate(parent, dependent)).claims.append(item)

    for spec in scenarios:
        for snap in scenario_snapshots(spec, registry):
            templates = frozenset({snap.template})
            direct = {(p, d): t for p, d, t in snap.links}
            indirect = _ancestor_pairs(snap.links)
            for a, b in permutations(sorted(snap.memories), 2):
                parent, dependent = snap.memories[a], snap.memories[b]
                if (a, b) in direct:
                    item = Claim(ClaimKind.LINK, Provenance.SCENARIO, templates, direct[(a, b)])
                elif (a, b) in indirect:
                    item = Claim(ClaimKind.INDIRECT, Provenance.SCENARIO, templates)
                else:
                    item = Claim(ClaimKind.NO_LINK, Provenance.SCENARIO, templates)
                claim(snap.persona, parent, dependent, item)
                rule = label_by_structure(parent, dependent, snap.memories.values())
                if rule is not None:
                    claim(
                        snap.persona,
                        parent,
                        dependent,
                        Claim(
                            ClaimKind.LINK, Provenance.RULE, templates, rule.link_type, rule.rule
                        ),
                    )
    return candidates


@dataclass(frozen=True)
class _Resolved:
    key: PairKey
    candidate: _Candidate
    link_type: str | None
    provenance: Provenance
    note: str


def resolve(
    candidates: Mapping[PairKey, _Candidate], stats: Counter[str]
) -> tuple[list[_Resolved], list[_Resolved]]:
    """Merge every claim on a pair into one label; return (positives, negative pool)."""
    positives: list[_Resolved] = []
    negatives: list[_Resolved] = []
    for key in sorted(candidates, key=lambda k: (k.persona, k.parent, k.dependent)):
        candidate = candidates[key]
        claims = candidate.claims
        scenario_types = {
            c.link_type
            for c in claims
            if c.kind is ClaimKind.LINK and c.provenance is Provenance.SCENARIO
        }
        rule_claims = [
            c for c in claims if c.kind is ClaimKind.LINK and c.provenance is Provenance.RULE
        ]
        rule_types = {c.link_type for c in rule_claims}
        has_no_link = any(c.kind is ClaimKind.NO_LINK for c in claims)
        has_indirect = any(c.kind is ClaimKind.INDIRECT for c in claims)
        if scenario_types:
            if len(scenario_types) > 1 or has_no_link:
                stats["dropped_conflicting_scenario_labels"] += 1
                continue
            [link_type] = scenario_types
            if rule_types == {link_type}:
                # Derivable from structure and confirmed by the scenario: the RULE
                # stratum is "links structure determines" (ADR-0090), the rest of the
                # scenario links are the hidden ones a rule cannot see.
                stats["rule_vs_scenario_agree"] += 1
                rules = sorted({c.rule for c in rule_claims if c.rule})
                note = f"rule:{','.join(rules)}; scenario agrees"
                positives.append(_Resolved(key, candidate, link_type, Provenance.RULE, note))
                continue
            if rule_types:
                stats["rule_vs_scenario_disagree"] += 1
            else:
                stats["rule_vs_scenario_missed"] += 1
            positives.append(
                _Resolved(key, candidate, link_type, Provenance.SCENARIO, "scenario link")
            )
        elif rule_types:
            if len(rule_types) > 1:
                stats["dropped_conflicting_rule_labels"] += 1
            elif has_no_link or has_indirect:
                # A scenario's complete link list says otherwise: the rule is wrong
                # here, or the scenario is; neither label is safe to train on.
                stats["dropped_rule_vs_closed_world"] += 1
            else:
                [link_type] = rule_types
                stats["positives_rule_only"] += 1
                rules = sorted({c.rule for c in rule_claims if c.rule})
                positives.append(
                    _Resolved(key, candidate, link_type, Provenance.RULE, f"rule:{','.join(rules)}")
                )
        elif has_indirect:
            stats["excluded_indirect"] += 1
        elif has_no_link:
            negatives.append(_Resolved(key, candidate, None, Provenance.SCENARIO, ""))
    return positives, negatives


def sample_negatives(
    positives: Sequence[_Resolved],
    negatives: Sequence[_Resolved],
    *,
    seed: int,
    ratio: int,
    stats: Counter[str],
) -> list[_Resolved]:
    """Per persona: keep every reversed positive (direction is the label a linker most
    often gets wrong), then sample the rest up to `ratio` negatives per positive."""
    linked = {(p.key.persona, p.key.parent, p.key.dependent) for p in positives}
    by_persona_pos = Counter(p.key.persona for p in positives)
    kept: list[_Resolved] = []
    for persona in sorted({n.key.persona for n in negatives}):
        pool = [n for n in negatives if n.key.persona == persona]
        reversed_links = [n for n in pool if (persona, n.key.dependent, n.key.parent) in linked]
        others = [n for n in pool if (persona, n.key.dependent, n.key.parent) not in linked]
        budget = max(0, ratio * by_persona_pos[persona] - len(reversed_links))
        rng = random.Random(f"{seed}:negatives:{persona}")
        sampled = rng.sample(others, min(budget, len(others)))
        stats["negatives_available"] += len(pool)
        stats["negatives_reversed_link"] += len(reversed_links)
        stats["negatives_sampled_other"] += len(sampled)
        kept.extend(
            _Resolved(n.key, n.candidate, None, n.provenance, "reversed link")
            for n in reversed_links
        )
        kept.extend(
            _Resolved(n.key, n.candidate, None, n.provenance, "same scenario, no link")
            for n in sampled
        )
    return kept


def _templates_of(candidate: _Candidate) -> list[str]:
    return sorted({t for c in candidate.claims for t in c.templates})


def _pair_id(key: PairKey) -> str:
    digest = hashlib.sha256(f"{key.parent}\x1f{key.dependent}".encode()).hexdigest()[:16]
    return f"{TRACK}:{key.persona}:{digest}"


def to_labelled(
    resolved: _Resolved,
    *,
    train_personas: frozenset[str],
    train_templates: frozenset[str],
    registry: LinkTypeRegistry,
) -> LabelledPair:
    templates = _templates_of(resolved.candidate)
    split = split_for(
        resolved.key.persona in train_personas, all(t in train_templates for t in templates)
    )
    return LabelledPair(
        pair_id=_pair_id(resolved.key),
        track=TRACK,
        domain=DOMAIN,
        persona=resolved.key.persona,
        template=TEMPLATE_JOIN.join(templates),
        split=split,
        parent=resolved.candidate.parent,
        dependent=resolved.candidate.dependent,
        link_type=resolved.link_type,
        link_class=None if resolved.link_type is None else registry.class_of(resolved.link_type),
        provenance=resolved.provenance,
        note=resolved.note or None,
    )


def text_key(pair: LabelledPair) -> frozenset[str]:
    """Unordered: a train pair (a, b) teaches about a test pair (b, a) as well."""
    return frozenset({pair.parent.content, pair.dependent.content})


def decontaminate(pairs: Sequence[LabelledPair], stats: Counter[str]) -> list[LabelledPair]:
    test_texts = {text_key(p) for p in pairs if p.split is Split.TEST}
    kept: list[LabelledPair] = []
    for pair in pairs:
        if pair.split is Split.TRAIN and text_key(pair) in test_texts:
            stats["train_dropped_text_in_test"] += 1
            continue
        kept.append(pair)
    return kept


def build_pairs(
    source_dir: Path = SOURCE_DIR, *, seed: int = DEFAULT_SEED, ratio: int = NEGATIVE_RATIO
) -> PairBuild:
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    train_personas = frozenset(manifest["personas"]["train"])
    train_templates = frozenset(manifest["templates"]["train"])
    registry = jobs_registry()
    scenarios = [load_scenario(source_dir / entry["file"]) for entry in manifest["scenarios"]]
    stats: Counter[str] = Counter()
    candidates = collect_candidates(scenarios, registry)
    stats["candidate_pairs"] = len(candidates)
    positives, negative_pool = resolve(candidates, stats)
    negatives = sample_negatives(positives, negative_pool, seed=seed, ratio=ratio, stats=stats)
    labelled = [
        to_labelled(
            r, train_personas=train_personas, train_templates=train_templates, registry=registry
        )
        for r in [*positives, *negatives]
    ]
    labelled = decontaminate(labelled, stats)
    problems = leakage_problems(
        labelled,
        test_personas=frozenset(manifest["personas"]["test"]),
        test_templates=frozenset(manifest["templates"]["test"]),
    )
    if problems:
        raise ValueError("leaking pair set: " + "; ".join(problems[:5]))
    labelled.sort(key=lambda p: p.pair_id)
    return PairBuild(
        labelled,
        {
            "source": {
                "dir": source_dir.relative_to(REPO_ROOT).as_posix()
                if source_dir.is_relative_to(REPO_ROOT)
                else str(source_dir),
                "track": manifest["track"],
                "data_sha256": manifest["data_sha256"],
                "generator_seed": manifest["seed"],
                "test_personas": sorted(manifest["personas"]["test"]),
                "test_templates": sorted(manifest["templates"]["test"]),
            },
            "process": {name: stats[name] for name in PROCESS_COUNTERS},
        },
    )


def counts(pairs: Sequence[LabelledPair]) -> dict[str, object]:
    by_cell: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    for pair in pairs:
        label = "link" if pair.is_link else "no_link"
        by_cell[f"{pair.split}/{pair.provenance}/{label}"] += 1
        by_type[f"{pair.split}/{pair.link_type or 'none'}"] += 1
    return {
        "total": len(pairs),
        "by_split_provenance_label": dict(sorted(by_cell.items())),
        "by_split_link_type": dict(sorted(by_type.items())),
        "personas": sorted({p.persona for p in pairs}),
        **text_overlap(pairs),
    }


def text_overlap(pairs: Sequence[LabelledPair]) -> dict[str, object]:
    """What the persona/template split does not remove: identical test pairs across
    personas, identical texts with different labels, and test pairs that share one
    text with train (ADR-0091; read before trusting a test number)."""
    labels_by_text: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for pair in pairs:
        key = (pair.split.value, pair.parent.content, pair.dependent.content)
        labels_by_text[key].add(pair.link_type or "none")
    test = [p for p in pairs if p.split is Split.TEST]
    train_texts = {
        text
        for p in pairs
        if p.split is Split.TRAIN
        for text in (p.parent.content, p.dependent.content)
    }
    prevalence = {
        split.value: _share([p.is_link for p in pairs if p.split is split]) for split in Split
    }
    return {
        "prevalence_by_split": prevalence,
        "test_duplicate_texts": len(test)
        - len({(p.parent.content, p.dependent.content) for p in test}),
        "same_texts_different_labels": sum(1 for v in labels_by_text.values() if len(v) > 1),
        "test_pairs_sharing_a_text_with_train": sum(
            1 for p in test if p.parent.content in train_texts or p.dependent.content in train_texts
        ),
    }


def _share(flags: Sequence[bool]) -> float | None:
    return None if not flags else round(sum(flags) / len(flags), 4)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_build(build: PairBuild, output_dir: Path, *, seed: int, ratio: int) -> Path:
    path = pairs_path(output_dir)
    write_pairs(path, build.pairs)
    manifest = {
        "track": TRACK,
        "format": "C5 LabelledPair JSON Lines (bench/linkpairs.py)",
        "generator": {"module": "training.jobs_pairs", "version": GENERATOR_VERSION},
        "seed": seed,
        "negative_ratio": ratio,
        "content": "synthetic (RippleBench v0 jobs track)",
        "file": path.name,
        "file_sha256": file_sha256(path),
        **build.stats,
        "counts": counts(build.pairs),
    }
    target = manifest_path(output_dir)
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def check(output_dir: Path, *, seed: int, ratio: int, scratch: Path) -> list[str]:
    """Regenerate into `scratch` and compare with the files in `output_dir`."""
    write_build(build_pairs(seed=seed, ratio=ratio), scratch, seed=seed, ratio=ratio)
    problems: list[str] = []
    for name in (pairs_path(output_dir).name, manifest_path(output_dir).name):
        current, fresh = output_dir / name, scratch / name
        if not current.exists():
            problems.append(f"{current} is missing")
        elif current.read_bytes() != fresh.read_bytes():
            problems.append(f"{current} differs from a fresh generation")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--ratio", type=int, default=NEGATIVE_RATIO)
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args(argv)
    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as scratch:
            problems = check(args.out, seed=args.seed, ratio=args.ratio, scratch=Path(scratch))
        for problem in problems:
            print(problem, file=sys.stderr)
        print("ok" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    build = build_pairs(seed=args.seed, ratio=args.ratio)
    path = write_build(build, args.out, seed=args.seed, ratio=args.ratio)
    print(f"wrote {len(build.pairs)} pairs to {path}")
    print(json.dumps(counts(build.pairs)["by_split_provenance_label"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
