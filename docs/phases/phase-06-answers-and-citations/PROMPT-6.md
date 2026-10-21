# Phase 6 prompt (summary of the approved mission)

Mission: Phase 6 of SecureSearch AI (answers and citations), in three layers: 6A answer engine (LLM adapter, prompt, citation validator, refusal), 6B API (`POST /ask`, rate limit, search history, feedback), 6C screen (answer, citations, thumbs, history). One layer at a time, each needs the owner's approval.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen), sections 9, 9.5, 12 and the Phase 6 row. Requirements: FR-10, FR-11, FR-12, FR-18; NFR-01, NFR-10.

Approved on 2026-10-22 ("Plan ok, 6A suru"): GPT-4o mini; English only in the product; fake model in tests; the owner supplies the key in `.env` and deletes it afterwards.

Rules: the model is not a security layer; authorize first; every citation validated; uniform refusals; no question or answer text in logs; the key never logged or committed; synthetic data only; log every challenge in `docs/CHALLENGES.md`.
