"""Central configuration – loads .env and exposes key settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Locate the .env at the repo root (two levels up from this file)
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)

# ── API keys ──────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Model settings ────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
TAGGING_MODEL: str = os.getenv("TAGGING_MODEL", "xlm-roberta-base")
SUMMARIZATION_MODEL: str = os.getenv("SUMMARIZATION_MODEL", "google/flan-t5-small")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_RAW: Path = PROJECT_ROOT / "data" / "raw"
DATA_GOLD: Path = PROJECT_ROOT / "data" / "gold"
DATA_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
