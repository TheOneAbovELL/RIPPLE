# Incident runbook (ADR-0107)
For the single operator of the pilot. Read the severity table, then the checklist for
the symptom. Commands assume `C="docker compose -f infra/docker-compose.prod.yml"` on
the VPS, in the repository folder.

## Severity
| Level | Meaning (harm to a student) | Examples | Respond |
|---|---|---|---|
| S1 | Wrong information acted on, or data exposed | wrong eligibility shown; another student's data visible; a deletion request not honoured; a secret leaked | same day, contain first |
| S2 | Unavailable or noisy | bot down; digest missing or sent twice; LLM provider down > 1 hour | within a day |
| S3 | Degraded but correct | slow replies; one failed job the next run recovered | next working session |

## First 15 minutes (every incident)
1. Write down the time (UTC) and what was reported, by whom (count, not names, in the
   log below).
2. Pick a severity from the table. When unsure between two, take the higher.
3. Contain without deleting data: stop the job or route that causes harm
   (`$C stop worker`, or take the API down with `$C stop api`). Never `docker volume
   rm`, never `DROP`, never edit rows by hand before a backup exists
   (`$C run --rm backup /bin/sh /scripts/backup.sh once`).
4. S1 and S2: tell the affected students in their own Telegram chat what happened and
   what to ignore. Ripple never contacts anyone else (I6).
5. Diagnose with the symptom checklist below; then fix, verify, write the log entry.

## Bot down (S2)
Symptom: students' messages get no reply; the dashboard may still work.
1. `curl -s https://$RIPPLE_DOMAIN/healthz` and `/readyz`. 503 from `/readyz` names the
   failing check (Postgres or Redis): go to that service's logs (`$C logs --tail=200
   postgres` or `redis`).
2. `$C ps`: is `api` running and healthy? If it restarts in a loop, `$C logs --tail=200
   api`. A missing TELEGRAM_WEBHOOK_SECRET stops the api on purpose (ADR-0078).
3. Webhook state, from the VPS:
   `curl -s https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo`
   (the token stays on the VPS; never paste the output anywhere public). Look at
   `url`, `last_error_message`, `pending_update_count`.
4. Re-register: `$C exec api python -m ripple.notify.inbound.register --url
   https://$RIPPLE_DOMAIN/telegram/webhook`. Certificates: `$C logs caddy`.
5. Verify by sending `/help` from your own linked account.

## Digest sent twice (S2)
Symptom: a student received the same morning digest two times.
1. Check the delivery log for that user and day (no content in it):
   `$C exec postgres psql -U ripple -c "SELECT kind, key, sent_at FROM delivery_log
   WHERE user_id = '<id>' ORDER BY sent_at DESC LIMIT 5"`.
2. One row and two messages: the send succeeded and the record did not, or two workers
   ran (ADR-0095 consequences). `$C ps worker`: more than one worker container is the
   cause; scale back to one (`$C up -d --scale worker=1`).
3. Look for a crash between send and record: `$C logs --since 24h worker | grep
   daily_digest`.
4. Tell the student it was a duplicate. No data change is needed: the log already
   blocks a third send that day.

## Wrong eligibility shown (S1)
Symptom: the bot or dashboard says a student is (not) eligible and that is false.
1. Contain: if more than one student is affected, `$C stop worker` so no digest or
   alert repeats it, and tell the affected students which opening to recheck.
2. On the dashboard (with the student, or through `GET /memories/{id}` with their
   consent): open the eligibility belief, follow its "why" links to the CGPA/batch
   fact and the opening's criteria. Note the memory ids, statuses and the ChangeEvent
   that last touched them.
3. Classify: a wrong fact (the student's CGPA or batch is stale: ask them to correct
   it; the ripple updates the belief), a wrong parse of the JD (the opening's
   structured criteria), a CGPA scale mismatch (ADR-0034), or a rule bug in
   `ripple.domains.jobs.rules` / `beliefs.compute_eligibility`.
4. A rule bug: write the failing test first (CLAUDE.md), fix, deploy, then trigger a
   re-derivation by the student editing or confirming the fact; check the open
   ChangeEvents count afterwards.
5. Record in the incident log and in the week's pilot report notes: an S1 on
   eligibility is exactly the failure Ripple claims to prevent (C2), so it is data.

## Data deletion request (S1 until done)
Symptom: a student asks to delete everything, by message or in person.
1. Preferred: the student uses Account → Delete everything (`DELETE /me`). Confirm the
   time with them.
2. If they cannot (lost token), there is no admin command yet that deletes a user or
   issues a new token for an existing one (open problem in
   docs/plans/parallel-execution/ws-16.md). Note the request date, take a backup, and
   escalate to the author; never delete rows by hand, because only the forget API
   cascades correctly (I7). The request stays S1 until it is done.
3. Verify: `SELECT count(*) FROM memories WHERE user_id = '<id>'` and the same for
   `pilot_feedback`, `resume_uploads`, `delivery_log`, `change_events` are 0;
   `forget_events` rows remain as the deletion audit (ADR-0044).
4. Backups still hold the data until they expire (BACKUP_RETENTION_DAYS, 30). Tell the
   student the expiry date and record it in the runbook's data-request table.

## LLM provider down (S2 after 1 hour)
Symptom: `LLMUnavailableError` in `$C logs api worker`; replies say the agent could not
answer; ChangeEvents stay open.
1. Check the provider's status page and whether ANTHROPIC_API_KEY was revoked or hit a
   spending limit (the provider console).
2. The router falls back to the next configured model (config/llm.default.toml); if
   every model of the provider fails, nothing more can be done in code.
3. Do not restart in a loop. Open ChangeEvents are resumed by the nightly sweep
   (21:00 UTC) once the provider answers; count them:
   `SELECT count(*) FROM change_events WHERE completed_at IS NULL`.
4. Tell students that answers and updates are delayed, not lost. The ripple engine's
   traversal never calls an LLM (I3); what waits is the resolver's decision on each
   affected memory.

## Incident log
| Date (UTC) | Severity | Symptom | Cause | Fix | Students affected |
|---|---|---|---|---|---|
| — | — | none yet | — | — | — |
