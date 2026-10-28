# Error handling strategy

Scope: the FastAPI backend, the background worker, the AI answer pipeline and the Next.js website (v1.0). Every error below was taken from the application code and from problems met during development. Statuses and codes are listed in [api.md](api.md); the reasons are in the ADRs ([023](adr/023-auth-implementation-details.md), [026](adr/026-ingestion-design.md), [030](adr/030-grounded-answers.md), [034](adr/034-sync-engine.md), [035](adr/035-github-connector.md)).

## 1. Principles
- **One error format.** Every API error is a Problem Details object (RFC 9457 style): `type`, `title`, `status`, `detail`, `request_id`. Validation errors add an `errors` list of field names and rule messages.
- **Never echo what the user sent.** Passwords, tokens, emails and document text never appear in an error body, a log line or an audit row.
- **Do not reveal existence.** A missing document and a document the person may not access return the same 404; every refusal of an answer shows the same sentence; an unknown email and a wrong password return the same 401.
- **Fail closed.** If a security step cannot complete (audit write, permission check, source listing), the request fails and nothing is returned or changed.
- **Fail safe for data.** A failed indexing job never damages the previous good index; a broken or empty source never wipes documents.
- **Traceable.** Every response carries a `request_id` that also appears in the structured log (ids and error types only).
- **Unexpected errors.** A last-resort handler returns a generic 500 and logs only the error type.

## 2. Authentication and session errors
| Error | When | Handling |
|---|---|---|
| **401 Invalid credentials** | Wrong email or password | Same message for an unknown email and a wrong password. The login page shows the error and shakes the form. Every failure is counted for lockout. |
| **401 Session expired** | The 15-minute access token expired, or the refresh token is missing, invalid, expired or revoked | The website calls `/auth/refresh` once (one refresh at a time) and retries; if that fails it sends the person to the login page. A refresh token used a second time is treated as theft and the whole session family is revoked. |
| **429 Too many attempts** (login) | 5 wrong passwords for one email (15-minute lock, also for unknown emails) or more than 30 login attempts per minute from one IP | Counters in Redis; `Retry-After` header and "Try again in N minutes". The real user can still use "Forgot password". |
| **400 Invalid link** | Reset or invitation link invalid, used or expired | One message for every case. Links are single use (30 minutes for reset, 72 hours for invitations); a newer link cancels older ones; the token sits after `#` so servers and logs never see it. |
| **400 Wrong password** | Wrong "current password" when changing a password | Clear message; nothing changes. |
| **403 Forbidden** | Signed in, but the role is not allowed | Generic message. The menu only shows what the role allows. |
| **403 Request origin not allowed** | A cookie endpoint (`/auth/refresh`, `/auth/logout`) called from another site (CSRF) | Origin check plus a SameSite=Lax cookie. |
| **Deactivated user, password change, sign out everywhere** | Account state changes while tokens are still valid | Refresh tokens are revoked and `auth_valid_after` is set, so older access tokens are rejected on the next request. |

## 3. General API errors
| Status | Cause | Handling |
|---|---|---|
| 400 | Not allowed operation (for example deactivating your own account) | Clear message; nothing changes. |
| 404 | Resource missing, or the person has no right to see it | One uniform "not found". |
| 405 | Wrong HTTP method | Standard Problem Details response. |
| 409 | Duplicate document (same SHA-256), duplicate name or rule, document already being processed, a team managed by a sync source | Message says what to do; for duplicates the existing document id is returned. A database index allows one unfinished job per document. |
| 413 / 422 | File too large (413); validation failure (422) | Field names and rule messages only, never the submitted values. Uploads are checked by real content (magic bytes), size and zip-bomb limits before anything is stored. |
| 429 | Rate limits: login, search (30 per minute), answers (10 per minute), uploads | `Retry-After` header and `retry_after_seconds`; counted in the metrics shown to administrators. |
| 500 | Unexpected bug | Generic message with `request_id`; only the error type is logged. On the answer stream, a short "The answer could not be completed" event. |
| 503 | File store down, answers not available (no key or provider down), evaluation cannot start | "Try again later". For answers the message says search still works, and nothing is saved in the history. |

