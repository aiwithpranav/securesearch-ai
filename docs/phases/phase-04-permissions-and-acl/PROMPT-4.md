# Phase 4 prompt (summary of the approved mission)

Mission: Phase 4 of SecureSearch AI (permissions and ACL), in three layers: 4A core (tables and resolver), 4B API (groups, rules, history, preview, seed), 4C UI (users, groups, access section). One layer at a time; stop for the owner's review after each.

Source of truth: Pre-Code Blueprint v1.2 FINAL (frozen), sections 9.1 to 9.4 and 10.1 to 10.3. Requirements: FR-07, FR-08, FR-04.

Approved on 2026-10-20 ("Approve") with 8 decisions (see BRIEF.md and ADR 027).

Rules: deny by default; DENY beats ALLOW; server decides from the database on every request; no cache; admin is not reader; table-driven and negative tests; log every challenge in `docs/CHALLENGES.md`; chat in simple Roman Marathi, repo in English; the owner does not use GitHub, so give click-by-click PR steps and check the remote; push only after the owner approves a layer; the owner says "go" before a tag (`v0.4` at the end of Phase 4).
