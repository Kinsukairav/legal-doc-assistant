"""Document ingestion – PDF/DOCX/text extraction and cleaning."""

from legalassist.ingestion.clean import clean_pages
from legalassist.ingestion.extract import (
    EmptyDocumentError,
    ExtractionError,
    UnsupportedFileTypeError,
    extract_pages,
)

__all__ = [
    "EmptyDocumentError",
    "ExtractionError",
    "UnsupportedFileTypeError",
    "clean_pages",
    "extract_pages",
]
