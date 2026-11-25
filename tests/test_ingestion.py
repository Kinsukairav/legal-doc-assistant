"""Tests for M1 document extraction and cleaning."""

from __future__ import annotations

import io

import docx
import pytest

from legalassist.ingestion.clean import clean_pages
from legalassist.ingestion.extract import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_pages,
)


def _build_minimal_pdf(page_texts: list[str]) -> bytes:
    """Construct a valid minimal multi-page PDF with Helvetica text streams."""
    objects: list[bytes] = []

    # 1: Catalog, 2: Pages, 3: Font
    page_ids: list[int] = []
    next_id = 4
    content_ids: list[int] = []
    for _ in page_texts:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2

    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>\nendobj\n".encode(
            "ascii"
        )
    )
    objects.append(
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for text, pid, cid in zip(page_texts, page_ids, content_ids):
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_str = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped}) Tj\nET\n"
        stream_bytes = stream_str.encode("latin-1")
        page_obj = (
            f"{pid} 0 obj\n<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {cid} 0 R >>\nendobj\n"
        ).encode("ascii")
        content_obj = (
            f"{cid} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        )
        objects.append(page_obj)
        objects.append(content_obj)

    header = b"%PDF-1.4\n"
    offsets: list[int] = []
    body = bytearray(header)
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)

    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for off in offsets:
        body.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    body.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(body)


def test_extract_txt_utf8_and_latin1() -> None:
    """TXT extraction handles UTF-8 (with BOM) and falls back to Latin-1."""
    utf8_bytes = "\ufeff1. Clause one — café".encode("utf-8")
    assert extract_pages(utf8_bytes, "notice.txt") == ["1. Clause one — café"]

    latin1_bytes = "1. Clause one - § 10".encode("latin-1")
    pages = extract_pages(latin1_bytes, "legacy.TXT")
    assert len(pages) == 1
    assert "§ 10" in pages[0]


def test_extract_docx_with_table_in_order() -> None:
    """DOCX extraction preserves paragraphs and table cell text in document order."""
    document = docx.Document()
    document.add_paragraph("1. Parties. Agreement between Landlord and Tenant.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Monthly Rent"
    table.cell(0, 1).text = "Rs. 22,000"
    table.cell(1, 0).text = "Security Deposit"
    table.cell(1, 1).text = "Rs. 44,000"
    document.add_paragraph("2. Lock-in Period. Six months from signing.")

    buf = io.BytesIO()
    document.save(buf)

    pages = extract_pages(buf.getvalue(), "lease.docx")
    assert len(pages) == 1
    text = pages[0]

    idx_p1 = text.index("1. Parties.")
    idx_tbl = text.index("Monthly Rent | Rs. 22,000")
    idx_tbl2 = text.index("Security Deposit | Rs. 44,000")
    idx_p2 = text.index("2. Lock-in Period.")
    assert idx_p1 < idx_tbl < idx_tbl2 < idx_p2


def test_extract_pdf_pages() -> None:
    """PDF extraction returns one string per page via pdfplumber."""
    pdf_bytes = _build_minimal_pdf(["Page one clause text", "Page two clause text"])
    pages = extract_pages(pdf_bytes, "sample.pdf")
    assert len(pages) == 2
    assert "Page one clause text" in pages[0]
    assert "Page two clause text" in pages[1]


def test_extract_errors_empty_and_unsupported() -> None:
    """Empty documents and unsupported file types raise clear custom errors."""
    with pytest.raises(UnsupportedFileTypeError):
        extract_pages(b"hello", "scan.png")

    with pytest.raises(EmptyDocumentError):
        extract_pages(b"   \n\t  ", "blank.txt")

    empty_doc = docx.Document()
    buf = io.BytesIO()
    empty_doc.save(buf)
    with pytest.raises(EmptyDocumentError):
        extract_pages(buf.getvalue(), "blank.docx")

    blank_pdf = _build_minimal_pdf([""])
    with pytest.raises(EmptyDocumentError):
        extract_pages(blank_pdf, "scanned.pdf")


def test_clean_pages_headers_page_numbers_dehyphenation_and_unicode() -> None:
    """clean_pages removes repeated headers/footers and page numbers while keeping clauses."""
    pages = [
        (
            "ACME LEGAL CORP - CONFIDENTIAL\n"
            "1. Definitions\n"
            "This \u201cagree-\nment\u201d governs all obliga-\ntions\u2014including rent.\n"
            "Page 1 of 3\n"
            "Internal Footer v2"
        ),
        (
            "ACME LEGAL CORP - CONFIDENTIAL\n"
            "2. Payment Terms\n"
            "2.1 Tenant\u2019s rent is due on the 5th.\n"
            "- 2 -\n"
            "Internal Footer v2"
        ),
        (
            "ACME LEGAL CORP - CONFIDENTIAL\n"
            "3. Termination\n"
            "Either party may give 30 days notice.\n"
            "Page 3 of 3\n"
            "Unique End Note"
        ),
    ]

    cleaned = clean_pages(pages)
    assert "ACME LEGAL CORP - CONFIDENTIAL" not in cleaned
    assert "Internal Footer v2" not in cleaned
    assert "Page 1 of 3" not in cleaned
    assert "- 2 -" not in cleaned
    assert "Page 3 of 3" not in cleaned

    # Unique footer appearing on only 1/3 (<=50%) pages is preserved.
    assert "Unique End Note" in cleaned

    # De-hyphenation and unicode normalization
    assert '"agreement"' in cleaned
    assert "obligations-including" in cleaned
    assert "Tenant's rent" in cleaned

    # Clause numbering preserved
    assert "1. Definitions" in cleaned
    assert "2. Payment Terms" in cleaned
    assert "2.1 Tenant's rent" in cleaned
    assert "3. Termination" in cleaned


def test_clean_pages_single_page_preserved() -> None:
    """Single-page text must not be stripped by the >50% repeated-line heuristic."""
    single = ["1. Single Clause\nAll obligations remain intact."]
    assert clean_pages(single) == "1. Single Clause\nAll obligations remain intact."
