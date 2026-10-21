"""Request and response shapes for POST /search (Phase 5B).

This is the ONLY response in the API that carries document text, and only text of documents the caller may read."""
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.retrieval.search import MAX_QUERY_CHARS


class SearchRequest(BaseModel):
    query: str = Field(max_length=MAX_QUERY_CHARS * 4)  # real limit checked below, after trimming
    mode: Literal["keyword", "vector", "hybrid"] | None = None  # None = the server default

    @field_validator("query")
    @classmethod
    def _query_rules(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Enter a question or some words to search for.")
        if len(value) > MAX_QUERY_CHARS:
            raise ValueError(f"Keep the question under {MAX_QUERY_CHARS} characters.")
        return value


class HitOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int | None = None
    section: str | None = None
    content: str
    score: float
    scores: dict[str, float] | None = None  # every signal; only for system_admin (to tune and debug)


class SearchResponse(BaseModel):
    mode: str
    count: int
    took_ms: int
    hits: list[HitOut]
