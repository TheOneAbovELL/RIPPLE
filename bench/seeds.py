"""Generator seeds for headline numbers (ADR-0121).

docs/04 asks for three seeds minimum for headline numbers. With the scripted oracle
resolver a replay has no randomness of its own, so a run seed would change nothing;
the variation worth measuring is in the data. A seed here is therefore a *generator*
seed: the track is generated again with it (personas, values, the persona/template
split), in memory, so the checked-in files of the default seed are never touched.

The seeds of a track are its generator's DEFAULT_SEED and the next ones
(DEFAULT_SEED + i). The default seed is generated too and must reproduce the
checked-in manifest's data hash exactly; a mismatch is drift and is refused rather
than run on data nobody checked in.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from bench.generate import ManifestEntry, load_manifest
from bench.scenario import ScenarioSpec

SEED_COUNT = 3
DATA_ROOT = Path(__file__).resolve().parent / "data"
# suite -> (generator module, checked-in data folder)
GENERATORS: dict[str, tuple[str, str]] = {
    "v0": ("bench.generate", "jobs_v0"),
    "news_v1": ("bench.generate_news", "news_v1"),
    "finance_v1": ("bench.generate_finance", "finance_v1"),
}


class SeedDriftError(ValueError):
    """The default seed no longer reproduces the checked-in data."""


@dataclass(frozen=True)
class SeededTrack:
    suite: str
    seed: int
    manifest: dict[str, Any]
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]]

    @property
    def data_sha256(self) -> str:
        return str(self.manifest["data_sha256"])


def _module(suite: str) -> ModuleType:
    # Imported on demand: a broken generator must not break the other suites (bench.run).
    import importlib

    if suite not in GENERATORS:
        raise ValueError(f"suite {suite!r} has no generator; seeded suites: {sorted(GENERATORS)}")
    return importlib.import_module(GENERATORS[suite][0])


def default_seed(suite: str) -> int:
    return int(_module(suite).DEFAULT_SEED)


def generator_seeds(suite: str, count: int = SEED_COUNT) -> tuple[int, ...]:
    if count < 1:
        raise ValueError("at least one generator seed is needed")
    first = default_seed(suite)
    return tuple(first + offset for offset in range(count))


def generate_track(suite: str, seed: int) -> SeededTrack:
    """The whole track generated with `seed`; the default seed is checked against the
    checked-in manifest."""
    generated = _module(suite).generate(seed)
    manifest: dict[str, Any] = generated.manifest
    scenarios: list[tuple[ManifestEntry, ScenarioSpec]] = generated.scenarios
    if seed == default_seed(suite):
        checked_in = load_manifest(DATA_ROOT / GENERATORS[suite][1])["data_sha256"]
        if checked_in != manifest["data_sha256"]:
            raise SeedDriftError(
                f"{suite}: seed {seed} generates data {manifest['data_sha256'][:12]}, the "
                f"checked-in manifest says {checked_in[:12]}; run the generator's --check"
            )
    return SeededTrack(suite=suite, seed=seed, manifest=manifest, scenarios=scenarios)


def select_split(
    scenarios: Sequence[tuple[ManifestEntry, ScenarioSpec]], split: str
) -> list[tuple[ManifestEntry, ScenarioSpec]]:
    """The loaders' split rule applied to generated scenarios (bench.generate.load_jobs_v0,
    bench.tracks.load_track): strict test is held_out both, or the whole domain."""
    if split == "all":
        return list(scenarios)
    if split in ("train", "test"):
        return [(e, s) for e, s in scenarios if e.split == split]
    if split == "strict_test":
        return [(e, s) for e, s in scenarios if e.held_out in ("both", "domain")]
    raise ValueError(f"split {split!r} cannot be selected from generated data")
