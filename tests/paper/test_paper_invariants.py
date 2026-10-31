"""I8: every number in README, docs or paper traces to a file in results/ (ADR-0111)."""

import re

import pytest
from paper.i8 import PLACEHOLDER, Verdict, check, describe
from paper.numbers import GENERATED_DIR, PENDING, REPO_ROOT, render_files, resolve_all
from paper.registry import REGISTRY


@pytest.fixture(scope="module")
def i8_result() -> tuple[list[Verdict], list[str]]:
    """One scan of README.md and docs/ shared by the I8 tests (it resolves every macro)."""
    return check()


def test_invariant_I8_every_result_number_in_docs_traces_to_results(i8_result):
    verdicts, _ = i8_result

    violations = [describe(v) for v in verdicts if v.accepted_by is None]
    assert violations == [], (
        "untraced result-like numbers (use a macro, cite the results/ folder, or list "
        "them in paper/i8_known_violations.toml with a reason):\n" + "\n".join(violations)
    )


def test_invariant_I8_rule_files_have_no_stale_entries(i8_result):
    _, stale = i8_result

    assert stale == [], "\n".join(stale)


def test_invariant_I8_outlines_cover_every_hypothesis_with_registered_macros():
    keys: set[str] = set()
    for name in ("paper-outline.md", "thesis-outline.md"):
        text = (REPO_ROOT / "docs" / "paper" / name).read_text(encoding="utf-8")
        keys |= set(PLACEHOLDER.findall(text))

    assert keys <= set(REGISTRY)
    for prefix in ("h1.", "h2.", "h3.", "h4.", "pilot.", "ablation.", "oracle.", "handcheck."):
        assert any(k.startswith(prefix) for k in keys), prefix


def test_invariant_I8_generated_numbers_match_results():
    files = render_files(resolve_all())

    stale = [
        path
        for path, content in files.items()
        if not (GENERATED_DIR / path).is_file()
        or (GENERATED_DIR / path).read_text(encoding="utf-8") != content
    ]
    assert stale == [], f"run `uv run python -m paper.numbers`; stale: {stale}"


def test_invariant_I8_generated_numbers_contain_no_untraced_value():
    """Each rendered row in numbers.md names the results/ folder it came from."""
    rows = (GENERATED_DIR / "numbers.md").read_text(encoding="utf-8").splitlines()
    for row in rows:
        if row.startswith("| `") and PENDING not in row:
            assert re.search(r"results/\S+", row), row
