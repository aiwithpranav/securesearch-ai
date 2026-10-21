"""Reciprocal Rank Fusion (RRF): merges ranked lists by adding 1 / (k + rank) for every list an item appears in.

Pure functions, no database: easy to test. Ranks start at 1. Ties are broken by the order of first appearance,
so the result is always the same for the same input."""
from collections.abc import Hashable, Sequence
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def rrf(ranked_lists: Sequence[Sequence[T]], k: int = 60) -> list[tuple[T, float]]:
    """Returns (item, fused score) with the best first."""
    scores: dict[T, float] = {}
    first_seen: dict[T, int] = {}
    for ranked in ranked_lists:
        for position, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + position)
            first_seen.setdefault(item, len(first_seen))
    return sorted(scores.items(), key=lambda pair: (-pair[1], first_seen[pair[0]]))
