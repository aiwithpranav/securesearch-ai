# Phase 6 Brief: Answers and citations

**Goal:** a person asks a question and gets a short answer written only from documents they may read, with citations to the exact passages, or one uniform refusal when the system cannot answer.

**Requirement IDs:** FR-10 (answers from permitted chunks with citations), FR-11 (every citation validated), FR-12 (uniform refusal), FR-18 (history); NFR-01, NFR-10.

## Layers (each needs the owner's approval)
| Layer | Content | Status |
|---|---|---|
| **6A** Engine | LLM adapter (GPT-4o mini and a fake), prompt, answer pipeline, citation validator, refusal policy, ADR 030 | Merged (PR #19) |
| **6B** API | `POST /chat` with the blueprint response shape, `/chat/stream`, evidence preview, rate limit, 503 without a key, search history, feedback | Merged (PR #20) |
| **6C** UI | Answer with citations on the search screen, evidence panel, thumbs, history | Built, waiting for owner review |

## Security rules that apply
- The model is not a security layer: it only sees passages the resolver allowed, marked as data, and has no tools.
- Every citation is checked against the passages the model was given; anything else blocks the answer.
- One refusal text for every reason; reasons are code words in the log only.
- No question or answer text in logs; the API key is never logged, returned or committed.

## Out of scope
Audit dashboard and evaluation (Phase 7), voice input, answer streaming (stage events only, per the blueprint).

## Estimate
Blueprint: 7 to 9 days. Plan: 6A about 3, 6B about 2, 6C about 2.
