"""The ingestion pipeline end to end, in this process, with the real database, real storage and the real
embedding model. (The Celery worker container uses the dev database, so it is tested separately.)"""
import logging
import uuid

import pytest

from app.core.config import settings
from app.ingest.pipeline import MAX_ATTEMPTS, run_ingestion
from app.scripts import synthetic_docs as sd
from app.storage import get_storage

LABEL = "BAAI/bge-small-en-v1.5@5c38ec7"


def _upload(api, admin, name, data, **fields):
    r = api.upload(admin, name, data, **fields)
    assert r.status_code == 202, r.text
    d = r.json()
    return d["id"], uuid.UUID(d["latest_job"]["id"])


def _chunks(pg, doc_id, active=None):
    q = "select count(*) from document_chunks where document_id=%s"
    if active is not None:
        q += " and is_active = %s"
        return pg.execute(q, (doc_id, active)).fetchone()[0]
    return pg.execute(q, (doc_id,)).fetchone()[0]


def _ready(api, admin, pg, enqueued, name="leave-policy.md"):
    s = next(x for x in sd.SAMPLES if x.filename == name)
    doc_id, job = _upload(api, admin, s.filename, sd.build(s), sensitivity_level=s.sensitivity)
    assert run_ingestion(job) == "READY"
    return doc_id, job


# ---------------------------------------------------------------- every kind of file

@pytest.mark.parametrize("sample", sd.SAMPLES, ids=lambda s: s.filename)
def test_each_synthetic_document_becomes_chunks_with_vectors(api, admin, enqueued, pg, sample):
    doc_id, job = _upload(api, admin, sample.filename, sd.build(sample), sensitivity_level=sample.sensitivity)
    assert run_ingestion(job) == "READY"

    status, current = pg.execute("select status, current_version_id is not null from documents").fetchone()
    assert (status, current) == ("READY", True)
    jstatus, err = pg.execute("select status, error_code from ingestion_jobs").fetchone()
    assert (jstatus, err) == ("READY", None)

    n = _chunks(pg, doc_id)
    assert n >= 1 and _chunks(pg, doc_id, active=True) == n
    dims, models, tsv_ok, tokens = pg.execute(
        "select min(vector_dims(embedding)), count(distinct embedding_model), bool_and(tsv is not null), max(token_count) "
        "from document_chunks"
    ).fetchone()
    assert dims == 384 and models == 1 and tsv_ok and tokens <= settings.chunk_max_tokens
    assert pg.execute("select embedding_model from document_chunks limit 1").fetchone()[0] == LABEL

    if sample.canary:  # the marker made it into the index, which is exactly why it must stay protected
        hits = pg.execute("select count(*) from document_chunks where content like %s", (f"%{sample.canary}%",)).fetchone()[0]
        assert hits >= 1
    detail = api.request("GET", f"/documents/{doc_id}", token=admin)
    assert detail.json()["chunk_count"] == n and detail.json()["status"] == "READY"
    assert (sample.canary or "no-canary") not in detail.text


def test_chunk_metadata_matches_the_file_type(api, admin, enqueued, pg):
    for name in ("fy2026-budget-forecast.pdf", "leave-policy.md", "holiday-calendar-2026.txt"):
        s = next(x for x in sd.SAMPLES if x.filename == name)
        doc_id, job = _upload(api, admin, s.filename, sd.build(s))
        assert run_ingestion(job) == "READY"
        pages, sections = pg.execute(
            "select count(page_number), count(section) from document_chunks where document_id=%s", (doc_id,)
        ).fetchone()
        n = _chunks(pg, doc_id)
        if name.endswith(".pdf"):
            assert pages == n and sections == 0
        elif name.endswith(".md"):
            assert sections == n and pages == 0
        else:
            assert pages == 0 and sections == 0


# ---------------------------------------------------------------- failures leave things clean

