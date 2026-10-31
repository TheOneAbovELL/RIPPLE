"""Helpers for the parser tests: a Router over FakeLLM, sample texts, builders, a
hand-built PDF. Not a conftest, so importing from it is an ordinary import."""

import json

from ripple.domains.jobs.vocabulary import CandidateFact, TextSpan
from ripple.llm.config import ModelSpec, RouterConfig
from ripple.llm.router import Router
from tests.fakes.llm import FakeLLM

JD_TEXT = """Acme Robotics — Software Engineer Intern (Summer 2027)

Location: Bengaluru, India
Eligibility: B.Tech 2027 batch, CGPA 7.5 and above, no active backlogs.
Skills: Python, C++, ROS
Apply by 15 November 2026, 11:59 PM IST via the placement portal.
"""

RESUME_TEXT = """Omjee R Giri
B.Tech Computer Science and Engineering, 2023-2027
CGPA: 8.1 / 10
Skills: Python, Go, PostgreSQL
Projects: Ripple - a consistency layer for agent memory
Open to backend roles in Bengaluru
"""


def router_for(task: str, llm: FakeLLM, *, max_retries: int = 2) -> Router:
    config = RouterConfig(
        tasks={task: [ModelSpec(provider="fake", model="f")]}, max_retries=max_retries
    )
    return Router(config, {"fake": llm})


def jd_reply(*fields: dict) -> str:
    return json.dumps({"fields": list(fields)})


def resume_reply(*candidates: dict) -> str:
    return json.dumps({"candidates": list(candidates)})


def candidate(
    attribute: str = "cgpa",
    value: str | int | float = 8.1,
    *,
    text: str = "CGPA: 8.1 / 10",
    start: int = 60,
    confidence: float = 1.0,
    content: str = "CGPA is 8.1",
) -> CandidateFact:
    return CandidateFact(
        attribute=attribute,
        value=value,
        span=TextSpan(start=start, end=start + len(text), text=text),
        confidence=confidence,
        content=content,
    )


def build_pdf(content_stream: bytes, *, pages: int = 1) -> bytes:
    """A minimal PDF with a hand-written xref table (no binary fixture); every page
    shows the same content stream."""
    page_numbers = [4 + 2 * i for i in range(pages)]  # page object, then its stream
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % n for n in page_numbers), pages),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for number in page_numbers:
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
            b"/Resources << /Font << /F1 3 0 R >> >> >>" % (number + 1)
        )
        objects.append(
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content_stream), content_stream)
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_at,
    )
    return bytes(out)


def text_stream(*lines: str) -> bytes:
    """One text-showing operator per line so pypdf extracts them line by line."""
    ops = b"BT /F1 12 Tf 72 720 Td "
    for index, line in enumerate(lines):
        if index:
            ops += b"0 -16 Td "
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops += b"(" + escaped.encode("latin-1") + b") Tj "
    return ops + b"ET"


def pdf_with_lines(*lines: str, pages: int = 1) -> bytes:
    return build_pdf(text_stream(*lines), pages=pages)
