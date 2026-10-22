"""Evaluation metrics (pure functions)."""
import math
from collections.abc import Sequence


def recall_at_k(ranked_titles: Sequence[str], expected: Sequence[str] | set[str], k: int) -> float:
    """1.0 when at least one expected document is among the first k distinct documents, else 0.0."""
    seen: list[str] = []
    for t in ranked_titles:
        if t not in seen:
            seen.append(t)
        if len(seen) == k:
            break
    return 1.0 if any(t in seen for t in expected) else 0.0


def reciprocal_rank(ranked_titles: Sequence[str], expected: Sequence[str] | set[str]) -> float:
    """1 / (position of the first expected document among distinct documents), 0.0 when it is not there."""
    seen: list[str] = []
    for t in ranked_titles:
        if t not in seen:
            seen.append(t)
        if t in expected:
            return 1.0 / len(seen)
    return 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (p from 0 to 100). 0.0 for no values."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return float(ordered[rank - 1])


def ratio(good: int, total: int) -> float:
    return good / total if total else 0.0
