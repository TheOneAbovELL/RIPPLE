#!/bin/sh
# Container entrypoint: run the requested process.
# Production migrates only in the one-shot `migrate` service, so api and worker never
# race on a fresh database and an older image never tries to "upgrade" a newer schema
# (ADR-0029). The development compose sets RIPPLE_MIGRATE_ON_START=1 on the api only.
set -eu

migrate_if_asked() {
  if [ "${RIPPLE_MIGRATE_ON_START:-0}" = "1" ]; then
    alembic upgrade head
  fi
}

case "${1:-api}" in
  api)
    migrate_if_asked
    exec uvicorn ripple.api.app:create_production_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  worker)
    exec arq ripple.worker.settings.WorkerSettings
    ;;
  mcp)
    # Streamable HTTP behind Caddy's /mcp route (ADR-0082).
    exec python -m ripple.mcp_server --transport http --host 0.0.0.0 --port "${RIPPLE_MCP_PORT:-8765}"
    ;;
  migrate)
    if ! alembic upgrade head; then
      echo "migrate: alembic upgrade head failed. If the database is at a revision this" >&2
      echo "image does not know, it was migrated by a newer release: roll back by running" >&2
      echo "'alembic downgrade <revision>' with the NEWER image first (docs/ops/deploy.md)." >&2
      exit 1
    fi
    ;;
  *)
    exec "$@"
    ;;
esac
