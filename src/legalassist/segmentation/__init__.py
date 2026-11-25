"""Clause segmentation and document-type detection."""

from legalassist.segmentation.doctype import DOC_TYPE_KEYWORDS, detect_doc_type
from legalassist.segmentation.segment import (
    Clause,
    llm_segment_fallback,
    segment_clauses,
)

__all__ = [
    "Clause",
    "DOC_TYPE_KEYWORDS",
    "detect_doc_type",
    "llm_segment_fallback",
    "segment_clauses",
]
