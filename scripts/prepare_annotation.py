"""Prepare gold annotation templates from raw documents in data/raw/."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from legalassist.config import DATA_GOLD, DATA_RAW
from legalassist.ingestion.clean import clean_pages
from legalassist.ingestion.extract import (
    SUPPORTED_EXTENSIONS,
    ExtractionError,
    extract_pages,
)
from legalassist.segmentation.doctype import detect_doc_type
from legalassist.segmentation.segment import segment_clauses

_DEFAULT_QA_TEMPLATE: dict[str, Any] = {
    "questions": [
        {
            "q": "",
            "answerable": True,
            "evidence_clause_ids": [],
            "gold_answer": "",
        }
    ]
}


@dataclass(frozen=True)
class PrepareReport:
    """Summary of files processed by :func:`prepare_annotations`."""

    processed_docs: list[str]
    skipped_annotated: list[str]
    failed_files: list[tuple[str, str]]


def _has_clause_annotations(path: Path) -> bool:
    """Return True if an existing clauses JSON contains any non-empty tags."""
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True  # Preserve unreadable/manually-edited file rather than overwriting.
    clauses = payload.get("clauses", [])
    if not isinstance(clauses, list):
        return True
    return any(bool(clause.get("tags")) for clause in clauses if isinstance(clause, dict))


def _has_qa_annotations(path: Path) -> bool:
    """Return True if an existing QA JSON contains any user-written questions/answers."""
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    questions = payload.get("questions", [])
    if not isinstance(questions, list) or len(questions) != 1:
        return True
    first = questions[0]
    if not isinstance(first, dict):
        return True
    return any(
        [
            bool(str(first.get("q", "")).strip()),
            bool(str(first.get("gold_answer", "")).strip()),
            bool(first.get("evidence_clause_ids")),
            first.get("answerable") is False,
        ]
    )


def _has_summary_annotations(path: Path) -> bool:
    """Return True if an existing summary text file is non-empty."""
    if not path.is_file():
        return False
    return bool(path.read_text(encoding="utf-8").strip())


def prepare_annotations(
    raw_dir: Path = DATA_RAW,
    gold_dir: Path = DATA_GOLD,
) -> PrepareReport:
    """Extract, clean, and segment files in ``raw_dir`` into ``gold_dir`` templates.

    Creates ``<doc_id>.clauses.json``, ``<doc_id>.qa.json``, and
    ``<doc_id>.summary.txt`` where ``doc_id`` is the filename stem. Files that
    already contain annotations are never overwritten.

    Args:
        raw_dir: Directory containing source documents.
        gold_dir: Target directory for gold annotation files.

    Returns:
        :class:`PrepareReport` detailing processed, skipped, and failed files.
    """
    gold_dir.mkdir(parents=True, exist_ok=True)
    if not raw_dir.is_dir():
        return PrepareReport(processed_docs=[], skipped_annotated=[], failed_files=[])

    processed_docs: list[str] = []
    skipped_annotated: list[str] = []
    failed_files: list[tuple[str, str]] = []

    for src_path in sorted(raw_dir.iterdir()):
        if not src_path.is_file() or src_path.name.startswith("."):
            continue
        if src_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        doc_id = src_path.stem
        clauses_path = gold_dir / f"{doc_id}.clauses.json"
        qa_path = gold_dir / f"{doc_id}.qa.json"
        summary_path = gold_dir / f"{doc_id}.summary.txt"

        clauses_annotated = _has_clause_annotations(clauses_path)
        qa_annotated = _has_qa_annotations(qa_path)
        summary_annotated = _has_summary_annotations(summary_path)

        if not clauses_annotated:
            try:
                pages = extract_pages(src_path.read_bytes(), src_path.name)
                cleaned = clean_pages(pages)
                doc_type, _ = detect_doc_type(cleaned)
                clauses = segment_clauses(cleaned)
            except ExtractionError as exc:
                failed_files.append((src_path.name, str(exc)))
                continue

            clauses_payload = {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "clauses": [
                    {
                        "id": clause.id,
                        "number": clause.number,
                        "text": clause.text,
                        "tags": [],
                    }
                    for clause in clauses
                ],
            }
            clauses_path.write_text(
                json.dumps(clauses_payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            skipped_annotated.append(clauses_path.name)

        if not qa_annotated:
            qa_path.write_text(
                json.dumps(_DEFAULT_QA_TEMPLATE, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            skipped_annotated.append(qa_path.name)

        if not summary_annotated:
            summary_path.write_text("", encoding="utf-8")
        else:
            skipped_annotated.append(summary_path.name)

        processed_docs.append(doc_id)

    return PrepareReport(
        processed_docs=processed_docs,
        skipped_annotated=skipped_annotated,
        failed_files=failed_files,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate annotation templates in data/gold/ from documents in data/raw/."
    )
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW, help="Raw files directory.")
    parser.add_argument("--gold-dir", type=Path, default=DATA_GOLD, help="Gold output directory.")
    args = parser.parse_args(argv)

    report = prepare_annotations(raw_dir=args.raw_dir, gold_dir=args.gold_dir)
    print(f"Processed documents ({len(report.processed_docs)}): {', '.join(report.processed_docs) or 'none'}")
    if report.skipped_annotated:
        print(f"Preserved annotated files ({len(report.skipped_annotated)}): {', '.join(report.skipped_annotated)}")
    if report.failed_files:
        for fname, err in report.failed_files:
            print(f"Failed '{fname}': {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
