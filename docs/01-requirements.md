# Requirements

## Functional (FR) — with acceptance criteria
- FR-1 Profile setup: parse an uploaded resume into profile facts; the user confirms each.
  AC: no fact is stored without confirmation (I5).
- FR-2 Openings intake: from pasted JD, forwarded email or Scout; parsed into structured
  requirements (skills, CGPA cutoff, batch, deadline, location) with source spans.
  AC: every parsed field links to the text span it came from.
- FR-3 Application tracking: status per application, resume version sent, follow-ups.
- FR-4 Derived beliefs: eligibility, fit (with cited JD lines), reminders, search criteria,
  each linked to the memories it depends on.
- FR-5 Change detection: detect contradictions and classify them as permanent or temporary.
  A temporary fact is stored with a valid_to (ADR-0015); the nightly sweep retires it at
  expiry and ripples the expiry without an LLM.
  AC: "busy with exams this month" ripples into availability, and after the month ends
  (FakeClock) availability is restored and no permanent fact was changed.
- FR-6 Ripple: traverse wave by wave (I3, ADR-0013); resolve keep / update / retire / ask
  per wave; a keep halts its branch; write one ChangeEvent per ripple (I2).
  AC: on the chain offer → availability → eligibility → recommendation, a keep at
  availability leaves eligibility and recommendation untouched and unresolved; an ask
  at availability leaves eligibility and recommendation SUSPECT (flagged) until the
  user answers.
- FR-7 Ask the user: when confidence is low or sensitivity high; questions are queued and
  answers applied.
- FR-8 Scout: daily schedule and on search-criteria change; allowed sources only (ADR-0008);
  dedupe; rank by eligibility, fit, urgency and variety.
- FR-9 Notifications: daily digest; alert for high-fit openings or deadlines within 48 hours.
- FR-10 Conversation: answers via validity-aware RAG with citations.
- FR-11 Tailor: suggests which real projects to highlight per JD; never invents (I5).
- FR-12 Memory inspector: see each belief, why it is held, its history; edit; forget (I7).
  An edit is a new version created_by user and ripples like any write (ADR-0015).
- FR-13 Map dashboard: openings, skills and applications as one live graph.
- FR-14 MCP server: search, save, update, forget, explain.
- FR-15 Export and delete all user data.
- FR-16 Link verification: the nightly sweep re-checks links whose confidence is below
  a threshold and records verified_at (design decision 2, "link when saving, verify later",
  in the project proposal of 2026-10-19). *Added by the collaborator from the proposal;
  author to confirm.*

## Non-functional (NFR)
- NFR-1 Tests run fully offline (no network, no real LLM).
- NFR-2 Cost and latency per ripple are logged per step. Targets are set after the first
  baselines (Phase 3) and recorded in docs/04-evaluation.md.
- NFR-3 Privacy: data stored privately; export and delete on request; consent for pilot;
  aligned with India's DPDP Act.
- NFR-4 Reliability: LLM provider fallback; a ripple wave is two atomic commits (mark
  SUSPECT, then resolve), so a failure leaves memory at the last commit and the sweep
  resumes the open ChangeEvent; a failed update leaves the old version and its links
  untouched.
- NFR-5 Reproducibility: every eval run records config, seeds, model and prompt versions,
  and git commit.
- NFR-6 Observability: every agent step traced with cost and latency.

## MVP (target: in daily use by 2027-02-01)
FR-1, FR-2 (paste + forward), FR-3, FR-4, FR-5, FR-6, FR-9 (digest), FR-10, FR-12 (basic).
