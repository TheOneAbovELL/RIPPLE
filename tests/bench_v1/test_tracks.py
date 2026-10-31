"""bench/tracks.py (ADR-0101): the v0 split rule, test-only tracks, files, curated stories."""

import json
import shutil
from pathlib import Path

import pytest
import yaml
from bench import generate as v0
from bench import generate_finance, generate_news
from bench.generate import TEMPLATES as JOBS_TEMPLATES
from bench.generate import make_personas as jobs_personas
from bench.scenario import ScenarioSpec
from bench.tracks import (
    CURATED_DIR,
    TrackSpec,
    assemble_track,
    check_track,
    curated_digest,
    load_curated,
    load_track,
    write_track,
)

CURATED_SOURCE = {
    "url": "https://example.org/story/1",
    "outlet": "Example Outlet",
    "published_on": "2026-05-01",
    "retrieved_on": "2026-10-31",
}


def curated_yaml(**provenance_overrides) -> str:
    """A minimal hand-written curated scenario, built from a generated news one."""
    _, spec = generate_news.generate(seed=3, personas=1).scenarios[0]
    provenance = {
        "kind": "curated",
        "story": "example-story",
        "sources": [CURATED_SOURCE],
        "curated_by": "OG",
        "curated_on": "2026-10-31",
        "text_policy": "paraphrased",
        **provenance_overrides,
    }
    meta = {**spec.meta, "persona": "curated", "provenance": provenance}
    meta.pop("content")
    curated = spec.model_copy(update={"name": "curated_example", "meta": meta})
    return yaml.safe_dump(curated.model_dump(mode="json", exclude_none=True), sort_keys=False)


@pytest.fixture
def news_dir(tmp_path) -> Path:
    out = tmp_path / "news_v1"
    write_track(generate_news.generate(seed=3, personas=5), out)
    return out


def test_assemble_track_splits_exactly_as_the_v0_generator_does():
    spec = TrackSpec("jobs_like", "jobs", "test", 1, JOBS_TEMPLATES)
    track = assemble_track(spec, jobs_personas(11, 5), 11)
    reference = v0.generate(seed=11, personas=5).manifest
    for key in ("personas", "templates"):
        assert track.manifest[key] == reference[key]
    split_of = {
        (r["persona"], r["template"]): (r["split"], r["held_out"]) for r in reference["scenarios"]
    }
    assert {
        (r["persona"], r["template"]): (r["split"], r["held_out"])
        for r in track.manifest["scenarios"]
    } == split_of


def test_a_test_only_track_holds_out_the_whole_domain():
    track = generate_finance.generate(seed=3, personas=4)
    manifest = track.manifest
    assert manifest["personas"]["train"] == [] and manifest["templates"]["train"] == []
    assert {(r["split"], r["held_out"]) for r in manifest["scenarios"]} == {("test", "domain")}


@pytest.mark.parametrize("module", [generate_news, generate_finance])
def test_every_manifest_and_scenario_is_labelled_synthetic(module):
    track = module.generate(seed=3, personas=2)
    assert (
        track.manifest["content"] == "synthetic" and "fictional" in track.manifest["content_note"]
    )
    for _, spec in track.scenarios:
        assert spec.meta["content"] == "synthetic" and spec.meta["domain"] == module.DOMAIN


