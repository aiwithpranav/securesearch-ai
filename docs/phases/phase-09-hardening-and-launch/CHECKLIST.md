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
## 9C Privacy and security documents (merged, PR #34)
- [x] Privacy, Terms, Security pages; SECURITY.md; docs/security.md; generated docs/api.md with CI diff; Lighthouse in CI; axe audit (14 pages, zero violations)

## 9D Launch and showcase
- [x] README rewritten, ten screenshots, architecture diagrams, deployment guide
- [x] `check_prereqs` scripts, production compose file and website Dockerfile
- [x] Quick start run on a clean copy (separate stack): login and permission-checked search worked; one bug found and fixed (status page on a fresh install)
- [x] Landing page: GitHub links, demo banner, honest SSO answer
- [ ] Owner approval, PR merged
- [ ] Public checklist (owner clicks): repository description and topics, private vulnerability reporting, branch protection with required CI, make public
- [ ] Release notes and tag `v1.0`

## Phase 9 close
- [ ] Owner approval, PRs merged, tag `v1.0`
