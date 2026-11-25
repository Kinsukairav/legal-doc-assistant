"""Document extraction for PDF, DOCX, and plain-text files."""

from __future__ import annotations

import io
from pathlib import Path

import docx
import pdfplumber
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})


class ExtractionError(Exception):
    """Base error raised when document text cannot be extracted."""


class UnsupportedFileTypeError(ExtractionError):
    """Raised when the input file extension is not supported."""


class EmptyDocumentError(ExtractionError):
    """Raised when no extractable text is found (e.g., scanned PDF without OCR)."""


def _extract_pdf(data: bytes, filename: str) -> list[str]:
    """Extract text page-by-page from PDF bytes via pdfplumber."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise ExtractionError(f"Failed to parse PDF '{filename}': {exc}") from exc

    if not any(page.strip() for page in pages):
        raise EmptyDocumentError(
            f"No extractable text found in '{filename}'. "
            "It is likely a scanned PDF; OCR is out of scope."
        )
    return pages


def _extract_table_text(table: Table) -> list[str]:
    """Extract table row text in order while deduplicating merged cells."""
    lines: list[str] = []
    for row in table.rows:
        seen_tcs: set[int] = set()
        cells: list[str] = []
        for cell in row.cells:
            tc_id = id(cell._tc)
            if tc_id in seen_tcs:
                continue
            seen_tcs.add(tc_id)
            cell_text = " ".join(part.strip() for part in cell.text.splitlines() if part.strip())
            if cell_text:
                cells.append(cell_text)
        if cells:
            lines.append(" | ".join(cells))
    return lines


def _extract_docx(data: bytes, filename: str) -> list[str]:
    """Extract paragraphs and tables in document order from DOCX bytes."""
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Failed to parse DOCX '{filename}': {exc}") from exc

    blocks: list[str] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            text = Paragraph(child, document).text.strip()
            if text:
                blocks.append(text)
        elif isinstance(child, CT_Tbl):
            blocks.extend(_extract_table_text(Table(child, document)))

    full_text = "\n\n".join(blocks)
    if not full_text.strip():
        raise EmptyDocumentError(f"DOCX file '{filename}' contains no extractable text.")
    return [full_text]


def _extract_txt(data: bytes, filename: str) -> list[str]:
    """Decode plain-text bytes using UTF-8 with Latin-1 fallback."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    if not text.strip():
        raise EmptyDocumentError(f"Text file '{filename}' is empty.")
    return [text]


def extract_pages(data: bytes, filename: str) -> list[str]:
    """Extract text pages from raw document bytes.

    Args:
        data: Raw file contents.
        filename: File name or path used to determine the extension.

    Returns:
        List of page strings (one string per page for PDFs; single-item list
        for DOCX and TXT).

    Raises:
        UnsupportedFileTypeError: If the file extension is not ``.pdf``,
            ``.docx``, or ``.txt``.
        EmptyDocumentError: If the extracted text is empty (e.g., scanned PDF).
        ExtractionError: If parsing the file fails.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext or '<none>'}' for '{filename}'. "
            f"Supported types: {supported}."
        )

    if not data:
        raise EmptyDocumentError(f"Input file '{filename}' is empty (0 bytes).")

    if ext == ".pdf":
        return _extract_pdf(data, filename)
    if ext == ".docx":
        return _extract_docx(data, filename)
    return _extract_txt(data, filename)
