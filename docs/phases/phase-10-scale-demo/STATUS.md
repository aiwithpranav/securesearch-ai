# STATUS: Phase 10, Layer 10A (scale demo)

Branch: `feat/scale-10a` (local, not pushed). `main` has Phases 1 to 9 (tag `v1.0`).

## Done
- Plan approved by the owner (sources: Kubernetes docs, Docker docs, GitLab handbook; about 100,000 passages and 1,000 people; separate stack; data kept outside Git; results kept in `RESULTS.md`).
- Scripts, helpers, tests and documents written (see CHECKLIST).
- Trial in a throw-away stack (30 files, 200 people): indexing finished, 0 violations; a deliberate resolver mistake was caught. The throw-away stack and its volumes were removed.

## In progress
- Nothing. The full run (download and load of the real documents, hours of indexing) is done after the owner's approval and when the laptop is free.

## Exact next action
1. Owner reviews and approves ("10A Approved"); Claude pushes `feat/scale-10a`, gives the PR link, the owner watches the checks and merges.
2. Full run, with the owner's permission for the download (names, sources and size are shown first): `bash scripts/big/download.sh`, start the big stack, `big_load`, wait for the worker (`big_check --status`), `big_check`, fill `RESULTS.md`, screenshots, tag `v1.1` after "go".

## Blockers
- None. The full run needs a free evening (hours of CPU work) and the owner's yes for the download.

## Decisions this session
- A separate Phase 10, not a change to Phases 1 to 9 (frozen). Version `v1.1`.
- Real public Markdown documentation instead of more invented documents: the point is real formatting and real volume.
- Synthetic people and rules: roles for team documents (so the system administrator is still not a reader), executives may also read restricted documents, clearance gate as in the demo.

## Open issues
- Nothing is measured at 100,000 passages yet: `RESULTS.md` says so until the full run is done.

## Resume prompt
"Read docs/phases/phase-10-scale-demo/STATUS.md, BRIEF.md and docs/CHALLENGES.md in D:\\AI\\RAG\\Secure_Search_AI. Layer 10A is built and waiting for my review. Continue from the Exact next action. Reply in simple Roman Marathi; keep all repo files in English. I do not use GitHub: give click-by-click steps for PRs."
