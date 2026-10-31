"""paper.i8: what counts as a result-like number, and how a claim is accepted."""

import json
import time
from pathlib import Path

import pytest
from paper.i8 import (
    Category,
    CategoryRule,
    Claim,
    KnownViolation,
    Rules,
    TextRule,
    judge,
    line_claims,
    load_rules,
    make_citation_check,
    mask_line,
    scan_text,
)
from paper.numbers import Refused, Rendered

NO_RULES = Rules((), (), ())


def claims(line: str, path: str = "docs/x.md", block: str = "") -> list[tuple[Category, str]]:
    return [(c.category, c.text) for c in line_claims(path, 1, line, block)]


def never_cited(claim: Claim) -> None:
    return None


# ------------------------------------------------------------------ detection


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Ripple reached 93.4% accuracy.", [(Category.PERCENT, "93.4%")]),
        ("check_everything passed 30/35 scenarios.", [(Category.FRACTION, "30/35")]),
        ("F1 was 0.81 on the test split.", [(Category.DECIMAL, "0.81")]),
        ("Error rates of 0.12 were seen.", [(Category.DECIMAL, "0.12")]),
        ("A ripple costs $0.012 on average.", [(Category.CURRENCY, "$0.012")]),
        ("Ripple is 4x cheaper than re-checking.", [(Category.MULTIPLIER, "4x cheaper")]),
        ("It used 412 tokens per ripple.", [(Category.METRIC_COUNT, "412 tokens")]),
        ("We saw 30 scenarios passed.", [(Category.METRIC_COUNT, "30 scenarios passed")]),
        ("A pilot of 30\u201350 students.", [(Category.METRIC_COUNT, "30\u201350 students")]),
    ],
)
def test_line_claims_detects_result_like_numbers(line: str, expected: list[tuple[Category, str]]):
    assert claims(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "170/175 checks passed",
        "It took 2048 tokens per ripple.",
        "In Phase 3, 93% of updates were right.",
        "Line 2 and 40% fewer calls.",
        "H1 \u2013 90% of the accuracy.",
        "update accuracy >= 93% here",
    ],
)
def test_line_claims_still_sees_numbers_next_to_structural_ones(line: str):
    assert claims(line) != []


@pytest.mark.parametrize(
    "line",
    [
        "Written 2026-10-31, revisit in May 2028.",
        "ADR-0063 and ADR 0110\u20130114 decide it; see H1, C1\u2013C4 and I8.",
        "Phase 3 task 0.1\u20130.7 built; WS-17 owns it.",
        "Pinned pydantic==2.14.1 on Python 3.12; ruff 0.17.1.",
        "........................ [ 98%]",
        "Refuse 401/403/407 responses.",
        "Read docs/00-vision.md and bench/run.py:120.",
        "Split by item (random 70/30) leaks personas.",
        "1. Add a macro to the registry.",
        "The model is claude-sonnet-5-5; the sha is 9f2c1ab.",
    ],
)
def test_structural_numbers_are_not_claims(line: str):
    assert claims(line) == []


def test_a_fraction_needs_a_result_context():
    assert claims("The JD says 3.0/4 as a cutoff.") == []


def test_a_decimal_needs_a_metric_word():
    assert claims("The resume says CGPA 8.4 now.") == []


def test_a_sentence_final_full_stop_does_not_hide_a_fraction():
    assert claims("so update accuracy = 3/4.") == [(Category.FRACTION, "3/4")]


def test_every_digit_is_a_claim_in_docs_paper_glued_units_included():
    assert claims("We ran 12 scenarios.", path="docs/paper/x.md") == [(Category.STRICT, "12")]
    assert claims("Latency 120ms, -5 points.", path="docs/paper/x.md") == [
        (Category.STRICT, "120"),
        (Category.STRICT, "-5"),
    ]
    assert claims("We ran 12 scenarios.") == []


def test_test_runner_counts_are_verification():
    assert claims("Full suite: 1346 passed, 31 xfailed.") == [
        (Category.VERIFICATION, "1346 passed"),
        (Category.VERIFICATION, "31 xfailed"),
    ]
    assert claims("0 errors, 0 warnings, 0 informations") == [
        (Category.VERIFICATION, "0 errors"),
        (Category.VERIFICATION, "0 warnings"),
    ]


