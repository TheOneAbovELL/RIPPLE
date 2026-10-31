"""paper.numbers: macros render from results/ only, with provenance, or are refused."""

import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest
from paper.numbers import (
    PENDING,
    Refused,
    Rendered,
    figure_cells,
    format_value,
    main,
    render_document,
    render_figure_svg,
    render_files,
    render_json,
    render_tex,
    resolve_all,
    resolve_macro,
)
from paper.registry import (
    FIGURES,
    LINKERS,
    MACRO_NAME,
    REGISTRY,
    Aggregate,
    AnySpec,
    DerivedSpec,
    FigureSpec,
    Format,
    MacroSpec,
    Prefix,
)

PINNED = {"resolver": "claude-sonnet-5-5"}
CLEAN_SHA = "abc1234"


def write_run(results: Path, folder: str, config: dict[str, object], metrics: dict[str, object]):
    run = results / folder
    run.mkdir(parents=True)
    (run / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (run / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")


def bench_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "suite": "v0",
        "strategy": "check_everything",
        "split": "all",
        "data": {"data_sha256": "d0"},
        "resolver": "scripted oracle (test)",
        "git_sha": CLEAN_SHA,
        "models": None,
        "prompt_versions": None,
        "seeds": {"generator_seed": 1, "run_seed": None},
        "run_at": "2026-10-19T05:00:00+00:00",
    }
    config.update(overrides)
    return config


def complete(**values: object) -> dict[str, object]:
    """metrics.json of a bench run where every scenario ran."""
    return {"scenarios_not_runnable": 0, **values}


def count_spec(**overrides: object) -> MacroSpec:
    fields: dict[str, object] = {
        "name": "t.check_everything.scenarios_passed",
        "description": "test",
        "run_pattern": "*_v0_check_everything_*",
        "json_path": "scenarios_passed",
        "fmt": "int",
        "config_match": {"suite": "v0", "strategy": "check_everything", "ablation": None},
    }
    fields.update(overrides)
    return MacroSpec(**fields)  # pyright: ignore[reportArgumentType]


def headline_spec(**overrides: object) -> MacroSpec:
    fields: dict[str, object] = {
        "name": "t.ripple.update_accuracy",
        "json_path": "memory_metrics.update_accuracy",
        "fmt": "pct:1",
        "headline": True,
        "aggregate": Aggregate.MEAN,
        "run_pattern": "*_v0_ripple_*",
        "config_match": {"suite": "v0", "strategy": "ripple"},
    }
    fields.update(overrides)
    return count_spec(**fields)


def headline_config(seed: int, **overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "strategy": "ripple",
        "models": PINNED,
        "prompt_versions": {"resolver": "v1"},
        "seeds": {"generator_seed": 1, "run_seed": seed},
        "run_at": f"2026-11-0{seed}T00:00:00+00:00",
    }
    fields.update(overrides)
    return bench_config(**fields)


def headline_metrics(accuracy: float) -> dict[str, object]:
    return complete(llm_calls=10, memory_metrics={"update_accuracy": accuracy})


def write_seeded(
    results: Path,
    run_seeds: tuple[int, ...],
    accuracy: float = 0.9,
    config: dict[str, object] | None = None,
):
    for seed in run_seeds:
        write_run(
            results,
            f"2026-11-0{seed}_v0_ripple_{CLEAN_SHA}",
            headline_config(seed, **(config or {})),
            headline_metrics(accuracy),
        )


# ------------------------------------------------------------------ single runs


def test_resolve_macro_picks_the_newest_run_by_run_at_not_by_value_or_name(tmp_path: Path):
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_b",
        bench_config(data={"data_sha256": "old"}),
        complete(scenarios_passed=31),
    )
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_a",
        bench_config(run_at="2026-10-19T06:00:00+00:00"),
        complete(scenarios_passed=30),
    )

    outcome = resolve_macro(count_spec(), tmp_path)

    assert isinstance(outcome, Rendered)
    assert outcome.markdown == "30"
    assert [r.folder for r in outcome.sources] == ["2026-10-19_v0_check_everything_a"]
    assert [(s.folder, s.value) for s in outcome.superseded] == [
        ("2026-10-19_v0_check_everything_b", 31.0)
    ]


def test_resolve_macro_refuses_when_runs_of_one_configuration_disagree(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_a", bench_config(), complete(checks=96))
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_b",
        bench_config(run_at="2026-10-19T06:00:00+00:00"),
        complete(checks=76),
    )

    outcome = resolve_macro(count_spec(json_path="checks"), tmp_path)

    assert isinstance(outcome, Refused)
    assert "disagree" in outcome.reason


