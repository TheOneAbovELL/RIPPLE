#!/bin/sh
# Nightly pg_dump (custom format) with retention, optional S3 copy (ADR-0029).
# Runs as the `backup` service: sleeps until 02:00 UTC, dumps, prunes, repeats.
set -eu

BACKUP_DIR=/backups
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

dump_once() {
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  file="$BACKUP_DIR/ripple-$stamp.dump"
  pg_dump --format=custom --compress=6 --file="$file.tmp" && mv "$file.tmp" "$file"
  sha256sum "$file" > "$file.sha256"
  echo "backup written $file"
  if [ -n "${BACKUP_S3_URL:-}" ]; then
    # aws cli is not in this image; the deploy runbook installs it or swaps the image.
    if command -v aws >/dev/null 2>&1; then
      aws s3 cp "$file" "$BACKUP_S3_URL/" --sse AES256 && aws s3 cp "$file.sha256" "$BACKUP_S3_URL/"
    else
      echo "BACKUP_S3_URL set but aws cli missing; local copy only" >&2
    fi
  fi
  find "$BACKUP_DIR" -name 'ripple-*.dump*' -mtime +"$RETENTION_DAYS" -delete
}

if [ "${1:-}" = "once" ]; then
  dump_once
  exit 0
fi

while true; do
  now=$(date -u +%s)
  target=$(date -u -d "tomorrow 02:00" +%s 2>/dev/null || echo $((now + 86400)))
  sleep $((target - now))
  dump_once || echo "backup failed at $(date -u)" >&2
done