def test_the_runner_may_be_named_on_the_line_above():
    block = "uv run pytest tests/paper -q\n78 passed in 3.91s"
    assert claims("78 passed", block=block) == [(Category.VERIFICATION, "78 passed")]


def test_pass_counts_beside_bench_vocabulary_are_metric_counts():
    assert claims("pytest: check_everything 30 passed, 5 failed") == [
        (Category.METRIC_COUNT, "30 passed"),
        (Category.METRIC_COUNT, "5 failed"),
    ]


def test_generated_and_macro_digits_are_not_strict_claims():
    line = "Accuracy {{num:h1.accuracy_ratio}} and 85.7%<!--num:v0.x.pass_share-->."
    assert [c for c in claims(line, path="docs/paper/x.md") if c[0] is not Category.MACRO] == []


def test_file_name_mask_stays_linear_on_a_long_token():
    token = "a1" * 2500 + "!"
    started = time.perf_counter()
    mask_line(token)
    assert time.perf_counter() - started < 1.0


# ------------------------------------------------------------------ macros


def _outcomes() -> dict[str, Rendered | Refused]:
    return {
        "oracle.v0.check_everything.pass_share": Rendered(
            "oracle.v0.check_everything.pass_share", 0.857, "85.7%", "85.7\\%", ()
        ),
        "h1.accuracy_ratio": Refused("h1.accuracy_ratio", "pending"),
    }


def test_registered_placeholder_is_accepted():
    assert scan_text("docs/paper/x.md", "H1: {{num:h1.accuracy_ratio}}", _outcomes()) == []


def test_unknown_placeholder_is_a_claim():
    found = scan_text("docs/x.md", "H1: {{num:h1.made_up}}", _outcomes())
    assert [(c.category, c.text) for c in found] == [(Category.MACRO, "{{num:h1.made_up}}")]


def test_annotated_value_must_equal_the_rendered_macro():
    key = "oracle.v0.check_everything.pass_share"
    good = f"passes 85.7%<!--num:{key}--> of scenarios"
    stale = f"passes 90.0%<!--num:{key}--> of scenarios"
    refused = "ratio 95.0%<!--num:h1.accuracy_ratio-->"

    assert scan_text("docs/x.md", good, _outcomes()) == []
    assert [c.category for c in scan_text("docs/x.md", stale, _outcomes())] == [Category.MACRO]
    assert [c.category for c in scan_text("docs/x.md", refused, _outcomes())] == [Category.MACRO]


def test_macro_syntax_inside_inline_code_is_documentation():
    assert scan_text("docs/x.md", "write `{{num:<key>}}` in Markdown", _outcomes()) == []


def test_a_backticked_annotation_does_not_hide_its_number():
    found = scan_text("docs/x.md", "it was `97.0%<!--num:anything-->`", _outcomes())
    assert [(c.category, c.text) for c in found] == [(Category.PERCENT, "97.0%")]


# ------------------------------------------------------------------ citations


