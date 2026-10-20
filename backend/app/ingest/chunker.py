"""Cuts text blocks into chunks of about 450 tokens with a 50-token overlap (blueprint: ~500, overlap).

Rules:
- Section-aware: a chunk never crosses a page or section boundary, so its page number and section
  are exact (useful for citations in Phase 6).
- We cut at SENTENCE boundaries. The overlap repeats the last sentences of the previous chunk, so an
  answer that sits on a boundary is still found whole in one of the two chunks.
- A single sentence longer than the hard maximum is split by tokens.
- Tokens are counted with the embedding model's own tokenizer (the model reads 512 tokens at most)."""
import re
from dataclasses import dataclass
from typing import Protocol

from app.ingest.parsers import Block

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class Tokenizer(Protocol):
    def count(self, texts: list[str]) -> list[int]: ...

    def split(self, text: str, max_tokens: int) -> list[str]:
        """Splits one long text into pieces of at most max_tokens tokens."""
        ...


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    page: int | None
    section: str | None
    token_count: int


@dataclass
class _Unit:
    text: str
    tokens: int
    sep: str  # what to put in front when joining ("\n\n" starts a paragraph, " " continues one)


def _units(blocks: list[Block], tok: Tokenizer, max_tokens: int) -> list[_Unit]:
    pieces: list[tuple[str, str]] = []
    for block in blocks:
        sentences = [s for s in _SENTENCE_END.split(block.text) if s.strip()]
        for n, s in enumerate(sentences):
            pieces.append((s.strip(), "\n\n" if n == 0 else " "))
    counts = tok.count([p[0] for p in pieces]) if pieces else []
    units: list[_Unit] = []
    for (text, sep), n in zip(pieces, counts):
        if n <= max_tokens:
            units.append(_Unit(text, n, sep))
        else:  # one enormous "sentence" (for example a table dump): cut it by tokens
            parts = tok.split(text, max_tokens)
            part_counts = tok.count(parts)
            for k, (pt, pn) in enumerate(zip(parts, part_counts)):
                units.append(_Unit(pt, pn, sep if k == 0 else " "))
    return units


def _assemble(units: list[_Unit], target: int, overlap: int, max_tokens: int) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    cur: list[_Unit] = []
    cur_tokens = 0
    new_units = 0  # units in `cur` that were not already part of the previous chunk

    def emit() -> None:
        text = "".join((u.sep if i else "") + u.text for i, u in enumerate(cur))
        out.append((text, cur_tokens))

    for u in units:
        if cur and cur_tokens + u.tokens > target:
            emit()
            tail: list[_Unit] = []
            size = 0
            for x in reversed(cur):  # keep the last sentences as overlap
                if size + x.tokens > overlap:
                    break
                tail.insert(0, x)
                size += x.tokens
            cur, cur_tokens, new_units = tail, size, 0
            if cur_tokens + u.tokens > max_tokens:  # overlap would make the chunk too big: drop it
                cur, cur_tokens = [], 0
        cur.append(u)
        cur_tokens += u.tokens
        new_units += 1
    if cur and new_units:
        emit()
    return out


def chunk_blocks(
    blocks: list[Block], tok: Tokenizer, target: int = 450, overlap: int = 50, max_tokens: int = 500
) -> list[Chunk]:
    """Returns the chunks of a whole document, numbered from 0 in reading order."""
    chunks: list[Chunk] = []
    scope: list[Block] = []
    scope_key: tuple[int | None, str | None] | None = None

    def flush() -> None:
        if not scope:
            return
        for text, tokens in _assemble(_units(scope, tok, max_tokens), target, overlap, max_tokens):
            chunks.append(Chunk(len(chunks), text, scope[0].page, scope[0].section, tokens))
        scope.clear()

    for b in blocks:
        key = (b.page, b.section)
        if key != scope_key:
            flush()
            scope_key = key
        scope.append(b)
    flush()
    return chunks