def test_corrupt_pdf_fails_cleanly_with_a_notification(api, admin, enqueued, pg):
    doc_id, job = _upload(api, admin, "broken.pdf", sd.corrupt_pdf())  # passes the upload checks (has %PDF-)
    assert run_ingestion(job) == "FAILED"
    jstatus, code, msg = pg.execute("select status, error_code, error_message from ingestion_jobs").fetchone()
    assert (jstatus, code) == ("FAILED", "PARSE_ERROR") and "garbage" not in msg
    assert pg.execute("select status from documents").fetchone()[0] == "FAILED"
    assert _chunks(pg, doc_id) == 0
    note = pg.execute("select kind, payload->>'error_code', payload->>'document_id' from notifications").fetchall()
    assert note == [("INGESTION_FAILED", "PARSE_ERROR", doc_id)]
    listed = api.request("GET", "/notifications", token=admin).json()
    assert len(listed) == 1 and listed[0]["kind"] == "INGESTION_FAILED"


def test_scanned_pdf_has_a_clear_no_text_failure(api, admin, enqueued, pg):
    _, job = _upload(api, admin, "scan.pdf", sd.scanned_like_pdf())
    assert run_ingestion(job) == "FAILED"
    assert pg.execute("select error_code from ingestion_jobs").fetchone()[0] == "NO_TEXT"


def test_missing_original_and_tampered_original_fail(api, admin, enqueued, pg):
    s = next(x for x in sd.SAMPLES if x.filename == "leave-policy.md")
    _, job1 = _upload(api, admin, s.filename, sd.build(s))
    storage = get_storage()
    (key,) = storage.list_keys("documents/")
    storage.delete(key)
    assert run_ingestion(job1) == "FAILED"
    assert pg.execute("select error_code from ingestion_jobs").fetchone()[0] == "STORAGE_ERROR"

    s2 = next(x for x in sd.SAMPLES if x.filename == "payments-runbook.md")
    _, job2 = _upload(api, admin, s2.filename, sd.build(s2))
    key2 = [k for k in storage.list_keys("documents/")][0]
    storage.put_bytes(key2, b"# someone changed this file\n\nafter it was stored")
    assert run_ingestion(job2) == "FAILED"
    assert pg.execute("select error_code from ingestion_jobs where id=%s", (job2,)).fetchone()[0] == "INTEGRITY_ERROR"


def test_deleted_document_is_not_processed_and_causes_no_alert(api, admin, enqueued, pg):
    doc_id, job = _upload(api, admin, "a.txt", b"some text to process")
    api.request("DELETE", f"/documents/{doc_id}", token=admin)
    assert run_ingestion(job) == "FAILED"
    assert pg.execute("select error_code from ingestion_jobs").fetchone()[0] == "DELETED"
    assert _chunks(pg, doc_id) == 0
    assert pg.execute("select count(*) from notifications").fetchone()[0] == 0


def test_failed_reindex_keeps_the_previous_index_active(api, admin, enqueued, pg):
    doc_id, _ = _ready(api, admin, pg, enqueued)
    old_ids = {r[0] for r in pg.execute("select id from document_chunks where document_id=%s", (doc_id,)).fetchall()}
    assert old_ids

    r = api.request("POST", f"/documents/{doc_id}/reindex", token=admin)
    assert r.status_code == 202
    job2 = uuid.UUID(r.json()["id"])

    def boom(texts):
        raise RuntimeError("model crashed")

    results = [run_ingestion(job2, embed=boom) for _ in range(MAX_ATTEMPTS)]
    assert results == ["RETRY", "RETRY", "FAILED"]
    assert pg.execute("select status, error_code from ingestion_jobs where id=%s", (job2,)).fetchone() == ("FAILED", "EMBEDDING_ERROR")
    still = {r[0] for r in pg.execute("select id from document_chunks where document_id=%s and is_active", (doc_id,)).fetchall()}
    assert still == old_ids  # the old, good chunks were never touched
    assert _chunks(pg, doc_id, active=False) == 0 and pg.execute("select status from documents").fetchone()[0] == "READY"
    assert pg.execute("select count(*) from notifications").fetchone()[0] == 1


