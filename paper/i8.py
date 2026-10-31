"""The I8 check: result-like numbers in README.md and docs/ must trace to results/ (ADR-0111).

    uv run python -m paper.i8            # list every finding not yet accepted
    uv run python -m paper.i8 --all      # also list accepted claims and why

A *claim* is a number that reads like a result: a percentage, a fraction in a result
context, a decimal beside a metric word, a currency amount, a multiplier ("Nx faster"),
a count of a metric noun ("N scenarios passed", "N tokens") or of a test outcome
("N passed" beside a test runner). In docs/paper/ (outside generated/) every digit is a
claim. A claim is accepted when it is
1. a macro: `{{num:<key>}}` with a registered key, or `<value><!--num:<key>-->` whose
   value equals the macro rendered from results/ now;
2. cited: its paragraph, list item or table row names a results/<run> folder whose
   report.md holds the claim's exact text, or whose metrics.json holds the counted
   number under the noun's key ("N resolver calls" -> resolver_calls);
3. allow-listed in paper/i8_allowlist.toml, by category for named paths or by exact
   text on a line holding a stated context, each with a reason and a source;
4. a known violation in paper/i8_known_violations.toml, listed with a reason.
Anything else is a new violation. Structural numbers (dates, versions, ADR/FR/WS ids,
claim and hypothesis ids, phases, HTTP status lists, pytest progress) are masked first.
The detector is a heuristic: it errs toward flagging, and a bare integer with no metric
noun is not seen outside docs/paper/ (stated in ADR-0111).
"""

import argparse
import io
import json
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from paper.numbers import (
    MACRO_OPENING,
    MACRO_REFERENCE,
    REPO_ROOT,
    RESULTS_DIR,
    Outcome,
    Rendered,
    resolve_all,
)
from paper.registry import REGISTRY, AnySpec

ALLOWLIST_FILE = Path(__file__).with_name("i8_allowlist.toml")
KNOWN_VIOLATIONS_FILE = Path(__file__).with_name("i8_known_violations.toml")
STRICT_PREFIX = "docs/paper/"
EXCLUDED_PREFIX = "docs/paper/generated/"  # written by paper.numbers from results/


class Category(StrEnum):
    PERCENT = "percent"
    FRACTION = "fraction"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    MULTIPLIER = "multiplier"
    METRIC_COUNT = "metric_count"
    VERIFICATION = "verification"  # test-runner output counts
    STRICT = "strict"  # any digit in docs/paper
    MACRO = "macro"  # an unknown macro key or a stale annotated value


@dataclass(frozen=True)
class Claim:
    path: str  # posix, relative to the repository root
    line: int
    category: Category
    text: str  # the matched span, whitespace collapsed
    context: str  # the stripped line, for humans and for text rules
    block: str = ""  # the paragraph, list item or table row holding the line

    @property
    def key(self) -> tuple[str, str]:
        return self.path, self.text


@dataclass(frozen=True)
class Verdict:
    claim: Claim
    accepted_by: str | None  # None = violation


# ------------------------------------------------------------------ masking


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


# A number followed by one of these is a quantity even when it looks like a year.
_QUANTITY_AHEAD = (
    r"(?!\s*(?:%|tokens|students|users|participants|ms\b|seconds|resolver|LLM|checks?\b|"
    r"scenarios?\b|calls|passed|failed|pairs|questions|runnable|stale|rupees|dollars|USD|"
    r"INR|EUR|per\b)|/\d)"
)
# A number glued to a percent sign is never structural, whatever precedes it.
_NOT_PERCENT = r"(?![\d.]*%)"
_HTTP = r"(?:20[0-8]|30[0-8]|4[0-2]\d|431|451|50\d|51[01])"

