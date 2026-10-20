"""Chunker rules: size limits, overlap, sentence cuts, no crossing of pages or sections."""
from app.ingest.chunker import chunk_blocks
from app.ingest.parsers import Block
from app.ingest.tokenizer import ModelTokenizer


class WordTokenizer:
    """Stand-in tokenizer: one word = one token. Makes the numbers easy to reason about."""

    def count(self, texts):
        return [len(t.split()) for t in texts]

    def split(self, text, max_tokens):
        words = text.split()
        return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), max_tokens)]


TOK = WordTokenizer()


def sentences(n, start=0):
    return " ".join(f"Sentence number {start + i} has some words here." for i in range(n))  # 7 words each


def test_small_document_is_one_chunk():
    chunks = chunk_blocks([Block("One short sentence. And another one.")], TOK, 100, 10, 120)
    assert len(chunks) == 1 and chunks[0].index == 0


def test_chunks_respect_the_maximum_and_are_numbered_in_order():
    chunks = chunk_blocks([Block(sentences(200))], TOK, target=50, overlap=10, max_tokens=60)
    assert len(chunks) > 5
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(0 < c.token_count <= 60 for c in chunks)
    assert all(c.text.strip() for c in chunks)


def test_neighbouring_chunks_overlap_by_whole_sentences():
    chunks = chunk_blocks([Block(sentences(60))], TOK, target=50, overlap=14, max_tokens=60)
    for a, b in zip(chunks, chunks[1:]):
        last_sentence_of_a = a.text.split(". ")[-1].rstrip(".")
        assert last_sentence_of_a in b.text  # repeated at the start of the next chunk


def test_no_chunk_is_only_a_repeat_of_the_previous_overlap():
    chunks = chunk_blocks([Block(sentences(30))], TOK, target=49, overlap=14, max_tokens=60)
    texts = [c.text for c in chunks]
    assert len(set(texts)) == len(texts)
    last_new = f"Sentence number 29"
    assert last_new in texts[-1]
    assert not all(t in texts[-2] for t in [texts[-1]])


def test_chunks_never_cross_sections_or_pages():
    blocks = [
        Block(sentences(20), page=1, section="A"),
        Block(sentences(20, 100), page=1, section="B"),
        Block(sentences(20, 200), page=2, section="B"),
    ]
    chunks = chunk_blocks(blocks, TOK, target=40, overlap=7, max_tokens=50)
    for c in chunks:
        numbers = {int(w) for w in c.text.replace(".", " ").split() if w.isdigit()}
        assert len({n // 100 for n in numbers}) == 1  # only one of the three blocks per chunk
    assert {(c.page, c.section) for c in chunks} == {(1, "A"), (1, "B"), (2, "B")}


def test_one_huge_sentence_is_cut_by_tokens():
    huge = " ".join(f"w{i}" for i in range(500)) + "."  # a single "sentence" of 500 words
    chunks = chunk_blocks([Block(huge)], TOK, target=100, overlap=10, max_tokens=120)
    assert len(chunks) >= 4 and all(c.token_count <= 120 for c in chunks)


def test_paragraph_breaks_are_kept_inside_a_chunk():
    chunks = chunk_blocks([Block("First paragraph here."), Block("Second paragraph here.")], TOK, 100, 10, 120)
    assert chunks[0].text == "First paragraph here.\n\nSecond paragraph here."


def test_empty_input_gives_no_chunks():
    assert chunk_blocks([], TOK) == []


def test_same_input_gives_same_output():
    blocks = [Block(sentences(80), page=1)]
    a = chunk_blocks(blocks, TOK, 50, 10, 60)
    b = chunk_blocks(blocks, TOK, 50, 10, 60)
    assert a == b


def test_real_model_tokenizer_keeps_chunks_under_the_model_limit():
    text = " ".join(
        f"Employees should read policy section {i} carefully before they submit any request to the team." for i in range(300)
    )
    tok = ModelTokenizer()
    chunks = chunk_blocks([Block(text)], tok, target=450, overlap=50, max_tokens=500)
    assert len(chunks) >= 3
    assert all(c.token_count <= 500 for c in chunks)
    assert all(tok.count([c.text])[0] <= 510 for c in chunks)  # real recount; the model reads 512
