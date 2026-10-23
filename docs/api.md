# API reference

> Generated from the application by `python -m app.scripts.gen_api_docs`. Do not edit by hand: CI fails when this page is out of date.

Interactive documentation with every request and response shape: `/api/docs` (Swagger UI) on a running server, and `/api/openapi.json`.

## Conventions
- **Base path** `/api/v1`. The API only ever grows by adding routes (the contract is frozen).
- **Sign in** with `POST /api/v1/auth/login`; send the returned access token as `Authorization: Bearer <token>`. It lives 15 minutes; a rotating, httpOnly refresh cookie renews it (`POST /api/v1/auth/refresh`). Roles are always read from the database, never from the token.
- **Errors** are Problem Details JSON: `type`, `title`, `status`, `detail` and a `request_id` (also sent as the `X-Request-ID` header). Error text never contains what you sent (passwords, tokens, emails). A refusal for something you may not see looks exactly like "not found".
- **Rate limits** answer `429` with a `Retry-After` header and `retry_after_seconds`.
- **Nothing returns document text except** `POST /search`, `POST /chat` (and its stream) and `GET /chunks/{id}/preview`, and only for documents the caller may read. Administrators manage documents but never receive their content.

## Health and status

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/health` | anyone (public) | Is the server up (for automatic checks). |
| GET | `/ready` | anyone (public) | Are the database and Redis reachable (503 if not). |
| GET | `/status` | anyone (public) | The public status page's data: a name and up or down for each part, and one overall word. |

## Sign in and sessions

| Method | Path | Who may call | What it does |
|---|---|---|---|
| POST | `/auth/change-password` | any signed-in person | Change password |
| POST | `/auth/forgot-password` | anyone (public) | Forgot password |
| POST | `/auth/login` | anyone (public) | Sign in with email and password. |
| POST | `/auth/logout` | anyone (public) | Sign out this device. |
| POST | `/auth/logout-all` | any signed-in person | Sign out every device. |
| GET | `/auth/me` | any signed-in person | The signed-in person's profile. |
| POST | `/auth/refresh` | anyone (public) | Exchange the refresh cookie for a new access token (rotates the cookie). |
| POST | `/auth/reset-password` | anyone (public) | Reset password |

## People, roles and departments

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/departments` | system administrator | List departments |
| GET | `/roles` | system administrator | List roles |
| POST | `/roles` | system administrator | Create role |
| GET | `/users` | system administrator | List users |
| POST | `/users` | system administrator | Create user |
| GET | `/users/{user_id}` | system administrator | Get user |
| PATCH | `/users/{user_id}` | system administrator | Update user |
| POST | `/users/{user_id}/deactivate` | system administrator | Deactivate user |
| POST | `/users/{user_id}/roles` | system administrator | Set user roles |

## Groups

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/groups` | system administrator | List groups |
| POST | `/groups` | system administrator | Create group |
| GET | `/groups/{group_id}` | system administrator | Get group |
| DELETE | `/groups/{group_id}/members` | system administrator | Remove member |
| POST | `/groups/{group_id}/members` | system administrator | Add member |

## Documents and ingestion

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/documents` | system administrator | List documents |
| POST | `/documents/upload` | system administrator | Upload document |
| DELETE | `/documents/{document_id}` | system administrator | Delete document |
| GET | `/documents/{document_id}` | system administrator | Get document |
| POST | `/documents/{document_id}/reindex` | system administrator | Reindex document |
| POST | `/documents/{document_id}/restore` | system administrator | Restore document |
| GET | `/documents/{document_id}/versions` | system administrator | List versions |
| POST | `/documents/{document_id}/versions` | system administrator | A new file for an existing document. |
| GET | `/ingestion/jobs` | system administrator | List jobs |
| GET | `/ingestion/jobs/{job_id}` | system administrator | Get job |

## Groups and access rules

| Method | Path | Who may call | What it does |
|---|---|---|---|
| PATCH | `/documents/{document_id}` | MANAGE on that document (system administrators always) | Edit a document's title, department, type, sensitivity or countries. |
| GET | `/documents/{document_id}/access-preview` | MANAGE on that document (system administrators always) | Access preview |
| GET | `/documents/{document_id}/acl` | MANAGE on that document (system administrators always) | List rules |
| POST | `/documents/{document_id}/acl` | MANAGE on that document (system administrators always) | Add rule |
| GET | `/documents/{document_id}/acl/history` | MANAGE on that document (system administrators always) | Rule history |
| DELETE | `/documents/{document_id}/acl/{rule_id}` | MANAGE on that document (system administrators always) | Delete rule |
| PATCH | `/documents/{document_id}/acl/{rule_id}` | MANAGE on that document (system administrators always) | Update rule |

## Notifications

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/notifications` | any signed-in person | List notifications |
| POST | `/notifications/{notification_id}/read` | any signed-in person | Mark read |

## Search

| Method | Path | Who may call | What it does |
|---|---|---|---|
| POST | `/search` | any signed-in person | Find the passages that match a question, only from documents the caller may read. |

## Answers

| Method | Path | Who may call | What it does |
|---|---|---|---|
| POST | `/chat` | any signed-in person | Ask a question: a short answer with validated sources, or one uniform refusal. |
| POST | `/chat/feedback` | any signed-in person | Rate an answer with a thumbs up or down. |
| POST | `/chat/stream` | any signed-in person | Progress as Server-Sent Events: small `stage` messages, then one `result` with the same shape as /chat. |
| GET | `/chunks/{chunk_id}/preview` | any signed-in person | The passage behind a citation. |
| GET | `/me/search-history` | any signed-in person | List history |
| DELETE | `/me/search-history/{history_id}` | any signed-in person | Delete history item |

## Audit trail

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/audit/access-events` | security administrator or auditor | List access events |
| GET | `/audit/answers` | security administrator or auditor | List answers |
| GET | `/audit/export` | security administrator or auditor | CSV of the query trail (FR-19). |
| GET | `/audit/queries` | security administrator or auditor | List queries |

## Evaluation

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/evaluation/runs` | system administrator | List runs |
| POST | `/evaluation/runs` | system administrator | Start run |
| GET | `/evaluation/runs/{run_id}` | system administrator | Get run |
| GET | `/evaluation/runs/{run_id}/failures` | system administrator | Get failures |

## Dashboards

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/dashboards/admin-overview` | system administrator | Admin overview |
| GET | `/dashboards/knowledge-gaps` | system or security administrator | Knowledge gaps |
| GET | `/me/suggested-questions` | any signed-in person | Suggested questions |

## Sync sources

| Method | Path | Who may call | What it does |
|---|---|---|---|
| GET | `/sync/runs/{run_id}` | system administrator | Get run |
| GET | `/sync/sources` | system administrator | List sources |
| POST | `/sync/sources` | system administrator | Create source |
| PATCH | `/sync/sources/{source_id}` | system administrator | Update source |
| POST | `/sync/sources/{source_id}/run` | system administrator | Run source |
| GET | `/sync/sources/{source_id}/runs` | system administrator | List runs |
