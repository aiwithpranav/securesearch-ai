"""Cross-encoder reranker (BAAI/bge-reranker-base, MIT licence).

A cross-encoder reads the question and one passage TOGETHER, so it orders the final candidates better than the
two fast first-stage searches. It only reorders passages that already passed the access check: it never adds any.

- The model files are baked into the Docker image at build time; nothing is downloaded at run time.
- Loaded lazily, once per process.
- Scores are squashed to 0..1 with a sigmoid, so a threshold (Phase 6 refusals) is easy to reason about.
- Tests swap in a fake with set_reranker(), so they stay fast and need no model."""
import math
import threading
from typing import Any, Protocol

import torch

from app.core.config import settings


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self) -> None:
        self._model: Any = None
        self._lock = threading.Lock()

    def _get_model(self) -> Any:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder  # heavy import, so only when needed

                    self._model = CrossEncoder(settings.reranker_model_path, device="cpu", max_length=512)
        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        # Identity: ask for the raw model score (a logit). sentence-transformers would otherwise apply its own
        # sigmoid and ours would then be applied twice, squeezing every score into 0.5 to 0.73.
        raw = self._get_model().predict(
            [(query, p) for p in passages], batch_size=8, show_progress_bar=False, activation_fn=torch.nn.Identity()
        )
        return [1.0 / (1.0 + math.exp(-float(x))) for x in raw]


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def set_reranker(reranker: Reranker | None) -> None:
    """Replace the reranker (tests). Pass None to go back to the real one."""
    global _reranker
    _reranker = reranker
