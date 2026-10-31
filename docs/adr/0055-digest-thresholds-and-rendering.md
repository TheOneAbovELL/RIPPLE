# ADR-0055: Digest and alert policy: thresholds, rendering, what never alerts
Status: Accepted under the autonomous mandate · Date: 2026-10-19 (WS-6)

## Context
FR-9 asks for a daily digest and alerts "for high-fit openings or deadlines within 48
hours" but fixes no fit threshold, no message shape and no rule for openings the system
itself doubts. ADR-0025 chose plain Telegram messages. The digest consumes rankings only
through `RecommendationSource` (contract C1), which hands it `Recommendation` values
with a `fit_score` in 0..1, `fit_reasons` that cite JD lines or profile facts, an
optional `deadline` and a `flagged` bit (built on a SUSPECT or PENDING_USER memory, I1).

## Decision
1. **Thresholds** live in one dataclass (`ripple.notify.contracts.Thresholds`), injected,
   with these defaults: `fit_alert = 0.8`; `deadline_window = 48 h` (FR-9's number);
   `alert_cooldown = 7 days`; `digest_limit = 10` items; `alert_scan_limit = 50`
   ranked items scanned for alerts, deeper than the digest because a low-fit opening
   with a deadline tomorrow sits far down a fit-ordered ranking and is exactly what
   FR-9 must not miss. They are policy, not measurements; the pilot may tune them and
   the ADR is amended with the evidence.
2. **Rendering** is plain text, transport-agnostic (`ripple.notify.render`). Per item:
   rank number, title at company, eligible yes/no, fit as a floored percent of the
   source's score, every fit reason verbatim, deadline with whole hours left floored (never
   rounded up), "not stated" when no deadline is known, "(passed)" when it is behind us.
   A flagged item carries the suffix `[unconfirmed]`. The renderer never computes a
   number the source did not give it except hours left, which is deadline minus the
   injected clock. The fit percent is rounded to six decimals before flooring so
   binary noise (0.57 × 100 = 56.999…) cannot show a lower percent than the source
   gave. A digest longer than Telegram's 4096 characters drops trailing items whole
   and ends with "N more not shown (message limit)."; the omitted openings are
   counted, never summarised.
3. **What alerts**: an eligible, unflagged opening whose fit is at or above `fit_alert`
   (`HIGH_FIT`) or whose deadline is in `(now, now + deadline_window]`
   (`DEADLINE_SOON`). Flagged or ineligible openings never alert; they appear in the
   digest only. Each (user, opening, kind) alerts at most once per cooldown; the hourly
   job passes `since = now - alert_cooldown` and the service re-alerts only when the last
   alert for that pair is older than `since`. Only the kinds that are due appear in the
   message and are recorded, so a second kind for an already-alerted opening goes out
   alone and does not restart the first kind's cooldown.
4. **Empty digest**: when nothing ranks, no message is sent and the day is not
   recorded, so a later run the same day can still deliver if openings appear.

## Alternatives considered
- Alert on flagged items with a warning — pushes the user to act on a belief the
  system doubts, the exact failure FR-9's consistency story must avoid. Lost.
- Alert once ever per opening (no cooldown) — simpler, but a long-running opening
  that stays high-fit for weeks would never resurface. The cooldown keeps `since`
  meaningful and the once-ever behaviour is one configuration (`alert_cooldown` very
  large). Lost on flexibility.
- Rich formatting (MarkdownV2 / HTML parse_mode) — Telegram escaping rules bite on
  company names with `_` or `*`; plain text cannot fail to render. Lost for now.
- Send a "nothing today" digest — daily noise with no action in it; students mute
  noisy bots. Lost.

## Consequences
- Fit and deadline thresholds are visible in one place and testable with FakeClock.
- The renderer is reusable for an email transport later (ADR-0025).
- A ranking source that puts rounded or invented numbers into `fit_reasons` is not
  caught here; I5 is enforced where the reasons are produced (WS-1).

## Revisit if
The pilot's alert volume is above roughly one per user per day, or users report missing
a deadline that the 48 h window did not catch; then the thresholds move with data.
