"""Clause segmentation for legal and government documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CLAUSE_CHARS = 1200

_UNIT_GUARD_RE = re.compile(
    r"^(?:%|percent|lakh|lakhs|crore|crores|million|billion|thousand|"
    r"days?|months?|years?|hours?|weeks?|kg|km|mg|ml)\b",
    re.IGNORECASE,
)
_CONNECTOR_GUARD_RE = re.compile(
    r"^(?:of|and|or|to|in|on|under|above|below|herein|hereof|thereof|"
    r"is|was|are|were|states|provides|applies|requires)\b",
    re.IGNORECASE,
)

# Line-start clause marker patterns
_NAMED_RE = re.compile(
    r"^(?P<label>(?:Clause|Section|Article)\s+(?:\d+(?:\.\d+)*|[IVXLCDM]+))"
    r"(?P<sep>\s*[:.\-]|\s+|$)",
    re.IGNORECASE,
)
_DECIMAL_TOP_RE = re.compile(r"^(?P<num>\d{1,3})\.(?=[ \t]+|$)")
_DECIMAL_SUB_RE = re.compile(r"^(?P<num>\d{1,3}(?:\.\d{1,3})+)\.?(?=[ \t]+|$)")
_PAREN_RE = re.compile(r"^\((?P<inner>[a-z]{1,5})\)(?=[ \t]+|$)")

_ROMAN_ONLY_RE = re.compile(
    r"^(?:ii|iii|iv|vi|vii|viii|ix|xi|xii|xiii|xiv|xv)$"
)

# Sentence boundary regex; abbreviations and leading numbers are filtered in Python.
_SENTENCE_END_RE = re.compile(r"[.!?]+(?=\s+[A-Z0-9\"'(\[])")
_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "mr",
        "ms",
        "mrs",
        "dr",
        "rs",
        "no",
        "vs",
        "st",
        "co",
        "sr",
        "jr",
        "lt",
        "eg",
        "ie",
        "sec",
        "art",
        "ltd",
        "inc",
        "pvt",
        "etc",
        "cl",
    }
)


@dataclass(frozen=True)
class Clause:
    """Single segmented clause or sub-clause from a legal document."""

    id: str
    number: str | None
    heading: str | None
    text: str
    start: int
    end: int


@dataclass
class _RawMarker:
    """Internal representation of a detected clause boundary in text."""

    start: int
    line_end: int
    kind: str  # "named" | "decimal" | "alpha" | "roman" | "heading"
    raw_token: str
    depth: int
    number: str | None
    heading: str | None


def _is_all_caps_heading(line: str) -> bool:
    """Return True if a stripped line looks like a standalone ALL-CAPS heading."""
    if not line or len(line) > 80 or line.endswith("."):
        return False
    words = line.split()
    if len(words) > 10:
        return False
    alpha_chars = [ch for ch in line if ch.isalpha()]
    if len(alpha_chars) < 2:
        return False
    if not all(ch.isupper() for ch in alpha_chars):
        return False
    # Avoid treating short acronyms or currency codes alone as headings unless 2+ letters.
    return any(sum(1 for c in w if c.isalpha()) >= 2 for w in words)


def _detect_line_marker(line: str, line_start: int, line_end: int) -> _RawMarker | None:
    """Match a clause marker or ALL-CAPS heading at the start of a line."""
    stripped = line.lstrip(" \t")
    if not stripped:
        return None
    leading_ws = len(line) - len(stripped)
    marker_start = line_start + leading_ws

    # 1. Clause / Section / Article N
    m_named = _NAMED_RE.match(stripped)
    if m_named:
        rest = stripped[m_named.end() :].lstrip()
        sep = m_named.group("sep").strip()
        if sep in {":", ".", "-"} or not rest or not _CONNECTOR_GUARD_RE.match(rest):
            label = re.sub(r"\s+", " ", m_named.group("label")).strip()
            return _RawMarker(
                start=marker_start,
                line_end=line_end,
                kind="named",
                raw_token=label,
                depth=0,
                number=label,
                heading=None,
            )

    # 2. Multi-level decimal (1.1, 1.1.1)
    m_sub = _DECIMAL_SUB_RE.match(stripped)
    if m_sub:
        rest = stripped[m_sub.end() :].lstrip()
        if not rest or not _UNIT_GUARD_RE.match(rest):
            num = m_sub.group("num")
            depth = num.count(".") + 1
            return _RawMarker(
                start=marker_start,
                line_end=line_end,
                kind="decimal",
                raw_token=num,
                depth=depth,
                number=num,
                heading=None,
            )

    # 3. Single-level decimal (1.)
    m_top = _DECIMAL_TOP_RE.match(stripped)
    if m_top:
        num = m_top.group("num")
        if 1 <= int(num) <= 199:
            return _RawMarker(
                start=marker_start,
                line_end=line_end,
                kind="decimal",
                raw_token=num,
                depth=1,
                number=num,
                heading=None,
            )

    # 4. Parenthesized letter or roman numeral: (a), (i)
    m_paren = _PAREN_RE.match(stripped)
    if m_paren:
        inner = m_paren.group("inner")
        token = f"({inner})"
        kind = "roman" if _ROMAN_ONLY_RE.match(inner) else "alpha_or_roman"
        return _RawMarker(
            start=marker_start,
            line_end=line_end,
            kind=kind,
            raw_token=token,
            depth=10,
            number=token,
            heading=None,
        )

    # 5. ALL-CAPS heading
    cleaned_line = stripped.rstrip()
    if _is_all_caps_heading(cleaned_line):
        heading_text = cleaned_line.rstrip(":").strip()
        return _RawMarker(
            start=marker_start,
            line_end=line_end,
            kind="heading",
            raw_token=heading_text,
            depth=0,
            number=None,
            heading=heading_text,
        )

    return None


def _resolve_hierarchy(markers: list[_RawMarker]) -> list[_RawMarker]:
    """Assign hierarchical parent numbers (e.g., 4.2(a), 4.2(b)(i)) to markers."""
    stack: list[tuple[str, int, str]] = []  # (kind, rank, full_number)
    last_alpha_char: str | None = None

    for marker in markers:
        if marker.kind == "heading":
            stack.clear()
            last_alpha_char = None
            continue

        if marker.kind == "named":
            stack = [("named", 0, marker.raw_token)]
            last_alpha_char = None
            marker.number = marker.raw_token
            continue

        if marker.kind == "decimal":
            rank = marker.depth
            # Drop any finer/sibling levels and any named level once decimal starts
            # unless decimal starts with the named clause number (e.g. Clause 3 -> 3.1).
            while stack and (stack[-1][0] in {"alpha", "roman", "named"} or stack[-1][1] >= rank):
                stack.pop()
            stack.append(("decimal", rank, marker.raw_token))
            last_alpha_char = None
            marker.number = marker.raw_token
            continue

        # Disambiguate (i), (v), (x) between alpha and roman
        inner = marker.raw_token.strip("()")
        if marker.kind == "alpha_or_roman":
            if len(inner) == 1 and inner in {"i", "v", "x"}:
                expected_prev = {"i": "h", "v": "u", "x": "w"}[inner]
                if last_alpha_char == expected_prev and any(k == "alpha" for k, _, _ in stack):
                    kind = "alpha"
                else:
                    kind = "roman"
            elif len(inner) == 1:
                kind = "alpha"
            else:
                continue  # ignore invalid multi-letter non-roman tokens like (etc)
        else:
            kind = "roman"

        marker.kind = kind
        if kind == "alpha":
            while stack and stack[-1][0] in {"alpha", "roman"}:
                stack.pop()
            parent = stack[-1][2] if stack else ""
            full_num = f"{parent}{marker.raw_token}" if parent else marker.raw_token
            stack.append(("alpha", 10, full_num))
            last_alpha_char = inner
            marker.number = full_num
        else:  # roman
            while stack and stack[-1][0] == "roman":
                stack.pop()
            parent = stack[-1][2] if stack else ""
            full_num = f"{parent}{marker.raw_token}" if parent else marker.raw_token
            stack.append(("roman", 20, full_num))
            marker.number = full_num

    # Drop invalid markers that were skipped (multi-letter non-roman)
    return [m for m in markers if m.kind != "alpha_or_roman"]


def _extract_heading(block_text: str, marker: _RawMarker) -> str | None:
    """Extract an optional short heading from a clause block."""
    if marker.kind == "heading":
        return marker.heading

    # Strip the leading marker token + punctuation from the first line.
    lines = block_text.splitlines()
    if not lines:
        return None

    first_line = lines[0]
    if marker.kind == "named":
        body_on_first = re.sub(
            r"^(?:Clause|Section|Article)\s+(?:\d+(?:\.\d+)*|[IVXLCDM]+)\s*[:.\-]?\s*",
            "",
            first_line,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
    elif marker.kind == "decimal":
        body_on_first = re.sub(
            r"^\d{1,3}(?:\.\d{1,3})*\.?\s*", "", first_line, count=1
        ).strip()
    else:
        body_on_first = re.sub(r"^\([a-z]+\)\s*", "", first_line, count=1).strip()

    if not body_on_first:
        return None

    # Pattern A: short title line followed by body on subsequent line(s).
    has_more_lines = any(ln.strip() for ln in lines[1:])
    if has_more_lines and len(body_on_first) <= 70:
        word_count = len(body_on_first.split())
        if (not body_on_first.endswith(".") and word_count <= 8) or (
            body_on_first.endswith(".") and word_count <= 4 and len(body_on_first) <= 45
        ):
            return body_on_first.rstrip(".:-").strip() or None

    # Pattern B: "TITLE. Body..." or "Title: Body..." on the same line.
    colon_match = re.match(r"^([A-Za-z][A-Za-z0-9 &/\-]{1,50}):\s+\S", body_on_first)
    if colon_match and len(colon_match.group(1).split()) <= 6:
        return colon_match.group(1).strip()

    caps_match = re.match(r"^([A-Z][A-Z0-9 &/\-]{2,60})\.\s+\S", body_on_first)
    if caps_match and len(caps_match.group(1).split()) <= 8:
        return caps_match.group(1).strip()

    return None


def _split_span_sentences(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    """Split a long text span [start, end) at sentence boundaries."""
    span = text[start:end]
    if len(span) <= max_chars:
        return [(start, end)]

    split_points = [0]
    for match in _SENTENCE_END_RE.finditer(span):
        if match.group(0).startswith("."):
            prefix = span[: match.start()]
            token_match = re.search(r"([A-Za-z0-9]+)$", prefix)
            if token_match:
                token = token_match.group(1)
                if token.isdigit() or token.lower() in _ABBREVIATIONS:
                    continue
        split_points.append(match.end())
    split_points.append(len(span))

    sentences: list[tuple[int, int]] = []
    for idx in range(len(split_points) - 1):
        s_start = start + split_points[idx]
        s_end = start + split_points[idx + 1]
        while s_start < s_end and text[s_start].isspace():
            s_start += 1
        while s_end > s_start and text[s_end - 1].isspace():
            s_end -= 1
        if s_start < s_end:
            sentences.append((s_start, s_end))

    if not sentences:
        return [(start, end)]

    chunks: list[tuple[int, int]] = []
    cur_start, cur_end = sentences[0]
    for s_start, s_end in sentences[1:]:
        if s_end - cur_start <= max_chars:
            cur_end = s_end
        else:
            chunks.append((cur_start, cur_end))
            cur_start, cur_end = s_start, s_end
    chunks.append((cur_start, cur_end))
    return chunks


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim leading and trailing whitespace from a [start, end) slice."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _paragraph_fallback(text: str) -> list[Clause]:
    """Split unnumbered text on blank lines into Clause objects."""
    clauses: list[Clause] = []

    # Build raw paragraph spans using paragraph breaks.
    raw_spans: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"\n[ \t]*\n+", text):
        s, e = _trim_span(text, cursor, match.start())
        if s < e:
            raw_spans.append((s, e))
        cursor = match.end()
    s, e = _trim_span(text, cursor, len(text))
    if s < e:
        raw_spans.append((s, e))

    idx = 1
    for p_start, p_end in raw_spans:
        for c_start, c_end in _split_span_sentences(text, p_start, p_end, MAX_CLAUSE_CHARS):
            clauses.append(
                Clause(
                    id=f"c{idx}",
                    number=None,
                    heading=None,
                    text=text[c_start:c_end],
                    start=c_start,
                    end=c_end,
                )
            )
            idx += 1
    return clauses


def segment_clauses(text: str) -> list[Clause]:
    """Segment legal text into hierarchical or paragraph-level clauses.

    Detects ``1.``, ``1.1``, ``1.1.1``, ``(a)``, ``(i)``,
    ``Clause/Section/Article N``, and ALL-CAPS headings. Maintains hierarchical
    parent numbers (e.g., ``4.2(a)``), splits clauses longer than 1200 chars
    at sentence boundaries, and falls back to paragraph splitting if no
    numbering or section headings are found.

    Args:
        text: Cleaned document text.

    Returns:
        Ordered list of :class:`Clause` objects.
    """
    if not text or not text.strip():
        return []

    raw_markers: list[_RawMarker] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        line_no_nl = line.rstrip("\r\n")
        line_end = offset + len(line_no_nl)
        marker = _detect_line_marker(line_no_nl, offset, line_end)
        if marker is not None:
            raw_markers.append(marker)
        offset += len(line)

    # Filter out ALL-CAPS headings that have no body text before the next marker
    # (e.g., document titles sitting immediately above Clause 1).
    filtered_markers: list[_RawMarker] = []
    for i, marker in enumerate(raw_markers):
        if marker.kind == "heading":
            next_start = raw_markers[i + 1].start if i + 1 < len(raw_markers) else len(text)
            between = text[marker.line_end : next_start].strip()
            if not between:
                continue
        filtered_markers.append(marker)

    resolved = _resolve_hierarchy(filtered_markers)
    if not resolved:
        return _paragraph_fallback(text)

    clauses: list[Clause] = []
    clause_idx = 1
    for i, marker in enumerate(resolved):
        raw_end = resolved[i + 1].start if i + 1 < len(resolved) else len(text)
        b_start, b_end = _trim_span(text, marker.start, raw_end)
        if b_start >= b_end:
            continue

        heading = _extract_heading(text[b_start:b_end], marker)
        for c_start, c_end in _split_span_sentences(text, b_start, b_end, MAX_CLAUSE_CHARS):
            clauses.append(
                Clause(
                    id=f"c{clause_idx}",
                    number=marker.number,
                    heading=heading,
                    text=text[c_start:c_end],
                    start=c_start,
                    end=c_end,
                )
            )
            clause_idx += 1

    return clauses


def llm_segment_fallback(text: str) -> list[Clause]:
    """LLM-assisted clause segmentation fallback for unnumbered documents.

    Implemented in Step 5.
    """
    raise NotImplementedError("llm_segment_fallback will be implemented in Step 5.")
