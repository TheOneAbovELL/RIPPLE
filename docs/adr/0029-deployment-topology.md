# ADR-0029: Deployment topology: one VPS, Compose, Caddy TLS, GHCR images, pg_dump backups
Status: Accepted · Date: 2026-10-24 (under the autonomous mandate)

## Context
docs/02 says "Docker Compose, one VPS for the pilot" (ADR-0004, ADR-0017). Nothing
decided TLS, image distribution, migrations in deployment, backups or restore. The
production plan needs these fixed once so the pilot (30–50 students, Aug–Oct 2027)
runs on infrastructure a single developer can operate.

## Decision
- **Images**: CI builds one image (infra/Dockerfile) and publishes it to GitHub
  Container Registry tagged with the git sha and, on a release tag, the version.
  The VPS pulls by tag; no builds on the server.
- **Compose on the VPS**: infra/docker-compose.prod.yml runs postgres (pgvector),
  redis, a one-shot `migrate` job, `api`, `worker`, `bot` (the Telegram webhook is a
  route on the API; the long-poll worker is development only), `web` (static dashboard
  export) and **Caddy** as the only public listener: automatic TLS, reverse proxy to the
  API and the dashboard, security headers, request size limits.
- **Secrets**: a single `.env` on the VPS, never in the image or the repository;
  `.env.example` documents every variable. Postgres and Redis are not exposed publicly.
- **Backups**: nightly `pg_dump` (custom format) from a sidecar container to a local
  volume and, when configured, to S3-compatible object storage with 30-day retention;
  `infra/scripts/restore.sh` restores into an empty database; the runbook tests a
  restore before the pilot starts.
- **Operations**: docs/ops/deploy.md (first deploy and upgrades), docs/ops/runbook.md
  (incidents, rollback = previous image tag + migration downgrade if needed, key
  rotation), health endpoints (/healthz liveness, /readyz checks Postgres and Redis).

## Alternatives considered
- Kubernetes or a managed PaaS — more moving parts or monthly cost for a student
  pilot on one box. Lost.
- Nginx + certbot — works, but Caddy's automatic TLS removes a cron and a renewal
  failure mode. Lost on operations.
- Building images on the VPS — ties deploys to the server's Docker cache and skips
  CI. Lost.
- Managed Postgres — simpler backups, but the pilot's data residency (DPDP, NFR-3)
  and cost favour a local database with tested backups. Revisit for scale.

## Consequences
- The author needs a VPS, a domain and a GHCR token when deploying for real; the
  compose file and runbook are written and tested in CI (compose config validation) now.
- Backups contain personal data: encrypted at rest in object storage, retention
  documented in the consent text.

## Revisit if
Pilot load exceeds one VPS, or the department requires hosting elsewhere.
