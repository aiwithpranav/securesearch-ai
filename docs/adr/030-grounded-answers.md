# ADR 030: Grounded answers, citations and refusals (Phase 6)

## Status
Accepted (2026-10-22). The owner approved the Phase 6 plan ("Plan ok, 6A suru"). The owner can reverse any item.

## Context
Blueprint sections 9 and 9.5, FR-10 to FR-12 and ADR 016: answers come only from permitted passages, carry citations, every citation is validated, and the system refuses in one uniform way when it cannot answer. The language model is not a security layer.

## Decision
- **Order of work:** retrieval with the allow-list first (ADR 028); a second check of every chosen document with the access resolver; a confidence check on the reranker score; the model call; validation of the reply; the response. Nothing the model wrote leaves the server before validation has passed.
- **Confidence:** if even the best passage scores below `ANSWER_MIN_SCORE` (0.03, provisional, tuned in Phase 7) the system refuses WITHOUT calling the model. Only passages at or above that score go to the model, at most 6.
- **Model:** GPT-4o mini behind one small interface (`app/llm`). Temperature 0, JSON output, 500 output tokens at most, no tools or functions, one retry for a busy service, then a short error. The API key is read from `.env` only, never logged, never in an error or `repr`, and given to the backend container only (not the worker). Without a key `/ask` (6B) will answer 503 and everything else works.
- **Prompt (data, not instructions):** the question and every passage sit inside `<question>` and `<sources>` blocks; the system prompt says they are untrusted data. Text that looks like our tags is defused so a document or a question cannot close a block or fake a source.
- **Reply contract:** exactly one JSON object `{"can_answer", "answer", "citations"}`. The validator blocks the answer when: the shape is wrong; `can_answer` is true without a citation; a cited id or an inline `[S#]` marker was not given to the model (a hallucinated or leaked id); the text contains a link, image, HTML, code or is over 1,500 characters. A malformed or invalid reply gets one retry, then the refusal.
- **Inline markers are optional.** The first live check showed the real model lists its sources in `citations` but often leaves out `[S1]` in the sentence, so requiring markers refused every answer. The citations field is the checked contract; markers are accepted and validated when present.
- **One refusal text for every reason:** "Could not find enough accessible source material to answer this question." Statuses follow the blueprint (`ANSWERED`, `REFUSED_NO_ACCESS_EVIDENCE`, `REFUSED_LOW_CONFIDENCE`); the reason (a code word) goes to the log, never to the person. A restricted topic and a missing topic give the same status and text.
- **Citations returned:** source id, chunk id, document id and title, section, page, a snippet of at most 240 characters and the document's updated time. Only the passages the answer actually cites.

## Addition in 6B
- Routes follow the blueprint contract: `POST /chat`, `POST /chat/stream`, `POST /chat/feedback`, `GET /chunks/{id}/preview`, `GET /me/search-history`, `DELETE /me/search-history/{id}`. Additive response fields: `history_id` (so feedback can name an answer) and `refusal` (the one uniform text).
- Signed in is enough to ask; 10 answers per minute per person; no key or a model failure gives one 503 ("Answers are not available right now. You can still search.") and nothing is saved.
- **History** (`search_history`) belongs to the person: question, outcome and cited passage ids, never the answer text, so an answer cannot outlive the permission it was built on. They can delete items; feedback (`chat_feedback`, one rating per answer) is deleted with them. The audit log for security staff is separate (Phase 7). The blueprint's feedback table points at an audit row; here it points at the history item, because the audit tables do not exist yet.
- **Preview** re-checks READ on every call; every not-allowed case, including an administrator without a rule, gives the same 404.
- **Stream:** stage events only (search with the person's own readable-document count, writing the answer, checking the sources), then one result. No answer text before validation.
- The question and the answer are never logged; one `chat` event holds ids, status, a reason code, token counts and time.

## How it is proven
- 83 new tests with a fake model (no key, no cost): validator rules; prompt defusing; the OpenAI client over a fake network (request shape, key never in repr or errors, retry once, short error codes); the pipeline (forbidden text never in the prompt, uniform refusals, model not called for weak or empty evidence, second wall, injected document and question, malformed replies); random worlds against the Phase 4 oracle (the model, the answer and the citations only ever hold oracle-allowed documents).
- Mutation check: 11 deliberate mistakes (invalid ids allowed, links allowed, no citation required, no length limit, tags not defused, untrusted-data rule dropped, weak evidence not refused, second wall removed, all passages cited, extra retry) are all caught.
- Live check with the real model on the synthetic demo documents (8 questions, about $0.0005): correct cited answers, restricted and unknown topics refused without calling the model, the injection document answered normally while its instruction was ignored.

## Consequences
- Answer quality depends on retrieval and on the threshold; both are measured in Phase 7.
- Each answer costs a few tenths of a cent at most; the spend limit at the provider is the real safety net.
- Chunks the person may read leave the machine to the provider (synthetic data only in this project; ADR 016).
