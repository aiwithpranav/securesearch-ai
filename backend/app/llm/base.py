"""The language model interface. The model is NOT a security layer: it only ever receives text that the access
resolver already allowed, and everything it returns is checked before it leaves the server."""
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings


class LlmError(Exception):
    """The model could not be used. The message is a short fixed code word, never a response body or a key."""


class LlmNotConfigured(LlmError):
    """No API key is set (the owner adds it to .env when answers should be live)."""


@dataclass
class LlmResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class LlmClient(Protocol):
    def complete(self, system: str, user: str, max_output_tokens: int) -> LlmResult: ...


_client: LlmClient | None = None


def get_llm() -> LlmClient:
    global _client
    if _client is None:
        if not settings.openai_api_key or settings.openai_api_key == "CHANGE_ME":
            raise LlmNotConfigured("not_configured")
        from app.llm.openai_client import OpenAiClient

        _client = OpenAiClient(
            api_key=settings.openai_api_key, model=settings.llm_model, base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return _client


def set_llm(client: LlmClient | None) -> None:
    """Replace the client (tests use a fake, so no key and no network are ever needed). None resets it."""
    global _client
    _client = client
