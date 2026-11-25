"""Smoke test – verifies the package is importable and config loads."""

import sys
from pathlib import Path

# Ensure src/ is on the path so legalassist is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_package_imports() -> None:
    """Core package and all subpackages should be importable."""
    import legalassist
    import legalassist.config
    import legalassist.ingestion
    import legalassist.segmentation
    import legalassist.tagging
    import legalassist.summarization
    import legalassist.qa
    import legalassist.llm
    import legalassist.i18n
    import legalassist.evaluation

    assert legalassist.__version__ == "0.1.0"


def test_config_paths_exist() -> None:
    """Config paths should point to real directories (created by scaffold)."""
    from legalassist.config import PROJECT_ROOT, DATA_RAW, DATA_GOLD

    assert PROJECT_ROOT.exists()
    assert DATA_RAW.exists()
    assert DATA_GOLD.exists()
