"""Tests for M2 clause segmentation, doc-type detection, and scripts.analyze."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from legalassist.ingestion.clean import clean_pages
from legalassist.ingestion.extract import extract_pages
from legalassist.segmentation.doctype import detect_doc_type
from legalassist.segmentation.segment import llm_segment_fallback, segment_clauses

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_fixture(name: str) -> str:
    raw = (FIXTURES_DIR / name).read_bytes()
    pages = extract_pages(raw, name)
    return clean_pages(pages)


def test_rental_agreement_segmentation_and_doctype() -> None:
    """Rental fixture segments into 15 hierarchical clauses and detects rental_agreement."""
    text = _load_fixture("rental_agreement.txt")
    doc_type, conf = detect_doc_type(text)
    assert doc_type == "rental_agreement"
    assert conf > 0.6

    clauses = segment_clauses(text)
    assert len(clauses) == 15

    numbers = [c.number for c in clauses]
    assert numbers == [
        "1",
        "2",
        "2.1",
        "2.2",
        "3",
        "3.1",
        "3.1.1",
        "3.2",
        "3.2(a)",
        "3.2(b)",
        "3.2(b)(i)",
        "3.2(b)(ii)",
        "Clause 4",
        "Section 5",
        None,
    ]
    assert clauses[-1].heading == "GOVERNING LAW AND EVICTION"
    for c in clauses:
        assert text[c.start : c.end] == c.text


def test_terms_of_service_segmentation_and_doctype() -> None:
    """ToS fixture segments into 15 clauses with nested numbers and detects terms_of_service."""
    text = _load_fixture("terms_of_service.txt")
    doc_type, conf = detect_doc_type(text)
    assert doc_type == "terms_of_service"
    assert conf > 0.6

    clauses = segment_clauses(text)
    assert len(clauses) == 15

    numbers = [c.number for c in clauses]
    assert numbers == [
        "1",
        "2",
        "2.1",
        "2.2",
        "3",
        "3.1",
        "3.1.1",
        "4",
        "4(a)",
        "4(b)",
        "4(b)(i)",
        "4(b)(ii)",
        "Clause 5",
        "Article 6",
        None,
    ]
    assert clauses[-1].heading == "LIMITATION OF LIABILITY"


def test_government_notice_segmentation_and_doctype() -> None:
    """Notice fixture segments into 15 clauses and detects government_notice."""
    text = _load_fixture("government_notice.txt")
    doc_type, conf = detect_doc_type(text)
    assert doc_type == "government_notice"
    assert conf > 0.6

    clauses = segment_clauses(text)
    assert len(clauses) == 15

    numbers = [c.number for c in clauses]
    assert numbers == [
        "1",
        "1.1",
        "1.1.1",
        "2",
        "2.1",
        "2.1(a)",
        "2.1(b)",
        "2.1(b)(i)",
        "2.1(b)(ii)",
        "3",
        "Clause 4",
        "Section 5",
        "Section 5.1",
        "Article 6",
        None,
    ]
    assert clauses[-1].heading == "SIGNATORY AND OFFICE SEAL"


def test_doctype_unknown_for_unrelated_or_empty_text() -> None:
    """Unrelated or blank text yields 'unknown' with zero confidence."""
    assert detect_doc_type("") == ("unknown", 0.0)
    doc_type, conf = detect_doc_type("The weather tomorrow will be sunny with light winds.")
    assert doc_type == "unknown"
    assert conf == 0.0


def test_long_clause_split_at_sentence_boundaries() -> None:
    """Clauses exceeding 1200 chars are split at sentence boundaries."""
    sentence = "The Tenant shall keep the premises clean and promptly report plumbing leaks to the Landlord."
    long_body = " ".join([sentence] * 20)  # ~1800 chars
    text = f"1. Maintenance.\n{long_body}\n2. Inspection. Monthly visits require 24 hours notice."

    clauses = segment_clauses(text)
    clause_1_chunks = [c for c in clauses if c.number == "1"]
    assert len(clause_1_chunks) >= 2
    assert all(len(c.text) <= 1200 for c in clause_1_chunks)
    assert all(c.heading == "Maintenance" for c in clause_1_chunks)
    assert clauses[-1].number == "2"


def test_paragraph_fallback_when_no_numbering() -> None:
    """Unnumbered prose falls back to paragraph splitting."""
    text = (
        "First paragraph explaining general background context without numbering.\n\n"
        "Second paragraph stating payment procedures and timelines clearly.\n\n"
        "Third paragraph describing dispute resolution contacts."
    )
    clauses = segment_clauses(text)
    assert len(clauses) == 3
    assert all(c.number is None and c.heading is None for c in clauses)
    assert clauses[0].text.startswith("First paragraph")
    assert clauses[2].text.startswith("Third paragraph")


def test_llm_segment_fallback_not_implemented() -> None:
    """llm_segment_fallback raises NotImplementedError until Step 5."""
    with pytest.raises(NotImplementedError):
        llm_segment_fallback("Sample unnumbered text.")


def test_analyze_cli_json_output() -> None:
    """`python -m scripts.analyze <file>` prints valid JSON with doc_type, count, clauses."""
    fixture = FIXTURES_DIR / "rental_agreement.txt"
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.analyze", str(fixture)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["doc_type"] == "rental_agreement"
    assert payload["clause_count"] == 15
    assert len(payload["clauses"]) == 15
    assert payload["clauses"][8]["number"] == "3.2(a)"