## 4. Document processing errors (worker)
| Code | Meaning | Strategy |
|---|---|---|
| `UNSUPPORTED_TYPE`, `EMPTY`, `TOO_LARGE` | Wrong type, empty file, too large | Fail at once with a fixed message. |
| `NO_TEXT`, `PARSE_ERROR` | Scanned image PDF (no OCR), damaged or protected file | Fail at once; OCR is documented as out of scope. |
| `INTEGRITY_ERROR` | Stored file does not match its recorded SHA-256 | Fail; nothing is indexed from a file that may have been changed. |
| `STORAGE_ERROR`, `EMBEDDING_ERROR`, `INTERNAL` | Temporary infrastructure problems | **Retryable**: up to 3 retries; jobs are idempotent (a retry first removes its own leftovers). |
| `TIMEOUT`, `DELETED` | Job took too long; document deleted while processing | Job stopped with a fixed message. |

Only fixed texts are stored (never file content); a failed job leaves the previous version answering; administrators get a notification and see the history on the document page.

## 5. AI answer pipeline
| Case | Handling |
|---|---|
| No API key, or provider problem (`unavailable`, `timeout`, `rate_limited`, `auth`, `bad_response`) | One retry for a busy service, then a short error code (503 "Answers are not available right now. You can still search."). The key is never logged or shown. The failure is audited with status UNAVAILABLE. |
| Reply not valid JSON, cites a source that was not given, has a link, HTML or code, or is too long | The validator blocks it; one retry; then the uniform refusal. Nothing the model wrote reaches the person before validation. |
| Weak evidence or the model cannot answer | `REFUSED_LOW_CONFIDENCE` with one uniform sentence. For weak evidence the model is not called at all. |
| No readable passages, or a passage fails the second permission check | `REFUSED_NO_ACCESS_EVIDENCE` with the same sentence; the reason code goes only to the log. |
| Prompt injection in a question or a document | Question and passages are marked as untrusted data, tag-like text is defused, the model has no tools, the output is validated. |

## 6. Infrastructure and operations
| Case | Handling |
|---|---|
| PostgreSQL restarts after an unclean shutdown | Healthcheck, automatic crash recovery, dependent services wait for "healthy". Seen after a forced shutdown: data intact. |
| Redis or the file store is down | Rate limits and the queue are unavailable; the public status page shows the component as down; 503 where the store is needed. |
| Worker stops or is killed | A heartbeat goes stale and the status page shows it; unfinished jobs are re-sent at worker start (visibility timeout 900 s; jobs are idempotent). |
| Audit row cannot be written | **No audit, no answer**: the request fails and nothing is returned. |
| Source sync problems (`TOKEN_MISSING`, `BAD_CREDENTIALS`, `NOT_FOUND`, `RATE_LIMITED`, `SOURCE_UNREACHABLE`, `BAD_ACCESS_FILE`, `TREE_TOO_LARGE`) | An unreachable source changes nothing; an empty listing, or one that would delete more than half of at least 4 documents, stops the run before anything changes; one bad item is counted and the run ends PARTIAL. A fixed message is shown on the Sources screen. |
| Missing file bucket on a brand-new installation | The status check creates the bucket before listing it (found by a clean-machine test, challenge 147). |
| Flaky downloads in CI (Docker Hub 502), noisy speed score on a shared runner | Image downloads retry up to 4 times; the landing page speed is the median of three runs. |

## 7. Retries and fallbacks at a glance
**Fallbacks (another path):** search stays available when answers are not; weak evidence is refused without calling the model; an invalid model reply becomes the uniform refusal; a failed index job leaves the old index answering; an unreachable or suspicious source stops the sync without changes; a failed audit write stops the request.

**Retries:** model service busy or timed out, 1 retry; invalid model reply, 1 retry; worker jobs `STORAGE_ERROR`, `EMBEDDING_ERROR`, `INTERNAL`, up to 3 retries; GitHub server error, 1 retry; CI image downloads, 4 retries (gitleaks image 3); website 401, one refresh.

**No retry (fail at once):** unsupported, empty, scanned, damaged or too large files; wrong password; 429 (the person waits, `Retry-After`).

**Not built (honest):** a second model provider as a fallback, a circuit breaker for the model provider, exponential backoff on API calls (only the CI downloads wait longer each time). See [scale-and-limits.md](scale-and-limits.md).

## 8. How it is tested
Table-driven and mutation tests cover access decisions, the answer validator, audit, sync and the connector (deliberate mistakes were introduced and all relevant ones were caught). More than 730 backend tests and 130 frontend tests run on every pull request in GitHub Actions, including a leak gate ([ci.md](ci.md)).
