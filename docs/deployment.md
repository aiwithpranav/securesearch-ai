# Deployment guide

How to run SecureSearch AI on a real machine (one Linux server or a spare computer). It is written for a single company on a single machine: Docker Compose, no cloud account needed. No paid hosting is part of the project.

> All data in this repository is synthetic. Before a real company puts real documents in, read [docs/security.md](security.md) (especially "What this project does not do": no SSO, no MFA, no independent audit) and have the Privacy and Terms pages reviewed.

## What you need
- A machine with Docker and the Compose plugin, about 8 GB of memory and 15 GB of free disk (the first build downloads PyTorch and two models).
- A domain name pointing at the machine, and a way to serve HTTPS (a reverse proxy; an example is below).
- A real mail server for password reset and invitation emails (SMTP).
- Optional: an OpenAI key (for written answers) and a read-only GitHub token (for a GitHub source).

Check a computer with `scripts/check_prereqs.sh` (Linux, macOS, Git Bash) or `scripts/check_prereqs.ps1` (Windows).

## 1. Settings
```bash
bash scripts/setup_env.sh          # creates .env with random secrets
```
Then edit `.env` and set:
- `FRONTEND_ORIGIN=https://search.example.com` (the public address of the website; the API only accepts requests from this address)
- `SMTP_HOST` and `SMTP_PORT` of your mail server (the default points at the test mailbox, which production does not start)
- Optional: `OPENAI_API_KEY`, `GITHUB_TOKEN` (see [.env.example](../.env.example))
- Optional: `AUDIT_RETENTION_DAYS` (default 365) and `KEEP_VERSIONS` (default 3)

In the shell that starts Compose (or in `.env`) also set the address the website uses to reach the API, as a public URL (it is not a secret):
```bash
export PUBLIC_API_URL=https://search.example.com   # when the proxy below serves the API on the same address under /api
```

## 2. Start
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic upgrade head
```
The production file adds `restart: unless-stopped` to everything, runs the API without auto-reload and with `APP_ENV=production` (cookies become HTTPS-only, demo scripts refuse to run), runs the website as a container, and does not start the test mailbox. `WEB_WORKERS` sets how many API processes run (default 1; each loads the two models, about 1.2 GB).

Create the first administrator by hand (the demo seed refuses to run in production): open a database shell, `docker compose exec postgres psql ...`, or run your own small script that uses `app.core.security.hash_password`. People are then added in the Users screen.

## 3. HTTPS with a reverse proxy
The website listens on `127.0.0.1:3000` and the API on `127.0.0.1:8000`; neither is exposed. Put a proxy in front. Example with [Caddy](https://caddyserver.com/) (it gets certificates by itself):
```text
search.example.com {
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```
Same address for both means no cross-site cookie problems and a single `FRONTEND_ORIGIN`.

## 4. Check it
- `https://search.example.com/status` shows every part as working.
- Sign in, upload a document, give a group access, ask a question as two different people.
- Make a backup right away and restore it somewhere else once: [runbook](runbook.md).

## 5. Keep it healthy
- **Backups:** `bash scripts/backup.sh` (schedule it daily; copy it off the machine; encrypt it).
- **Updates:** `git pull`, then the same `up -d --build` command, then `alembic upgrade head`. Make a backup first.
- **Logs:** `docker compose logs backend --tail 100` (structured JSON; ids only, never document text).
- **Dependabot** opens weekly update pull requests in the repository; each one runs the full checks ([docs/ci.md](ci.md)).

## What is not included
No cloud templates, no autoscaling, no high availability (one machine is one point of failure), no managed secrets store, no web application firewall. Those are the usual next steps for a larger deployment.
