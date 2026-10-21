"""Helpers for retrieval tests: write documents' chunks (with real local embeddings) straight into the test database."""
import hashlib
import uuid

from app.embeddings import embed_documents, model_label


def vector_literal(vector):
    return "[" + ",".join(f"{x:.7f}" for x in vector) + "]"


def add_chunks(pg, doc, texts, active=True):
    """Gives a document one version, one job and one chunk per text. Returns the chunk ids in order."""
    version = pg.execute(
        "insert into document_versions (document_id, version_no, content_hash, storage_path, size_bytes, content_type)"
        " values (%s, 1, %s, %s, 1, 'text/plain') returning id",
        (doc, hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest(), f"test/{uuid.uuid4()}"),
    ).fetchone()[0]
    job = pg.execute(
        "insert into ingestion_jobs (document_id, document_version_id, status, content_hash)"
        " values (%s, %s, 'READY', 'x') returning id",
        (doc, version),
    ).fetchone()[0]
    ids = []
    for index, (text, vector) in enumerate(zip(texts, embed_documents(texts), strict=True)):
        ids.append(
            pg.execute(
                "insert into document_chunks (document_id, document_version_id, ingestion_job_id, is_active, chunk_index,"
                " content, token_count, embedding, embedding_model) values (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)"
                " returning id",
                (doc, version, job, active, index, text, len(text.split()), vector_literal(vector), model_label()),
            ).fetchone()[0]
        )
    return ids
