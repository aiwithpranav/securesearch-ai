# Security policy

SecureSearch AI is a portfolio project: all data in it is synthetic and no real deployment is run by the author. Even so, security reports are welcome and taken seriously, because the whole point of the project is that the access rules hold.

## Reporting a vulnerability
Please **do not open a public issue** for a security problem.

Use GitHub's private reporting: on the repository page choose **Security**, then **Report a vulnerability** (direct link: `https://github.com/aiwithpranav/securesearch-ai/security/advisories/new`). Include what you found, how to reproduce it, and what you think the impact is. You will get a reply within 7 days; a fix or a written decision follows as soon as it can be made.

## What is in scope
Anything that breaks one of the project's promises:
- Someone reads, searches, sees cited, or sees counted a document they may not read (a leak), including through prompt injection, timing, wording, counts, progress messages, history or the audit trail.
- A role, department or clearance is taken from anything other than the database (forged or replayed requests).
- Sign-in, session, password reset or rate-limit weaknesses; account discovery.
- An administrator reading document content, or the audit trail being changed or read by someone who should not.
- A secret (key, token, password) appearing in a response, a log, a saved setting, a screen or the repository.
- Unsafe handling of an uploaded file or of a connected source.

## Out of scope
- Findings that need access to the machine, the database login or the `.env` file (an owner of those can do anything).
- Missing features the project lists as not built (see [docs/security.md](docs/security.md), section "What this project does not do").
- Denial of service by sheer volume against a local demo, and reports from automated scanners with no demonstrated impact.

## Supported versions
Only the latest release on `main` is supported.

## What you can expect from the project
- Every security rule has an automated test that fails when the rule is broken, and a leak fails the build ([docs/ci.md](docs/ci.md)).
- Dependencies are pinned and scanned on every pull request; the whole git history is scanned for secrets.
- Findings and fixes are written down in `docs/CHALLENGES.md`.
