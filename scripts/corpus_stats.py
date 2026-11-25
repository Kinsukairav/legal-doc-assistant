"""Report clause counts, tag distributions, and unannotated documents in data/gold/."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from legalassist.config import DATA_GOLD

KNOWN_TAGS: tuple[str, ...] = ("obligation", "right", "deadline", "penalty")


@dataclass(frozen=True)
class DocStats:
    """Clause and tag counts for a single annotated document."""

    doc_id: str
    doc_type: str
    clause_count: int
    annotated_clauses: int
    tag_counts: dict[str, int]


@dataclass(frozen=True)
class CorpusStats:
    """Aggregated statistics across all ``*.clauses.json`` files."""

    docs: list[DocStats]
    total_clauses: int
    total_annotated_clauses: int
    tag_counts: dict[str, int]
    unannotated_docs: list[str]


def compute_corpus_stats(gold_dir: Path = DATA_GOLD) -> CorpusStats:
    """Read ``*.clauses.json`` files in ``gold_dir`` and compute summary stats."""
    if not gold_dir.is_dir():
        return CorpusStats(
            docs=[],
            total_clauses=0,
            total_annotated_clauses=0,
            tag_counts={tag: 0 for tag in KNOWN_TAGS},
            unannotated_docs=[],
        )

    docs: list[DocStats] = []
    total_clauses = 0
    total_annotated = 0
    total_tags: Counter[str] = Counter({tag: 0 for tag in KNOWN_TAGS})
    unannotated_docs: list[str] = []

    for path in sorted(gold_dir.glob("*.clauses.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        doc_id = str(payload.get("doc_id") or path.name.removesuffix(".clauses.json"))
        doc_type = str(payload.get("doc_type") or "unknown")
        clauses = payload.get("clauses", [])

        doc_tag_counts: Counter[str] = Counter({tag: 0 for tag in KNOWN_TAGS})
        annotated_count = 0

        for clause in clauses:
            tags = clause.get("tags", []) if isinstance(clause, dict) else []
            if tags:
                annotated_count += 1
            for tag in tags:
                doc_tag_counts[tag] += 1
                total_tags[tag] += 1

        clause_count = len(clauses)
        total_clauses += clause_count
        total_annotated += annotated_count
        if annotated_count == 0:
            unannotated_docs.append(doc_id)

        docs.append(
            DocStats(
                doc_id=doc_id,
                doc_type=doc_type,
                clause_count=clause_count,
                annotated_clauses=annotated_count,
                tag_counts=dict(doc_tag_counts),
            )
        )

    return CorpusStats(
        docs=docs,
        total_clauses=total_clauses,
        total_annotated_clauses=total_annotated,
        tag_counts=dict(total_tags),
        unannotated_docs=unannotated_docs,
    )


def format_stats_report(stats: CorpusStats) -> str:
    """Format :class:`CorpusStats` as a human-readable CLI report."""
    if not stats.docs:
        return "No *.clauses.json files found."

    lines: list[str] = [
        f"Documents: {len(stats.docs)} | Clauses: {stats.total_clauses} | Annotated: {stats.total_annotated_clauses}",
        "",
        "Per-document breakdown:",
    ]
    for doc in stats.docs:
        flag = "  [FLAG: 0 annotated clauses]" if doc.annotated_clauses == 0 else ""
        tag_summary = ", ".join(f"{tag}={doc.tag_counts.get(tag, 0)}" for tag in KNOWN_TAGS)
        lines.append(
            f"  - {doc.doc_id} ({doc.doc_type}): "
            f"{doc.annotated_clauses}/{doc.clause_count} annotated | {tag_summary}{flag}"
        )

    lines.append("")
    lines.append("Total per-tag counts:")
    for tag, count in stats.tag_counts.items():
        lines.append(f"  - {tag}: {count}")

    if stats.unannotated_docs:
        lines.append("")
        lines.append(
            f"FLAGGED (zero annotated clauses): {', '.join(stats.unannotated_docs)}"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Print per-document and per-tag clause counts from data/gold/*.clauses.json."
    )
    parser.add_argument("--gold-dir", type=Path, default=DATA_GOLD, help="Gold directory path.")
    args = parser.parse_args(argv)

    stats = compute_corpus_stats(gold_dir=args.gold_dir)
    print(format_stats_report(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
