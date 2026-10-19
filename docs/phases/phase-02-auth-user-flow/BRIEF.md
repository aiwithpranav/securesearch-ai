# Phase 2 Brief: Auth and user flow

**Goal:** a person can sign in safely, stay signed in safely, and an admin can manage accounts. Delivered in three layers: **2A** backend foundation (done), **2B** auth backend (built, waiting for owner review), **2C** login screens and protected routes (not started).

**Requirement IDs (whole phase):** FR-02, FR-03, FR-04, FR-23 to FR-27, FR-35, NFR-02, NFR-03 (login), NFR-06.
**2B covers:** FR-02, FR-03, FR-04 (stored per user), FR-25 (invite, forgot and reset; admin-initiated reset deferred, see ADR 023), FR-26, NFR-02, the login part of NFR-03.
**2C will cover:** FR-23, FR-24, FR-27, protected routes, profile page.

**Definition of done (blueprint):** each seed user logs in and sees the correct role and department; every login state behaves per spec; refresh rotation, lockout and reset-by-email are tested.

**Out of scope:** SSO, public sign-up, documents, groups, ACL.
