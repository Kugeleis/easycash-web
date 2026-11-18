"""Pytest configuration for EasyCash&Tax Web."""

from pathlib import Path

import pytest


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Temporary DATA_DIR for tests."""
    return tmp_path
