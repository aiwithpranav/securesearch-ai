#!/usr/bin/env bash
# Restores a backup made by scripts/backup.sh (Phase 9B, FR-38, NFR-16). THIS REPLACES the current database and adds the files.
#   bash scripts/restore.sh backups/20261024-101500 --yes
# Steps: check the backup is whole, stop the app, rebuild the database from the dump, bring the schema up to date, put the files
# back, start everything, and compare the counts with the manifest. Run it on a stack that is up (docker compose up -d) and has a
# .env (new secrets are fine: sign-in passwords live in the database, only open sessions end).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

dir="${1:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then echo "Usage: bash scripts/restore.sh <backup folder> --yes"; exit 2; fi
if [ "${2:-}" != "--yes" ]; then
  echo "This REPLACES the current database with the backup in $dir."
  echo "Add --yes to continue."
  exit 3
fi

echo "1/6 Checking the backup is whole ..."
(cd "$dir" && sha256sum -c SHA256SUMS > /dev/null) || { echo "The backup is damaged or incomplete (checksums do not match). Nothing was changed."; exit 1; }

echo "2/6 Stopping the app (the database keeps running) ..."
docker compose stop backend worker > /dev/null

echo "3/6 Rebuilding the database from the dump ..."
docker compose exec -T postgres sh -c 'dropdb --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' < "$dir/database.dump"

echo "4/6 Starting the app and bringing the schema up to date ..."
docker compose up -d backend > /dev/null
for _ in $(seq 1 40); do
  [ "$(docker compose ps backend --format '{{.Health}}')" = "healthy" ] && break
  sleep 3
done
docker compose exec -T backend alembic upgrade head > /dev/null

echo "5/6 Putting the uploaded files back ..."
docker compose exec -T backend python -m app.scripts.storage_archive import < "$dir/files.tar"

echo "6/6 Starting everything and comparing with the manifest ..."
docker compose up -d > /dev/null
count() { docker compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tA -c \"$1\"" | tr -d '\r'; }
bad=0
check() {  # name, sql
  want="$(grep "^$1=" "$dir/manifest.txt" | cut -d= -f2-)"
  got="$(count "$2")"
  if [ "$want" = "$got" ]; then echo "  ok       $1 = $got"; else echo "  MISMATCH $1: backup $want, now $got"; bad=1; fi
}
check documents 'select count(*) from documents'
check document_versions 'select count(*) from document_versions'
check chunks 'select count(*) from document_chunks'
check users 'select count(*) from users'
check acl_rules 'select count(*) from document_acl'
check audit_queries 'select count(*) from query_audit_logs'
if [ "$bad" -eq 0 ]; then echo "Restore finished: every count matches the backup."; else echo "Restore finished, but some counts differ. See above."; exit 1; fi