def test_resolve_macro_refuses_when_a_newer_run_fails_the_checks(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_a", bench_config(), complete(checks=5))
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_b",
        bench_config(run_at="2026-10-20T00:00:00+00:00"),
        {"scenarios_not_runnable": 3, "checks": 5},
    )

    outcome = resolve_macro(count_spec(json_path="checks"), tmp_path)

    assert isinstance(outcome, Refused)
    assert "newer run 2026-10-19_v0_check_everything_b" in outcome.reason


def test_resolve_macro_refuses_when_no_folder_matches_and_names_the_pattern(tmp_path: Path):
    outcome = resolve_macro(count_spec(provisional="producer not built"), tmp_path)

    assert isinstance(outcome, Refused)
    assert "*_v0_check_everything_*" in outcome.reason
    assert "producer not built" in outcome.reason


def test_discover_runs_ignores_a_folder_without_both_json_files(tmp_path: Path):
    (tmp_path / "2026-10-19_v0_check_everything_x").mkdir()
    (tmp_path / "2026-10-19_v0_check_everything_x" / "config.json").write_text("{}")

    assert isinstance(resolve_macro(count_spec(), tmp_path), Refused)


def test_resolve_macro_quotes_a_pending_string_value(tmp_path: Path):
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_x",
        bench_config(),
        complete(memory_metrics="TBD (pending run): bench/metrics.py is TODO(human)"),
    )

    outcome = resolve_macro(count_spec(json_path="memory_metrics.update_accuracy"), tmp_path)

    assert isinstance(outcome, Refused)
    assert "TBD (pending run)" in outcome.reason


@pytest.mark.parametrize(
    ("config", "metrics", "reason"),
    [
        ({}, {"scenarios_passed": 0, "scenarios_not_runnable": 35}, "35 scenarios not runnable"),
        ({}, {"scenarios_passed": 0}, "cannot tell whether the bench run is complete"),
        ({"git_sha": "uncommitted"}, complete(scenarios_passed=30), "not a clean commit"),
        ({"run_at": None}, complete(scenarios_passed=30), "run_at"),
        ({}, complete(scenarios_passed=30, llm_calls=4), "no models"),
        ({"models": PINNED}, complete(scenarios_passed=30), "no prompt versions"),
    ],
)
def test_resolve_macro_provenance_refusals(
    tmp_path: Path, config: dict[str, object], metrics: dict[str, object], reason: str
):
    write_run(tmp_path, "2026-10-19_v0_check_everything_x", bench_config(**config), metrics)

    outcome = resolve_macro(count_spec(), tmp_path)

    assert isinstance(outcome, Refused)
    assert reason in outcome.reason


def test_resolve_macro_derives_completeness_from_per_scenario(tmp_path: Path):
    metrics = {"scenarios_passed": 0, "per_scenario": [{"runnable": True}, {"runnable": False}]}
    write_run(tmp_path, "2026-10-19_v0_check_everything_x", bench_config(), metrics)

    outcome = resolve_macro(count_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "1 scenarios not runnable" in outcome.reason


def test_draft_mode_allows_an_uncommitted_run_for_non_headline_macros(tmp_path: Path):
    config = bench_config(git_sha="uncommitted")
    write_run(tmp_path, "2026-10-19_v0_check_everything_x", config, complete(scenarios_passed=30))

    assert isinstance(resolve_macro(count_spec(), tmp_path, draft=True), Rendered)
    assert isinstance(resolve_macro(count_spec(), tmp_path), Refused)


def test_draft_mode_allows_an_uncommitted_headline_mean_but_keeps_the_seed_gate(tmp_path: Path):
    """ADR-0135: --draft relaxes only the clean-commit gate; three seeds are still needed."""
    write_seeded(tmp_path, (1, 2, 3), config={"git_sha": "uncommitted"})

    assert isinstance(resolve_macro(headline_spec(), tmp_path, draft=True), Rendered)
    assert isinstance(resolve_macro(headline_spec(), tmp_path), Refused)
    for seed in (2, 3):
        (tmp_path / f"2026-11-0{seed}_v0_ripple_{CLEAN_SHA}" / "config.json").unlink()
        (tmp_path / f"2026-11-0{seed}_v0_ripple_{CLEAN_SHA}" / "metrics.json").unlink()
    outcome = resolve_macro(headline_spec(), tmp_path, draft=True)
    assert isinstance(outcome, Refused) and "needs 3 run seeds" in outcome.reason


def test_run_seeds_count_the_generator_seed_of_a_generator_seeded_run(tmp_path: Path):
    """ADR-0121: one folder per generator seed, run_seed null; the generator seed varies."""
    for seed in (1, 2, 3):
        generator = {"kind": "generator", "generator_seed": 100 + seed, "run_seed": None}
        write_run(
            tmp_path,
            f"2026-11-0{seed}_v0_ripple_{CLEAN_SHA}",
            headline_config(seed, seeds=generator),
            headline_metrics(0.5 + seed / 10),
        )

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Rendered)
    assert outcome.markdown == "70.0%"
    assert outcome.seeds == {"101.0", "102.0", "103.0"}


