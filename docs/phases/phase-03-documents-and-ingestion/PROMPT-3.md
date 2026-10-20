# Phase 3 prompt (summary of the approved mission)

Mission: Phase 3 of SecureSearch AI (documents and ingestion), in three layers: 3A infrastructure, 3B pipeline and API, 3C admin UI. Do one layer at a time and stop for the owner's review after each.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen). Requirements: FR-05, FR-06, FR-33, NFR-03, NFR-05, NFR-06, NFR-10.

Approved on 2026-10-20 by "Start next phase" after the plan: CR-001 (SeaweedFS replaces archived MinIO), model baked into the image, CPU-only PyTorch, status values `UPLOADED/PROCESSING/PUBLISHED/FAILED`, soft delete, one shared image for backend and worker.

Rules: synthetic data only; no secrets in Git; admin is not reader; deny by default; atomic activation; log every challenge in `docs/CHALLENGES.md`; chat in simple Roman Marathi, repo in English; push only after the owner approves a layer; the owner merges PRs and says "go" before a tag (`v0.3` at the end of Phase 3).
