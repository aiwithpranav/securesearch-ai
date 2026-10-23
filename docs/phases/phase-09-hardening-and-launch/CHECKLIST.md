# Phase 9 Checklist

## 9A Quality gates (built, waiting for owner review)
- [x] mypy clean (36 errors fixed), ruff clean (38 fixed, rules in `backend/pyproject.toml`), ESLint clean (21 advisory warnings with a ceiling)
- [x] CI workflow with five jobs, leak gate, coverage gate (83 % overall), image build, gitleaks over the whole history (no leaks), pip-audit and npm audit
- [x] `pypdf` upgraded 6.19.0 to 6.21.1 (8 known vulnerabilities in the PDF parser); Dockerfile layer order fixed (backlog 31)
- [x] Dependabot, pull request template, CONTRIBUTING, MIT licence, pre-commit config, `scripts/setup_env.sh`, `docs/ci.md`, ADR 036
- [x] All 697 backend and 123 frontend tests pass
- [ ] First CI run green on the pull request (GitHub runs it; Claude fixes anything red)
- [ ] Owner approval

## 9B Operations (not started)
## 9C Privacy and security documents (not started)
## 9D Launch and showcase (not started)

## Phase 9 close
- [ ] Owner approval, PRs merged, tag `v1.0`