def test_reindex_swaps_the_whole_set_atomically(api, admin, enqueued, pg):
    doc_id, _ = _ready(api, admin, pg, enqueued)
    n = _chunks(pg, doc_id, active=True)
    old_ids = {r[0] for r in pg.execute("select id from document_chunks where document_id=%s", (doc_id,)).fetchall()}
    job2 = uuid.UUID(api.request("POST", f"/documents/{doc_id}/reindex", token=admin).json()["id"])

    seen_during_embedding: list[int] = []

    def watching_embed(texts):
        # While the new set is being computed, searchers must still see the complete OLD set.
        seen_during_embedding.append(_chunks(pg, doc_id, active=True))
        from app.embeddings import embed_documents
        return embed_documents(texts)

    assert run_ingestion(job2, embed=watching_embed) == "READY"
    assert seen_during_embedding == [n]
    new_ids = {r[0] for r in pg.execute("select id from document_chunks where document_id=%s", (doc_id,)).fetchall()}
    assert len(new_ids) == n and not (new_ids & old_ids)  # a complete new set replaced the old one
    assert _chunks(pg, doc_id, active=True) == n and _chunks(pg, doc_id, active=False) == 0


# ---------------------------------------------------------------- safe to run twice

def test_running_a_finished_job_again_changes_nothing(api, admin, enqueued, pg):
    doc_id, job = _ready(api, admin, pg, enqueued)
    ids = {r[0] for r in pg.execute("select id from document_chunks").fetchall()}
    assert run_ingestion(job) == "SKIPPED"
    assert {r[0] for r in pg.execute("select id from document_chunks").fetchall()} == ids


def test_a_job_that_was_interrupted_midway_can_be_run_again_without_duplicates(api, admin, enqueued, pg):
    s = next(x for x in sd.SAMPLES if x.filename == "leave-policy.md")
    doc_id, job = _upload(api, admin, s.filename, sd.build(s))
    # Pretend a worker claimed the job, wrote a stray chunk, then died.
    pg.execute("update ingestion_jobs set status='PROCESSING', attempt=1 where id=%s", (job,))
    version_id = pg.execute("select id from document_versions").fetchone()[0]
    pg.execute(
        "insert into document_chunks (document_id, document_version_id, ingestion_job_id, is_active, chunk_index, content,"
        " token_count, embedding, embedding_model) values (%s,%s,%s,false,0,'stray',1,%s::vector,'x')",
        (doc_id, version_id, job, "[" + ",".join(["0"] * 384) + "]"),
    )
    assert run_ingestion(job) == "READY"
    texts = [r[0] for r in pg.execute("select content from document_chunks where document_id=%s", (doc_id,)).fetchall()]
    assert "stray" not in texts and len(texts) == len(set(texts)) >= 1
    assert pg.execute("select attempt from ingestion_jobs").fetchone()[0] == 2


def test_database_allows_only_one_unfinished_job_per_document(api, admin, enqueued, pg):
    import psycopg

    doc_id, _ = _upload(api, admin, "a.txt", b"some text to process")
    version_id = pg.execute("select id from document_versions").fetchone()[0]
    with pytest.raises(psycopg.errors.UniqueViolation):
        pg.execute(
            "insert into ingestion_jobs (document_id, document_version_id, status, content_hash) values (%s,%s,'QUEUED','h')",
            (doc_id, version_id),
        )


# ---------------------------------------------------------------- privacy

def test_logs_never_contain_document_text(api, admin, enqueued, pg, caplog):
    caplog.set_level(logging.DEBUG)
    s = next(x for x in sd.SAMPLES if x.filename == "salary-bands-2026.docx")
    _, ok_job = _upload(api, admin, s.filename, sd.build(s), sensitivity_level=3)
    run_ingestion(ok_job)
    _, bad_job = _upload(api, admin, "broken.pdf", sd.corrupt_pdf() + s.canary.encode())
    run_ingestion(bad_job)
    logged = "\n".join(f"{r.getMessage()} {getattr(r, 'fields', '')}" for r in caplog.records)
    assert s.canary not in logged and "Band L1" not in logged and "garbage" not in logged
    stored_errors = " ".join(str(r) for r in pg.execute("select error_message from ingestion_jobs").fetchall())
    assert s.canary not in stored_errors
