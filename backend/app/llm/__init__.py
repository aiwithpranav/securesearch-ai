"""Language model adapter (Phase 6): one small interface, so the model can be swapped (ADR 016)."""
from app.llm.base import LlmClient, LlmError, LlmNotConfigured, LlmResult, get_llm, set_llm

__all__ = ["LlmClient", "LlmError", "LlmNotConfigured", "LlmResult", "get_llm", "set_llm"]
