# Security model

SecureSearch AI is an AI knowledge search that **checks permissions before it searches**, so the language model never sees text a person may not read. This page explains the rules, where each one is enforced, which test fails when it is broken, and, just as important, what the project does **not** do.

The source of truth for the design is the blueprint (v1.2, frozen); this page records what was actually built. To report a problem see [SECURITY.md](../SECURITY.md).

## The rules
1. **Deny by default.** No matching ALLOW rule means no access. A document with no rules is invisible to everyone.
2. **Authorize before retrieval.** The set of documents a person may read is part of the SQL that fetches passages, not a filter applied afterwards.
3. **Deny beats allow.** One matching DENY removes access whatever else says ALLOW.
4. **The server decides.** Roles, groups, clearance and country are read from the database on every request. The token carries only the user id.
5. **The model is a writer, not a guard.** It has no tools. It receives only permitted passages, marked as untrusted data, and its output is validated.
6. **An administrator is not a reader.** Managing users, rules and documents does not grant permission to read content.
7. **Uniform failure.** A refusal looks identical whether the topic is restricted or simply missing (same text, same shape, same 404).
8. **Log ids, not content.** The audit trail keeps ids, counts and outcomes; never answers and never document text.
9. **No side doors.** Progress messages, suggestions, history and dashboards only use what the person may already see; counts are only ever of the person's own readable set.

The access decision (all in SQL, per request): the document is live and READY; no matching DENY; a matching, unexpired ALLOW; the person's clearance is at least the document's sensitivity; the person's country is allowed when the document limits countries. See [ADR 027](adr/027-access-decision-design.md).

## Six walls (defence in depth)
| # | Wall | Where | What breaks if it has a bug |
|---|---|---|---|
| 1 | Endpoint authorization on every route | `app/api/deps.py` (`get_current_user`, `require_admin`, role checks) | An employee reaching an admin route |
| 2 | Retrieval needs to know who is asking | `app/retrieval/search.py` (every function takes the user) | Search without a person |
| 3 | The allow-list inside the SQL | `app/access/resolver.py` (`readable_ids_stmt`), used by keyword, vector and fusion queries | Text outside the list being scored |
| 4 | Second look after retrieval | `app/retrieval/search.py` (`_load_hits` repeats the check), `app/answers/service.py` | A passage that slipped through being shown or sent to the model |
| 5 | Citation validation | `app/answers/validator.py` | An answer citing something the person may not read |
| 6 | Leak tests on every change | `tests/test_eval.py`, `tests/test_access_oracle.py`, the CI "leak gate" ([docs/ci.md](ci.md)) | A leak reaching `main` |

## Threat model: what an attacker might try, and what stops it
| # | Threat | Control | Proven by |
|---|---|---|---|
| T1 | A question phrased to reach restricted content | Allow-list in SQL at every retrieval stage | `tests/test_access_oracle.py` (random worlds against an independent oracle), `tests/test_access_resolver.py`, `tests/test_retrieval.py`; 10 unauthorized cases in the evaluation |
| T2 | Direct prompt injection ("ignore all rules") | Security does not depend on prompts; the rules are in SQL | 5 injection cases in `app/eval/cases.py`, run by `tests/test_eval.py` |
| T3 | Injection hidden in an uploaded document | Retrieved text is marked as untrusted data, tags are defused, the model has no tools, output is schema-checked | `tests/test_answers.py`, `tests/test_answers_unit.py`; the poisoned sample document in `sample-data/` |
| T4 | Stolen or replayed token | 15-minute access token, rotating httpOnly refresh cookie, reuse of an old refresh token revokes the session | `tests/test_auth_sessions.py`, `tests/test_security_unit.py` |
| T5 | Client forges its role or department | Roles are never read from the token or the request | forged-request scenario in the evaluation; `tests/test_users_admin.py`, `tests/test_auth_login.py` |
| T6 | Side channels: counts, wording, timing reveal restricted documents | One refusal text; identical 404 for not-allowed and missing; no counts of hidden items | `tests/test_chat_api.py`, `tests/test_answers.py`, `tests/test_search_api.py` |
| T7 | Audit log, logs or errors leak content | Ids only; fixed field list for security events; error bodies generic; audit views permission-gated | `tests/test_audit.py` (forbidden text never reaches an audit table), the evaluation scanner (answers, search results, the model prompt, audit rows and logs) |
| T8 | Malicious upload | Type allow-list, size cap, content checks, parsing in the worker, no execution | `tests/test_ingest_validation.py`, `tests/test_documents_api.py`, `tests/test_ingest_parsers.py` |
| T9 | The vector store exposes embeddings | Vectors are reachable only through the access-checked queries; the database is on a private network and publishes no port | `tests/test_retrieval.py`; `docker-compose.yml` |
| T10 | Stale permissions after a change | Rules are read at query time; no cache of decisions | 14 scenarios in the evaluation (revoke, group left, expiry, delete, new version, clearance, country, deactivation); `tests/test_sync.py` (a team member removed at the source loses access at the next question) |
| T11 | An insider administrator reads everything | Admin is not reader; permission changes keep a history; the system administrator cannot read the audit trail | `tests/test_access_resolver.py`, `tests/test_documents_api.py`, `tests/test_groups_acl_api.py`, `tests/test_audit.py` |
| T12 | A vulnerable or poisoned dependency | Pinned versions, vulnerability scans and a secret scan of the whole history on every pull request | CI ([docs/ci.md](ci.md)); the first scan found and fixed 8 known problems in the PDF reader |
| T13 | Cost or availability abuse | Rate limits (sign-in, search 30 a minute, answers 10 a minute, preview 60, upload 20, status 60), token caps, input length limits | `tests/test_search_api.py`, `tests/test_chat_api.py`, `tests/test_documents_api.py`, `tests/test_auth_login.py`, `tests/test_ops.py` |
| T14 | The progress or suggestion screens leak hidden titles or counts | Fixed stage labels; suggestions only from titles of documents the person may read; counts only of their own readable set | `tests/test_chat_api.py`, `tests/test_dashboards.py` |
| T15 | Account takeover or discovery through sign-in and reset | Generic replies, lockout, single-use hashed expiring reset tokens, the same message for a wrong email or password, rate limits | `tests/test_auth_login.py`, `tests/test_auth_passwords.py`, `tests/test_auth_sessions.py` |
| T16 | Voice input misuse | Not applicable: **voice input was not built** (blueprint FR-29, "should") | n/a |

