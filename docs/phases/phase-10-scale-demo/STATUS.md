# STATUS: Phase 10, Layer 10A (scale demo)

Branch: `feat/scale-10a` (local, not pushed). `main` has Phases 1 to 9 (tag `v1.0`).

## Done
- Plan approved by the owner (sources: Kubernetes docs, Docker docs, GitLab handbook; about 100,000 passages and 1,000 people; separate stack; data kept outside Git; results kept in `RESULTS.md`).
- Scripts, helpers, tests and documents written (see CHECKLIST).
- Trial in a throw-away stack (30 files, 200 people): indexing finished, 0 violations; a deliberate resolver mistake was caught. The throw-away stack and its volumes were removed.
- Full run (2026-10-29): downloaded three public sources (6,758 Markdown files, about 80 MB), loaded 1,000 people and 5,850 documents, indexed 90,956 passages (about 1 h 50 min), `big_check`: 1,040 queries, 0 violations. Findings recorded in `RESULTS.md`.

## In progress
- Nothing. Waiting for the owner's review.

## Exact next action
1. Owner reviews and approves ("10A Approved"); Claude pushes `feat/scale-10a`, gives the PR link, the owner watches the checks and merges.
2. Tag `v1.1` after "go". Later, only when the space is needed: delete the big stack with `down -v` and the folder `C:/Users/prana/ss-big`; `RESULTS.md` stays.

## Blockers
- None.

## Decisions this session
- A separate Phase 10, not a change to Phases 1 to 9 (frozen). Version `v1.1`.
- Real public Markdown documentation instead of more invented documents: the point is real formatting and real volume.
- Synthetic people and rules: roles for team documents (so the system administrator is still not a reader), executives may also read restricted documents, clearance gate as in the demo.

## Open issues
- Two weak spots found and recorded, not fixed here (backlog 55 and 56): exact-identifier search ranks poorly at this size; the default search (with the reranker) has P95 5.4 s on this laptop against a 5 s target.

## Resume prompt
"Read docs/phases/phase-10-scale-demo/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 10A is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."
