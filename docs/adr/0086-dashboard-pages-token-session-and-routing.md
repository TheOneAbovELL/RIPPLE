# ADR-0086: Dashboard pages, token session in sessionStorage, query-string routing
Status: Accepted under the autonomous mandate · Date: 2026-10-24 (WS-12)

## Context
FR-12 (inspector: see, why, history, edit, forget), FR-7 (questions), FR-13 (map),
FR-15 (export, delete). ADR-0040 authenticates with bearer tokens minted by the admin
CLI; ADR-0042 fixes inspector semantics (I1 at the boundary, history on request, edits
go straight to versioning); ADR-0044 fixes export and delete. The dashboard needs a
page set, a way to hold the token in the browser, and routing that survives a static
export.

## Decision
**Pages** (apps/web/src/app):
| Route | Shows | Calls |
|---|---|---|
| `/` | token login | `GET /me` to check the token |
| `/memories/` | list with status chip (colour + text), kind and status filters, flagged toggle | `GET /memories?kind&status&flagged` |
| `/memories/detail/?id=` | content, structured fact, why (parents), history (versions, ChangeEvents with decisions, reasons, questions), edit, forget with confirmation | `GET /memories/{id}?history=true`, `POST …/edit`, `POST …/forget` |
| `/questions/` | parked questions with still holds / no longer holds / correction (content, valid_to) | `GET /questions`, `POST /questions/{id}/answer` |
| `/map/` | React Flow graph of openings, skills, applications and derived beliefs (ADR-0087) | `GET /memories`, `GET /memories/{id}` per node |
| `/recommendations/` | ranked openings with eligibility, fit, reasons, deadline, flag | `GET /recommendations?limit=50` |
| `/account/` | profile, export download, delete everything with a typed phrase | `GET /me`, `GET /me/export`, `DELETE /me` |

**Token session.** The token is kept in `sessionStorage` under one key and nowhere
else: never `localStorage` (would outlive the tab on a shared lab machine), never a
cookie (the API reads the `Authorization` header only, and a cookie would ride along
on every request, including ones the user did not make). It is validated against
`GET /me` before being stored; logout removes it; a 401 from any call, read or
write, removes it (the client is wrapped once in the session provider) and the user
is returned to the login page. The token is read through `useSyncExternalStore`, so the
pre-rendered HTML has no token and the first client render after hydration does.

**Routing.** A static export cannot pre-render one page per memory, so the detail page
takes `?id=`; links use `/memories/detail?id=<id>` and Next adds the trailing slash the
export needs. Caddy's `try_files {path} {path}/ /index.html` serves the folder index for
both spellings.

**Filters are server-side.** Kind, status and flagged are query parameters of
`GET /memories`; the page shows what the API returned. The status filter offers only
VALID, SUSPECT and PENDING_USER, because the endpoint rejects RETIRED (ADR-0042).

**I1 at the UI.** One predicate (`src/lib/visibility.ts`) is applied by the list, the
map and the "why" parents section: a RETIRED row is dropped even if one arrives. The
history section of the detail page is the one place a retired version is listed,
labelled "Retired" with a strikethrough chip; following such a version opens it
read-only (no edit, no forget) with a notice.

**Edit.** The form edits `content`; `valid_to` is shown read-only because `EditIn` has
no such field (a contract request in the handover). A PENDING_USER memory has edit
disabled with a link to the questions page, mirroring the API's 409.

**Destructive actions.** Forget uses a native `<dialog>` with an explicit confirm; delete
everything requires typing `delete everything`. Export is offered on the same page,
above the delete section, as ADR-0044 asks.

## Alternatives considered
- Token in `localStorage` "so students stay logged in": convenience against leaving a
  live token on a shared machine. Lost; the token is short to paste.
- HttpOnly cookie set by the API: safest against script access but needs CSRF defence
  and a cookie-aware API; ADR-0040 chose headers. Lost for now; revisit with real
  session management.
- `/memories/[id]` dynamic route with `generateStaticParams`: impossible for unknown
  ids in a static export. Lost.
- Client-side filtering of a full list: duplicates the API's I1 filter in a second
  place. Lost.

## Consequences
- Closing the tab logs the user out; the login page says so.
- Deep links to a memory carry the id in the query string and are not pretty.
- Every page can show four states (loading, empty, error, data) and each has a test.

## Revisit if
The pilot needs persistent sessions, or the API moves to cookie sessions.
