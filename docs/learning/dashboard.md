# apps/web — the dashboard (home, write flows, inspector, questions, map)
Written 2026-10-24 for workstream WS-12 (docs/plans/production-plan.md); extended
2026-10-31 by WS-20 (home, Telegram link, resume review, openings, "Say what changed",
the visual system; ADR-0130, ADR-0131).

## 1. What it does
A static web app a student opens with the token the admin gave them. It lands on Home:
open questions, upcoming deadlines, recent ripples and a count of what Ripple knows,
each linking into its area. From the "Tell Ripple" group the student states a change
(free text, or one profile fact picked from what Ripple holds), pastes a job
description, uploads a resume and confirms or rejects each extracted fact, and on
Account links Telegram with a one-time `/link CODE`. Every write shows what the API
did: the change kind and the ripple, wave by wave, with each decision's reason. It shows every
belief Ripple holds about them with its state, why it is held and how it changed; lets
them edit or forget a belief; answers the questions the resolver parked; draws
openings, skills, applications and derived beliefs as one graph; lists ranked
openings; and offers export and delete-everything. It computes nothing about the
beliefs: every state, flag, verdict and reason on screen came from the API as is.

## 2. Why it exists
FR-1 (resume, I5 visible), FR-2 (openings), FR-4/5 (a stated change and its ripple),
FR-12 (inspector), FR-7 (questions), FR-13 (map), FR-15 (export, delete), NFR-3
(privacy: no analytics, no third-party scripts, token kept only for the tab). It is
the pilot student's only window into their memory besides Telegram, and the author's
demo surface for the thesis. ADR-0085 fixes the stack, ADR-0086 the pages and session,
ADR-0087 the map.

## 3. How it works
- **Build and serve.** `next build` with `output: "export"` writes `apps/web/out`:
  one folder per route with an `index.html` plus hashed chunks under `_next/`. The
  deploy step copies `out/` to `infra/web-dist`, which Caddy mounts at `/srv/web` and
  serves at the site root with `try_files {path} {path}/ /index.html`; `/api/*` is
  stripped of its prefix and proxied to the API (infra/Caddyfile, ADR-0029). The app
  therefore calls `/api/...` on its own origin; `NEXT_PUBLIC_RIPPLE_API_BASE` overrides
  that at build time for local work against a bare uvicorn.
- **Client** (`src/api`). `openapi.json` is a committed snapshot of the FastAPI schema,
  produced offline from the test harness. `npm run gen:api` turns it into
  `schema.d.ts`; `types.ts` names the shapes the pages use; `client.ts` is a fetch
  wrapper with one method per endpoint, bearer header, query encoding and `ApiError`.
  `RippleApi` is an interface so tests pass a fake.
- **Session** (`src/auth`). `token.ts` is a tiny store over `sessionStorage` with
  subscribe/notify; `SessionProvider` reads it with `useSyncExternalStore` (server
  snapshot: no token) and exposes `login` (checks `GET /me`, then stores), `logout`,
  `api` and `ready`. `Shell` renders a page only once `ready` and `api` exist, else
  sends the user to `/`. `RequestView` logs out on a 401.
- **Pages** (`src/app` are thin routes; `src/features/*` hold the views so tests render
  them without Next). `useRequest(load, key)` gives every view the same four states;
  `RequestView` renders loading and error, the view decides empty versus data.
- **Status chips** (`src/components/StatusChip.tsx`): one table from `Status` to a
  label and a CSS class, so colour and text always travel together. `Flagged` is the
  API's I1 flag, printed, never computed.
- **Map** (`src/features/map`). `graph.ts` is pure: given `GET /graph` (visible
  memories and the links between them) and the kinds from `GET /vocabulary` it returns
  React Flow nodes (columns by dependency depth, rows by kind then label) and edges
  (one per link, labelled with `link_type`, solid for depends_on, dashed for
  snapshot_of). `MapView` makes those two calls, renders the canvas and the same graph
  as a text list; a failed vocabulary only loses the kind order.
- **Vocabulary** (`src/features/domain/vocabulary.ts`). The kind filter and the map's
  kind labels come from `GET /vocabulary`; nothing in `src/` names a domain's kinds. If
  the request fails the filter is disabled at "Any kind" with a sentence saying why.
- **Frame and navigation** (`src/components/Shell.tsx`, ADR-0130). A sidebar in four
  labelled groups (Today, Tell Ripple, What Ripple knows, You) that becomes a disclosure
  menu under 760 px; every page has a title and a one-sentence lede. Login lands on
  `/home/`.
