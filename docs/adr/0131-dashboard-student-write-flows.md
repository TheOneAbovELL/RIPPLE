# ADR-0131: Student write flows in the dashboard (Telegram link, resume, openings, statements)
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · workstream: WS-20

## Context
FR-1 (resume), FR-2 (openings), FR-4/5 (a changed fact ripples) and the Telegram link
(ADR-0025) existed in the API and over Telegram, but the dashboard could only read and
edit. A student without Telegram could not tell Ripple anything new. The endpoints are
`POST /me/telegram/link`, `POST /resume`, `GET /resume/candidates`,
`POST /resume/candidates/{id}/confirm|reject`, `POST /openings`, `POST /statements`.
Several of them call a model (resume and JD parsing, change detection and linking), so
without `ANTHROPIC_API_KEY` they answer 503.

## Decision
1. **Client.** One method per endpoint in `src/api/client.ts`, shapes from the
   generated schema; the resume upload is the only multipart call (the browser sets the
   boundary, so the client sets no Content-Type for it).
2. **Telegram link** (Account). A button mints a code; the page shows the code in
   large monospace, its expiry, and the exact instruction `/link CODE` with a copy
   button. Linked accounts see "Linked" and no button.
3. **Resume** (I5 made visible). Upload a PDF, then review each candidate with its
   source span quoted. Pending candidates sit under "Not saved yet: nothing from your
   resume is stored as a belief until you confirm it"; confirm writes through Intake
   and shows the resulting ripple; reject keeps the row as declined. Earlier decisions
   are listed below with their outcome.
4. **Openings.** Paste or drop a text file of a JD. The result shows the summary, each
   recorded field with the JD span it came from, and the derived verdict, read from
   `GET /recommendations` (eligible, fit, reasons) for that opening id, plus links to
   the opening's beliefs. The page computes no verdict.
5. **Say what changed** (`/tell/`). A statement box (free text) with an optional
   "this changes one profile fact" section, which sends a structured fact so detection,
   linking and the rules need no model (ADR-0116). The choices are the profile facts
   the student already holds (with today's value and type), then the other profile
   facts the vocabulary lists. `GET /vocabulary` mixes profile and opening attributes
   and does not publish the profile subject, so `PROFILE_SUBJECT` and `PROFILE_FACTS`
   (attribute: number or text) are a named stopgap in `features/domain/vocabulary.ts`
   until the API publishes them (WS-20 handover, request 1). The result shows the
   change kind and the ripple: each decision of the returned ChangeEvent grouped by
   wave, with the action word and the resolver's reason and a link to the belief.
6. **Recent ripples on Home** come from `GET /me/export` (`change_events` that decided
   something, newest first by parsed time, five shown), the only read that lists events
   today. It is a stopgap: the export carries all history, the resume text and feedback
   to label five events. `GET /events?limit=` is requested in the WS-20 handover.
7. **503 from a model-backed endpoint** renders `ActionError` (`src/components`): "Ripple needs its
   language model … (locally: ANTHROPIC_API_KEY is not set)", plus
   what still works. For a structured statement it adds that the fact may already be
   saved, because Intake writes the version before the ripple, whose fallback resolver
   may need the model (see consequences).

## Alternatives considered
- A wizard for resume review: more clicks for a list of five to fifteen facts; a
  single review list with per-row decisions is faster and shows I5 at a glance.
- Polling the ripple after a statement: the API returns the completed event in the
  same response (the runner runs inline), so there is nothing to poll.
- Reconstructing ripples from memory version chains on Home: N+1 detail calls and
  client-side reconstruction of what the API already records in ChangeEvents.

## Consequences
- Found while building, fixed meanwhile by ADR-0116 for linking and detection: a
  structured statement no longer calls the model. It still can when a jobs rule
  declines during the ripple: the version is written, the LLM fallback raises, the API
  answers 503 and the event stays open until the sweep. The UI says the fact may be
  saved; the handover asks whether the API should answer 201 with an open event instead.
- The no-business-logic scan covers the new files; the opening verdict is a lookup by
  id in the API's ranking, not a computation.

## Revisit if
`GET /events` lands (switch Home to it), or the API starts returning the opening's
derived beliefs in `OpeningOut` (drop the recommendations lookup).
