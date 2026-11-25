"""Rule-based document-type detection via weighted keyword/phrase scoring."""

from __future__ import annotations

import re

DOC_TYPE_KEYWORDS: dict[str, dict[str, float]] = {
    "rental_agreement": {
        "rental agreement": 4.0,
        "lease agreement": 4.0,
        "leave and license": 3.5,
        "landlord": 3.0,
        "tenant": 3.0,
        "lessor": 2.5,
        "lessee": 2.5,
        "security deposit": 3.0,
        "monthly rent": 3.0,
        "lock-in": 3.0,
        "lock-in period": 3.5,
        "tenancy": 2.5,
        "sublet": 2.5,
        "subletting": 2.5,
        "premises": 2.0,
        "eviction": 2.0,
        "maintenance charges": 2.0,
        "rent": 1.5,
        "vacate": 1.5,
    },
    "terms_of_service": {
        "terms of service": 4.0,
        "terms of use": 3.5,
        "terms and conditions": 3.0,
        "by accessing or using": 3.5,
        "you agree": 3.0,
        "limitation of liability": 3.0,
        "user account": 2.5,
        "user content": 2.5,
        "intellectual property": 2.5,
        "non-exclusive": 2.5,
        "privacy policy": 2.5,
        "license": 2.5,
        "account": 2.0,
        "indemnify": 2.0,
        "warranty": 2.0,
        "subscription": 2.0,
        "cookies": 2.0,
        "third-party": 2.0,
        "liability": 1.5,
    },
    "government_notice": {
        "government notice": 4.0,
        "show cause notice": 4.0,
        "public notice": 3.5,
        "competent authority": 3.5,
        "within 30 days": 3.0,
        "within 15 days": 2.5,
        "statutory": 3.0,
        "gazette": 3.0,
        "ministry": 3.0,
        "undersigned": 3.0,
        "show cause": 3.0,
        "hereby": 2.5,
        "authority": 2.5,
        "pursuant to": 2.5,
        "municipal": 2.5,
        "directed to": 2.5,
        "notice": 2.0,
        "penalty": 2.0,
        "compliance": 2.0,
        "department": 2.0,
    },
}

_MIN_SCORE_THRESHOLD = 3.0
_MIN_SHARE_THRESHOLD = 0.45

_COMPILED_PATTERNS: dict[str, list[tuple[re.Pattern[str], float]]] = {
    doc_type: [
        (re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE), weight)
        for phrase, weight in keywords.items()
    ]
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items()
}


def detect_doc_type(text: str) -> tuple[str, float]:
    """Detect the document type and confidence using weighted keyword scoring.

    Args:
        text: Cleaned document text.

    Returns:
        Tuple of ``(doc_type, confidence)`` where ``doc_type`` is one of
        ``"rental_agreement"``, ``"terms_of_service"``,
        ``"government_notice"``, or ``"unknown"``, and ``confidence`` is a float
        in ``[0.0, 1.0]``.
    """
    if not text or not text.strip():
        return ("unknown", 0.0)

    scores: dict[str, float] = {}
    for doc_type, patterns in _COMPILED_PATTERNS.items():
        score = 0.0
        for pattern, weight in patterns:
            matches = len(pattern.findall(text))
            if matches > 0:
                # Cap repeat boost so frequent generic terms cannot dominate domain terms.
                score += weight * (1.0 + 0.2 * min(matches - 1, 3))
        scores[doc_type] = score

    total_score = sum(scores.values())
    if total_score <= 0.0:
        return ("unknown", 0.0)

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    share = best_score / total_score

    if best_score < _MIN_SCORE_THRESHOLD or share < _MIN_SHARE_THRESHOLD:
        return ("unknown", 0.0)

    strength = min(1.0, best_score / 12.0)
    confidence = round(min(1.0, share * (0.5 + 0.5 * strength)), 4)
    return (best_type, confidence)
