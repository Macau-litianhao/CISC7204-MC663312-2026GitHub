"""Settings loader - the only place in the project that reads ``config/project.yaml``.

Why a dotted-path getter instead of a settings class: the configuration is
mostly a list of paths plus a few numbers, and a class with forty attributes
would be longer than the file it wraps. ``get("models.gbm_max_depth")`` keeps
call sites readable and fails loudly only where a default was not supplied.

Mode switch
-----------
``TEAM01_MODE=sample`` redirects the flight table to the 60k-row smoke fixture
used by the test suite and by ``make smoke``. Every other path is unchanged, so
the pipeline code has no idea which data it is running on.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# src/team01/config.py -> src/team01 -> src -> repository root
ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "project.yaml"

MODE_ENV = "TEAM01_MODE"
VALID_MODES = ("full", "sample")


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    """Parsed YAML configuration (cached for the lifetime of the process)."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"missing configuration file: {CONFIG_FILE}")
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def mode() -> str:
    """Active data mode: ``full`` (real panel) or ``sample`` (smoke fixture)."""
    value = os.environ.get(MODE_ENV, str(settings().get("mode", "full"))).strip().lower()
    if value not in VALID_MODES:
        raise ValueError(f"{MODE_ENV} must be one of {VALID_MODES}, got {value!r}")
    return value


def get(dotted: str, default: Any = None) -> Any:
    """Read a nested setting, e.g. ``get("models.gbm_max_depth")``."""
    node: Any = settings()
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            if default is None:
                raise KeyError(f"setting not found in {CONFIG_FILE.name}: {dotted}")
            return default
        node = node[key]
    return node


def get_for_mode(dotted: str, default: Any = None) -> Any:
    """Read a setting that may carry a fixture-specific override.

    ``get_for_mode("attribution.carrier_min_flights")`` returns
    ``attribution.carrier_min_flights_sample`` in sample mode when that key
    exists, and the plain key otherwise. Absolute thresholds do not survive a
    hundredfold change in data volume: a floor tuned on the ten-year panel
    empties every table on the 47k-row fixture, and a floor tuned on the fixture
    would admit carriers with a few hundred flights in the real panel. Keeping
    both numbers in one file, side by side, is what makes the difference visible
    to a reader instead of hidden in a default argument.
    """
    if mode() == "sample":
        override = f"{dotted}_sample"
        try:
            return get(override)
        except KeyError:
            return get(dotted, default)
    return get(dotted, default)


def path(dotted: str) -> Path:
    """Absolute path for a ``paths.*`` or ``files.*`` entry."""
    value = ROOT / str(get(dotted))
    if mode() == "sample":
        if dotted in {"paths.figures", "paths.tables", "paths.metrics"}:
            value = value / "sample"
        elif dotted in {"files.airport_features_parquet", "files.airport_clusters_csv"}:
            value = value.parent / "sample" / value.name
    return value


def ensure_dir(dotted: str) -> Path:
    """Absolute path for a directory entry, created if it does not exist."""
    target = path(dotted)
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_parent(target: Path) -> Path:
    """Create the parent directory of a file path and return the path."""
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


# --------------------------------------------------------------------------
# Frequently used paths, resolved once at import time
# --------------------------------------------------------------------------
RAW_FLIGHTS_DIR = ROOT / str(get("paths.raw_flights"))
RAW_WEATHER_DIR = ROOT / str(get("paths.raw_weather"))
REFERENCE_DIR = ROOT / str(get("paths.reference"))
INTERIM_DIR = ROOT / str(get("paths.interim"))
PROCESSED_DIR = ROOT / str(get("paths.processed"))
FIG_DIR = path("paths.figures")
TABLE_DIR = path("paths.tables")
METRIC_DIR = path("paths.metrics")


def flights_file() -> Path:
    """Flight table for the active mode."""
    key = "files.flights_sample_parquet" if mode() == "sample" else "files.flights_parquet"
    return ROOT / str(get(key))


def airports_file() -> Path:
    """Airport reference table for the active mode.

    The fixture must not write into ``data/raw/``: that directory is the record
    of what was downloaded, and a synthetic file there silently satisfies
    ``download(..., force=False)`` for every later real run.
    """
    key = "files.airports_sample_csv" if mode() == "sample" else "files.airports_csv"
    return ROOT / str(get(key))


def weather_file() -> Path:
    return ROOT / str(get("files.weather_parquet"))


def airport_features_file() -> Path:
    return path("files.airport_features_parquet")


def airports_clustered_file() -> Path:
    return path("files.airport_clusters_csv")


def years() -> list[int]:
    return [int(y) for y in get("panel.years")]


def threshold() -> float:
    """Arrival-delay threshold above which BTS reports cause minutes."""
    return float(get("panel.attribution_threshold_min"))


def panel_controls() -> list[str]:
    """Columns entering every model as a control block rather than a factor."""
    return [str(column) for column in get("models.panel_controls", [])]


def sensitivity_years() -> list[int]:
    """Years dropped when the headline results are recomputed."""
    return [int(year) for year in get("panel.sensitivity_exclude_years", [])]


def min_hour_flights() -> float:
    """Departure count below which an hourly share or mean is not drawn.

    Read by the printed cascade figure and by the dashboard hourly panel, so
    the two cannot disagree about where sample size stops supporting a claim.
    """
    return float(get("viz.min_hour_flights", 200))


def seed() -> int:
    return int(get("sampling.seed"))


def summarise() -> str:
    """One-line description of the active configuration, for log headers."""
    return (
        f"{get('project.name')} v{get('project.version')} | mode={mode()} | "
        f"years={years()[0]}-{years()[-1]} | "
        f"flights={flights_file().name}"
    )
