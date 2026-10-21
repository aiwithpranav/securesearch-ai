"""Phase 5A: authorized hybrid retrieval.

Two kinds of checks:
1. Behaviour: each search mode finds the right text, odd input never crashes, the reranker only ever sees allowed text.
2. Safety: in many random worlds, every mode returns ONLY chunks of documents the independent Python oracle says
   the person may read, and the keyword mode returns ALL of them. Ranking can never widen access."""
import pytest

from app.core.config import settings
from app.db.sync import SyncSession
from app.retrieval import search
from app.retrieval.fusion import rrf
from app.retrieval.reranker import set_reranker
from tests.access_world import World
from tests.retrieval_world import add_chunks
from tests.test_access_oracle import build_random_world, load, oracle

MODES = ("keyword", "vector", "hybrid")

VPN = "Employees connect to the company network through the VPN client and approve each login on their phone."
LEAVE = "Annual leave requests are approved by the line manager and must be filed two weeks in advance."
ROCKET = "The rocket engine test stand measures thrust in kilonewtons during every static fire."


class FakeReranker:
    """Scores by word overlap, and remembers every passage it was asked to score."""

    def __init__(self):
        self.seen = []

    def score(self, query, passages):
        self.seen.extend(passages)
        words = set(query.lower().split())
        return [len(words & set(p.lower().split())) / 10 for p in passages]


@pytest.fixture(autouse=True)
def fake_reranker():
    fake = FakeReranker()
    set_reranker(fake)
    yield fake
    set_reranker(None)


def run(user, query, **kwargs):
    with SyncSession() as s:
        return search.retrieve(s, user, query, **kwargs)


def readable_world(pg):
    """One reader and three documents the reader may read."""
    w = World(pg)
    reader = w.user(clearance=2, roles=("employee",))
    docs = {}
    for name, text in (("vpn", VPN), ("leave", LEAVE), ("rocket", ROCKET)):
        d = w.doc(sensitivity=1, filename=f"{name}.txt")
        w.acl(d, ("ROLE", "employee"))
        add_chunks(pg, d, [text])
        docs[name] = d
    return w, reader, docs


# ---------------------------------------------------------------- fusion (pure)