STRUCTURAL_MASKS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*\d+[.)](?=\s)"),  # ordered-list markers
    re.compile(r"https?://\S+"),
    re.compile(r"\]\([^)]*\)"),  # Markdown link targets
    re.compile(r"^[.FEsxX]*\s*\[\s*\d{1,3}%\]\s*$"),  # a pytest progress line
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:.+]+Z?)?"),  # ISO dates and timestamps
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),  # day/month/year
    re.compile(
        r"(?<![$\u20b9\u20ac\u00a3\d.,/])\b(?:19|20)\d{2}(?:[\u2013-](?:19|20)?\d{2})?\b"
        + _QUANTITY_AHEAD
    ),
    re.compile(r"\bv?\d+\.\d+\.\d+[\w.-]*"),  # semantic versions
    re.compile(r"\b(?:Python|python|py)\s?\d+(?:\.\d+)*"),
    re.compile(
        r"\b(?:ADRs?|FR|NFR|WS|IDEAS|[Pp]roposals?|[Pp]hase|[Mm]igrations?|[Ww]ave|"
        r"[Ss]ection|[Ss]tep|[Ii]tem|[Ll]ine|[Rr]ound|[Cc]heckpoint|[Ii]nvariant|PR)"
        r"[\s#-]?\d+(?![\d.]*%)(?:\s?(?:\u2013|-|\.\.)\s?\d+(?![\d.]*%))*"
    ),
    re.compile(r"(?<!\w)#\d+\b"),
    re.compile(r"\b[Tt]asks?\s+\d+\.\d+(?:\s?[\u2013-]\s?\d+\.\d+)?"),  # roadmap task ids
    re.compile(r"\b[CHQI]\d+(?:\s?[\u2013-]\s?[CHQI]\d+)?\b"),  # C1-C4, H1, Q3, I8
    re.compile(r":\d+(?::\d+)?\b" + _NOT_PERCENT),  # file:line and ports
    re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),  # shas (at least one letter)
)
# Tokens are matched whole so the file-name test cannot backtrack across a long word.
PATH_TOKEN = re.compile(r"[\w./\\-]+")
FILE_SUFFIX = re.compile(r"\.(?:md|py|json|toml|ya?ml|tsx?|csv|svg|tex|dat|jsonl)$")


def _blank_file_name(match: re.Match[str]) -> str:
    token = match.group(0)
    is_file = any(c.isdigit() for c in token) and FILE_SUFFIX.search(token.rstrip("."))
    return " " * len(token) if is_file else token


# Masks that depend on what surrounds the number.
HTTP_LIST = re.compile(rf"\b{_HTTP}(?:/{_HTTP})+\b")  # 401/403/407
HTTP_CONTEXT = re.compile(r"\b(?:HTTP|status|respon\w*|codes?|refus\w*|redirect\w*)\b", re.I)
# "batch 2026/2027" is a year pair, "accuracy 1980/2000" is a fraction.
YEAR_PAIR = re.compile(r"\b(?:19|20)\d{2}/(?:19|20)?\d{2}\b" + _QUANTITY_AHEAD)
PIN = re.compile(r"\b([A-Za-z][\w.-]*)[=<>~!]=\d+\.\d+[\w.]*" + _NOT_PERCENT)


def _blank_pin(match: re.Match[str]) -> str:
    """pydantic==2.14.1 is a pin; recall>=0.93 is a claim."""
    return match.group(0) if METRIC_WORDS.fullmatch(match.group(1)) else _blank(match)


def mask_line(line: str) -> str:
    original = line
    line = PATH_TOKEN.sub(_blank_file_name, line)
    for pattern in STRUCTURAL_MASKS:
        line = pattern.sub(_blank, line)
    line = PIN.sub(_blank_pin, line)
    if not RESULT_CONTEXT.search(original):
        line = YEAR_PAIR.sub(_blank, line)
        if HTTP_CONTEXT.search(original):
            line = HTTP_LIST.sub(_blank, line)
    return line


def _collapse(text: str) -> str:
    return " ".join(text.split())


# ------------------------------------------------------------------ detection

PLACEHOLDER = MACRO_REFERENCE  # one pattern for the renderer and the check
ANNOTATED = re.compile(r"(\S+?)<!--\s*num:([^\s>]*)\s*-->")
INLINE_CODE = re.compile(r"`[^`]*`")
RESULTS_CITATION = re.compile(r"(?<![\w/\\])results[/\\]((?:pilot[/\\])?[\w.-]+)")

