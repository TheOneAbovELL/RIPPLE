"""A CSS selector subset for extraction hints (ADR-0070, point 5).

Supported: `tag`, `.class`, `#id`, `[attr]`, `[attr=value]`, compounds of those,
the descendant (space) and child (`>`) combinators, and comma alternatives. Parsing is
separate from matching so the registry can refuse a bad selector at load time, before
any page is fetched.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol


class SelectableNode(Protocol):
    """What matching needs from an element tree node."""

    @property
    def tag(self) -> str: ...

    @property
    def attrs(self) -> dict[str, str]: ...

    @property
    def classes(self) -> set[str]: ...


@dataclass(frozen=True)
class SimpleSelector:
    tag: str | None
    id: str | None
    classes: frozenset[str]
    attrs: tuple[tuple[str, str | None], ...]

    def matches(self, element: SelectableNode) -> bool:
        if self.tag is not None and element.tag != self.tag:
            return False
        if self.id is not None and element.attrs.get("id") != self.id:
            return False
        if not self.classes <= element.classes:
            return False
        for name, value in self.attrs:
            if name not in element.attrs:
                return False
            if value is not None and element.attrs[name] != value:
                return False
        return True


# One alternative: (combinator, simple) pairs; " " descendant, ">" child.
CompoundSelector = list[tuple[str, SimpleSelector]]


def parse_simple(token: str) -> SimpleSelector:
    tag: str | None = None
    id_: str | None = None
    classes: set[str] = set()
    attrs: list[tuple[str, str | None]] = []
    index = 0
    while index < len(token):
        char = token[index]
        if char == "[":
            end = token.find("]", index)
            if end < 0:
                raise ValueError(f"unclosed attribute selector in {token!r}")
            name, has_value, value = token[index + 1 : end].partition("=")
            if not name.strip():
                raise ValueError(f"empty attribute name in {token!r}")
            attrs.append((name.strip().lower(), value.strip().strip("\"'") if has_value else None))
            index = end + 1
            continue
        end = index + 1
        while end < len(token) and token[end] not in ".#[":
            end += 1
        word = token[index + 1 : end] if char in ".#" else token[index:end]
        if not word:
            raise ValueError(f"bad selector token {token!r}")
        if char == ".":
            classes.add(word)
        elif char == "#":
            id_ = word
        else:
            tag = word.lower()
        index = end
    return SimpleSelector(tag, id_, frozenset(classes), tuple(attrs))


def parse_selector(selector: str) -> list[CompoundSelector]:
    """Every comma alternative as a list of (combinator, simple); ValueError when malformed."""
    alternatives: list[CompoundSelector] = []
    for alternative in selector.split(","):
        tokens = alternative.replace(">", " > ").split()
        if not tokens:
            raise ValueError(f"empty selector in {selector!r}")
        parts: CompoundSelector = []
        combinator = " "
        for token in tokens:
            if token == ">":
                combinator = ">"
                continue
            parts.append((combinator, parse_simple(token)))
            combinator = " "
        if not parts:
            raise ValueError(f"empty selector in {selector!r}")
        alternatives.append(parts)
    return alternatives


def select[NodeT: SelectableNode](
    root: NodeT, selector: str, children: Callable[[NodeT], Sequence[NodeT]]
) -> list[NodeT]:
    """Elements under `root` matching `selector`, in document order, each once.

    `children(node)` lists a node's element children; descendants are derived from it.
    """
    results: list[NodeT] = []
    seen: set[int] = set()
    for parts in parse_selector(selector):
        for element in _select_parts([root], parts, children):
            if id(element) not in seen:
                seen.add(id(element))
                results.append(element)
    return results


def _descendants[NodeT: SelectableNode](
    element: NodeT, children: Callable[[NodeT], Sequence[NodeT]]
) -> list[NodeT]:
    out: list[NodeT] = []
    for child in children(element):
        out.append(child)
        out.extend(_descendants(child, children))
    return out


def _select_parts[NodeT: SelectableNode](
    scope: list[NodeT], parts: CompoundSelector, children: Callable[[NodeT], Sequence[NodeT]]
) -> list[NodeT]:
    current = scope
    for combinator, simple in parts:
        found: list[NodeT] = []
        seen: set[int] = set()
        for element in current:
            pool = list(children(element)) if combinator == ">" else _descendants(element, children)
            for candidate in pool:
                if id(candidate) not in seen and simple.matches(candidate):
                    seen.add(id(candidate))
                    found.append(candidate)
        current = found
    return current
