"""Local embedding model: 384 numbers, offline, sensible similarity. Loads the real model (a few seconds)."""
import math
import os

from app.core.config import settings
from app.embeddings import QUERY_INSTRUCTION, embed_documents, embed_query, model_label


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_vectors_have_384_numbers_and_unit_length():
    vecs = embed_documents(["Annual leave policy for employees.", "The payments runbook."])
    assert len(vecs) == 2
    for v in vecs:
        assert len(v) == settings.embedding_dimensions == 384
        assert math.isclose(math.sqrt(_dot(v, v)), 1.0, rel_tol=1e-3)


def test_same_text_gives_same_vector_and_empty_input_is_empty():
    a = embed_documents(["hello world"])[0]
    b = embed_documents(["hello world"])[0]
    assert _dot(a, b) > 0.9999
    assert embed_documents([]) == []


def test_similar_meaning_scores_higher_than_unrelated():
    q = embed_query("How many days of annual leave do I get?")
    related = embed_documents(["Employees receive 24 days of paid annual leave each year."])[0]
    unrelated = embed_documents(["The data centre cooling system must be inspected quarterly."])[0]
    assert _dot(q, related) > _dot(q, unrelated) + 0.1


def test_query_uses_instruction_prefix_documents_do_not():
    text = "refund policy"
    plain = embed_documents([text])[0]
    as_query = embed_query(text)
    assert as_query != plain
    assert _dot(embed_documents([QUERY_INSTRUCTION + text])[0], as_query) > 0.9999


def test_model_runs_offline_from_the_image_and_is_labelled():
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.path.isfile(os.path.join(settings.embedding_model_path, "model.safetensors"))
    assert model_label() == "BAAI/bge-small-en-v1.5@5c38ec7"
