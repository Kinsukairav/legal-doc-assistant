"""CLI script to extract, clean, classify, and segment a document to JSON."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

# Allow running via `python -m scripts.analyze <file>` without editable install.
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from legalassist.ingestion.clean import clean_pages
from legalassist.ingestion.extract import ExtractionError, extract_pages
from legalassist.segmentation.doctype import detect_doc_type
from legalassist.segmentation.segment import segment_clauses


def analyze_file(file_path: Path) -> dict[str, object]:
    """Run extraction, cleaning, doc-type detection, and segmentation on a file."""
    data = file_path.read_bytes()
    pages = extract_pages(data, file_path.name)
    cleaned = clean_pages(pages)
    doc_type, confidence = detect_doc_type(cleaned)
    clauses = segment_clauses(cleaned)
    return {
        "filename": file_path.name,
        "doc_type": doc_type,
        "confidence": confidence,
        "clause_count": len(clauses),
        "clauses": [dataclasses.asdict(clause) for clause in clauses],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze a legal document (.pdf, .docx, .txt) and output clauses as JSON."
    )
    parser.add_argument("file", type=Path, help="Path to the input document.")
    args = parser.parse_args(argv)

    file_path: Path = args.file
    if not file_path.is_file():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 1

    try:
        result = analyze_file(file_path)
    except ExtractionError as exc:
        print(f"Extraction error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
