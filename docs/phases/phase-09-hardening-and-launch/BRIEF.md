# Phase 9 Brief: Hardening and launch

**Goal:** make the project ready to be shown and to be run by a stranger: quality gates in CI, operations (retention, health, backup and restore), honest privacy and security documents, and a README, demo and clean-machine start that make a strong first impression.

**Requirement IDs:** FR-36 (audit retention), FR-37 (health and status page), FR-38 (backup and restore runbook), NFR-03, NFR-06, NFR-09 (one command starts everything), NFR-16 (recoverability). Plus blueprint 14.3 (CI gates), 15 (README) and 24 (real-company readiness).

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **9A** Quality gates | GitHub Actions CI (lint, types, tests, leak gate, coverage, scans, image build), Dependabot, templates, licence, pre-commit, setup script for Linux and macOS | Built, waiting for owner review |
| **9B** Operations | Audit retention and a safe purge, status page and metrics, backup and restore with one tested restore, cleanup of old passages | Not started |
| **9C** Privacy and security documents | Privacy and terms text made accurate, SECURITY.md, docs/security.md (OWASP LLM Top 10), docs/api.md, accessibility checks | Not started |
| **9D** Launch and showcase | README, architecture diagram, screenshots, demo script, a readiness check command for a new laptop, clean-machine test, history scan, public checklist, tag v1.0 | Not started |

## Security rules that apply
- CI never sees a real secret: a throw-away `.env` with random values, a fake model, synthetic data.
- Any leak in the leak gate fails the build.
- Nothing about the product's behaviour changes in 9A.

## Out of scope
Paid hosting, SSO, multi-tenant (see blueprint section 24).

## Estimate
Blueprint: 5 to 7 days. Plan: 9A about 1, 9B about 2, 9C about 1, 9D about 2.
