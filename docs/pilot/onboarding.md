# Pilot onboarding checklist
Draft for departmental review, revised 2026-10-31. Per student, about 15 minutes.
The author runs steps 1 to 4; the student does 5 to 9.

Before the first student: the deploy checklist (docs/ops/deploy.md) is done, `/readyz`
is 200, a restore drill is recorded in docs/ops/runbook.md, and the consent form has
the department's approval (docs/pilot/consent.md is a draft until then).

1. Explain the project in two minutes; the student reads the consent form, asks
   questions, signs. File the signed copy; record only the date in the pilot sheet.
2. Give the student an anonymous pilot code (P01, P02, …) for the weekly survey. The
   code-to-name list stays on paper with the consent forms, not in the database.
3. `python -m ripple.api.admin create-user "<name>"` → token, shown once, handed over
   in person (never by email or chat).
4. The student installs nothing: dashboard URL + token, Telegram bot handle.
5. Dashboard login → Account → `/me/telegram/link` code → send `/link <code>` to the
   bot.
6. Upload resume → confirm or reject each extracted fact (nothing is stored before
   confirmation).
7. Paste or forward one JD → see eligibility, fit reasons and the reminder appear;
   check the first digest the next morning.
8. Tell the bot one change ("my CGPA is now 7.9") and watch the Memories page update;
   answer any question the agent asks.
9. Show the feedback buttons: "Saved", "Applied", "Not interested" on recommendations
   and "Useful" / "Not useful" under a question. Say plainly: pressing "Applied" only
   tells Ripple; it applies nowhere.

Record per student in the pilot sheet (code, not name): date onboarded, facts
confirmed/rejected counts, first digest received (yes/no), first question asked
(yes/no). Weekly: the survey (docs/pilot/metrics.md) and the pilot report
(`python -m ripple.pilot.report`, docs/ops/runbook.md).

Leaving the pilot: the student uses Account → Delete everything, or asks the author
(docs/ops/incident.md, "Data deletion request"); record the date and the backup expiry.
