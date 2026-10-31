"""news_v1 and finance_v1 generators (ADR-0101): determinism, validity, hygiene, outcomes."""

import re
from pathlib import Path

import pytest
from bench import generate_finance, generate_news
from bench.generate import DATA_DIR as JOBS_DIR
from bench.generate import scenario_yaml
from bench.scenario import ScenarioRunner, validate_scenario
from bench.tracks import check_track, load_track

MODULES = [generate_news, generate_finance]
REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILIES = {"changed", "unchanged", "temporary", "chain", "ask", "snapshot", "forget"}


def yaml_of(track):
    return [scenario_yaml(spec) for _, spec in track.scenarios]


@pytest.mark.parametrize("module", MODULES)
def test_generate_is_deterministic_for_the_same_seed(module):
    first, again = module.generate(seed=7, personas=5), module.generate(seed=7, personas=5)
    assert yaml_of(first) == yaml_of(again) and first.manifest == again.manifest
    assert first.extra_files == again.extra_files


@pytest.mark.parametrize("module", MODULES)
def test_generate_changes_with_the_seed(module):
    assert (
        module.generate(seed=1, personas=3).manifest["data_sha256"]
        != module.generate(seed=2, personas=3).manifest["data_sha256"]
    )


@pytest.mark.parametrize("module", MODULES)
def test_adding_a_persona_leaves_earlier_personas_scenarios_unchanged(module):
    four, five = module.generate(seed=7, personas=4), module.generate(seed=7, personas=5)
    earlier = {p.id for p in module.make_personas(7, 4)}
    assert {e.name: scenario_yaml(s) for e, s in four.scenarios} == {
        e.name: scenario_yaml(s) for e, s in five.scenarios if e.persona in earlier
    }


@pytest.mark.parametrize("module", MODULES)
def test_every_scenario_is_valid_in_its_domain_and_every_family_is_covered(module):
    track = module.generate(seed=7, personas=5)
    assert len(track.scenarios) == 35
    assert {entry.family for entry, _ in track.scenarios} == FAMILIES
    for entry, spec in track.scenarios:
        assert validate_scenario(spec) == [], entry.name
        assert any(event.expect for event in spec.events), entry.name


@pytest.mark.parametrize("module", MODULES)
def test_the_snapshot_family_uses_the_domains_snapshot_link(module):
    snapshot_type = {"news": "shared_from", "finance": "journaled_with"}[module.DOMAIN]
    track = module.generate(seed=7, personas=2)
    for entry, spec in track.scenarios:
        uses = any(link[2] == snapshot_type for link in spec.links)
        assert uses == (entry.family == "snapshot"), entry.name


@pytest.mark.parametrize("module", MODULES)
def test_the_checked_in_track_matches_a_fresh_generation(module):
    assert check_track(module.generate(), module.DATA_DIR) == []


def _track_text(folder: Path) -> str:
    return " ".join(p.read_text(encoding="utf-8") for p in folder.glob("*.yaml")).lower()


@pytest.mark.parametrize("module", MODULES)
def test_v1_persona_names_never_appear_in_another_track(module):
    # Cross-track hygiene: a finance persona inside jobs or news data would let the
    # link finder see the unseen domain's text (H4); news and jobs stay apart likewise.
    others = [
        d
        for d in (JOBS_DIR, generate_news.DATA_DIR, generate_finance.DATA_DIR)
        if d != module.DATA_DIR
    ]
    for folder in others:
        text = _track_text(folder)
        assert not {n for n in module.NAMES if f" {n}" in text or f"_{n}" in text}, folder.name


def _identifiers(module) -> set[str]:
    if module is generate_news:
        return set(generate_news.PLACES)
    names = {name.lower() for _, name, _ in generate_finance.COMPANIES}
    tickers = {ticker.lower() for ticker, _, _ in generate_finance.COMPANIES}
    return names | tickers | {leader.lower() for leader in generate_finance.LEADERS}


@pytest.mark.parametrize("module", MODULES)
def test_v1_place_and_company_names_appear_in_no_other_data(module):
    # H4 needs the finance text unseen: not in the jobs or news tracks, nor in any
    # link-pair file the training side keeps (training/data, WS-14's output). News
    # places stay out of jobs and finance data likewise.
    folders = [JOBS_DIR, generate_news.DATA_DIR, generate_finance.DATA_DIR]
    sources = {d.name: _track_text(d) for d in folders if d != module.DATA_DIR}
    jsonl_files = [
        *generate_finance.DATA_DIR.glob("*.jsonl"),
        *(REPO_ROOT / "training" / "data").glob("*.jsonl"),
    ]
    for path in jsonl_files:
        if path.parent != module.DATA_DIR:
            sources[path.name] = path.read_text(encoding="utf-8").lower()
    leaks = {
        source: sorted(i for i in _identifiers(module) if re.search(rf"\b{re.escape(i)}\b", text))
        for source, text in sources.items()
    }
    assert all(not found for found in leaks.values()), leaks


@pytest.mark.parametrize(
    ("module", "ask_template"),
    [(generate_news, "conflicting_reports"), (generate_finance, "rate_edge")],
)
def test_baselines_fail_and_check_everything_misses_only_the_ask_family(module, ask_template):
    # The expected v0 picture (ADR-0061) holds in the new domains: every family needs
    # propagation, and only the subtree below a question needs the graph.
    scenarios = load_track(module.DATA_DIR)
    for strategy in ("append_only", "newest_wins"):
        assert not any(ScenarioRunner(s, strategy=strategy).run().passed for _, s in scenarios)
    failed = {
        entry.template
        for entry, spec in scenarios
        if not ScenarioRunner(spec, strategy="check_everything").run().passed
    }
    assert failed == {ask_template}
