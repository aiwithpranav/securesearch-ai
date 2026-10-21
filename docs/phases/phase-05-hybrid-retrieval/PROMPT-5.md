# Phase 5 prompt (summary of the approved mission)

Mission: Phase 5 of SecureSearch AI (hybrid retrieval), in three layers: 5A engine (indexes, allow-list first search, RRF, reranker), 5B `/search` API with three modes, 5C search screen. One layer at a time, each needs the owner's approval.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen), sections 9, 23 and the Phase 5 row of the roadmap. Requirement: FR-09, NFR-01, NFR-04.

Approved on 2026-10-21 ("5A suru kara") with 5 decisions: three layers; local CPU reranker (no key); hybrid default but all three modes measured; search only inside what the person may read (admin is not reader); the search screen shows chunk text to the reader, no source links yet (Phase 6).

Rules: authorize before retrieval; no unauthorized chunk is ever scored, returned or logged as content; log every challenge in `docs/CHALLENGES.md`; secrets never in Git; synthetic data only.