- **Visual system** (`src/app/globals.css`). Tokens on `:root` (colour, type scale,
  spacing, radius, shadow) redefined under `prefers-color-scheme: dark`; local font
  stacks only (serif headings, system sans, system mono), since the CSP allows no remote
  origin. Lists are ruled ledgers inside one surface; status chips carry a shape and a
  word as well as a colour.
- **The ripple trace** (`src/features/ripple`). `RippleTrace` draws one ChangeEvent:
  a summary ("1 belief updated · 2 kept"), then each wave with its decisions (Updated,
  Kept, Retired, Asked you), the resolver's reason, the question when there is one, and
  a link to the belief (the new version for an update, with "Was:" under it).
  `useMemoryLabels` fetches each named memory with `history=true`, because a decision
  may point at a version that is now RETIRED.
- **Write flows** (ADR-0131). `features/tell` posts `/statements` and shows
  `IntakeResult`; `features/openings` posts `/openings`, lists every field with its JD
  span, and prints the verdict from `GET /recommendations` for that opening id;
  `features/resume` uploads the PDF (multipart, the only non-JSON call), lists pending
  candidates under a "Not saved yet" note (I5) with their source span, and confirms or
  rejects each; `features/account` mints a Telegram code. The fact picker on Tell is
  driven by `GET /vocabulary`: `profile_subject` addresses the student, and
  `profile_attributes` lists what the student may state (`stated_by_user`), each with a
  `value_type` (number, integer, bool as a yes/no select, text) and whether it is
  `permanent` (a non-permanent fact says "Ripple may ask a model whether this is
  temporary"). A 503 from these endpoints renders `ActionError`: when its body lists
  `open_change_event_ids`, the write is stored and the page says "Saved. Ripple couldn't
  finish re-checking because the model is unavailable; it will finish automatically."
  (the nightly sweep resumes those events); otherwise the model message. A 409 with
  `OpeningAlreadyRecordedError` says "You already saved this opening" and links to it.
  `ApiError` keeps the whole JSON body for this (`errorName`, `openChangeEventIds`).
- **Home** (`features/home`). Five blocks, each its own request so one failure hides
  nothing else. Recent ripples come from `GET /events?limit=5&rippled_only=true`,
  whose `memories` label every id the events name; a version the event retired comes
  back RETIRED and is drawn struck through with "(earlier version)" (`MemoryName`).
- **Map layout and fit** (`features/map/graph.ts`, `MapView.tsx`). Nodes go in bands by
  dependency depth. A band taller than the frame wraps into sub-columns, sized so the
  graph is about 1.6 times as wide as it is tall. Within a band a node follows its first
  parent, so an opening's fields sit together beside it. Labels are clamped to two lines
  and edge labels show only on hover or selection. The fit uses React Flow's queued
  `fitView` with `minZoom` 0.2, plus one more fit on the frame after init. The default
  minZoom (0.5) is what once left the canvas empty. An effect on `useNodesInitialized`
  does not work here: with controlled nodes React Flow never sets it.
- **Verdicts** (`components/VerdictChip.tsx`). The API's eligibility with its flag: a
  flagged verdict reads "… · waiting on your answer" in amber, with a link to answer it.
- **Destructive actions.** Forget and delete-everything go through `ConfirmDialog`, a
  native `<dialog>`; delete needs the phrase `delete everything` typed.
- **Pilot feedback** (`src/features/feedback`, ADR-0105). Each recommendation offers
  Saved / Applied / Not interested and each answered question asks "Was this question
  useful?"; both send `POST /feedback`, whose 201 or 200 the client reports as new or
  already recorded, and the recommendations page reads the earlier statements with one
  `GET /feedback` grouped by target (tests: recommendations.test, questions.test).

## 4. Trade-offs
- The fact picker on "Say what changed" offers the facts the student already holds
  (with today's value) first, then the vocabulary's other `stated_by_user` attributes.
  Nothing in `src/` names a profile attribute or the profile subject.
- Deadlines on Home are ordered by date and shown with a relative phrase ("in 3
  days"); the page sets no urgency threshold, which is FR-9's policy in the worker.
- Static export over a Node server: nothing to run on the VPS besides Caddy, at the
  cost of query-string ids for the detail page.
- The map first shipped with N+1 detail calls so FR-13 was usable before a graph
  endpoint existed. Since checkpoint C3 it loads `GET /graph` in one call (same I1
  boundary as the list) and draws every visible memory, laid out by dependency depth,
  so no domain kind decides a column.
- sessionStorage over localStorage: a shared lab machine forgets the token when the
  tab closes; the student pastes it again.
- One global stylesheet instead of a framework: a six-page tool does not need one, and
  the CSP in the Caddyfile stays simple.
- The edit form offers three `valid_to` choices because `EditIn` tells three apart:
  keep (the field is omitted), end at a date and time (an ISO timestamp, read from a
  `datetime-local` input in the browser's zone) and no end (explicit null). Kinds come
  from `GET /vocabulary` rather than a copy of the jobs adapter's list.

## 5. Failure modes and tests
| Failure | Test (apps/web/tests) |
|---|---|
| Token kept in localStorage or a cookie, or stored before it is checked | session.test: stores an accepted token…; keeps a rejected token out of storage |
| A page renders without a session, or logout leaves the token | session.test Shell cases; memories.test logs out when the token is rejected |
| A RETIRED memory shows in the list or the map | memories.test "invariant I1 at the UI"; map.test never draws a RETIRED memory |
| Status shown by colour only | memories.test status chip carries text and a colour class |
| Filtering done on the client | memories.test asks the API for the chosen kind |
| A rule computed client-side | recommendations.test prints the API's eligibility verdict…; no-business-logic.test scans src for rule-shaped code and proves the scan catches samples |
| Edit sends the wrong body or loses the new version id | detail.test saves an edit through the API and follows the new version; the three valid_to tests (omitted, set, explicit null) |
| Kinds hardcoded, or the page fails when the vocabulary does | memories.test offers the kinds GET /vocabulary lists; falls back … when the vocabulary fails; map.test still draws the map when the vocabulary request fails |
| Forget or delete without confirmation | detail.test forgets only after confirmation; account.test requires the exact phrase |
| Answer bodies wrong | questions.test sends still_holds / no_longer_holds / correction |
| Wrong Authorization header, query encoding, error mapping | client.test |
| A page lacks a loading, empty or error state | every *.test has the three |
| A resume fact looks saved before confirmation (I5) | resume.test "says so above the list and marks each pending row as not saved" |
| Confirm or reject hits the wrong endpoint, or the list does not move | resume.test confirms / rejects through the API… |
| A 503 reads as a passing outage | tell.test, openings.test, resume.test "explains a 503 as the missing model" |
| A ripple decision is lost or shown without its reason | tell.test "shows the change and every decision of the ripple with its reason" |
| The opening verdict computed client-side | openings.test prints the ranking entry for that id |
| The Telegram code or instruction is wrong | account.test "Telegram linking" |
| One Home block failing blanks the page | home.test "loads each block on its own" |
| A retired version reads as current | home.test "shows a version the ripple retired as the past" |
| A fact typed wrong for its value type, or a non-stated fact offered | tell.test (bool, integer, text-with-digits, Resume not offered) |
| A stored write reported as lost when the model is down | tell.test "says the fact is saved and the ripple will finish" |
| A duplicate opening shown as an error | openings.test "says the opening is already saved and links to it on a 409" |
| Navigation without groups, current page or phone menu | session.test Shell cases |

Not covered offline: the real Caddy, and the CSP (see the handover: inline scripts
need `script-src 'unsafe-inline'` or hashes).

## 6. Interview questions
1. *Where does the dashboard decide that a memory is suspect?* Nowhere. `status` and
   `flagged` arrive from the API; the chip table only maps a status to a label and a
   colour. The no-business-logic test fails the build if a comparison on fit score,
   CGPA, deadline or status appears in `src/`.
2. *Why sessionStorage and not a cookie?* The API authenticates with a header
   (ADR-0040). A cookie would be sent by the browser on every request to the origin,
   which brings CSRF into a design that has none; sessionStorage is read only by code
   on the page and dies with the tab.
3. *How does the generated client stay honest?* The types come from `openapi.json`,
   which a Python test diffs against the live schema. A backend change that alters a
   response shape fails that test; regenerating makes `tsc` fail wherever the UI used
   the old shape.
4. *Why does the detail route use `?id=`?* The export writes one HTML file per known
   route at build time; memory ids are not known then. Caddy serves the folder index
   and the page reads the query string.
5. *What happens on a 401 mid-session?* `RequestView` sees `ApiError(401)`, calls
   `logout`, the token store notifies, `Shell` sees no client and replaces the route
   with `/`.

## 7. Exercise
Add a line to `RecommendationsView` such as `const late = new Date(item.deadline) <
new Date();` and run `npm test`: the no-business-logic test names the file and the
rule it matched. Remove it. Then change `openapi.json` so `RecommendationOut` renames
`fit_reasons`, run `npm run gen:api` and `npx tsc --noEmit`, and read where the UI breaks.
