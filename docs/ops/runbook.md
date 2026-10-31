# Operations runbook
For the single operator of the pilot. Every entry: symptom → check → action. Incidents,
severities and first-15-minutes checklists: docs/ops/incident.md (ADR-0107). Commands
assume `C="docker compose -f infra/docker-compose.prod.yml"` on the VPS.

## Health
- `GET /healthz` 200: the API process is up. `GET /readyz` 200: Postgres and Redis
  answer; a 503 body names the failing check. Caddy's access log is JSON in the
  `caddy-data` volume.
- Traces: Langfuse (ADR-0028) when LANGFUSE_* are set; otherwise structured JSON logs
  from `$C logs api worker` with `trace_id` on every line of a request.

## Monitoring checklist
Daily, about five minutes, after the 02:30 UTC digest run (08:00 IST):
- [ ] `curl -s -o /dev/null -w "%{http_code}" https://$RIPPLE_DOMAIN/readyz` is 200.
- [ ] `$C ps`: api, worker, mcp, caddy, postgres, redis, backup are `running`
      (`migrate` exited 0); no container restarting.
- [ ] Worker jobs ran: `$C logs --since 24h worker | grep -E
      "daily_digest|hourly_alerts|nightly_sweep|scout_run"` shows each cron job's last
      run without a traceback; the digest job's result counts look like yesterday's.
- [ ] Delivery log moved: `SELECT count(*) FROM delivery_log WHERE kind = 'digest' AND
      sent_at >= current_date` equals the number of students with a linked chat.
- [ ] Open ChangeEvents are not piling up: `SELECT count(*) FROM change_events WHERE
      completed_at IS NULL` is near zero after the 21:00 UTC sweep.
- [ ] Langfuse (if configured): yesterday's traces exist; no spike of failed
      generations; cost per day in line with config/llm.default.toml prices.
- [ ] Backup freshness: `$C exec backup ls -lt /backups | head -3` shows a
      `ripple-<UTC stamp>.dump` from the last 26 hours; `$C logs --since 26h backup`
      has no "backup failed".
- [ ] Disk: `df -h /` below 80%; `docker system df` not growing day over day.
Weekly (Monday):
- [ ] Pilot report for the week that ended (ADR-0106): `$C exec api python -m
      ripple.pilot.report --week <YYYY-Www> --results-dir /tmp/pilot --code-version
      "$RIPPLE_IMAGE"` (the image's /app is not writable by the `ripple` user and
      has no .git, so the image tag names the code), then
      `docker cp "$($C ps -q api)":/tmp/pilot/. results/pilot/`. The command prints
      the folder it wrote: `<YYYY-Www>/` when at least five students were active
      (commit it from the author's machine), `raw/<YYYY-Www>/` otherwise (gitignored,
      never published). Read report.md; note S1 incidents of the week.
- [ ] Any deletion requests whose backup expiry date has passed: mark them done below.
Monthly:
- [ ] Restore drill (docs/ops/deploy.md, infra/scripts/restore.sh) into a scratch
      database; record it below.

## Symptoms
| Symptom | Check | Action |
|---|---|---|
| Digest not received | `$C logs worker` for `daily_digest`; delivery_log row for the user and day | If the row exists the message was sent; otherwise run the job by hand per docs/learning/worker-and-notify.md |
| Telegram replies stop | `/readyz`; `getWebhookInfo` (docs/ops/incident.md, "Bot down") | Re-register the webhook; check TELEGRAM_WEBHOOK_SECRET matches |
| LLM errors (LLMUnavailableError in logs) | Provider status; ANTHROPIC_API_KEY validity | Router falls back to the next configured model; fix the key; ripples resume via the nightly sweep |
| Open ChangeEvents piling up | `SELECT count(*) FROM change_events WHERE completed_at IS NULL` | The sweep resumes events older than 1 hour; run the sweep job manually if urgent |
| Feedback buttons do nothing | `$C logs api` for `POST /feedback` 4xx | 404: the target belongs to another user or was forgotten; 422: wrong kind for the target (ADR-0105) |
| Disk filling | `docker system df`; `backups` volume size | Lower BACKUP_RETENTION_DAYS; prune old images |
| Certificate problems | Caddy logs | Confirm DNS and ports 80/443; Caddy retries automatically |

## Data requests (DPDP, FR-15)
- Export: the student uses the dashboard Account page or `GET /me/export`.
- Delete: `DELETE /me` removes memories, links, candidates, uploads, delivery records,
  pilot feedback (in Postgres the forget and user cascades remove it; ADR-0105) and
  the user's ChangeEvents; ForgetEvents (ids only) remain as the deletion audit. Backups
  containing the data expire with retention; record the request so the operator can
  confirm expiry. Checklist: docs/ops/incident.md, "Data deletion request".

| Request date | Kind | Done on | Backups expire on |
|---|---|---|---|
| — | — | — | — |

## Rollback and restore
See docs/ops/deploy.md. Restore drills: record each drill here with date and outcome.

| Date | Drill | Outcome |
|---|---|---|
| TBD | first restore drill before the pilot | |

## Key rotation
Edit `.env`, `$C up -d`. For API tokens: `python -m ripple.api.admin create-user`
issues a new token for a new user; revoking a token or issuing one for an existing
user needs an admin command that does not exist yet (`revoke-token`, `issue-token`).
