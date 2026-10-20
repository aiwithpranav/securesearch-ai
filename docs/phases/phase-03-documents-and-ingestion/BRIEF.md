# Phase 3 Brief: Documents and ingestion

**Goal:** an administrator uploads a PDF, DOCX, TXT or MD file and the system turns it into text chunks, each with a 384-number vector, without ever damaging the previous good version. No search and no answers yet.

**Requirement IDs:** FR-05 (upload with metadata, type and size checks), FR-06 (parse, chunk, embed, index, show status), FR-33 (in-app notifications for admins on failed ingestion). Also NFR-05 (a failed ingestion never damages the previous valid index, jobs are retryable), NFR-03 (upload type and size limits, default 50 MB), NFR-10 (logs hold IDs, not document text), NFR-06.

## Layers (each one needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **3A** Infrastructure | `storage` service (SeaweedFS), `worker` (Celery), local embedding model in the image, storage adapter, env doctor and setup script updates | Built, merged |
| **3B** Pipeline and API | Migration `0002` (documents, document_versions, document_chunks, ingestion_jobs, notifications), validate, store, parse, chunk, embed, index, atomic activate, admin API | Built, merged |
| **3C** Admin UI | `/admin/documents`: list, upload, document page (edit, re-index, delete, history), notification bell | Built, waiting for owner review |

## Security rules that apply in Phase 3
- Only `system_admin` can upload or manage documents.
- **Admin is not reader:** no endpoint returns chunk text or a preview; the list shows metadata only. Originals cannot be downloaded.
- No ACL exists yet (Phase 4), so every document is invisible to readers (deny by default).
- File type allow-list (extension and magic bytes), size cap, zip-bomb guard for DOCX, safe file names, SHA-256 hash.
- Logs never contain document text.

## Out of scope
Permissions and ACL (Phase 4), search (5), answers (6), new-version upload and incremental sync (8), OCR (blueprint out of scope), file download.

## Estimate
Blueprint: 7 to 10 days. Plan: 3A about 2, 3B about 4, 3C about 2.

## Open design decisions (confirmed by the owner's "start" on 2026-10-20)
1. Embedding model baked into the image at build time (offline at run time).
2. CPU-only PyTorch.
3. Status values: `QUEUED`, `PROCESSING`, `READY`, `FAILED` (blueprint user story US-15; Phase 4 SQL will use `READY`; see ADR 026).
4. `DELETE /documents/{id}` is a soft delete (`deleted_at`).
5. Worker and backend share one image (blueprint 8.6).
6. Storage: SeaweedFS instead of MinIO (CR-001).
