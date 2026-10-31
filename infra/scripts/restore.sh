#!/bin/sh
# Restore a pg_dump custom-format backup into the running postgres service (ADR-0029).
# Usage, from the repo root on the VPS:
#   docker compose -f infra/docker-compose.prod.yml stop api worker
#   docker compose -f infra/docker-compose.prod.yml run --rm -v "$PWD/backups:/backups:ro" \
#       backup /bin/sh /scripts/restore.sh /backups/ripple-<stamp>.dump
#   docker compose -f infra/docker-compose.prod.yml up -d
# The target database is dropped and recreated: this is a full restore, not a merge.
set -eu

file="${1:?path to a ripple-*.dump file}"
[ -f "$file" ] || { echo "no such file: $file" >&2; exit 1; }
if [ -f "$file.sha256" ]; then
  (cd "$(dirname "$file")" && sha256sum -c "$(basename "$file").sha256")
fi

echo "restoring $file into $PGDATABASE on $PGHOST"
psql -v ON_ERROR_STOP=1 -d postgres -c "DROP DATABASE IF EXISTS ${PGDATABASE}_restore;"
psql -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE ${PGDATABASE}_restore OWNER $PGUSER;"
pg_restore --no-owner --role="$PGUSER" -d "${PGDATABASE}_restore" "$file"
psql -v ON_ERROR_STOP=1 -d postgres <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PGDATABASE}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${PGDATABASE}_previous;
ALTER DATABASE ${PGDATABASE} RENAME TO ${PGDATABASE}_previous;
ALTER DATABASE ${PGDATABASE}_restore RENAME TO ${PGDATABASE};
SQL
echo "restore complete; previous database kept as ${PGDATABASE}_previous until you drop it"
