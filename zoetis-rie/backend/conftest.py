"""Pytest configuration: make the ``app`` package importable from the backend
root and guarantee a seed-42 dataset exists before any test runs.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data import generator  # noqa: E402
from app.data.provider import reset_provider  # noqa: E402


def pytest_configure(config):
    """Ensure deterministic seeds are present (idempotent)."""
    seeds = BACKEND_ROOT / "app" / "data" / "seeds"
    if not (seeds / "metadata.json").exists():
        generator.generate(seed=42, issues=30)
    reset_provider()
