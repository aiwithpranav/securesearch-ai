"""Turns a file into text blocks. A block is one paragraph with the page and section it belongs to.

PDF: one set of blocks per page (page number kept). DOCX: headings become sections. MD: '#' lines become
sections. TXT: paragraphs separated by blank lines. No OCR: a PDF made of images has no text and fails
with NO_TEXT (blueprint: OCR is out of scope)."""
import io
import re
from dataclasses import dataclass

from app.core.config import settings
from app.ingest.errors import IngestError

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class Block:
    text: str
    page: int | None = None
    section: str | None = None


def _clean(text: str) -> str:
    """Postgres cannot store NUL characters; also drop other control characters and tidy spaces."""
    text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t ]+", " ", text).strip()


def _paragraphs(text: str) -> list[str]:
    return [p for p in (_clean(p.replace("\n", " ")) for p in re.split(r"\n\s*\n", text)) if p]


def parse_txt(data: bytes) -> list[Block]:
    return [Block(p) for p in _paragraphs(data.decode("utf-8-sig"))]


_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")


def parse_md(data: bytes) -> list[Block]:
    blocks: list[Block] = []
    section: str | None = None
    buf: list[str] = []
    in_code = False

    def flush() -> None:
        if buf:
            for p in _paragraphs("\n".join(buf)):
                blocks.append(Block(p, section=section))
            buf.clear()

    for line in data.decode("utf-8-sig").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            buf.append(line)
            continue
        m = None if in_code else _MD_HEADING.match(line)
        if m:
            flush()
            section = _clean(m.group(1)) or section
            blocks.append(Block(section or "", section=section))  # the heading itself is searchable text
        elif not line.strip() and not in_code:
            buf.append("")
        else:
            buf.append(line)
    flush()
    return [b for b in blocks if b.text]


def parse_docx(data: bytes) -> list[Block]:
    try:
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        doc = Document(io.BytesIO(data))
    except Exception:
        raise IngestError("PARSE_ERROR") from None

    blocks: list[Block] = []
    section: str | None = None
    try:
        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                para = Paragraph(child, doc)
                text = _clean(para.text)
                if not text:
                    continue
                style = (para.style.name if para.style is not None else "") or ""
                if style.startswith("Heading") or style == "Title":
                    section = text
                blocks.append(Block(text, section=section))
            elif tag == "tbl":
                table = Table(child, doc)
                for row in table.rows:
                    cells = [_clean(c.text) for c in row.cells]
                    line = " | ".join(c for c in cells if c)
                    if line:
                        blocks.append(Block(line, section=section))
    except Exception:
        raise IngestError("PARSE_ERROR") from None
    return blocks


def parse_pdf(data: bytes) -> list[Block]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    raise IngestError("PARSE_ERROR")
            except Exception:
                raise IngestError("PARSE_ERROR") from None
        page_count = len(reader.pages)
    except IngestError:
        raise
    except Exception:
        raise IngestError("PARSE_ERROR") from None

    if page_count > settings.max_pdf_pages:
        raise IngestError("TOO_LARGE")

    blocks: list[Block] = []
    total = 0
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            raise IngestError("PARSE_ERROR") from None
        total += len(text)
        if total > settings.max_extracted_chars:
            raise IngestError("TOO_LARGE")
        for p in _paragraphs(text):
            blocks.append(Block(p, page=number))
    return blocks


def parse(kind: str, data: bytes) -> list[Block]:
    """Parses a validated file. Raises IngestError (NO_TEXT, PARSE_ERROR, TOO_LARGE...)."""
    parsers = {"pdf": parse_pdf, "docx": parse_docx, "txt": parse_txt, "md": parse_md}
    if kind not in parsers:
        raise IngestError("UNSUPPORTED_TYPE")
    try:
        blocks = parsers[kind](data)
    except IngestError:
        raise
    except RecursionError:
        raise IngestError("PARSE_ERROR") from None
    except Exception:
        raise IngestError("PARSE_ERROR") from None
    if sum(len(b.text) for b in blocks) > settings.max_extracted_chars:
        raise IngestError("TOO_LARGE")
    if not any(b.text.strip() for b in blocks):
        raise IngestError("NO_TEXT")
    return blocks
