"""Shared pytest fixtures.

The suite runs on the synthetic fixture, not on the panel: a test that needs a
four-gigabyte download is a test nobody runs. The fixture is small but keeps the
structure the code depends on - rotations, a cause split above the 15-minute
threshold, cancellations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from team01 import clean, config, synth  # noqa: E402


@pytest.fixture(scope="session")
def panel():
    """Small prepared panel in the project schema (~7k rows)."""
    return synth.make_panel(days=30, tails=40, seed=7)


@pytest.fixture(scope="session")
def completed(panel):
    return clean.completed(panel)


@pytest.fixture(scope="session")
def universe(panel):
    return clean.attribution_universe(panel)


@pytest.fixture()
def figure_dir(tmp_path, monkeypatch):
    """Redirect figures to a temporary directory so tests leave no artefacts."""
    monkeypatch.setattr(config, "FIG_DIR", tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def airport_reference():
    return synth.make_airport_reference()
