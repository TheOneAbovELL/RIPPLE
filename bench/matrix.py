"""The full benchmark grid in one command (docs/results/benchmark.md is read from it).

    uv run python -m bench.matrix            # every run below, then bench.summary
    uv run python -m bench.matrix --dry-run  # print the bench.run argument lists only

Grid (ADR-0121, ADR-0122): smoke under every strategy; v0 and news_v1 on the test and
all splits, finance_v1 on test (it is test only), each under every strategy and three
generator seeds; the two offline ablations of ripple on the test split of every track,
three seeds. Every run is an ordinary `bench.run` invocation writing its own folder.
"""

import argparse
import sys
from collections.abc import Iterator

from bench import run as bench_run
from bench import summary
from bench.seeds import SEED_COUNT
from bench.strategies import ABLATIONS, STRATEGY_NAMES

TRACK_SPLITS: dict[str, tuple[str, ...]] = {
    "v0": ("test", "all"),
    "news_v1": ("test", "all"),
    "finance_v1": ("test",),
}
ABLATION_SPLIT = "test"


def grid() -> Iterator[list[str]]:
    for strategy in STRATEGY_NAMES:
        yield ["--suite", "smoke", "--strategy", strategy]
    seeds = ["--generator-seeds", str(SEED_COUNT)]
    for suite, splits in TRACK_SPLITS.items():
        for split in splits:
            for strategy in STRATEGY_NAMES:
                yield ["--suite", suite, "--strategy", strategy, "--split", split, *seeds]
        for ablation in ABLATIONS:
            yield [
                *("--suite", suite, "--strategy", "ripple", "--split", ABLATION_SPLIT),
                *("--ablation", ablation, *seeds),
            ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the whole RippleBench grid")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    refused: list[str] = []
    for run_argv in grid():
        if args.dry_run:
            print("bench.run " + " ".join(run_argv))
            continue
        # A failing scenario is a result, not an error: baselines are meant to fail gold.
        # A refused invocation (argparse exit) is an error: the grid would be incomplete.
        try:
            bench_run.main(run_argv)
        except SystemExit:
            refused.append(" ".join(run_argv))
    if args.dry_run:
        return 0
    if refused:
        for line in refused:
            print(f"REFUSED bench.run {line}")
        return 2  # no summary of a partial grid
    return summary.main([])


if __name__ == "__main__":
    sys.exit(main())
