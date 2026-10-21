"""Checks everything the language model returns before any of it leaves the server (OWASP LLM05).

Pure functions with no database and no network, so they are easy to test hard.
A reply is accepted only when: it is the expected JSON object; it cites at least one source; every cited id and every
[S#] marker in the text is a source the model was actually given (so a hallucinated or leaked id blocks the answer);
and the text carries nothing that could exfiltrate data or run in a browser (links, images, HTML, code).
Inline [S#] markers are welcome (they show which sentence came from which source) but not required, because the real
model sometimes lists its sources only in the citations field (found in the live check, challenge 85)."""
import json
import re
from dataclasses import dataclass

MAX_ANSWER_CHARS = 1500

_MARKER = re.compile(r"\[(S\d+)\]")
_UNSAFE = re.compile(r"(https?://|ftp://|www\.|data:|javascript:|!\[|\]\(|<\s*[a-z/!]|```|&#|&lt;)", re.IGNORECASE)
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


@dataclass
class Parsed:
    can_answer: bool
    answer: str
    citations: list[str]


@dataclass
class Verdict:
    ok: bool
    reason: str = ""  # fixed code words, for logs only (the person sees one uniform refusal)


def parse(text: str) -> Parsed | None:
    """The reply as a Parsed object, or None if it is not exactly the expected JSON shape."""
    try:
        data = json.loads(_FENCE.sub("", text.strip()))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or set(data) - {"can_answer", "answer", "citations"}:
        return None
    can, answer, cites = data.get("can_answer"), data.get("answer", ""), data.get("citations", [])
    if not isinstance(can, bool) or not isinstance(answer, str):
        return None
    if not isinstance(cites, list) or not all(isinstance(c, str) for c in cites):
        return None
    return Parsed(can, answer.strip(), [c.strip() for c in cites])


def validate(parsed: Parsed, allowed_ids: set[str]) -> Verdict:
    """allowed_ids are the source ids the model was given, for example {"S1", "S2"}."""
    if not parsed.can_answer:
        return Verdict(True, "MODEL_DECLINED")  # valid reply; the service turns it into a refusal
    if not parsed.answer:
        return Verdict(False, "EMPTY_ANSWER")
    if len(parsed.answer) > MAX_ANSWER_CHARS:
        return Verdict(False, "TOO_LONG")
    if _UNSAFE.search(parsed.answer):
        return Verdict(False, "UNSAFE_OUTPUT")
    if not parsed.citations:
        return Verdict(False, "NO_CITATION")
    cited = set(parsed.citations)
    if not cited <= allowed_ids:
        return Verdict(False, "INVALID_CITATION")
    in_text = set(_MARKER.findall(parsed.answer))
    if not in_text <= allowed_ids:
        return Verdict(False, "INVALID_CITATION")
    return Verdict(True)
