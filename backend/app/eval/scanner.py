"""The canary scanner (blueprint 13.2): "zero leakage" is proven by search, not by reading answers by eye.

For one question asked by one person we know which documents that person must NOT read. Everything that person
could receive or that is recorded about the request (the API answers, the passages, the exact prompt sent to the
model, the audit rows, the logs) is turned into text and searched for:
- the unique canary strings of the forbidden documents,
- the ids of their passages and documents,
- their titles (even the existence of a document you may not read is information).
One single hit fails the whole run. Pure functions: no database, no network."""
from dataclasses import dataclass, field


@dataclass
class Forbidden:
    canaries: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)  # chunk ids and document ids, as text
    titles: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Leak:
    where: str  # the place that held it, for example "chat response" or "model prompt"
    kind: str  # CANARY, ID or TITLE
    token: str


def scan(blobs: dict[str, str], forbidden: Forbidden) -> list[Leak]:
    """Every forbidden token found in any of the named texts."""
    leaks: list[Leak] = []
    for where, text in blobs.items():
        if not text:
            continue
        for token in sorted(forbidden.canaries):
            if token in text:
                leaks.append(Leak(where, "CANARY", token))
        for token in sorted(forbidden.ids):
            if token in text:
                leaks.append(Leak(where, "ID", token))
        lowered = text.lower()
        for token in sorted(forbidden.titles):
            if token.lower() in lowered:
                leaks.append(Leak(where, "TITLE", token))
    return leaks


def scan_without_question(blobs: dict[str, str], forbidden: Forbidden, question: str) -> list[Leak]:
    """Like scan, but the person's own question is removed first: asking about a title is not a leak, repeating a
    forbidden document back to them is. (A question that carries a canary string cannot be blamed on the system.)"""
    cleaned = {where: text.replace(question, "") if question else text for where, text in blobs.items()}
    return scan(cleaned, forbidden)
