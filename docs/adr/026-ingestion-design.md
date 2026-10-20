# ADR 026: Ingestion design decisions (Phase 3B)

## Status
Accepted (2026-10-20). The owner replied "Merged ... keep working the same way" to the 3B plan with its 9 decisions; this was treated as approval and can be reversed.

## Context
The blueprint fixes the big picture (section 8.5: validate, store, parse, chunk, embed, index, activate atomically) and a few words that disagree with each other. This ADR records the details that make it work.

## Decision
- **Status words:** documents and ingestion jobs use `QUEUED -> PROCESSING -> READY` or `FAILED` (blueprint user story US-15). The illustrative SQL in blueprint section 10.3 says `status = 'PUBLISHED'`; Phase 4 will use `READY` there (the SQL is marked "final code is written in Phase 4", so no Change Request).
- **Document status vs job status:** a document that already has an active index stays `READY` while a re-index job runs or fails. It becomes `FAILED` only when it has no active chunks at all.
- **Publishing is ONE database transaction:** lock the document row, switch off the old active chunks, insert the new chunks as active, update the document and job. The blueprint describes "insert inactive, then flip"; one transaction gives the same guarantee (a search sees the complete old set or the complete new set) and a crash can never leave a half-written set. Parsing, chunking and embedding happen before that transaction, so it is short.
- **Chunks belong to a job** (`document_chunks.ingestion_job_id`, an additive column). This is what makes a retry safe: a retried job first deletes its own leftovers; a finished job is never run again.
- **One unfinished job per document**, enforced by a partial unique index (`uq_ingestion_jobs_one_active`). Two re-index clicks cannot create two jobs.
- **Chunking:** about 450 tokens, 50-token overlap made of whole sentences, hard maximum 500 (the model reads 512). Chunks never cross a PDF page or a section heading, so page numbers and sections are exact for citations. Tokens are counted with the embedding model's own tokenizer.
- **Errors:** only fixed codes and fixed texts (`PARSE_ERROR`, `NO_TEXT`, ...). File content never appears in an error, a log line or an API answer. Retryable codes (storage, embedding) are retried up to 3 times; everything else fails at once.
- **Duplicates:** the same file content (SHA-256) cannot be uploaded twice (HTTP 409), unless the first copy was deleted.
- **Worker recovery:** Redis keeps a job "unacknowledged" after the whole worker is killed. The visibility timeout is 900 s (longer than the 660 s job limit) and the worker re-sends every unfinished job when it starts. Both are safe because jobs are idempotent.
- **Soft delete:** `deleted_at` is set and the chunks stop being active. The stored original stays until a cleanup job exists (backlog).

## Addition in 3C
`GET /ingestion/jobs` accepts an optional `document_id` filter so the document page can show its processing history. It is an optional query parameter on an existing endpoint (additive), so no Change Request was needed.

## Consequences
- No endpoint, field or log can reveal document text in Phase 3 (admin is not reader). Tests scan the OpenAPI schema and the logs for this.
- GIN (full-text) and HNSW (vector) indexes are not created yet; they belong to Phase 5. The `tsv` column already exists and is filled by Postgres.
- A re-index of a very large document holds a database transaction while inserting its chunks (seconds); acceptable at the planned scale.
- Scanned PDFs fail with `NO_TEXT` (no OCR, blueprint out of scope).
