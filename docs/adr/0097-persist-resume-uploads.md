# ADR-0097: The text layer of every resume upload is stored so span references resolve
Status: Accepted under the autonomous mandate · Date: 2026-10-26
Amends ADR-0043 (what `POST /resume` stores) and the `ResumeParser` contract.

## Context
A confirmed resume fact carries `source_ref = "resume:<upload id>#<start>-<end>"`
(WS-2's `candidate_to_statement`, ADR-0043). Until now the upload id named nothing:
the parser's text was discarded after extraction, so the offsets pointed into text no
one kept. FR-12 asks the inspector to show where a belief came from, and I5 says the
agent never invents a profile fact; a quote that cannot be shown cannot be checked.
The round-2 brief for WS-13 asks to persist the text and show the quoted line on
`GET /memories/{id}`.

## Decision
1. A `resume_uploads` table (`ripple.storage.uploads_tables`, migration 0006,
   hand-written per ADR-0016): `id`, `user_id` (foreign key to `users.id`, `ON DELETE
   CASCADE`), `filename` (≤ 255), `sha256` of the PDF bytes, `text`, `uploaded_at`
   (timezone-aware), indexed on `user_id`. The PDF bytes are not stored: the spans
   index into the text, and the file is the user's.
2. `ResumeUpload` model and `UploadStore` protocol (`add_upload`, `get_upload`,
   `uploads_for_user` oldest first then by id, `delete_for_user`) in
   `ripple.storage.uploads`, with `InMemoryUploadStore` and `PostgresUploadStore` and
   one contract test. `Services.upload_store` defaults to the in-memory store;
   `build_services` passes the Postgres one, and a test pins that.
3. `ResumeParser.parse` now returns `ResumeParse(text, facts)` instead of the facts
   alone; the production adapter already had the text and passes it through.
4. `POST /resume` builds the upload id first, parses with `source_ref=resume:<id>`,
   refuses text longer than `MAX_RESUME_TEXT_CHARS` (200,000) with 413 and stores
   nothing, then writes the upload **before** the candidates, so a candidate never
   points at a missing upload.
5. `parse_resume_ref` reads `resume:<id>` or `resume:<id>#<start>-<end>` and returns
   `None` for anything else, including start > end. `quote(text, start, end)` returns
   exactly `text[start:end]` and the whole line around it, or `None` when the span is
   outside the text. Both are pure.
6. `GET /memories/{id}` gains `source: SourceOut | None` (upload id, filename,
   uploaded_at, and start, end, quote, line when the reference has a span), built by
   `ripple.api.uploads.source_for`. A reference that is not an upload, names another
   user's upload, or falls outside the text resolves to `None`, never to a guess.
7. Uploads are listed with their text in the export and removed by `DELETE /me`
   before the user row (ADR-0044); the cascade on `user_id` is a second guard.

## Alternatives considered
- Store the PDF bytes (database or object storage) and re-extract on demand —
  re-extraction with a different pypdf version can shift offsets, so spans would
  silently point at the wrong characters; it also keeps a file with more personal
  data than the text. Lost.
- Store only each candidate's `span_text` (already on the candidate row) — shows the
  matched characters but not the line around them, and a fact edited later has no
  candidate to read from. The full text is small (a ten-page resume is around 30k
  characters). Lost.
- Put the text on the candidates table, one copy per candidate — the same text many
  times per upload. Lost.
- Object storage (S3-compatible) for the text — one more service and credential for
  a few kilobytes per user (ADR-0029 keeps the pilot on one Postgres). Lost.

## Consequences
- Resume text is personal data held in Postgres and in the nightly `pg_dump` backups
  (ADR-0029), covered by the same consent text and retention.
- Forgetting a resume-derived memory through the forget API (I7) does not delete the
  upload: the text belongs to the upload, not to one memory. Only `DELETE /me`
  removes it. A per-upload delete endpoint does not exist yet.
- The 413 for overlong text is a policy limit, not a measurement: 200,000 characters
  is far above any resume, so hitting it means the PDF is not one.
- Migration 0006 depends on 0005; the drift test for it is slow and unverified on the
  author's machine until a database is available.
- The dashboard client was regenerated with `SourceOut` and `ResumeUpload` (WS-12
  handover).

## Revisit if
Students ask to delete one resume without deleting their account, or uploads become
large or frequent enough that the text should move out of the primary database.
