"""Module-boundary tests for ripple.core (docs/02-architecture.md, ADR-0005, ADR-0016).

core is pure: it may import the standard library, pydantic and itself. This is an
allowlist, so a new vendor SDK or framework is a breach without anyone listing it.
"""

import ast
import sys
from pathlib import Path

import ripple.core

CORE_DIR = Path(ripple.core.__file__).parent

ALLOWED_TOP_LEVEL = set(sys.stdlib_module_names) | {"pydantic", "ripple"}

# Reading the wall clock in core makes time logic untestable; only clock.py may do it.
CLOCK_READS = {"now", "utcnow", "today", "time", "monotonic", "perf_counter"}


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _clock_reads(tree: ast.AST) -> set[str]:
    reads: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in CLOCK_READS
            # An injected Clock (self._clock.now(), clock.now()) is the sanctioned path.
            and "clock" not in ast.unparse(node.func.value).lower()
        ):
            reads.add(ast.unparse(node.func))
    return reads


def _core_sources() -> list[tuple[Path, ast.AST]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(CORE_DIR.rglob("*.py"))
    ]


def _is_allowed(module: str) -> bool:
    top = module.split(".", 1)[0]
    if top == "ripple":
        return module == "ripple.core" or module.startswith("ripple.core.")
    return top in ALLOWED_TOP_LEVEL


def test_core_only_imports_stdlib_pydantic_and_itself():
    breaches = [
        f"{path.relative_to(CORE_DIR)} imports {name}"
        for path, tree in _core_sources()
        for name in sorted(_imported_modules(tree))
        if not _is_allowed(name)
    ]
    assert breaches == []


def test_core_never_reads_the_wall_clock_outside_clock_module():
    breaches = [
        f"{path.relative_to(CORE_DIR)} calls {call}"
        for path, tree in _core_sources()
        if path.name != "clock.py"
        for call in sorted(_clock_reads(tree))
    ]
    assert breaches == []


def test_boundary_check_detects_a_forbidden_import():
    # The checker itself must fail on a breach, or the two tests above prove nothing.
    tree = ast.parse("from sqlalchemy import select\nimport ripple.llm\n")
    assert sorted(m for m in _imported_modules(tree) if not _is_allowed(m)) == [
        "ripple.llm",
        "sqlalchemy",
    ]


def test_clock_check_detects_disguised_now_calls():
    tree = ast.parse("from datetime import datetime as dt\nx = dt.now()\ny = time.time()\n")
    assert _clock_reads(tree) == {"dt.now", "time.time"}


def test_clock_check_allows_injected_clock():
    tree = ast.parse("now = self._clock.now()\nlater = clock.now()\n")
    assert _clock_reads(tree) == set()