## OWASP Top 10 for LLM Applications (2025)
| Item | How it is covered | Evidence |
|---|---|---|
| LLM01 Prompt injection | Authorization lives outside the model; retrieved text is data; strict output schema | T2 and T3 above |
| LLM02 Sensitive information disclosure | Only permitted passages reach the model; canary strings in every restricted document; no content in logs | evaluation report: 0 leaks on 62 cases; `docs/evaluation-report.md` |
| LLM03 Supply chain | Pinned packages and model revisions; scans in CI | [ADR 022](adr/022-pinned-versions.md), [ADR 036](adr/036-ci-and-quality-gates.md) |
| LLM05 Improper output handling | The reply must be JSON of a fixed shape; every citation id is checked; links, HTML and code are refused; output is shown as text | `app/answers/validator.py`, `tests/test_answers_unit.py` |
| LLM06 Excessive agency | The model has no tools and cannot call anything | `app/llm/` (one completion call only) |
| LLM07 System prompt leakage | The prompt contains no secrets and no access logic | `app/answers/prompt.py` |
| LLM08 Vector and embedding weaknesses | The vector query uses the same allow-list as keyword search; the database is private | `app/retrieval/search.py`, `tests/test_retrieval.py` |
| LLM09 Misinformation | Grounded answers with citations, a confidence threshold tuned by measurement (0.30), refusal when evidence is weak | [ADR 032](adr/032-evaluation-design.md) |
| LLM10 Unbounded consumption | Rate limits, a cap on model output, a cap on question length | T13 above |

(LLM04 data and model poisoning and LLM03 training-data topics apply only to training; no model is trained here.)

## Secrets
- Secrets live only in the local `.env` (git-ignored), generated by `scripts/setup_env.sh` or `scripts/setup_env.ps1`.
- The OpenAI key goes to the backend only; the GitHub token (read-only) goes to the worker only. Saved source settings may not contain secret-looking keys.
- Passwords are Argon2id hashes. Tokens in the database are hashed. Nothing secret is logged; the whole git history is scanned for secrets in CI.

## What leaves the machine
- Question text and a few permitted passages go to the AI provider when an answer is written.
- A connected GitHub folder is read with the read-only token; nothing is written to GitHub.
- Everything else (storage, search, ranking, embeddings, audit) stays on the server.

## What this project does not do
Stated plainly, so nobody has to find it out:
- **No single sign-on, no multi-factor authentication, no automatic user provisioning (SCIM).** Passwords only. These are the first items a real company would ask for.
- **No multi-tenancy.** One company per installation.
- **No malware scanning of uploads** (type and size checks and safe parsing only) and **no OCR** (scanned documents are refused).
- **No PostgreSQL Row-Level Security wall.** It was deliberately deferred; the six walls above are application-level.
- **No encryption of stored data at the application level.** Use disk or volume encryption where the data lives.
- **No voice input.**
- **No independent security audit or penetration test, and no formal compliance (SOC 2, GDPR processes).**
- **Someone who controls the database login or the `.env` file controls everything.** The append-only audit tables and the retention purge guard against mistakes and bugs, not against that person ([ADR 037](adr/037-operations.md)).

## Known limits of the evidence
- The evaluation is 62 cases over 48 short invented documents: a result for that set, not a promise for any other.
- The automated runs use a stand-in answer writer; a run with the real model is still open (backlog 35).
- With the refusal threshold at 0.30, only 4 of 8 paraphrased questions are answered (the right document is found, but the model is not asked); this is a deliberate trade for safety (backlog 34).