def test_rrf_adds_one_over_k_plus_rank_for_every_list():
    fused = dict(rrf([["a", "b"], ["b", "c"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["c"] == pytest.approx(1 / 62)


def test_rrf_ranks_items_found_by_both_lists_first_and_is_deterministic():
    result = rrf([["x", "a", "b"], ["y", "b", "a"]])
    assert {item for item, _ in result[:2]} == {"a", "b"}
    assert rrf([["x", "a", "b"], ["y", "b", "a"]]) == result  # same input, same output


def test_rrf_handles_empty_input():
    assert rrf([]) == []
    assert rrf([[], []]) == []
    assert [i for i, _ in rrf([["a"], []])] == ["a"]


# ---------------------------------------------------------------- behaviour

def test_keyword_mode_finds_the_exact_words(pg):
    _, reader, docs = readable_world(pg)
    hits = run(reader, "rocket thrust", mode="keyword")
    assert [h.document_id for h in hits] == [docs["rocket"]]


def test_vector_mode_finds_meaning_without_shared_words(pg):
    _, reader, docs = readable_world(pg)
    hits = run(reader, "how do I log in to the corporate network remotely", mode="vector")
    assert hits and hits[0].document_id == docs["vpn"]


def test_hybrid_mode_combines_both_and_explains_its_scores(pg):
    _, reader, docs = readable_world(pg)
    hits = run(reader, "VPN login phone", mode="hybrid")
    assert hits[0].document_id == docs["vpn"]
    assert {"keyword_rank", "vector_rank", "rrf_score", "rerank_score"} <= set(hits[0].scores)
    assert hits[0].document_title == "vpn.txt" and hits[0].content == VPN


def test_rerank_default_is_hybrid_only_and_can_be_forced(pg, fake_reranker):
    _, reader, _ = readable_world(pg)
    run(reader, "VPN login", mode="keyword")
    run(reader, "VPN login", mode="vector")
    assert fake_reranker.seen == []
    run(reader, "VPN login", mode="hybrid")
    assert fake_reranker.seen
    seen_before = len(fake_reranker.seen)
    run(reader, "VPN login", mode="hybrid", rerank=False)
    assert len(fake_reranker.seen) == seen_before


def test_the_reranker_reorders_the_candidates(pg):
    _, reader, docs = readable_world(pg)
    set_reranker(type("Reverse", (), {"score": lambda self, q, ps: [1.0 if "rocket" in p else 0.0 for p in ps]})())
    hits = run(reader, "VPN login rocket thrust leave", mode="hybrid")
    assert hits[0].document_id == docs["rocket"]
    assert hits[0].score == 1.0


def test_unknown_mode_is_refused(pg):
    _, reader, _ = readable_world(pg)
    with pytest.raises(ValueError):
        run(reader, "vpn", mode="magic")


@pytest.mark.parametrize("query", ["", "   ", "the", "!!! ???", '"unclosed quote', "a & | ! ( ) :*", "'; drop table users; --", "x" * 5000])
@pytest.mark.parametrize("mode", MODES)
def test_odd_queries_never_crash(pg, query, mode):
    _, reader, _ = readable_world(pg)
    assert isinstance(run(reader, query, mode=mode), list)


def test_final_k_limits_the_result(pg):
    w = World(pg)
    reader = w.user(clearance=2, roles=("employee",))
    d = w.doc()
    w.acl(d, ("ROLE", "employee"))
    add_chunks(pg, d, [f"policy paragraph number {i} about travel expenses" for i in range(12)])
    assert len(run(reader, "travel expenses", mode="keyword", final_k=5)) == 5
    assert len(run(reader, "travel expenses", mode="keyword")) == settings.retrieval_final_k


def test_inactive_chunks_are_never_returned(pg):
    w = World(pg)
    reader = w.user(clearance=2, roles=("employee",))
    d = w.doc()
    w.acl(d, ("ROLE", "employee"))
    add_chunks(pg, d, ["old superseded wording about holidays"], active=False)
    for mode in MODES:
        assert run(reader, "holidays", mode=mode) == []


# ---------------------------------------------------------------- safety: nothing outside the allow-list

def forbidden_world(pg):
    """The best match for the question is in a document the reader may NOT read, in every way we know."""
    w = World(pg)
    reader = w.user(clearance=1, country="IN", roles=("employee",), groups=("g1",))
    text = "confidential salary revision budget for the executive team"
    cases = {}
    cases["no_rule"] = w.doc()
    cases["denied"] = w.doc()
    w.acl(cases["denied"], ("ROLE", "employee"))
    w.acl(cases["denied"], ("USER", reader), effect="DENY")
    cases["too_sensitive"] = w.doc(sensitivity=3)
    w.acl(cases["too_sensitive"], ("ROLE", "employee"))
    cases["wrong_country"] = w.doc(countries=["US"])
    w.acl(cases["wrong_country"], ("ROLE", "employee"))
    cases["expired"] = w.doc()
    w.acl(cases["expired"], ("ROLE", "employee"), expires="-1 hour")
    cases["deleted"] = w.doc(deleted=True)
    w.acl(cases["deleted"], ("ROLE", "employee"))
    cases["processing"] = w.doc(status="QUEUED")
    w.acl(cases["processing"], ("ROLE", "employee"))
    for d in cases.values():
        add_chunks(pg, d, [text])
    return w, reader, cases, text


@pytest.mark.parametrize("mode", MODES)
def test_no_search_mode_returns_text_the_reader_may_not_see(pg, mode, fake_reranker):
    _, reader, cases, text = forbidden_world(pg)
    assert run(reader, text, mode=mode) == []
    assert not any("salary" in p for p in fake_reranker.seen)  # the reranker never saw it either


@pytest.mark.parametrize("mode", MODES)
def test_every_blocking_rule_blocks_search_and_each_gate_is_what_blocks(pg, mode):
    w, reader, cases, text = forbidden_world(pg)
    # lift one gate at a time: exactly the document that gate was blocking appears
    pg.execute("update users set clearance_level=3 where id=%s", (reader,))
    assert {h.document_id for h in run(reader, text, mode=mode)} == {cases["too_sensitive"]}
    w.acl(cases["no_rule"], ("COMPANY", None))
    assert {h.document_id for h in run(reader, text, mode=mode)} == {cases["too_sensitive"], cases["no_rule"]}
    pg.execute("delete from document_acl where document_id=%s and effect='DENY'", (cases["denied"],))
    assert {h.document_id for h in run(reader, text, mode=mode)} == {
        cases["too_sensitive"], cases["no_rule"], cases["denied"]}


@pytest.mark.parametrize("mode", MODES)
def test_revoking_access_takes_effect_on_the_very_next_search(pg, mode):
    w, reader, docs = readable_world(pg)
    assert run(reader, "VPN login phone", mode=mode)
    w.acl(docs["vpn"], ("USER", reader), effect="DENY")
    assert all(h.document_id != docs["vpn"] for h in run(reader, "VPN login phone", mode=mode))


def test_an_inactive_user_and_an_admin_without_a_rule_find_nothing(pg):
    w, reader, docs = readable_world(pg)
    pg.execute("update users set is_active=false where id=%s", (reader,))
    admin = w.user(clearance=4, roles=("system_admin",))
    for mode in MODES:
        assert run(reader, "VPN login phone", mode=mode) == []
        assert run(admin, "VPN login phone", mode=mode) == []  # admin is not a reader


def test_the_vector_search_still_fills_the_result_when_most_rows_are_forbidden(pg):
    """pgvector filters after the index scan. With iterative scan the allowed rows are still found."""
    w = World(pg)
    reader = w.user(clearance=2, roles=("employee",))
    other = w.doc()
    add_chunks(pg, other, [f"hidden storage tank pressure reading {i}" for i in range(60)])  # forbidden, closest
    mine = w.doc()
    w.acl(mine, ("ROLE", "employee"))
    add_chunks(pg, mine, ["tank pressure notes for the operators", "cafeteria menu for next week"])
    hits = run(reader, "storage tank pressure reading", mode="vector")
    assert hits and {h.document_id for h in hits} == {mine}


# ---------------------------------------------------------------- safety: random worlds against the oracle

@pytest.mark.parametrize("seed", range(6))
def test_in_random_worlds_every_mode_returns_only_what_the_oracle_allows(pg, seed, monkeypatch):
    monkeypatch.setattr(settings, "retrieval_final_k", 100)
    monkeypatch.setattr(settings, "retrieval_fts_limit", 100)
    monkeypatch.setattr(settings, "retrieval_vector_limit", 100)
    monkeypatch.setattr(settings, "retrieval_rerank_candidates", 100)
    users, docs = build_random_world(pg, seed)
    chunk_doc = {}
    for d in docs:
        for cid in add_chunks(pg, d, ["quarterly zebra planning notes", "zebra migration budget summary"]):
            chunk_doc[cid] = d
    data = load(pg)
    returned = allowed_total = 0
    for u in users:
        expected = {d for d in docs if oracle(data, u, d, "READ")}
        for mode in MODES:
            got = {h.chunk_id for h in run(u, "zebra planning budget", mode=mode)}
            assert {chunk_doc[c] for c in got} <= expected, ("LEAK", mode, u)
            if mode == "keyword":  # the search words are in every chunk, so nothing allowed may be missing
                assert {chunk_doc[c] for c in got} == expected, ("MISSING", mode, u)
            returned += len(got)
        allowed_total += len(expected)
    assert allowed_total > 0 and returned > 0  # the worlds really mix allowed and forbidden documents
