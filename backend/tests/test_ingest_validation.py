"""Upload validation: wrong types, fake files, oversize, zip bombs, hostile file names. Pure logic."""
import asyncio
import hashlib
import io
import zipfile

import pytest

from app.core.config import settings
from app.ingest.errors import IngestError
from app.ingest.validation import clean_filename, read_limited, validate_file
from app.scripts import synthetic_docs as sd


def _code(fn, *args):
    with pytest.raises(IngestError) as exc:
        fn(*args)
    return exc.value.code


def test_clean_filename_keeps_only_a_safe_display_name():
    assert clean_filename("../../etc/passwd") == "passwd"
    assert clean_filename("C:\\Users\\x\\report.pdf") == "report.pdf"
    assert clean_filename("bad\x00name\x1f.txt") == "badname.txt"
    assert clean_filename("   ") == "document"
    assert clean_filename(None) == "document"
    assert len(clean_filename("a" * 500 + ".txt")) == 200


@pytest.mark.parametrize("sample", sd.SAMPLES, ids=lambda s: s.filename)
def test_every_synthetic_sample_is_accepted(sample):
    data = sd.build(sample)
    v = validate_file(sample.filename, data)
    assert v.kind == sample.kind and v.size == len(data)
    assert v.sha256 == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("name", ["virus.exe", "noextension", "report.pdf.exe", "image.png", "notes.TXT.zip"])
def test_wrong_extensions_are_rejected(name):
    assert _code(validate_file, name, b"hello") == "UNSUPPORTED_TYPE"


def test_empty_file_is_rejected():
    assert _code(validate_file, "a.txt", b"") == "EMPTY"


def test_file_over_the_limit_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 1000)
    assert _code(validate_file, "a.txt", b"x" * 1001) == "TOO_LARGE"
    assert validate_file("a.txt", b"x" * 1000).size == 1000


def test_files_pretending_to_be_other_types_are_rejected():
    assert _code(validate_file, "a.pdf", b"just some text") == "UNSUPPORTED_TYPE"
    assert _code(validate_file, "a.docx", sd.fake_docx()) == "UNSUPPORTED_TYPE"
    docx_bytes = sd.build(next(s for s in sd.SAMPLES if s.kind == "docx"))
    assert _code(validate_file, "a.pdf", docx_bytes) == "UNSUPPORTED_TYPE"
    assert _code(validate_file, "a.txt", b"binary\x00data") == "UNSUPPORTED_TYPE"
    assert _code(validate_file, "a.md", b"\xff\xfa\xfb not utf8") == "UNSUPPORTED_TYPE"


def test_zip_without_word_document_is_not_a_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "hi")
    assert _code(validate_file, "a.docx", buf.getvalue()) == "UNSUPPORTED_TYPE"


def test_zip_bomb_is_rejected_by_ratio_and_by_total_size(monkeypatch):
    bomb = sd.zip_bomb_docx(uncompressed_mb=20)
    assert len(bomb) < 100_000  # tiny on disk
    assert _code(validate_file, "bomb.docx", bomb) == "TOO_LARGE"  # ratio rule
    monkeypatch.setattr(settings, "max_zip_ratio", 10_000_000)
    monkeypatch.setattr(settings, "max_docx_uncompressed_bytes", 1024 * 1024)
    assert _code(validate_file, "bomb.docx", bomb) == "TOO_LARGE"  # total size rule


def test_utf8_bom_text_is_accepted():
    assert validate_file("a.txt", "\ufeffhello".encode("utf-8")).kind == "txt"


class _FakeUpload:
    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)

    async def read(self, n: int) -> bytes:
        return self._buf.read(n)


def test_read_limited_stops_early_on_a_huge_upload():
    with pytest.raises(IngestError) as exc:
        asyncio.run(read_limited(_FakeUpload(b"x" * 5000), limit=2048))
    assert exc.value.code == "TOO_LARGE"
    assert asyncio.run(read_limited(_FakeUpload(b"x" * 2048), limit=2048)) == b"x" * 2048
