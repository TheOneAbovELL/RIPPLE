# ADR-0107: Three incident severities and a daily monitoring check for a one-operator pilot
Status: Accepted under the autonomous mandate · Date: 2026-10-31

## Context
The pilot (C3) runs on one VPS (ADR-0029) with one operator, the author, who is also a
full-time student. There is no pager, no on-call rota and no alerting service; Langfuse
(ADR-0018, ADR-0028) and JSON logs are the only telemetry. Students trust the bot with
placement decisions, so the failures that matter most are wrong eligibility and
unwanted data, not downtime. Wave B asks for an incident runbook and a monitoring
checklist (docs/plans/wave-b.md, WS-16).

## Decision
1. Three severities, defined by harm to a student rather than by component:
   - **S1** — wrong or harmful information acted on, or data exposed: wrong
     eligibility shown, another student's data visible, a deletion request not
     honoured, a secret leaked. Respond the same day; pause the affected path first.
   - **S2** — the product is unavailable or noisy: bot down, digests missing or sent
     twice, LLM provider down for more than an hour. Respond within one day.
   - **S3** — degraded but correct: slow replies, one failed job that the next run
     recovers, a cosmetic dashboard fault. Next working session.
2. Every incident starts with the same first 15 minutes: note the time, assess
   severity, contain (pause the job or route, never delete data to contain), tell the
   affected students in their own chat for S1 and S2, then diagnose. The per-symptom
   checklists live in docs/ops/incident.md.
3. Monitoring is a manual daily check (about five minutes, after the 02:30 UTC digest
   run) plus a weekly one (pilot report, backup restore drill monthly), listed in
   docs/ops/runbook.md. No automated alerting service is added.
4. Each S1 or S2 gets a short entry in the incident log table in docs/ops/incident.md
   (date, severity, symptom, cause, fix, students affected as a count, never names),
   and an S1 also gets a line in the weekly pilot report's notes.

## Alternatives considered
- An uptime monitor or alerting SaaS (UptimeRobot, Grafana Cloud) — a new external
  service and account (an ADR and the author's sign-up), and it would page a student
  during exams for an S3. Deferred: listed as an author decision in the handover.
- Severity by component (API, worker, LLM) — easy to classify, but it ranks "bot
  down" above "wrong eligibility", which is backwards for this product. Lost.
- Four or five levels as in industry runbooks — with one operator, the only real
  choices are "now", "today", "this week". Lost.

## Consequences
- Detection depends on the operator's daily check and on students reporting; an
  outage at night may last until morning. Accepted for a pilot of 30–50 students.
- Containing an S1 may mean pausing the worker (`docker compose stop worker`), which
  stops digests for everyone; the checklist says to tell students.
- No new code or dependency.

## Revisit if
The pilot grows beyond one department, a second operator joins, or an S2 goes
unnoticed for more than a day.
