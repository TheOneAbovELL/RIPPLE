# ADR-0024: Resume parsing: pypdf text extraction, LLM structuring, user confirmation
Status: Accepted · Date: 2026-10-19 (under the autonomous mandate)

## Context
FR-1: parse an uploaded resume into profile facts the user confirms one by one; I5:
nothing is stored without confirmation. Resumes arrive as PDF.

## Decision
`pypdf` (pure Python, exact pin) extracts text. The LLM structures it into a validated
schema of candidate facts (ripple.llm.schemas.resume) with the text span each fact
came from. Candidate facts are held in a pending-confirmation state outside the memory
store (they are not memories yet); only confirmed facts become memories through
ripple.core.intake. Rejected candidates are discarded. Scanned PDFs without a text
layer are reported as unparseable; OCR is out of scope.

## Alternatives considered
- pdfminer.six / PyMuPDF — more capable layout analysis; heavier (PyMuPDF is a binary
  wheel). Resumes are simple text documents; lost on weight.
- LLM reads the PDF directly (vision) — vendor-specific, costly, and the text layer is
  enough. Lost.
- Storing candidates as PENDING_USER memories — tempting, but PENDING_USER means "was
  valid, now in question"; unconfirmed extractions were never valid (I5). Lost.

## Consequences
- One small dependency. A confirmation flow and its storage belong to the API
  workstream (ADR-0040 range).
- Every stored profile fact has source_ref pointing at the resume upload and span.

## Revisit if
Pilot resumes are mostly scanned images, which would justify OCR.
