# ADR-0130: Dashboard information architecture and visual system
Status: Accepted under the autonomous mandate · Date: 2026-10-31 · workstream: WS-20

## Context
The dashboard (ADR-0085, ADR-0086) grew page by page as an inspector: a top bar of five
links, white boxes on grey, and a login that lands on the raw memory list. A student
opening it for the first time saw database rows, not "what does Ripple think about me
and what does it need from me". The author asked on 2026-10-31 for a professional,
calm, distinctive UI that a student understands without a manual. Constraints that do
not move: static export, the Caddy CSP (`script-src 'self' 'unsafe-inline'`, no
third-party origin, so no remote fonts or CDNs), no new dependency, no business logic
in the frontend (.claude/rules/frontend.md), state shown by colour AND text.

## Decision
1. **Home first.** Login lands on `/home/`, an overview that answers three questions
   in order: what needs you (parked questions, upcoming deadlines), what changed
   (recent ripples), what Ripple knows (counts of visible and flagged beliefs). Each
   block loads on its own and links into its area.
2. **Navigation by intent, not by table.** A sidebar on wide screens, a disclosure menu
   under 760 px, in three labelled groups: *Today* (Home, Questions, Recommendations),
   *Tell Ripple* (Say what changed, Add an opening, Resume), *What Ripple knows*
   (Beliefs, Map), then Account. Page titles say what the page is for, each with a
   one-sentence lede.
3. **Visual system in one stylesheet, as tokens.** Colour, type scale, spacing, radius
   and elevation are CSS custom properties on `:root`, redefined for
   `prefers-color-scheme: dark`. Typography uses locally installed faces only: a
   humanist serif stack for headings (Iowan Old Style, Palatino, Georgia), the system
   sans for text, the system monospace for codes. A deep teal accent and an ink-on-
   paper neutral; status hues (valid, suspect, awaiting, retired) each carry a label.
4. **Rows, not floating cards.** Lists render as ruled ledgers inside one surface;
   ripples render as a wave trace (wave 1, wave 2 … with an action word per decision:
   Updated, Kept, Retired, Asked you). The brand mark is three concentric arcs drawn in
   inline SVG, which is the product's idea and needs no asset.
5. **States are designed, not defaulted.** Every request has loading (with
   `role=status`), error (with `role=alert` and Try again) and empty (with the next
   step) states; a 503 from an LLM-backed endpoint gets a dedicated message that says
   the feature needs a model key and nothing was stored (ADR-0131).
6. **Accessibility.** Skip link, landmarks, `aria-current` on navigation, visible
   focus ring from a token, 44 px touch targets on phones, reduced-motion respected,
   contrast checked for text tokens in both schemes (WCAG AA for body text).

## Alternatives considered
- A CSS framework (Tailwind, a component kit): a build step and a dependency for a
  dozen pages, and the generic look the author asked to avoid.
- Web fonts bundled into the export: allowed by the CSP (same origin) but adds
  licensing and weight for little gain; the serif stack gives the same editorial
  character on Windows, macOS and Android.
- Keeping the top bar and adding links: eleven links in one bar wrap badly on phones
  and do not tell the student where to start.

## Consequences
- Existing class names stay (tests and views keep working); their look changes.
- The overview needs recent ChangeEvents. No list endpoint exists, so it reads them
  from `GET /me/export` (ADR-0131 point 5) until `GET /events` exists.
- Visual quality is checked by building and opening the export; there is no visual
  regression test.

## Revisit if
The dashboard grows past ~20 pages, or a design system is adopted for the thesis demo.