def test_config_filter_none_excludes_ablation_runs(tmp_path: Path):
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_x",
        bench_config(ablation="no_graph"),
        complete(scenarios_passed=1),
    )

    assert isinstance(resolve_macro(count_spec(), tmp_path), Refused)


def test_config_filter_prefix_matches_the_start_of_a_string(tmp_path: Path):
    write_run(
        tmp_path, "2026-10-19_v0_check_everything_x", bench_config(), complete(scenarios_passed=3)
    )

    oracle = count_spec(config_match={"resolver": Prefix("scripted oracle")})
    llm = count_spec(config_match={"resolver": Prefix("llm")})

    assert isinstance(resolve_macro(oracle, tmp_path), Rendered)
    assert isinstance(resolve_macro(llm, tmp_path), Refused)


def test_bool_is_not_a_number(tmp_path: Path):
    write_run(
        tmp_path,
        "2026-10-19_v0_check_everything_x",
        bench_config(),
        complete(scenarios_passed=True),
    )

    assert isinstance(resolve_macro(count_spec(), tmp_path), Refused)


# ------------------------------------------------------------------ headline


def test_headline_mean_over_three_seeds_keeps_the_spread(tmp_path: Path):
    for seed, accuracy in ((1, 0.8), (2, 0.9), (3, 1.0)):
        write_seeded(tmp_path, (seed,), accuracy)

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Rendered)
    assert outcome.value == pytest.approx(0.9)
    assert (outcome.markdown, outcome.tex) == ("90.0%", "90.0\\%")
    assert sorted(outcome.values) == pytest.approx([0.8, 0.9, 1.0])


def test_headline_refused_below_the_docs04_seed_count(tmp_path: Path):
    write_seeded(tmp_path, (1, 2))

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused)
    assert "needs 3 run seeds" in outcome.reason


def test_a_seed_run_twice_with_the_same_value_counts_once(tmp_path: Path):
    write_seeded(tmp_path, (1, 2, 3))
    write_run(
        tmp_path,
        f"2026-11-04_v0_ripple_{CLEAN_SHA}",
        headline_config(1, run_at="2026-11-04T00:00:00+00:00"),
        headline_metrics(0.9),
    )

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Rendered)
    assert len(outcome.sources) == 3
    assert f"2026-11-04_v0_ripple_{CLEAN_SHA}" in {r.folder for r in outcome.sources}


def test_a_seed_run_twice_with_different_values_is_refused(tmp_path: Path):
    write_seeded(tmp_path, (1, 2, 3))
    write_run(
        tmp_path,
        f"2026-11-04_v0_ripple_{CLEAN_SHA}",
        headline_config(1, run_at="2026-11-04T00:00:00+00:00"),
        headline_metrics(0.5),
    )

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "disagree" in outcome.reason


def test_runs_with_different_models_are_never_averaged(tmp_path: Path):
    write_seeded(tmp_path, (1, 2))
    write_seeded(tmp_path, (3,), config={"models": {"resolver": "claude-haiku-5-5"}})

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused)  # the newest configuration has one seed only


def test_linker_runs_on_different_pair_files_are_never_averaged(tmp_path: Path):
    write_seeded(tmp_path, (1, 2), config={"pairs_sha256": "a"})
    write_seeded(tmp_path, (3,), config={"pairs_sha256": "b"})

    assert isinstance(resolve_macro(headline_spec(), tmp_path), Refused)


def test_mixed_seed_layouts_are_refused(tmp_path: Path):
    write_run(
        tmp_path,
        f"2026-11-01_v0_ripple_{CLEAN_SHA}",
        headline_config(1, seeds={"generator_seed": 1, "run_seeds": [1, 2, 3]}),
        headline_metrics(0.9),
    )
    write_seeded(tmp_path, (2,))

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "mixed" in outcome.reason


