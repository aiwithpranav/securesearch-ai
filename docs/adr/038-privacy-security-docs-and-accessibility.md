# ADR 038: Privacy and security documents, a generated API reference and accessibility checks (Phase 9C)

## Status
Accepted (2026-10-24). Part of the Phase 9 plan the owner approved ("9C plan ok"). The owner can reverse any item.

## Context
The public Privacy page said the site "does not use cookies", but signing in sets one cookie (`refresh_token`); it did not say that a question and a few permitted passages are sent to the AI provider. The Security page promised results "once the evaluation exists". There was no security policy, no document tying the threat model to tests, no API reference, and no accessibility check beyond the first phases.

## Decision
- **Privacy and Terms pages** now describe what the software really does: no cookies on the public pages; one httpOnly sign-in cookie (1 day, or 7 with "Remember me"); a browser note about the skipped tour; what is stored (account, question history without answers, the audit trail without answers or document text, kept 365 days by default); and exactly what leaves the server (the question and a few passages the person may read go to the AI provider when an answer is written; a connected source is read with a read-only key). Terms say it is a demo with invented data, answers can be wrong, and no warranty. Both state that they are not legal advice.
- **Security page** lists the rules, the six walls and the measured result (62 questions, 8 people, 48 documents, 0 leaks, with its limits), and links to private vulnerability reporting.
- **`SECURITY.md`:** how to report (GitHub private vulnerability reporting, no public issue), scope, out of scope, supported version, what to expect.
- **`docs/security.md`:** the rules, the six walls with the file that enforces each, the 16 threats of the blueprint each tied to the tests that prove the control, the OWASP Top 10 for LLM Applications (2025) with evidence, secrets, what leaves the machine, and **what the project does not do** (no SSO or MFA, no multi-tenancy, no malware scan, no Row-Level Security wall, no application-level encryption, no voice input, no independent audit) and the limits of the evidence. Threat T16 (voice) is marked not applicable because voice input was not built.
- **`docs/api.md` is generated** from the application (`python -m app.scripts.gen_api_docs`): every route, who may call it (read from the route's own dependencies, so it cannot disagree with the code) and a one-line description. CI regenerates it and fails on any difference.
- **Accessibility and speed:** Lighthouse runs in CI against a production build of the six public pages (minimums: performance 75, accessibility 95, best practices 90, SEO 90; measured locally 97 to 100, 100, 96 to 100, 100). The performance limit is lower than the local numbers because the first CI run scored the landing page 80 on a slow shared runner against 98 on a developer machine: speed depends on the computer, accessibility does not. Signed-in screens cannot be reached by a CI browser without a login, so they were audited by hand with axe-core (WCAG 2 A and AA, 2.1, 2.2 and best-practice rules) on 14 pages; two real findings (empty table-header cells on the audit and evaluation tables, a skipped heading level on the evaluation page) were fixed and all pages then reported zero violations. Automated checks catch part of the problems; a person using a screen reader or keyboard still has to try the screens.

## How it is proven
The generated API reference has 4 tests (`tests/test_api_docs.py`: every route listed, public and administrator routes labelled correctly) and a CI diff; the Lighthouse job fails below the thresholds (the check script was also run against a deliberately low report); the pages were checked in a real browser.

## Consequences
- Changing a route without regenerating `docs/api.md` fails CI. Regenerate with the command in the file header.
- The axe audit of signed-in screens is manual; a Playwright run with a seeded user would automate it (backlog 48).
