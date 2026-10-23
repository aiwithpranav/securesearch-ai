# Phase 9 Checklist

## 9A Quality gates (merged, PR #32)
- [x] mypy clean (36 errors fixed), ruff clean (38 fixed, rules in `backend/pyproject.toml`), ESLint clean (21 advisory warnings with a ceiling)
- [x] CI workflow with five jobs, leak gate, coverage gate (83 % overall), image build, gitleaks over the whole history (no leaks), pip-audit and npm audit
- [x] `pypdf` upgraded 6.19.0 to 6.21.1 (8 known vulnerabilities in the PDF parser); Dockerfile layer order fixed (backlog 31)
- [x] Dependabot, pull request template, CONTRIBUTING, MIT licence, pre-commit config, `scripts/setup_env.sh`, `docs/ci.md`, ADR 036
- [x] All 697 backend and 123 frontend tests pass
- [x] First CI run green on the pull request (the first run found a real problem, fixed)
- [x] Owner approval (merged, PR #32)

## 9B Operations (merged, PR #33)
- [x] Audit retention (default 365 days, floor 30) with a guarded purge (migration `0009`), nightly job, command line, Overview number
- [x] `/status` (public, plain) with real checks and a worker heartbeat; public Status page; request, error and "too many requests" counters in the Overview
- [x] Nightly cleanup of passages of old versions (keep 3); object storage listing pages through results
- [x] `scripts/backup.sh`, `scripts/restore.sh`, `docs/runbook.md`; **a real restore tested on an empty stack** (all counts matched)
- [x] 35 new backend tests (732 total), 9 new frontend tests (132 total), 15 mutations all caught; real-browser check (status page with a real outage, Overview, 360 px)
- [ ] Owner manual checks and approval
## 9C Privacy and security documents (not started)
## 9D Launch and showcase (not started)

## Phase 9 close
- [ ] Owner approval, PRs merged, tag `v1.0`
