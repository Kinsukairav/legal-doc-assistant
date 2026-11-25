"""Tests for Step 2 corpus manifest, prepare_annotation, corpus_stats, and annotator."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.corpus_stats import compute_corpus_stats, format_stats_report
from scripts.prepare_annotation import prepare_annotations

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def test_prepare_annotation_creates_templates_from_synthetic_fixtures(tmp_path: Path) -> None:
    """prepare_annotations creates clauses, qa, and summary templates per raw file."""
    raw_dir = tmp_path / "raw"
    gold_dir = tmp_path / "gold"
    raw_dir.mkdir()

    for name in ("rental_agreement.txt", "terms_of_service.txt", "government_notice.txt"):
        shutil.copy(FIXTURES_DIR / name, raw_dir / name)

    # Dotfiles and unsupported extensions should be skipped gracefully.
    (raw_dir / ".gitkeep").write_text("", encoding="utf-8")
    (raw_dir / "ignored.md").write_text("notes", encoding="utf-8")

    report = prepare_annotations(raw_dir=raw_dir, gold_dir=gold_dir)
    assert report.failed_files == []
    assert report.skipped_annotated == []
    assert report.processed_docs == [
        "government_notice",
        "rental_agreement",
        "terms_of_service",
    ]

    expected_types = {
        "government_notice": "government_notice",
        "rental_agreement": "rental_agreement",
        "terms_of_service": "terms_of_service",
    }
    for doc_id, expected_type in expected_types.items():
        clauses_data = json.loads((gold_dir / f"{doc_id}.clauses.json").read_text(encoding="utf-8"))
        assert set(clauses_data.keys()) == {"doc_id", "doc_type", "clauses"}
        assert clauses_data["doc_id"] == doc_id
        assert clauses_data["doc_type"] == expected_type
        assert len(clauses_data["clauses"]) == 15
        for clause in clauses_data["clauses"]:
            assert set(clause.keys()) == {"id", "number", "text", "tags"}
            assert clause["tags"] == []

        qa_data = json.loads((gold_dir / f"{doc_id}.qa.json").read_text(encoding="utf-8"))
        assert qa_data == {
            "questions": [
                {
                    "q": "",
                    "answerable": True,
                    "evidence_clause_ids": [],
                    "gold_answer": "",
                }
            ]
        }

        summary_text = (gold_dir / f"{doc_id}.summary.txt").read_text(encoding="utf-8")
        assert summary_text == ""


def test_prepare_annotation_never_overwrites_existing_annotations(tmp_path: Path) -> None:
    """Re-running prepare_annotations preserves existing clause tags, QA pairs, and summaries."""
    raw_dir = tmp_path / "raw"
    gold_dir = tmp_path / "gold"
    raw_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "rental_agreement.txt", raw_dir / "rent_01.txt")

    prepare_annotations(raw_dir=raw_dir, gold_dir=gold_dir)

    clauses_path = gold_dir / "rent_01.clauses.json"
    clauses_data = json.loads(clauses_path.read_text(encoding="utf-8"))
    clauses_data["clauses"][0]["tags"] = ["obligation"]
    clauses_path.write_text(json.dumps(clauses_data, indent=2), encoding="utf-8")

    qa_path = gold_dir / "rent_01.qa.json"
    annotated_qa = {
        "questions": [
            {
                "q": "What is the monthly rent?",
                "answerable": True,
                "evidence_clause_ids": ["c6"],
                "gold_answer": "Rs. 22,000 per month.",
            }
        ]
    }
    qa_path.write_text(json.dumps(annotated_qa, indent=2), encoding="utf-8")

    summary_path = gold_dir / "rent_01.summary.txt"
    summary_text = "Plain-language summary written by annotator."
    summary_path.write_text(summary_text, encoding="utf-8")

    report = prepare_annotations(raw_dir=raw_dir, gold_dir=gold_dir)
    assert set(report.skipped_annotated) == {
        "rent_01.clauses.json",
        "rent_01.qa.json",
        "rent_01.summary.txt",
    }

    assert json.loads(clauses_path.read_text(encoding="utf-8"))["clauses"][0]["tags"] == [
        "obligation"
    ]
    assert json.loads(qa_path.read_text(encoding="utf-8")) == annotated_qa
    assert summary_path.read_text(encoding="utf-8") == summary_text


def test_prepare_annotation_cli(tmp_path: Path) -> None:
    """`python -m scripts.prepare_annotation` processes custom directories cleanly."""
    raw_dir = tmp_path / "raw"
    gold_dir = tmp_path / "gold"
    raw_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "terms_of_service.txt", raw_dir / "tos_01.txt")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.prepare_annotation",
            "--raw-dir",
            str(raw_dir),
            "--gold-dir",
            str(gold_dir),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "tos_01" in proc.stdout
    assert (gold_dir / "tos_01.clauses.json").is_file()


def test_corpus_stats_counts_and_flags_unannotated(tmp_path: Path) -> None:
    """corpus_stats computes per-doc, total, and per-tag counts and flags empty docs."""
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()

    (gold_dir / "rent_01.clauses.json").write_text(
        json.dumps(
            {
                "doc_id": "rent_01",
                "doc_type": "rental_agreement",
                "clauses": [
                    {"id": "c1", "number": "1", "text": "Pay by 5th.", "tags": ["obligation", "deadline"]},
                    {"id": "c2", "number": "2", "text": "Late fee applies.", "tags": ["penalty"]},
                    {"id": "c3", "number": "3", "text": "Definitions.", "tags": []},
                ],
            }
        ),
        encoding="utf-8",
    )
    (gold_dir / "gov_01.clauses.json").write_text(
        json.dumps(
            {
                "doc_id": "gov_01",
                "doc_type": "government_notice",
                "clauses": [
                    {"id": "c1", "number": "1", "text": "Clause A.", "tags": []},
                    {"id": "c2", "number": "2", "text": "Clause B.", "tags": []},
                    {"id": "c3", "number": "3", "text": "Clause C.", "tags": []},
                    {"id": "c4", "number": "4", "text": "Clause D.", "tags": []},
                ],
            }
        ),
        encoding="utf-8",
    )

    stats = compute_corpus_stats(gold_dir=gold_dir)
    assert stats.total_clauses == 7
    assert stats.total_annotated_clauses == 2
    assert stats.tag_counts == {"obligation": 1, "right": 0, "deadline": 1, "penalty": 1}
    assert stats.unannotated_docs == ["gov_01"]

    report_text = format_stats_report(stats)
    assert "rent_01 (rental_agreement): 2/3 annotated" in report_text
    assert "gov_01 (government_notice): 0/4 annotated" in report_text
    assert "FLAG" in report_text
    assert "FLAGGED (zero annotated clauses): gov_01" in report_text

    proc = subprocess.run(
        [sys.executable, "-m", "scripts.corpus_stats", "--gold-dir", str(gold_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Documents: 2 | Clauses: 7 | Annotated: 2" in proc.stdout
    assert "gov_01" in proc.stdout


def test_corpus_stats_empty_dir(tmp_path: Path) -> None:
    """corpus_stats handles an empty gold directory cleanly."""
    stats = compute_corpus_stats(gold_dir=tmp_path)
    assert stats.docs == []
    assert stats.total_clauses == 0
    assert format_stats_report(stats) == "No *.clauses.json files found."


def test_manifest_guidelines_and_self_contained_annotator() -> None:
    """Verify manifest header, guidelines tags, and offline HTML annotator."""
    manifest_path = REPO_ROOT / "data" / "manifest.csv"
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows == [
        [
            "doc_id",
            "doc_type",
            "title",
            "source_url",
            "license_or_terms_note",
            "language",
            "pages",
            "notes",
        ]
    ]

    guidelines = (REPO_ROOT / "docs" / "annotation_guidelines.md").read_text(encoding="utf-8")
    for tag in ("obligation", "right", "deadline", "penalty"):
        assert tag in guidelines

    html = (REPO_ROOT / "tools" / "annotate.html").read_text(encoding="utf-8")
    assert "http://" not in html
    assert "https://" not in html
    for token in ("obligation", "right", "deadline", "penalty", "ArrowRight", "ArrowLeft"):
        assert token in html