def test_a_seedless_run_cannot_join_a_mean(tmp_path: Path):
    write_seeded(tmp_path, (1, 2, 3), config={"seeds": {"generator_seed": 1, "run_seed": None}})

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "no run seed" in outcome.reason


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"git_sha": "uncommitted"}, "not a clean commit"),
        ({"git_sha": f"{CLEAN_SHA}-dirty"}, "not a clean commit"),
        ({"models": None}, "no models"),
        ({"models": {"resolver": "claude-sonnet-latest"}}, "unpinned"),
        ({"prompt_versions": None}, "no prompt versions"),
    ],
)
def test_headline_provenance_refusals(tmp_path: Path, override: dict[str, object], reason: str):
    write_seeded(tmp_path, (1, 2, 3), config=override)

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused)
    assert reason in outcome.reason


def test_headline_empty_models_needs_llm_calls_to_confirm_no_model(tmp_path: Path):
    for seed in (1, 2, 3):
        write_run(
            tmp_path,
            f"2026-11-0{seed}_v0_ripple_{CLEAN_SHA}",
            headline_config(seed, models={}, prompt_versions={}),
            complete(memory_metrics={"update_accuracy": 0.9}),
        )

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "no llm_calls" in outcome.reason


def test_one_folder_may_declare_its_run_seeds(tmp_path: Path):
    config = headline_config(1, seeds={"generator_seed": 1, "run_seeds": [1, 2, 3]})
    write_run(tmp_path, f"2026-11-01_v0_ripple_{CLEAN_SHA}", config, headline_metrics(0.75))

    outcome = resolve_macro(headline_spec(aggregate=Aggregate.SINGLE), tmp_path)

    assert isinstance(outcome, Rendered)
    assert outcome.markdown == "75.0%"


# ------------------------------------------------------------------ derived and formats


def _registry(results: Path) -> dict[str, AnySpec]:
    write_run(
        results,
        "2026-10-19_v0_check_everything_x",
        bench_config(),
        complete(scenarios_passed=30, scenarios=35),
    )
    passed = count_spec()
    total = count_spec(name="t.check_everything.scenarios", json_path="scenarios")
    missing = count_spec(name="t.ripple.scenarios", run_pattern="*_v0_ripple_*")
    return {
        passed.name: passed,
        total.name: total,
        missing.name: missing,
        "x.share": DerivedSpec("x.share", "t", "ratio", (passed.name, total.name), "pct:1"),
        "x.diff": DerivedSpec("x.diff", "t", "difference", (total.name, passed.name), "int"),
        "x.refused": DerivedSpec("x.refused", "t", "ratio", (passed.name, missing.name), "pct:1"),
    }


def test_derived_macros_combine_and_propagate_refusal(tmp_path: Path):
    outcomes = resolve_all(tmp_path, _registry(tmp_path))

    share = outcomes["x.share"]
    assert isinstance(share, Rendered) and share.markdown == "85.7%"
    diff = outcomes["x.diff"]
    assert isinstance(diff, Rendered) and diff.markdown == "5"
    refused = outcomes["x.refused"]
    assert isinstance(refused, Refused) and "t.ripple.scenarios" in refused.reason


def _two_strategies(results: Path, ripple_data: str) -> dict[str, AnySpec]:
    write_run(
        results,
        "2026-10-19_v0_check_everything_x",
        bench_config(engine="one-shot"),
        complete(scenarios_passed=30),
    )
    write_run(
        results,
        "2026-10-19_v0_ripple_x",
        bench_config(strategy="ripple", engine="wave", data={"data_sha256": ripple_data}),
        complete(scenarios_passed=33),
    )
    ce = count_spec(name="t.ce")
    ripple = count_spec(
        name="t.ripple",
        run_pattern="*_v0_ripple_*",
        config_match={"suite": "v0", "strategy": "ripple"},
    )
    ratio = DerivedSpec(
        "t.ratio", "t", "ratio", ("t.ripple", "t.ce"), "pct:1", differ=("strategy", "engine")
    )
    return {"t.ce": ce, "t.ripple": ripple, "t.ratio": ratio}


def test_derived_inputs_may_differ_only_in_the_compared_fields(tmp_path: Path):
    outcome = resolve_all(tmp_path, _two_strategies(tmp_path, ripple_data="d0"))["t.ratio"]

    assert isinstance(outcome, Rendered) and outcome.markdown == "110.0%"


def test_derived_inputs_from_different_data_are_refused(tmp_path: Path):
    outcome = resolve_all(tmp_path, _two_strategies(tmp_path, ripple_data="other"))["t.ratio"]

    assert isinstance(outcome, Refused) and "differ beyond" in outcome.reason


