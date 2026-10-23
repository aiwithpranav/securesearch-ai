#!/usr/bin/env bash
# Creates or completes a local .env with freshly generated random secrets (Linux, macOS, CI, Git Bash).
# The same job as scripts/setup_env.ps1 for Windows PowerShell. Run from anywhere:  bash scripts/setup_env.sh
# - No .env yet: creates it from .env.example.
# - .env exists: adds ONLY the keys that are missing. Existing lines are never changed or removed.
# - Never prints secrets. .env is git-ignored. Do not paste its contents into chat or commit it.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
example="$root/.env.example"
target="$root/.env"

secret() {  # base64url text from n random bytes: safe inside URLs, JSON and .env files
  head -c "$1" /dev/urandom | base64 | tr -d '\n=' | tr '+/' '-_'
}

pg_password="$(secret 24)"
declare -A values=(
  [APP_ENV]="development"
  [APP_SECRET_KEY]="$(secret 48)"
  [JWT_SECRET_KEY]="$(secret 48)"
  [POSTGRES_USER]="securesearch"
  [POSTGRES_PASSWORD]="$pg_password"
  [POSTGRES_DB]="securesearch"
  [DATABASE_URL]="postgresql://securesearch:${pg_password}@postgres:5432/securesearch"
  [REDIS_URL]="redis://redis:6379/0"
  [SMTP_HOST]="mailpit"
  [SMTP_PORT]="1025"
  [SEED_USER_PASSWORD]="$(secret 15)"
  [S3_ENDPOINT_URL]="http://storage:8333"
  [S3_ACCESS_KEY]="$(secret 12)"
  [S3_SECRET_KEY]="$(secret 32)"
  [S3_BUCKET]="securesearch-documents"
)
order=(APP_ENV APP_SECRET_KEY JWT_SECRET_KEY POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB DATABASE_URL REDIS_URL SMTP_HOST SMTP_PORT SEED_USER_PASSWORD S3_ENDPOINT_URL S3_ACCESS_KEY S3_SECRET_KEY S3_BUCKET)

if [ -f "$target" ]; then
  missing=()
  for k in "${order[@]}"; do
    grep -q "^${k}=" "$target" || missing+=("$k")
  done
  if [ "${#missing[@]}" -eq 0 ]; then
    echo ".env already has every key. Nothing changed."
    exit 0
  fi
  [ -n "$(tail -c1 "$target")" ] && echo >> "$target"
  for k in "${missing[@]}"; do echo "${k}=${values[$k]}" >> "$target"; done
  echo "Added missing keys to .env (values not shown): ${missing[*]}"
  exit 0
fi

while IFS= read -r line || [ -n "$line" ]; do
  if [[ "$line" =~ ^([A-Z0-9_]+)= ]] && [ -n "${values[${BASH_REMATCH[1]}]+x}" ]; then
    echo "${BASH_REMATCH[1]}=${values[${BASH_REMATCH[1]}]}"
  else
    echo "$line"
  fi
done < "$example" > "$target"
echo ".env created with generated secrets (values not shown)."
echo "Demo-user password = SEED_USER_PASSWORD inside .env (open the file locally to read it)."
