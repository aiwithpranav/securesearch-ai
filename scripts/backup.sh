#!/usr/bin/env bash
# Makes one backup of everything the system keeps: the database and the uploaded original files (Phase 9B, FR-38).
#   bash scripts/backup.sh                    # writes backups/<UTC date and time>/
#   bash scripts/backup.sh /path/to/folder    # writes there
# Needs the stack running (docker compose up -d). On Windows run it in Git Bash (it comes with Git).
#
# The backup holds the company's documents and every person's data: keep it private, never commit it (backups/ is git-ignored).
# It does NOT hold your .env (secrets). Keep that separately, for example in a password manager.
# Passwords are never printed: the database login is read inside the containers.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

out="${1:-backups/$(date -u +%Y%m%d-%H%M%S)}"
mkdir -p "$out"

echo "1/3 Database ..."
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner' > "$out/database.dump"

echo "2/3 Uploaded files ..."
docker compose exec -T backend python -m app.scripts.storage_archive export > "$out/files.tar"

echo "3/3 Checking and describing the backup ..."
count() { docker compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tA -c \"$1\"" | tr -d '\r'; }
{
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "migration=$(count 'select version_num from alembic_version')"
  echo "documents=$(count 'select count(*) from documents')"
  echo "document_versions=$(count 'select count(*) from document_versions')"
  echo "chunks=$(count 'select count(*) from document_chunks')"
  echo "users=$(count 'select count(*) from users')"
  echo "acl_rules=$(count 'select count(*) from document_acl')"
  echo "audit_queries=$(count 'select count(*) from query_audit_logs')"
} > "$out/manifest.txt"
(cd "$out" && sha256sum database.dump files.tar manifest.txt > SHA256SUMS && sha256sum -c SHA256SUMS > /dev/null)

echo "Backup written to $out"
sed -n '2,9p' "$out/manifest.txt" | sed 's/^/  /'