def test_figure_cells_from_incomparable_runs_are_all_refused(tmp_path: Path):
    outcomes = resolve_all(tmp_path, _two_strategies(tmp_path, ripple_data="other"))
    rows = (("ce", ("t.ce",)), ("ripple", ("t.ripple",)))
    figure = FigureSpec("f", "t", ("passed",), rows, "passed", differ=("strategy", "engine"))

    cells, mismatch = figure_cells(figure, outcomes)

    assert mismatch is not None
    assert all(isinstance(c, Refused) for row in cells for c in row)


def test_ratio_with_zero_denominator_is_refused(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_x", bench_config(), complete(a=1, b=0))
    a = count_spec(name="t.a", json_path="a")
    b = count_spec(name="t.b", json_path="b")
    registry: dict[str, AnySpec] = {
        "t.a": a,
        "t.b": b,
        "t.r": DerivedSpec("t.r", "t", "ratio", ("t.a", "t.b"), "pct:1"),
    }

    assert isinstance(resolve_all(tmp_path, registry)["t.r"], Refused)


def test_a_cycle_among_derived_macros_is_an_error(tmp_path: Path):
    registry: dict[str, AnySpec] = {
        "t.a": DerivedSpec("t.a", "t", "ratio", ("t.b", "t.b"), "pct:1"),
        "t.b": DerivedSpec("t.b", "t", "ratio", ("t.a", "t.a"), "pct:1"),
    }

    with pytest.raises(ValueError, match="cycle"):
        resolve_all(tmp_path, registry)


@pytest.mark.parametrize(
    ("value", "fmt", "expected"),
    [
        (30.0, "int", ("30", "30")),
        (0.857142, "pct:1", ("85.7%", "85.7\\%")),
        (0.042, "points:1", ("4.2", "4.2")),
        (0.01234, "usd:4", ("$0.0123", "\\$0.0123")),
        (2.5, "float:2", ("2.50", "2.50")),
    ],
)
def test_format_value(value: float, fmt: str, expected: tuple[str, str]):
    assert format_value(value, Format.parse(fmt)) == expected


def test_int_format_refuses_a_fraction():
    assert isinstance(format_value(2.5, Format.parse("int")), str)


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError):
        Format.parse("percent")


# ------------------------------------------------------------------ rendering


def test_rendered_files_carry_values_or_pending(tmp_path: Path):
    registry = _registry(tmp_path)
    outcomes = resolve_all(tmp_path, registry)

    tex = render_tex(outcomes)
    assert "\\expandafter\\newcommand\\csname rnum@x.share\\endcsname{85.7\\%}" in tex
    assert f"\\csname rnum@x.refused\\endcsname{{\\textbf{{{PENDING}}}}}" in tex
    assert "\\textbf{??\\detokenize{#1}}" in tex
    document = json.loads(render_json(outcomes, registry))
    by_name = {m["name"]: m for m in document["macros"]}
    assert by_name["x.share"]["sources"][0]["folder"] == "2026-10-19_v0_check_everything_x"
    assert by_name["x.refused"]["markdown"] == PENDING
    assert "reason" in by_name["x.refused"]


def test_draft_files_say_draft(tmp_path: Path):
    registry = _registry(tmp_path)
    outcomes = resolve_all(tmp_path, registry, draft=True)

    assert "DRAFT" in render_tex(outcomes, draft=True)
    assert "draft" in json.loads(render_json(outcomes, registry, draft=True))


def test_svg_draws_a_bar_for_a_rendered_cell(tmp_path: Path):
    registry = _registry(tmp_path)
    outcomes = resolve_all(tmp_path, registry)
    rows = (("ce", ("x.share",)), ("r", ("x.refused",)))
    figure = FigureSpec("f", "t", ("share",), rows, "share")

    svg = render_figure_svg(figure, outcomes, registry)

    bars = ElementTree.fromstring(svg).findall("{http://www.w3.org/2000/svg}rect")
    assert len(bars) == 1 and float(bars[0].attrib["width"]) > 0
    assert PENDING in svg


def test_figures_write_csv_dat_and_valid_svg(tmp_path: Path):
    files = render_files(resolve_all(tmp_path))

    for figure in FIGURES:
        assert files[f"figures/{figure.name}.csv"].startswith("label,")
        assert "nan" in files[f"figures/{figure.name}.dat"]  # empty results directory
        ElementTree.fromstring(files[f"figures/{figure.name}.svg"])


