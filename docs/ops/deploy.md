# Deploying Ripple (ADR-0029)
One VPS, Docker Compose, Caddy TLS, images from GitHub Container Registry.

## Prerequisites (once)
- A VPS with Docker Engine and Compose v2, ports 80 and 443 open, 2 vCPU / 4 GB is
  enough for the pilot.
- A domain (RIPPLE_DOMAIN) pointing at the VPS; Caddy obtains the certificate.
- A GHCR read token for `docker login ghcr.io` on the VPS.
- Telegram bot token (from @BotFather), ANTHROPIC_API_KEY, Langfuse keys (optional).

## First deploy
1. `git clone` the repository on the VPS (for infra/ files only; the app runs from images).
2. `cp .env.example .env` and fill every value. Generate secrets with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"` for POSTGRES_PASSWORD
   and TELEGRAM_WEBHOOK_SECRET.
3. Build or copy the dashboard export into `infra/web-dist/` (CI publishes `web-dist.tar.gz`
   as a release asset; `tar -xzf` it there).
4. `export RIPPLE_IMAGE=ghcr.io/<owner>/ripple:<tag>` then
   `docker compose -f infra/docker-compose.prod.yml up -d`.
   `migrate` runs Alembic to head and exits; `api`, `worker` and `mcp` start after it.
   The api service hosts the Telegram webhook when TELEGRAM_BOT_TOKEN is set (ADR-0078)
   and refuses to start if TELEGRAM_WEBHOOK_SECRET is missing. It runs with
   RIPPLE_TRUST_PROXY=true so rate limits are per client, not per Caddy (ADR-0098).
5. Create the first user and token: `docker compose -f infra/docker-compose.prod.yml exec api
   python -m ripple.api.admin create-user "<name>"`. The token is printed once.
6. Register the Telegram webhook: `docker compose ... exec api python -m
   ripple.notify.inbound.register --url https://$RIPPLE_DOMAIN/telegram/webhook`.
7. Check `https://$RIPPLE_DOMAIN/readyz` returns 200 and the dashboard loads.
8. MCP clients connect to `https://$RIPPLE_DOMAIN/mcp` with the same bearer token the
   dashboard uses (ADR-0081, ADR-0082).

## Upgrade
`export RIPPLE_IMAGE=ghcr.io/<owner>/ripple:<new-tag>` → `docker compose ... pull` →
`docker compose ... up -d`. Migrations run first; the API restarts after them.

## Rollback
If the release added a migration, downgrade first **with the new image still set**
(only it knows the newer revision): `docker compose -f infra/docker-compose.prod.yml
run --rm migrate alembic downgrade <previous revision>`; release notes name the
revision. Then set RIPPLE_IMAGE back to the previous tag and `up -d`. Skipping the
downgrade makes the old image's `migrate` fail with a message pointing here, and the
api waits on it. Only `migrate` migrates in production; api and worker never do.

## Backups
The `backup` service dumps nightly at 02:00 UTC into the `backups` volume (30-day
retention) and, when BACKUP_S3_URL and AWS credentials are set, to object storage with
server-side encryption. Run a dump now: `docker compose ... run --rm backup /bin/sh
/scripts/backup.sh once`. Restore: infra/scripts/restore.sh header. Test a restore before
the pilot starts and record the date in docs/ops/runbook.md.

## Secrets
Only in `.env` on the VPS, file mode 600, never in images or the repository. Rotating
the Telegram token or the API key is a `.env` edit plus `up -d`.
