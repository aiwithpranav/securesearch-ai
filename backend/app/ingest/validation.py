"""Checks an uploaded file BEFORE anything is stored or parsed (NFR-03).

We never trust the file name or the browser's content type. We look at the real bytes ("magic bytes")
and check that they match the extension. Rules:
- only .pdf .docx .txt .md (the LAST extension counts, so report.pdf.exe is rejected)
- not empty, not bigger than the size limit
- PDF starts with %PDF-
- DOCX is a real zip with word/document.xml and is not a zip bomb (tiny file that expands hugely)
- TXT/MD are valid UTF-8 text without NUL bytes (a renamed binary file is rejected)"""
import hashlib
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass

from app.core.config import settings
from app.ingest.errors import IngestError

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "md"}
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
}


@dataclass(frozen=True)
class ValidatedFile:
    kind: str  # pdf | docx | txt | md
    data: bytes
    sha256: str
    size: int
    content_type: str
    filename: str  # cleaned, for display only


def clean_filename(raw: str | None) -> str:
    """Keeps only the last path part, removes control characters, limits the length.
    The result is only ever DISPLAYED. It is never used as a path or as a storage key."""
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in unicodedata.normalize("NFC", name) if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name[:200] or "document"


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def _check_docx(data: bytes) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise IngestError("UNSUPPORTED_TYPE") from None
    with zf:
        infos = zf.infolist()
        if len(infos) > settings.max_zip_entries:
            raise IngestError("TOO_LARGE")
        names = {i.filename for i in infos}
        if "word/document.xml" not in names or "[Content_Types].xml" not in names:
            raise IngestError("UNSUPPORTED_TYPE")
        total = 0
        for i in infos:
            total += i.file_size
            if total > settings.max_docx_uncompressed_bytes:
                raise IngestError("TOO_LARGE")
            if i.file_size > 0 and i.compress_size > 0 and i.file_size / i.compress_size > settings.max_zip_ratio:
                raise IngestError("TOO_LARGE")
            if i.file_size > 1024 * 1024 and i.compress_size == 0:
                raise IngestError("TOO_LARGE")


def _check_text(data: bytes) -> None:
    if b"\x00" in data:
        raise IngestError("UNSUPPORTED_TYPE")
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise IngestError("UNSUPPORTED_TYPE") from None


def validate_file(filename: str | None, data: bytes) -> ValidatedFile:
    name = clean_filename(filename)
    kind = ALLOWED_EXTENSIONS.get(_extension(name))
    if kind is None:
        raise IngestError("UNSUPPORTED_TYPE")
    if len(data) == 0:
        raise IngestError("EMPTY")
    if len(data) > settings.max_upload_bytes:
        raise IngestError("TOO_LARGE")

    if kind == "pdf":
        if b"%PDF-" not in data[:1024]:
            raise IngestError("UNSUPPORTED_TYPE")
    elif kind == "docx":
        _check_docx(data)
    else:
        _check_text(data)

    return ValidatedFile(
        kind=kind,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        content_type=CONTENT_TYPES[kind],
        filename=name,
    )


async def read_limited(upload, limit: int | None = None) -> bytes:
    """Reads an uploaded file in 1 MB pieces and stops as soon as it is too big,
    so a huge upload cannot fill the server's memory."""
    limit = limit or settings.max_upload_bytes
    parts: list[bytes] = []
    total = 0
    while True:
        piece = await upload.read(1024 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > limit:
            raise IngestError("TOO_LARGE")
        parts.append(piece)
    return b"".join(parts)