def test_cli_writes_then_check_passes_and_detects_staleness(tmp_path: Path):
    results, out = tmp_path / "results", tmp_path / "out"
    results.mkdir()
    args = ["--results", str(results), "--out", str(out)]

    assert main(args) == 0
    assert main([*args, "--check"]) == 0
    (out / "numbers.md").write_text("edited by hand", encoding="utf-8")
    assert main([*args, "--check"]) == 1
    assert main([*args, "--strict"]) == 1  # everything is refused
    assert main([*args, "--draft"]) == 0
    assert (out / "draft" / "numbers.md").is_file()


# ------------------------------------------------------------------ the registry itself


def test_registry_entries_are_well_formed():
    for name, spec in REGISTRY.items():
        assert name == spec.name
        assert MACRO_NAME.match(name), name
        Format.parse(spec.fmt)
        if isinstance(spec, DerivedSpec):
            for dependency in spec.inputs:
                assert dependency in REGISTRY, (name, dependency)
                if spec.headline:
                    assert REGISTRY[dependency].headline, (name, dependency)
        elif spec.headline:
            assert spec.aggregate is Aggregate.MEAN, name
    resolve_all(Path("does-not-exist"))  # raises on a cycle among derived macros


def test_every_hypothesis_and_claim_has_a_macro():
    supported = {tag for spec in REGISTRY.values() for tag in spec.supports}
    assert {"C1", "C2", "C3", "C4", "H1", "H2", "H3", "H4", "baseline", "ablation"} <= supported


def test_figures_reference_registered_macros():
    for figure in FIGURES:
        assert figure.bar_column in figure.columns
        for _, macros in figure.rows:
            assert len(macros) == len(figure.columns)
            assert all(m in REGISTRY for m in macros)


def test_real_results_never_render_from_an_uncommitted_or_incomplete_run():
    """Against today's results/: every run is uncommitted, so nothing renders by default,
    and even the draft view takes nothing from a run with not-runnable scenarios."""
    for draft in (False, True):
        for name, outcome in resolve_all(draft=draft).items():
            if isinstance(outcome, Rendered):
                assert draft, name
                for run in outcome.sources:
                    assert not run.metrics.get("scenarios_not_runnable"), (name, run.folder)


# ------------------------------------------------------------------ second review


def test_an_llm_run_with_empty_prompt_versions_is_refused(tmp_path: Path):
    write_seeded(tmp_path, (1, 2, 3), config={"prompt_versions": {}})

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "prompt_versions is empty" in outcome.reason


