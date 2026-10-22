# ADR 035: The GitHub connector (Phase 8C)

## Status
Accepted (2026-10-23). Part of the Phase 8 plan the owner approved ("plan ok", "same repo"). The owner can reverse any item.

## Context
Blueprint FR-20: one real connector mirrors the source's permissions into the access rules (GitHub or Google Drive, chosen in Phase 8). GitHub was chosen: free, a simple read-only token, and no OAuth application to set up. The owner decided to use the project's own repository (folder `demo-docs/`) instead of a new one.

## Decision
- **What is imported:** one folder of one repository and branch (settings `repo`, `branch`, `path`). Files of type `.md`, `.txt`, `.pdf` and `.docx` up to 50 MB. Anything under a name that starts with a dot is ignored, so `.securesearch/` is never imported as a document. The source's item id is the file path.
- **Who may read:** `<folder>/.securesearch/access.json` has `teams` (team to GitHub logins) and `access` (folder prefix to teams). A file belongs to the teams of the LONGEST matching folder prefix; with no match, nobody may read it (deny by default). `users.json` maps a GitHub login to the e-mail of the person in the app (GitHub e-mails are usually private); a login with no mapping is ignored.
- **Real permissions:** with `mirror_collaborators` (the default) a person must ALSO be a collaborator of the repository, so removing someone on GitHub removes their access here at the next sync. The list of collaborators needs a token that may read the repository's administration data; if GitHub refuses, the run stops with `PERMISSIONS_UNAVAILABLE` and changes nothing (it never widens access). A source can turn the check off.
- **Token:** `GITHUB_TOKEN`, read-only, in the owner's `.env`, passed to the WORKER only (it runs the sync). The backend never calls GitHub and has no token. Saved settings are refused if they contain a key that looks like a secret. The token is sent only to the address in the environment (`GITHUB_API_URL`, default `api.github.com`), never to an address from saved settings; the repository setting is a checked `owner/name`, never a URL. Error messages are fixed code words, never GitHub's text, so the token cannot leak through them.
- **Network:** the worker was on the private (internal) network only. It now also joins the public network, for outgoing connections only; no port is published for it. This is the one place the worker reaches the internet.
- **Failure codes:** `TOKEN_MISSING`, `BAD_CREDENTIALS`, `NOT_FOUND`, `RATE_LIMITED`, `PERMISSIONS_UNAVAILABLE`, `TREE_TOO_LARGE`, `BAD_ACCESS_FILE`, `SOURCE_UNREACHABLE`. One server error is retried once. A damaged access file stops the run instead of being guessed.
- **Screen:** Manage, Sources (system administrator): the list with Sync now, automatic sync on or off, the interval, the last run and the recent runs in plain words, and a form to add a GitHub source. The form never asks for a token.
- **Demo data:** the folder `demo-docs/` holds six invented documents and the two access files.

## How it is proven
45 connector tests against a fake GitHub (no network is used): settings, folder and type filters, longest prefix, members and collaborators, pagination, every failure code, the retry, where the token goes, and the complete engine flow (first run, a removed collaborator, a changed access file, an edited and a removed file, a skipped run, no permission to list collaborators, token never in a run, log or audit row). 16 mutation checks, all caught. 22 frontend tests. A real-browser check with the real worker: a GitHub source was added and started from the screen and closed with the plain message that the token is missing.

## Consequences
- A live check against the real repository needs the owner's read-only token (done after the merge, with a short-lived token).
- Each run reads every file again (backlog 40); a git blob id could be used as a cheap "unchanged" hint later.
