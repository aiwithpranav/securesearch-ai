"""Local text embeddings with BAAI/bge-small-en-v1.5 (384 numbers per text).

- The model files are baked into the Docker image at build time and loaded from disk.
  Nothing is downloaded at run time and no text leaves the machine.
- The model is loaded lazily, once per process, because loading takes a few seconds.
- Vectors are normalised to length 1, so cosine similarity is just a dot product.

bge models expect a fixed instruction in front of SEARCH QUERIES (not in front of documents):
use embed_query() for questions and embed_documents() for chunks."""
import threading
from typing import Any

from app.core.config import settings

QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: Any = None
_lock = threading.Lock()


def model_label() -> str:
    """Stored next to every vector, so we always know which model made it."""
    return f"{settings.embedding_model_name}@{settings.embedding_model_revision[:7]}"


def _get_model() -> Any:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer  # heavy import, so only when needed

                _model = SentenceTransformer(settings.embedding_model_path, device="cpu")
                dims = _model.get_embedding_dimension()
                if dims != settings.embedding_dimensions:
                    raise RuntimeError(f"Embedding model has {dims} dimensions, expected {settings.embedding_dimensions}.")
    return _model


def _encode(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _get_model().encode(
        texts,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [[float(x) for x in v] for v in vectors]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embeds chunks of documents (no instruction prefix)."""
    return _encode(texts)


def embed_query(text: str) -> list[float]:
    """Embeds one search question (with the bge instruction prefix)."""
    return _encode([QUERY_INSTRUCTION + text])[0]