def test_a_newer_failing_run_without_run_at_still_blocks(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_a", bench_config(), complete(checks=5))
    write_run(
        tmp_path,
        "2026-10-20_v0_check_everything_b",
        bench_config(run_at="not a time"),
        complete(checks=5),
    )

    outcome = resolve_macro(count_spec(json_path="checks"), tmp_path)

    assert isinstance(outcome, Refused) and "newer run" in outcome.reason


def test_a_corrupt_matching_run_folder_blocks_the_macro(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_a", bench_config(), complete(checks=5))
    half = tmp_path / "2026-10-20_v0_check_everything_b"
    half.mkdir()
    (half / "config.json").write_text("{", encoding="utf-8")

    outcome = resolve_macro(count_spec(json_path="checks"), tmp_path)

    assert isinstance(outcome, Refused) and "unreadable" in outcome.reason


def test_equal_seeds_written_differently_count_once(tmp_path: Path):
    for index, seed in enumerate((1, 1.0, "1")):
        write_run(
            tmp_path,
            f"2026-11-0{index + 1}_v0_ripple_{CLEAN_SHA}",
            headline_config(
                1, seeds={"run_seed": seed}, run_at=f"2026-11-0{index + 1}T00:00:00+00:00"
            ),
            headline_metrics(0.9),
        )

    outcome = resolve_macro(headline_spec(), tmp_path)

    assert isinstance(outcome, Refused) and "needs 3 run seeds" in outcome.reason


def test_a_pct_macro_refuses_a_value_that_is_not_a_share(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_x", bench_config(), complete(share=93.4))

    outcome = resolve_macro(count_spec(json_path="share", fmt="pct:1"), tmp_path)

    assert isinstance(outcome, Refused) and "outside [0, 1]" in outcome.reason


def test_a_tiny_negative_share_never_prints_minus_zero():
    assert format_value(-0.00001, Format.parse("pct:1")) == ("0.0%", "0.0\\%")


def _linker_config(linker: str, track: str, seed: int, **overrides: object) -> dict[str, object]:
    """The shape training/evaluate.py writes (nested `data`, `typed`, top-level models)."""
    config: dict[str, object] = {
        "suite": "linkpairs",
        "track": track,
        "linker": linker,
        "linker_details": {"module": f"linker.{linker}"},
        "plumbing_only": False,
        "typed": linker != "rule",
        "models": {} if linker == "rule" else {"linker": "claude-haiku-5-5"},
        "prompt_versions": {} if linker == "rule" else {"linker": "v1"},
        "seeds": {"pair_seed": 7, "run_seed": seed},
        "transfer": None if track == "jobs_v0" else {"train_pairs_sha256": "jobs_v0"},
        "split": "test",
        "new_memory": "dependent",
        "data": {"pairs_file": f"training/data/{track}.jsonl", "pairs_sha256": track},
        "pair_count": 100 if track == "jobs_v0" else 60,
        "provenances": ["rule", "scenario"],
        "git_sha": CLEAN_SHA,
        "run_at": f"2026-11-0{seed}T00:00:00+00:00",
    }
    if linker == "trained":
        # training/evaluate.py: the training seed is in linker_details and the artifact
        # folder in models; the evaluation run seed is shared; no prompt (ADR-0126).
        config["linker_details"] = {"module": "linker.trained", "seed": seed}
        config["models"] = {"linker": f"training/artifacts/m_seed{seed}"}
        config["prompt_versions"] = {}
        config["seeds"] = {"pair_seed": 7, "run_seed": 7}
    config.update(overrides)
    return config


def _linker_metrics(linker: str, f1: float) -> dict[str, object]:
    return {
        "overall": {"f1": f1},
        "by_held_out": {"both": {"f1": f1}},
        "llm_calls": 100 if linker == "llm" else 0,
    }


def test_h4_and_the_linker_figure_render_from_real_harness_configs(tmp_path: Path):
    for track, f1 in (("jobs_v0", 0.8), ("finance_v1", 0.7)):
        for linker in LINKERS:
            for seed in (1, 2, 3):
                write_run(
                    tmp_path,
                    f"2026-11-0{seed}_linkpairs_{track}_{linker}_{CLEAN_SHA}",
                    _linker_config(linker, track, seed),
                    _linker_metrics(linker, f1),
                )

    outcomes = resolve_all(tmp_path)

    h4 = outcomes["h4.transfer_difference_points"]
    assert isinstance(h4, Rendered) and h4.markdown == "10.0"
    figure = next(f for f in FIGURES if f.name == "linker_f1")
    cells, mismatch = figure_cells(figure, outcomes)
    assert mismatch is None
    assert all(isinstance(c, Rendered) for row in cells for c in row)


def test_draft_figure_files_say_draft(tmp_path: Path):
    files = render_files(resolve_all(tmp_path, draft=True), draft=True)

    for figure in FIGURES:
        assert files[f"figures/{figure.name}.csv"].startswith("label (DRAFT),")
        assert "DRAFT" in files[f"figures/{figure.name}.dat"].splitlines()[0]
        assert "DRAFT" in files[f"figures/{figure.name}.svg"]


# ------------------------------------------------------------------ WS-21 (ADR-0135)


def test_trained_linker_mean_counts_the_training_seed_not_the_shared_run_seed(tmp_path: Path):
    for seed, f1 in ((1, 0.6), (2, 0.7), (3, 0.8)):
        write_run(
            tmp_path,
            f"2026-11-0{seed}_linkpairs_jobs_v0_trained_{CLEAN_SHA}",
            _linker_config("trained", "jobs_v0", seed),
            _linker_metrics("trained", f1),
        )

    outcome = resolve_all(tmp_path)["link.trained.jobs_v0.f1_both"]

    assert isinstance(outcome, Rendered)
    assert outcome.markdown == "70.0%"
    assert len(outcome.sources) == 3


def test_a_parent_orientation_run_never_doubles_a_trained_seed(tmp_path: Path):
    for seed in (1, 2, 3):
        write_run(
            tmp_path,
            f"2026-11-0{seed}_linkpairs_jobs_v0_trained_{CLEAN_SHA}",
            _linker_config("trained", "jobs_v0", seed),
            _linker_metrics("trained", 0.5),
        )
    parent = _linker_config(
        "trained", "jobs_v0", 1, new_memory="parent", run_at="2026-11-09T00:00:00+00:00"
    )
    write_run(
        tmp_path,
        f"2026-11-09_linkpairs_jobs_v0_trained_{CLEAN_SHA}",
        parent,
        _linker_metrics("trained", 0.9),
    )

    outcome = resolve_all(tmp_path)["link.trained.jobs_v0.f1_both"]

    assert isinstance(outcome, Rendered) and outcome.markdown == "50.0%"


def test_a_model_without_prompts_is_refused_unless_the_run_reports_zero_llm_calls(tmp_path: Path):
    for seed in (1, 2, 3):
        metrics = _linker_metrics("trained", 0.5)
        del metrics["llm_calls"]
        write_run(
            tmp_path,
            f"2026-11-0{seed}_linkpairs_jobs_v0_trained_{CLEAN_SHA}",
            _linker_config("trained", "jobs_v0", seed),
            metrics,
        )

    outcome = resolve_all(tmp_path)["link.trained.jobs_v0.f1_both"]

    assert isinstance(outcome, Refused) and "prompt_versions is empty" in outcome.reason


def test_the_rule_linker_renders_from_its_single_deterministic_run(tmp_path: Path):
    write_run(
        tmp_path,
        f"2026-11-01_linkpairs_jobs_v0_rule_{CLEAN_SHA}",
        _linker_config("rule", "jobs_v0", 1),
        _linker_metrics("rule", 0.5),
    )

    outcome = resolve_all(tmp_path)["link.rule.jobs_v0.f1_both"]

    assert isinstance(outcome, Rendered) and outcome.markdown == "50.0%"


def _oracle_bench_run(
    results: Path, strategy: str, seed: int, accuracy: float, **overrides: object
) -> None:
    config = bench_config(
        strategy=strategy,
        split="test",
        ablation=None,
        linker="scenario",
        models={},
        prompt_versions={},
        seeds={"kind": "generator", "generator_seed": seed, "run_seed": None},
        run_at=f"2026-11-0{seed - 20261018}T00:00:00+00:00",
    )
    config.update(overrides)
    metrics = complete(
        llm_calls=0,
        scenarios_passed=seed,
        memory_metrics={"update_accuracy": accuracy, "cost_per_ripple": accuracy * 2},
    )
    folder = f"2026-11-01_v0_{strategy}_g{seed}_{config['split']}_{CLEAN_SHA}"
    write_run(results, folder, config, metrics)


def test_oracle_memory_macros_and_h1_ratio_render_from_generator_seeded_runs(tmp_path: Path):
    for seed in (20261019, 20261020, 20261021):
        _oracle_bench_run(tmp_path, "ripple", seed, 1.0)
        _oracle_bench_run(tmp_path, "check_everything", seed, 0.8)

    outcomes = resolve_all(tmp_path)

    ripple = outcomes["oracle_mem.v0.ripple.update_accuracy"]
    assert isinstance(ripple, Rendered) and ripple.markdown == "100.0%"
    ratio = outcomes["oracle_h1.v0.accuracy_ratio"]
    assert isinstance(ratio, Rendered) and ratio.markdown == "125.0%"
    assert isinstance(outcomes["mem.ripple.update_accuracy"], Refused)  # linker "trained"


def test_oracle_v0_counts_read_the_checked_in_seed_not_the_newest(tmp_path: Path):
    for seed in (20261019, 20261020, 20261021):
        _oracle_bench_run(tmp_path, "ripple", seed, 1.0, split="all")

    outcome = resolve_all(tmp_path)["oracle.v0.ripple.scenarios_passed"]

    assert isinstance(outcome, Rendered) and outcome.markdown == "20261019"


def test_render_document_fills_values_and_marks_refused_and_unknown_macros(tmp_path: Path):
    write_run(tmp_path, "2026-10-19_v0_check_everything_a", bench_config(), complete(checks=96))
    registry: dict[str, AnySpec] = {
        "t.checks": count_spec(name="t.checks", json_path="checks"),
        "t.missing": count_spec(name="t.missing", json_path="absent"),
    }
    outcomes = resolve_all(tmp_path, registry)
    source = "Checks {{num:t.checks}}, then {{num:t.missing}} and {{num:t.unknown}}.\n"

    rendered = render_document("paper.md", source, outcomes, draft=True)
    assert rendered.endswith(f"Checks 96, then {PENDING} and ??t.unknown.\n")
    assert "DRAFT" in rendered.splitlines()[1]
    assert "{{num:" not in rendered


def test_render_document_leaves_a_macro_inside_inline_code_as_written():
    source = "Write `{{num:<key>}}` to cite {{num:t.unknown}}.\n"

    rendered = render_document("paper.md", source, {})

    assert rendered.endswith("Write `{{num:<key>}}` to cite ??t.unknown.\n")