def _run(results: Path, name: str, report: str, metrics: dict[str, object]) -> None:
    folder = results / name
    folder.mkdir(parents=True)
    (folder / "report.md").write_text(report, encoding="utf-8")
    (folder / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (folder / "config.json").write_text("{}", encoding="utf-8")


def _cited(results: Path, text: str) -> list[str | None]:
    found = scan_text("docs/x.md", text, {})
    verdicts, _ = judge(found, NO_RULES, make_citation_check(results))
    return [v.accepted_by for v in verdicts]


def test_a_citation_accepts_the_report_text_and_the_counted_metric(tmp_path: Path):
    _run(tmp_path, "r1", "Scenarios passed: 30/35 runnable", {"checks_failed": 5})

    accepted = _cited(tmp_path, "v0: 30/35 passed, 5 checks failed -> results\\r1")

    assert accepted == ["cited results/r1", "cited results/r1"]


def test_a_citation_needs_a_whole_number_match_in_the_report(tmp_path: Path):
    _run(tmp_path, "r1", "Scenarios passed: 30/35 runnable", {})

    assert _cited(tmp_path, "v0: 0/35 scenarios passed (results/r1)") == [None]


def test_a_citation_ties_a_count_to_its_own_metric_key(tmp_path: Path):
    metrics = {"checks_failed": 5, "per_scenario": [{"resolver_calls": 3}], "scenarios": 3}
    _run(tmp_path, "r1", "", metrics)

    assert _cited(tmp_path, "only 3 checks failed (results/r1)") == [None]


def test_a_citation_of_a_missing_or_escaping_folder_is_not_a_trace(tmp_path: Path):
    assert _cited(tmp_path, "v0: 30/35 scenarios passed (results/gone)") == [None]
    assert _cited(tmp_path, "v0: 30/35 scenarios passed (results/..)") == [None]


def test_a_citation_covers_its_paragraph_but_not_the_next(tmp_path: Path):
    _run(tmp_path, "r1", "Scenarios passed: 30/35 runnable", {})
    text = "- the re-run matches\n  results/r1 (30/35 passed).\n- elsewhere 30/35 passed.\n"

    assert _cited(tmp_path, text) == ["cited results/r1", None]


def test_table_rows_and_headings_do_not_share_a_citation(tmp_path: Path):
    _run(tmp_path, "r1", "Scenarios passed: 30/35 runnable", {})
    text = "| a | results/r1 |\n| b | 30/35 passed |\n"

    assert _cited(tmp_path, text) == [None]


# ------------------------------------------------------------------ rules


def _claim(path: str, text: str, category: Category = Category.PERCENT, line: str = "") -> Claim:
    return Claim(path, 1, category, text, line or text)


def test_category_rule_applies_only_inside_its_paths():
    rules = Rules((CategoryRule("verification", ("docs/plans/**",), "r", "s"),), (), ())
    inside = _claim("docs/plans/ws-1.md", "12 passed", Category.VERIFICATION)
    outside = _claim("docs/04-evaluation.md", "12 passed", Category.VERIFICATION)

    verdicts, _ = judge([inside, outside], rules, never_cited)

    assert verdicts[0].accepted_by is not None
    assert verdicts[1].accepted_by is None


def test_text_rule_needs_its_context_on_the_line():
    rule = TextRule("docs/04-evaluation.md", "90%", "H1 target line", "H1 target", "docs/04")
    rules = Rules((), (rule,), ())
    target = _claim("docs/04-evaluation.md", "90%", line="the H1 target line says 90%")
    result = _claim("docs/04-evaluation.md", "90%", line="we measured 90%")

    verdicts, _ = judge([target, result], rules, never_cited)

    assert [v.accepted_by is not None for v in verdicts] == [True, False]


def test_unused_rule_entries_are_reported_stale():
    rules = Rules(
        (CategoryRule("verification", ("docs/plans/**",), "r", "s"),),
        (TextRule("docs/a.md", "20%", "ctx", "r", "s"),),
        (),
    )

    _, stale = judge([], rules, never_cited)

    assert len(stale) == 2


def test_known_violation_covers_its_count_and_no_more():
    rules = Rules((), (), (KnownViolation("docs/a.md", "68%", 1, "estimate"),))
    found = [_claim("docs/a.md", "68%"), _claim("docs/a.md", "68%")]

    verdicts, stale = judge(found, rules, never_cited)

    assert [v.accepted_by for v in verdicts] == ["known violation", None]
    assert stale == []


def test_a_fixed_known_violation_is_reported_stale():
    rules = Rules((), (), (KnownViolation("docs/a.md", "68%", 2, "estimate"),))

    _, stale = judge([_claim("docs/a.md", "68%")], rules, never_cited)

    assert len(stale) == 1 and "listed 2x, found 1x" in stale[0]


def test_a_macro_problem_cannot_be_allow_listed_or_known():
    text = "{{num:x.y}}"
    rules = Rules(
        (),
        (TextRule("docs/a.md", text, text, "r", "s"),),
        (KnownViolation("docs/a.md", text, 1, "r"),),
    )

    verdicts, _ = judge([_claim("docs/a.md", text, Category.MACRO)], rules, never_cited)

    assert verdicts[0].accepted_by is None


@pytest.mark.parametrize(
    ("allow", "known", "message"),
    [
        ('[[text]]\npath = "docs/a.md"\ntext = "5%"\ncontext = "c"\nsource = "x"\n', "", "reason"),
        ('[[text]]\npath = "docs/a.md"\ntext = "5%"\nreason = "r"\nsource = "x"\n', "", "context"),
        (
            '[[category]]\ncategory = "verification"\npaths = "docs/**"\n'
            'reason = "r"\nsource = "s"\n',
            "",
            "paths",
        ),
        ("", '[[violation]]\npath = "docs/a.md"\ntext = "5%"\ncount = 0\nreason = "r"\n', "count"),
    ],
)
def test_load_rules_rejects_malformed_entries(tmp_path: Path, allow: str, known: str, message: str):
    (tmp_path / "allow.toml").write_text(allow, encoding="utf-8")
    (tmp_path / "known.toml").write_text(known, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_rules(tmp_path / "allow.toml", tmp_path / "known.toml")


def test_the_shipped_rule_files_load_and_never_overlap():
    rules = load_rules()

    allowed = {(r.path, r.text) for r in rules.texts}
    assert all((k.path, k.text) not in allowed for k in rules.known)


# ------------------------------------------------------------------ second review


@pytest.mark.parametrize(
    "line",
    [
        "passed 420/500 checks",
        "accuracy 300/308 on the test split",
        "\u20b92000 per month",
        "$2025 per run",
        "2000 rupees per month",
        "2015 questions asked",
        "accuracy 1980/2000",
        "see [93%](results/x/report.md) here",
        "accuracy [93%] on test",
        "accuracy>=93%",
        "recall==0.93 overall",
        "acc:93%",
    ],
)
def test_masks_do_not_hide_results_written_like_structure(line: str):
    assert claims(line) != []


def test_http_status_lists_are_masked_only_in_an_http_context():
    assert claims("Refuse 401/403/407 responses.") == []
    assert claims("checks passed 401/403") != []


def test_bench_pass_counts_are_never_verification():
    assert claims("finance_v1 suite: 12 passed, 3 failed") == [
        (Category.METRIC_COUNT, "12 passed"),
        (Category.METRIC_COUNT, "3 failed"),
    ]
    block = "uv run python -m bench.run --suite smoke --strategy ripple\n11 passed, 0 failed"
    assert claims("11 passed, 0 failed", block=block) == [
        (Category.METRIC_COUNT, "11 passed"),
        (Category.METRIC_COUNT, "0 failed"),
    ]


def test_runner_counts_beside_a_tests_path_or_vitest_output_are_verification():
    assert claims("routers (tests/llm 47 passed).") == [(Category.VERIFICATION, "47 passed")]
    assert claims("     Tests  112 passed (112)") == [(Category.VERIFICATION, "112 passed")]


def test_a_backticked_placeholder_does_not_hide_its_digits():
    found = scan_text("docs/x.md", "see `{{num:93%}}` here", {})
    assert [(c.category, c.text) for c in found] == [(Category.PERCENT, "93%")]


def test_a_citation_needs_a_results_folder_not_a_suffix(tmp_path: Path):
    _run(tmp_path, "r1", "Scenarios passed: 30/35 runnable", {})

    assert _cited(tmp_path, "v0: 30/35 passed (paper_results/r1)") == [None]


@pytest.mark.parametrize("category", ["strict", "macro"])
def test_load_rules_refuses_to_allow_list_strict_or_macro(tmp_path: Path, category: str):
    allow = (
        f'[[category]]\ncategory = "{category}"\npaths = ["docs/**"]\nreason = "r"\nsource = "s"\n'
    )
    (tmp_path / "allow.toml").write_text(allow, encoding="utf-8")
    (tmp_path / "known.toml").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot be allow-listed"):
        load_rules(tmp_path / "allow.toml", tmp_path / "known.toml")