def test_write_then_check_is_in_sync_and_catches_an_edited_extra_file(tmp_path):
    track = generate_finance.generate(seed=3, personas=2)
    write_track(track, tmp_path)
    assert check_track(track, tmp_path) == []
    pairs = tmp_path / generate_finance.PAIRS_FILE
    pairs.write_text(pairs.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert check_track(track, tmp_path) == [
        f"{generate_finance.PAIRS_FILE} differs from a fresh generation"
    ]


def test_rewriting_a_track_never_touches_its_curated_folder(news_dir):
    curated = news_dir / CURATED_DIR
    curated.mkdir()
    (curated / "story.yaml").write_text(curated_yaml(), encoding="utf-8")
    write_track(generate_news.generate(seed=4, personas=5), news_dir)
    assert (curated / "story.yaml").read_text(encoding="utf-8") == curated_yaml()


@pytest.mark.parametrize(
    ("split", "expected"),
    [("train", {"train"}), ("test", {"test"}), ("strict_test", {"test"})],
)
def test_load_track_filters_generated_scenarios_by_split(news_dir, split, expected):
    loaded = load_track(news_dir, split)
    assert loaded and {entry.split for entry, _ in loaded} == expected
    if split == "strict_test":
        assert {entry.held_out for entry, _ in loaded} == {"both"}


def test_load_track_adds_curated_stories_to_all_and_test_only(news_dir):
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "story.yaml").write_text(curated_yaml(), encoding="utf-8")
    names = {
        split: [e.name for e, _ in load_track(news_dir, split)]
        for split in ("all", "test", "train", "curated")
    }
    assert "curated_example" in names["all"] and "curated_example" in names["test"]
    assert "curated_example" not in names["train"] and names["curated"] == ["curated_example"]
    entry, _ = load_track(news_dir, "curated")[0]
    assert (entry.split, entry.held_out, entry.file) == ("test", "curated", "curated/story.yaml")


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"sources": []}, "invalid meta.provenance"),
        ({"sources": [{**CURATED_SOURCE, "url": "not a url"}]}, "invalid meta.provenance"),
        ({"text_policy": "verbatim"}, "invalid meta.provenance"),
        (
            {"sources": [{**CURATED_SOURCE, "retrieved_on": "2026-04-01"}]},
            "invalid meta.provenance",
        ),
        ({"curated_on": "2026-10-01"}, "invalid meta.provenance"),
    ],
)
def test_a_curated_story_with_bad_provenance_is_refused(news_dir, override, message):
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "bad.yaml").write_text(curated_yaml(**override), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_curated(news_dir, "news", "news_v1")


def test_a_curated_story_without_provenance_or_in_another_domain_is_refused(news_dir):
    folder = news_dir / CURATED_DIR
    folder.mkdir()
    raw = yaml.safe_load(curated_yaml())
    raw["meta"].pop("provenance")
    (folder / "bare.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=r"needs meta\.provenance"):
        load_curated(news_dir, "news", "news_v1")
    (folder / "bare.yaml").write_text(curated_yaml(), encoding="utf-8")
    with pytest.raises(ValueError, match=r"meta\.domain must be 'finance'"):
        load_curated(news_dir, "finance", "news_v1")


def test_curated_digest_counts_and_hashes_curated_files_only(news_dir):
    assert curated_digest(news_dir) == {"count": 0, "sha256": None}
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "story.yaml").write_text(curated_yaml(), encoding="utf-8")
    digest = curated_digest(news_dir)
    assert digest["count"] == 1 and isinstance(digest["sha256"], str)
    manifest = json.loads((news_dir / "manifest.json").read_text(encoding="utf-8"))
    assert digest["sha256"] != manifest["data_sha256"]


def test_copying_a_track_folder_keeps_it_loadable(news_dir, tmp_path):
    # The loader reads only manifest-listed files plus curated/, never stray yaml.
    copy = tmp_path / "copy"
    shutil.copytree(news_dir, copy)
    (copy / "stray.yaml").write_text("name: stray\nmemories: {}\nevents: []\n", encoding="utf-8")
    assert len(load_track(copy)) == 35
    assert all(isinstance(spec, ScenarioSpec) for _, spec in load_track(copy))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"name": "../escape"}, "must match"),
        ({"meta": {"track": "finance_v1"}}, r"meta\.track must be 'news_v1'"),
        ({"meta": {"content": "synthetic"}}, "cannot be labelled 'synthetic'"),
    ],
)
def test_a_curated_story_with_an_unsafe_name_or_wrong_labels_is_refused(news_dir, change, message):
    raw = yaml.safe_load(curated_yaml())
    raw["name"] = change.get("name", raw["name"])
    raw["meta"].update(change.get("meta", {}))
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "story.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_curated(news_dir, "news", "news_v1")


def test_a_curated_story_reusing_a_generated_name_is_refused(news_dir):
    taken = load_track(news_dir)[0][0].name
    raw = yaml.safe_load(curated_yaml())
    raw["name"] = taken
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "story.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="is already used"):
        load_track(news_dir, "curated")


def test_a_curated_file_that_is_not_a_scenario_names_the_file(news_dir):
    (news_dir / CURATED_DIR).mkdir()
    (news_dir / CURATED_DIR / "broken.yaml").write_text("name: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"broken\.yaml: not a valid scenario"):
        load_curated(news_dir, "news", "news_v1")
