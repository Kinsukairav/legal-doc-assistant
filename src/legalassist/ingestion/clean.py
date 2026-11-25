"""Page cleaning and text normalisation utilities."""

from __future__ import annotations

import re
from collections import Counter

_UNICODE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u2002": " ",
        "\u2003": " ",
        "\u2009": " ",
        "\u202f": " ",
        "\u200b": "",
        "\ufeff": "",
    }
)

_PAGE_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^page\s+\d+(?:\s*(?:of|/)\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^\d+\s*(?:of|/)\s*\d+$", re.IGNORECASE),
    re.compile(r"^p\.?\s*\d+$", re.IGNORECASE),
    re.compile(r"^\[\s*\d+\s*\]$"),
)

_BARE_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
_DEHYPHENATE_RE = re.compile(r"([A-Za-z]{2,})-\n[ \t]*([a-z]{2,})")


def _normalize_unicode(text: str) -> str:
    """Normalize line endings, unicode quotes/dashes, ellipses, and spaces."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u2026", "...")
    return text.translate(_UNICODE_TRANSLATION)


def _normalize_line_ws(line: str) -> str:
    """Collapse internal horizontal whitespace and strip edges."""
    return re.sub(r"[ \t]+", " ", line).strip()


def _is_standalone_page_number(line: str, is_edge: bool = False) -> bool:
    """Return True if a stripped line is a standalone page-number marker."""
    if any(pat.match(line) for pat in _PAGE_NUMBER_PATTERNS):
        return True
    if is_edge and _BARE_PAGE_NUM_RE.match(line):
        return True
    return False


def _detect_repeated_lines(normalized_pages: list[list[str]]) -> set[str]:
    """Find non-empty lines appearing on strictly more than 50% of pages."""
    num_pages = len(normalized_pages)
    if num_pages < 2:
        return set()

    page_counts: Counter[str] = Counter()
    for lines in normalized_pages:
        unique_lines = {ln for ln in lines if ln}
        page_counts.update(unique_lines)

    threshold = num_pages / 2.0
    return {line for line, count in page_counts.items() if count > threshold}


def clean_pages(pages: list[str]) -> str:
    """Clean extracted document pages into a single normalised string.

    Removes lines that repeat on >50% of pages (headers/footers), removes
    standalone page numbers, de-hyphenates words broken across line breaks,
    normalizes unicode quotes/dashes and whitespace, and preserves clause
    numbering and paragraph structure.

    Args:
        pages: List of raw page strings returned by :func:`extract_pages`.

    Returns:
        Cleaned document text.
    """
    if not pages:
        return ""

    normalized_pages: list[list[str]] = [
        [_normalize_line_ws(line) for line in _normalize_unicode(page).split("\n")]
        for page in pages
    ]
    repeated_lines = _detect_repeated_lines(normalized_pages)

    cleaned_pages: list[str] = []
    for lines in normalized_pages:
        non_empty_indices = [idx for idx, ln in enumerate(lines) if ln]
        first_ne = non_empty_indices[0] if non_empty_indices else -1
        last_ne = non_empty_indices[-1] if non_empty_indices else -1

        kept_lines: list[str] = []
        for idx, line in enumerate(lines):
            if not line:
                if kept_lines and kept_lines[-1] != "":
                    kept_lines.append("")
                continue
            if line in repeated_lines:
                continue
            is_edge = idx == first_ne or idx == last_ne
            if _is_standalone_page_number(line, is_edge=is_edge):
                continue
            kept_lines.append(line)

        page_text = "\n".join(kept_lines).strip()
        if page_text:
            cleaned_pages.append(page_text)

    if not cleaned_pages:
        return ""

    # Join pages with single newline when a word breaks across the page boundary.
    parts: list[str] = [cleaned_pages[0]]
    for nxt in cleaned_pages[1:]:
        prev = parts[-1]
        if re.search(r"[A-Za-z]{2,}-$", prev) and re.match(r"^[a-z]{2,}", nxt):
            parts.append("\n" + nxt)
        else:
            parts.append("\n\n" + nxt)

    joined = "".join(parts)
    joined = _DEHYPHENATE_RE.sub(r"\1\2", joined)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()
