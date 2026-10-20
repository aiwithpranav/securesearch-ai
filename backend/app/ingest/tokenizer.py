"""Token counting with the embedding model's own tokenizer, loaded from the baked-in model files."""
import threading
from typing import Any

from app.core.config import settings

_tok: Any = None
_lock = threading.Lock()


def _get() -> Any:
    global _tok
    if _tok is None:
        with _lock:
            if _tok is None:
                from transformers import AutoTokenizer

                _tok = AutoTokenizer.from_pretrained(settings.embedding_model_path, local_files_only=True)
    return _tok


class ModelTokenizer:
    def count(self, texts: list[str]) -> list[int]:
        if not texts:
            return []
        enc = _get()(texts, add_special_tokens=False, truncation=False)["input_ids"]
        return [len(ids) for ids in enc]

    def split(self, text: str, max_tokens: int) -> list[str]:
        tok = _get()
        ids = tok(text, add_special_tokens=False, truncation=False)["input_ids"]
        return [tok.decode(ids[i : i + max_tokens]) for i in range(0, len(ids), max_tokens)]
