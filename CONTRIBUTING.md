# Contributing

SecureSearch AI is a learning and portfolio project, and contributions are welcome. All data in the repository is synthetic: never add real documents, real people or secrets.

## Run it
1. Install Docker Desktop and Node.js 24.
2. Create your local settings: `bash scripts/setup_env.sh` (Linux, macOS, Git Bash) or `powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1` (Windows).
3. `docker compose up -d`, then `cd frontend && npm install && npm run dev`.

## Before you open a pull request
Run the same checks CI runs (details in [docs/ci.md](docs/ci.md)):

```bash
cd backend && ruff check .                      # style and mistakes
docker compose exec backend mypy                # types
docker compose exec backend python -m pytest    # tests
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Rules of the project
- Branches are named `type/short-name` (for example `feat/login-form`); commits follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- The security rules are not negotiable: deny by default, deny beats allow, the server decides, an administrator is not a reader, refusals are uniform, the model is a writer and never a guard. A change that weakens one needs a Change Request (see `docs/change-requests/`).
- The API contract only grows by adding. Every behaviour change needs a test; every security rule needs a test that fails when the rule is broken.
- Record a decision in `docs/adr/` and a difficulty in `docs/CHALLENGES.md`.

## Reporting a security problem
Please do not open a public issue. See [SECURITY.md](SECURITY.md) once it exists, or contact the author directly.
