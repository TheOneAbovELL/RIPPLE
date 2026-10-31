"""Candidate JD texts out of a fetched page (ADR-0070, point 4).

HTML goes through the standard library's html.parser into a small element tree and a
CSS selector subset (tag, .class, #id, [attr], [attr=value], descendant and child
combinators, comma alternatives); JSON through dotted paths. No new dependency: the
pilot's sources are a handful of career pages and APIs whose hints the author writes
by hand, not the open web. Text is the page's own words, which is all the JD parser
(WS-2) may quote (I5).
"""

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from ripple.domains.jobs.sources.registry import ExtractionHint
from ripple.domains.jobs.sources.selectors import select

_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source"}
    | {"track", "wbr"}
)
_SKIPPED = frozenset({"script", "style", "noscript", "template"})
_BLOCK = frozenset(
    {
        "address", "article", "aside", "blockquote", "dd", "details", "div", "dl", "dt",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
        "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
        "tbody", "td", "tfoot", "th", "thead", "tr", "ul", "br",
    }
)  # fmt: skip
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Candidate:
    """One possible opening: where it lives and the text the parser will read."""

    text: str
    url: str | None = None
    title: str | None = None


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list["_Element | str"] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("#root", {})
        self._stack: list[_Element] = [self.root]
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag, {k: v or "" for k, v in attrs})
        self._stack[-1].children.append(element)
        if tag in _SKIPPED:
            self._skipping += 1
        if tag not in _VOID:
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack[-1].children.append(_Element(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED and self._skipping:
            self._skipping -= 1
        # Close up to the nearest open element of this tag; a stray close tag is ignored.
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self._skipping and data:
            self._stack[-1].children.append(data)


def _parse_html(html: str) -> _Element:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


# ---- selectors ---------------------------------------------------------------------


def _element_children(element: _Element) -> list[_Element]:
    return [c for c in element.children if isinstance(c, _Element)]


def _descendants(element: _Element) -> list[_Element]:
    out: list[_Element] = []
    for child in _element_children(element):
        out.append(child)
        out.extend(_descendants(child))
    return out


def _select(root: _Element, selector: str) -> list[_Element]:
    return select(root, selector, _element_children)


# ---- text ------------------------------------------------------------------------


def _collect_text(element: _Element, out: list[str]) -> None:
    if element.tag in _SKIPPED:
        return
    if element.tag in _BLOCK:
        out.append("\n")
    for child in element.children:
        if isinstance(child, str):
            # Source newlines inside an element are formatting, not line breaks;
            # only block elements (above and below) start a new line.
            out.append(_WHITESPACE.sub(" ", child))
        else:
            _collect_text(child, out)
    if element.tag in _BLOCK:
        out.append("\n")


def _text_of(element: _Element) -> str:
    parts: list[str] = []
    _collect_text(element, parts)
    lines = (" ".join(line.split()) for line in "".join(parts).split("\n"))
    return "\n".join(line for line in lines if line)


def _first_href(element: _Element) -> str | None:
    if element.tag == "a" and element.attrs.get("href"):
        return element.attrs["href"]
    for child in _descendants(element):
        if child.tag == "a" and child.attrs.get("href"):
            return child.attrs["href"]
    return None


def _title_of(element: _Element, text: str) -> str | None:
    for child in _descendants(element):
        if child.tag in _HEADINGS:
            heading = _text_of(child)
            if heading:
                return heading
    first_line = text.split("\n", 1)[0]
    return first_line or None


def page_text(html: str, selector: str | None = None) -> str:
    """The page's text, or the text of the elements `selector` matches, one block each."""
    root = _parse_html(html)
    if selector is None:
        return _text_of(root)
    return "\n\n".join(text for text in (_text_of(e) for e in _select(root, selector)) if text)


def html_candidates(html: str, page_url: str, selector: str) -> list[Candidate]:
    root = _parse_html(html)
    candidates: list[Candidate] = []
    for element in _select(root, selector):
        text = _text_of(element)
        if not text:
            continue
        href = _first_href(element)
        url = urljoin(page_url, href) if href else None
        candidates.append(Candidate(text=text, url=url, title=_title_of(element, text)))
    return candidates


# ---- json ------------------------------------------------------------------------


def _walk(value: Any, path: str) -> Any:
    for part in path.split("."):
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        else:
            return None
    return value


def json_candidates(data: Any, page_url: str, hint: ExtractionHint) -> list[Candidate]:
    if hint.json_items is None or hint.json_text is None:
        raise ValueError("json extraction needs json_items and json_text hints")
    items = _walk(data, hint.json_items) if hint.json_items != "$" else data
    if not isinstance(items, list):
        return []
    candidates: list[Candidate] = []
    for item in items:
        text = _walk(item, hint.json_text)
        if not isinstance(text, str) or not text.strip():
            continue
        url_value = _walk(item, hint.json_url) if hint.json_url else None
        title_value = _walk(item, hint.json_title) if hint.json_title else None
        url = urljoin(page_url, url_value) if isinstance(url_value, str) and url_value else None
        title = title_value if isinstance(title_value, str) and title_value else None
        if "<" in text and ">" in text:  # APIs often return the description as HTML
            text = page_text(text)
        candidates.append(Candidate(text=text.strip(), url=url, title=title))
    return candidates


def extract_candidates(
    body: str, content_type: str, page_url: str, hint: ExtractionHint
) -> list[Candidate]:
    """Dispatch on the hint and the content type; a mismatch yields no candidates."""
    is_json = "json" in content_type.lower()
    if hint.json_items is not None and (is_json or hint.css_selector is None):
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"source returned invalid JSON: {exc}") from exc
        return json_candidates(data, page_url, hint)
    if hint.css_selector is not None:
        return html_candidates(body, page_url, hint.css_selector)
    return []