RESULT_CONTEXT = re.compile(
    r"\b(?:pass(?:ed|es)?|fail(?:ed|s)?|scenarios?|checks?|accuracy|correct|scor(?:e|es|ed)|"
    r"smoke|rates?|shares?|runnable|tests?|precision|recall|f1|agreement)\b|=",
    re.IGNORECASE,
)
METRIC_WORDS = re.compile(
    r"\b(?:accurac(?:y|ies)|precision|recall|f1|auc|kappa|agreement|rates?|scor(?:e|es|ed|ing)|"
    r"shares?|ratios?|costs?|ttc|latency|mean|median|p\d{2}|tokens?|usd|seconds|ms)\b",
    re.IGNORECASE,
)
# "N passed" is test output only beside a named test runner and away from bench
# vocabulary in its whole paragraph.
TEST_RUNNER = re.compile(
    r"\b(?:pytest|vitest|jest|ruff|pyright|npm|informations)\b|\bin \d+(?:\.\d+)?s\b|={3,}|"
    r"(?<![\w/\\])tests[/\\]|\bTest Files\b|^\s*Tests\s+\d",
    re.IGNORECASE,
)
BENCH_WORDS = re.compile(
    r"(?<![/\\\w])(?:scenarios?|checks? failed|v0|smoke|bench|check_everything|append_only|"
    r"newest_wins|strateg(?:y|ies)|oracle|linkpairs|resolver calls)\b|bench\.run|"
    r"\b[a-z]+_v\d+\b|(?<![\w/\\])results[/\\]",
    re.IGNORECASE,
)
# Outcomes only a test runner reports; a bench run never has an "xfailed" or "N tests".
RUNNER_ONLY = re.compile(r"\b(?:xfailed|xpassed|skipped|deselected|warnings?|tests?)$")
OUTCOME_COUNT = re.compile(
    r"(?<![\w.:/-])\d[\d,]*\s+(?:passed|failed|xfailed|xpassed|skipped|deselected|errors?|"
    r"warnings?|tests?)\b"
)
METRIC_NOUNS = (
    r"(?:runnable\s+)?scenarios?\s+passed|checks?\s+failed|resolver\s+calls|LLM\s+calls|"
    r"tokens|students|users|participants|questions\s+asked|"
    r"stale\s+(?:recommendations|retrievals|beliefs)"
)
DETECTORS: tuple[tuple[Category, re.Pattern[str]], ...] = (
    (Category.PERCENT, re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?(?:%|per ?cent\b)")),
    (
        Category.CURRENCY,
        re.compile(
            r"[$₹€£]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:USD|INR|EUR|dollars|rupees)\b"
        ),
    ),
    (
        Category.MULTIPLIER,
        re.compile(
            r"(?<![\w.])\d+(?:\.\d+)?\s?(?:\u00d7|x)\s+"
            r"(?:faster|slower|cheaper|fewer|more|less|smaller|larger)\b"
        ),
    ),
    (
        Category.METRIC_COUNT,
        re.compile(
            rf"(?<![\w.:/-])\d[\d,]*(?:\s?[\u2013-]\s?\d[\d,]*)?\s+(?:{METRIC_NOUNS})\b",
            re.IGNORECASE,
        ),
    ),
)
# A sentence-final full stop ends a number; a dot followed by a digit continues it.
FRACTION = re.compile(r"(?<![\w./-])\d+(?:\.\d+)?/\d+(?:\.\d+)?(?![\w/]|\.\d)")
DECIMAL = re.compile(r"(?<![\w./-])\d*\.\d+(?![\w]|\.\d)")
# Strict mode also catches glued units ("120ms", "4x") and signed values ("-5").
STRICT_NUMBER = re.compile(r"(?<![\w./\\#])-?\d(?:[\d.,]*\d)?")


def _code_spans(line: str) -> list[tuple[int, int]]:
    return [m.span() for m in INLINE_CODE.finditer(line)]


def _inside(match: re.Match[str], spans: Sequence[tuple[int, int]]) -> bool:
    return any(start <= match.start() and match.end() <= end for start, end in spans)


def macro_claims(
    path: str, number: int, line: str, outcomes: Mapping[str, Outcome]
) -> Iterator[Claim]:
    """Problems with macro references on a line: unknown keys and stale values. A
    reference inside an inline code span documents the syntax and is not checked (and
    its digits are then scanned like any other text)."""
    code = _code_spans(line)
    for match in PLACEHOLDER.finditer(line):
        if match.group(1) not in REGISTRY and not _inside(match, code):
            yield Claim(path, number, Category.MACRO, match.group(0), line.strip())
    well_formed = {m.start() for m in PLACEHOLDER.finditer(line)}
    for match in re.finditer(re.escape(MACRO_OPENING), line):
        if match.start() not in well_formed and not _inside(match, code):
            yield Claim(
                path, number, Category.MACRO, line[match.start() :].strip()[:40], line.strip()
            )
    for match in ANNOTATED.finditer(line):
        if _inside(match, code):
            continue
        value, key = match.group(1), match.group(2)
        outcome = outcomes.get(key)
        if not isinstance(outcome, Rendered) or outcome.markdown != value:
            yield Claim(path, number, Category.MACRO, match.group(0), line.strip())


def _mask_macros(line: str) -> str:
    """Blank placeholders everywhere (they hold no value) and annotated values outside
    code (macro_claims checks those); an annotation inside code is plain text."""
    code = _code_spans(line)
    keep_code = lambda m: m.group(0) if _inside(m, code) else _blank(m)  # noqa: E731
    return ANNOTATED.sub(keep_code, PLACEHOLDER.sub(keep_code, line))


def line_claims(path: str, number: int, line: str, block: str = "") -> Iterator[Claim]:
    """Claims on one line; `block` (its paragraph) decides whether "N passed" is test
    output, since the runner command is often on the line above."""
    masked = mask_line(_mask_macros(line))
    taken: list[tuple[int, int]] = []

    def emit(category: Category, match: re.Match[str]) -> Iterator[Claim]:
        span = match.span()
        if any(span[0] < end and start < span[1] for start, end in taken):
            return
        taken.append(span)
        yield Claim(path, number, category, _collapse(match.group(0)), line.strip())

    for category, pattern in DETECTORS:
        for match in pattern.finditer(masked):
            yield from emit(category, match)
    # Test output: a runner named in the paragraph and no bench vocabulary on the line,
    # or a line that reports a runner-only outcome ("xfailed": a bench run has none).
    outcomes = list(OUTCOME_COUNT.finditer(masked))
    runner_line = any(RUNNER_ONLY.search(m.group(0)) for m in outcomes)

    def runner_without_bench(text: str) -> bool:
        return TEST_RUNNER.search(text) is not None and BENCH_WORDS.search(text) is None

    surrounding = mask_line(_mask_macros(block or line))
    test_output = runner_line or runner_without_bench(masked) or runner_without_bench(surrounding)
    for match in outcomes:
        yield from emit(Category.VERIFICATION if test_output else Category.METRIC_COUNT, match)
    if RESULT_CONTEXT.search(masked):
        for match in FRACTION.finditer(masked):
            yield from emit(Category.FRACTION, match)
    if METRIC_WORDS.search(masked):
        for match in DECIMAL.finditer(masked):
            yield from emit(Category.DECIMAL, match)
    if path.startswith(STRICT_PREFIX):
        for match in STRICT_NUMBER.finditer(masked):
            yield from emit(Category.STRICT, match)


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
OWN_BLOCK = re.compile(r"^\s*(?:\||#{1,6}\s)")  # table rows and headings stand alone


def blocks(lines: Sequence[str]) -> list[str]:
    """For each line, the paragraph, list item, table row or heading it belongs to: a
    citation anywhere in it covers the numbers of every line in it (a bullet wraps)."""
    groups: list[list[str]] = []
    owner: list[int] = []
    for index, line in enumerate(lines):
        starts_block = (
            index == 0
            or not line.strip()
            or not lines[index - 1].strip()
            or LIST_ITEM.match(line) is not None
            or OWN_BLOCK.match(line) is not None
            or OWN_BLOCK.match(lines[index - 1]) is not None
        )
        if starts_block:
            groups.append([])
        groups[-1].append(line)
        owner.append(len(groups) - 1)
    joined = ["\n".join(group) for group in groups]
    return [joined[group] for group in owner]


def scan_text(path: str, text: str, outcomes: Mapping[str, Outcome]) -> list[Claim]:
    claims: list[Claim] = []
    lines = text.splitlines()
    for number, (line, block) in enumerate(zip(lines, blocks(lines), strict=True), start=1):
        claims.extend(macro_claims(path, number, line, outcomes))
        found = line_claims(path, number, line, block)
        claims.extend(replace(c, block=block) for c in found)
    return claims


def scanned_files(root: Path = REPO_ROOT) -> list[Path]:
    files = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    return [
        f
        for f in files
        if f.is_file() and not f.relative_to(root).as_posix().startswith(EXCLUDED_PREFIX)
    ]


# ------------------------------------------------------------------ acceptance


@dataclass(frozen=True)
class CategoryRule:
    category: str
    paths: tuple[str, ...]
    reason: str
    source: str


@dataclass(frozen=True)
class TextRule:
    path: str
    text: str
    context: str  # a substring the claim's line must hold, so a later result is not covered
    reason: str
    source: str


@dataclass(frozen=True)
class KnownViolation:
    path: str
    text: str
    count: int
    reason: str


@dataclass(frozen=True)
class Rules:
    categories: tuple[CategoryRule, ...]
    texts: tuple[TextRule, ...]
    known: tuple[KnownViolation, ...]


def path_matches(pattern: str, path: str) -> bool:
    """Exact path, or a directory prefix written as `dir/**`."""
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return path == pattern


def _table(document: Mapping[str, Any], name: str) -> list[Mapping[str, Any]]:
    entries = document.get(name, [])
    if not isinstance(entries, list):
        raise ValueError(f"[[{name}]] must be an array of tables")
    return entries  # pyright: ignore[reportUnknownVariableType]


def _required(entry: Mapping[str, Any], field: str, where: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: `{field}` is required and must be non-empty")
    return value


def _paths(entry: Mapping[str, Any]) -> tuple[str, ...]:
    paths = entry.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):  # pyright: ignore[reportUnknownVariableType]
        raise ValueError("category rule: `paths` must be a non-empty list of strings")
    return tuple(paths)  # pyright: ignore[reportUnknownArgumentType]


def _allowable(category: str) -> str:
    """Strict-mode digits and macro problems are never allow-listed by category."""
    if Category(category) in (Category.STRICT, Category.MACRO):
        raise ValueError(f"category rule: `{category}` cannot be allow-listed")
    return category


def _count(entry: Mapping[str, Any]) -> int:
    count = entry.get("count", 1)
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError(f"violation {entry.get('text')!r}: `count` must be an integer >= 1")
    return count


def load_rules(
    allowlist: Path = ALLOWLIST_FILE, known_violations: Path = KNOWN_VIOLATIONS_FILE
) -> Rules:
    allow = tomllib.loads(allowlist.read_text(encoding="utf-8"))
    known = tomllib.loads(known_violations.read_text(encoding="utf-8"))
    categories = tuple(
        CategoryRule(
            category=_allowable(_required(e, "category", "category rule")),
            paths=_paths(e),
            reason=_required(e, "reason", "category rule"),
            source=_required(e, "source", "category rule"),
        )
        for e in _table(allow, "category")
    )
    texts = tuple(
        TextRule(
            path=_required(e, "path", "text rule"),
            text=_required(e, "text", "text rule"),
            context=_required(e, "context", f"text rule {e.get('text')!r}"),
            reason=_required(e, "reason", f"text rule {e.get('text')!r}"),
            source=_required(e, "source", f"text rule {e.get('text')!r}"),
        )
        for e in _table(allow, "text")
    )
    known_entries = tuple(
        KnownViolation(
            path=_required(e, "path", "violation"),
            text=_required(e, "text", "violation"),
            count=_count(e),
            reason=_required(e, "reason", f"violation {e.get('text')!r}"),
        )
        for e in _table(known, "violation")
    )
    return Rules(categories, texts, known_entries)


@dataclass(frozen=True)
class CitedRun:
    report: str  # report.md, whitespace collapsed
    metrics: Mapping[str, float]  # top-level numeric metrics only


def _cited_run(folder: Path) -> CitedRun | None:
    """What a cited run can vouch for; None when it is not a readable run folder."""
    try:
        report_file = folder / "report.md"
        report = report_file.read_text(encoding="utf-8") if report_file.is_file() else ""
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(metrics, dict):
        return None
    scalars = {
        str(k): float(v)
        for k, v in metrics.items()  # pyright: ignore[reportUnknownVariableType]
        if isinstance(v, int | float) and not isinstance(v, bool)
    }
    return CitedRun(_collapse(report), scalars)


COUNT_CLAIM = re.compile(r"(\d[\d,]*)\s+(.+)")


def _metric_key(noun: str) -> str:
    """'runnable scenarios passed' -> 'scenarios_passed', 'LLM calls' -> 'llm_calls'."""
    words = noun.lower().split()
    return "_".join(w for w in words if w != "runnable")


def vouches(run: CitedRun, claim: Claim) -> bool:
    bounded = re.compile(rf"(?<![\d.,/]){re.escape(claim.text)}(?![\d.,/%])")
    if bounded.search(run.report):
        return True
    count = COUNT_CLAIM.fullmatch(claim.text)
    if claim.category is Category.METRIC_COUNT and count:
        value = run.metrics.get(_metric_key(count.group(2)))
        return value is not None and value == float(count.group(1).replace(",", ""))
    return False


def make_citation_check(results_dir: Path) -> Callable[[Claim], str | None]:
    cache: dict[str, CitedRun | None] = {}

    def cited(claim: Claim) -> str | None:
        if claim.category in (Category.STRICT, Category.MACRO):
            return None
        for match in RESULTS_CITATION.finditer(claim.block or claim.context):
            name = match.group(1).replace("\\", "/").rstrip(".")
            if not name or ".." in name:
                continue
            if name not in cache:
                folder = results_dir / name
                cache[name] = _cited_run(folder) if folder.is_dir() else None
            run = cache[name]
            if run is not None and vouches(run, claim):
                return f"cited results/{name}"
        return None

    return cited


def judge(
    claims: Sequence[Claim], rules: Rules, cited: Callable[[Claim], str | None]
) -> tuple[list[Verdict], list[str]]:
    """Verdicts for every claim, and the stale entries of the rule files. A macro problem
    is never accepted by any rule."""
    verdicts: list[Verdict] = []
    used_texts: set[TextRule] = set()
    used_categories: set[CategoryRule] = set()
    known_left: Counter[tuple[str, str]] = Counter()
    for entry in rules.known:
        known_left[(entry.path, entry.text)] += entry.count
    known_seen: Counter[tuple[str, str]] = Counter()
    for claim in claims:
        accepted = None
        if claim.category is not Category.MACRO:
            accepted = cited(claim)
            if accepted is None:
                for category_rule in rules.categories:
                    if category_rule.category == claim.category.value and any(
                        path_matches(p, claim.path) for p in category_rule.paths
                    ):
                        used_categories.add(category_rule)
                        accepted = f"allow-list category {category_rule.category}"
                        break
            if accepted is None:
                for rule in rules.texts:
                    if (
                        rule.text == claim.text
                        and rule.context in claim.context
                        and path_matches(rule.path, claim.path)
                    ):
                        used_texts.add(rule)
                        accepted = f"allow-list: {rule.reason} ({rule.source})"
                        break
            if accepted is None and known_seen[claim.key] < known_left[claim.key]:
                known_seen[claim.key] += 1
                accepted = "known violation"
        verdicts.append(Verdict(claim, accepted))
    stale = [
        f"allow-list text {r.text!r} for {r.path} (context {r.context!r}) matches nothing"
        for r in rules.texts
        if r not in used_texts
    ]
    stale += [
        f"allow-list category {r.category} for {list(r.paths)} matches nothing"
        for r in rules.categories
        if r not in used_categories
    ]
    for key, count in known_left.items():
        if known_seen[key] < count:
            stale.append(
                f"known violation {key[1]!r} in {key[0]} listed {count}x, found "
                f"{known_seen[key]}x: lower the count or remove the entry"
            )
    return verdicts, stale


def check(
    root: Path = REPO_ROOT,
    results_dir: Path = RESULTS_DIR,
    rules: Rules | None = None,
    outcomes: Mapping[str, Outcome] | None = None,
    files: Iterable[Path] | None = None,
) -> tuple[list[Verdict], list[str]]:
    outcomes = resolve_all(results_dir) if outcomes is None else outcomes
    rules = load_rules() if rules is None else rules
    claims: list[Claim] = []
    for file in scanned_files(root) if files is None else files:
        path = file.relative_to(root).as_posix()
        claims.extend(scan_text(path, file.read_text(encoding="utf-8"), outcomes))
    return judge(claims, rules, make_citation_check(results_dir))


def describe(verdict: Verdict) -> str:
    c = verdict.claim
    return f"{c.path}:{c.line} [{c.category.value}] {c.text!r} — {c.context[:120]}"


def main(argv: list[str] | None = None, registry: Mapping[str, AnySpec] = REGISTRY) -> int:
    parser = argparse.ArgumentParser(description="Run the I8 check over README.md and docs/")
    parser.add_argument("--all", action="store_true", help="also list accepted claims")
    args = parser.parse_args(argv)
    # Docs quote dashes and arrows; a Windows console codepage would crash the report.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    verdicts, stale = check()
    violations = [v for v in verdicts if v.accepted_by is None]
    known = [v for v in verdicts if v.accepted_by == "known violation"]
    if args.all:
        for verdict in verdicts:
            if verdict.accepted_by is not None:
                print(f"ok    {describe(verdict)}  <- {verdict.accepted_by}")
    for verdict in violations:
        print(f"NEW   {describe(verdict)}")
    for entry in stale:
        print(f"STALE {entry}")
    print(
        f"{len(verdicts)} claims: {len(violations)} new violations, {len(known)} known, "
        f"{len(stale)} stale rule entries; {len(registry)} registered macros"
    )
    return 1 if violations or stale else 0


if __name__ == "__main__":
    sys.exit(main())
