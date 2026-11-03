"""Contract tests for the data layer.

These are the tests that protect the report's claims: a change that lets cause
minutes leak below the threshold, or that silently drops a year, breaks a test
here rather than a figure nobody looks at until the deadline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from team01 import clean, config, schema, synth


def test_apply_schema_is_idempotent(panel):
    again = clean.apply_schema(panel)
    assert list(again.columns) == list(panel.columns)
    assert len(again) == len(panel)


def test_source_columns_are_all_mapped():
    """Every BTS field we request has a target name; no orphan in the schema."""
    assert set(schema.RENAME) == set(schema.USECOLS)


def test_raw_fixture_uses_published_column_names():
    raw = synth.make_flights(days=2, tails=5, seed=1)
    assert "CarrierDelay" in raw.columns
    assert "flight_date" not in raw.columns


def test_completed_excludes_cancelled_and_diverted(panel):
    finished = clean.completed(panel)
    assert (finished["cancelled"].fillna(0) == 0).all()
    assert (finished["diverted"].fillna(0) == 0).all()
    assert finished["arr_delay"].notna().all()
    assert len(finished) <= len(panel)


def test_attribution_universe_respects_threshold(panel):
    universe = clean.attribution_universe(panel)
    assert (universe["arr_delay"] >= config.threshold()).all()
    # Nothing below the threshold may carry cause minutes.
    below = clean.completed(panel)
    below = below[below["arr_delay"] < config.threshold()]
    assert below[schema.CAUSE_COLUMNS].isna().all().all()


def test_cause_coverage_is_one_above_and_zero_below(panel):
    checks = clean.validate(panel, "fixture")
    assert checks["cause_coverage_above_threshold"] == pytest.approx(1.0, abs=1e-6)
    assert checks["cause_coverage_below_threshold"] == pytest.approx(0.0, abs=1e-6)


def test_validate_reports_rows_and_years(panel):
    checks = clean.validate(panel, "fixture")
    assert checks["rows"] == len(panel)
    assert checks["year_min"] <= checks["year_max"]
    assert checks["duplicate_rate"] <= 0.001


def test_validate_rejects_a_corrupted_table(panel):
    corrupted = pd.concat([panel, panel], ignore_index=True)
    with pytest.raises(ValueError):
        clean.validate(corrupted, "corrupted")


def test_validate_allows_a_month_of_mass_cancellations(panel):
    """A cancelled leg's blank arrival delay is correct, not missing data.

    February 2015's winter storms and March 2020's lockdowns each cancelled more
    than 5% of flights. Validation must not reject such a month, because the
    blanks sit on cancelled/diverted rows, not on operated ones.
    """
    corrupted = panel.copy()
    take = corrupted.index[: len(corrupted) // 3]
    corrupted.loc[take, "cancelled"] = 1
    corrupted.loc[take, "diverted"] = 0
    corrupted.loc[take, "arr_delay"] = np.nan

    checks = clean.validate(corrupted, "stormy_month")
    assert checks["missing_arr_delay"] == 0
    assert checks["arr_delay_na_total"] >= len(take)
    assert checks["cancelled_rows"] >= len(take)


def test_validate_rejects_operated_rows_missing_arrival_delay(panel):
    """The real defect: an operated flight whose arrival delay went missing."""
    corrupted = panel.copy()
    take = corrupted.index[: int(len(corrupted) * 0.1)]
    corrupted.loc[take, "cancelled"] = 0
    corrupted.loc[take, "diverted"] = 0
    corrupted.loc[take, "arr_delay"] = np.nan

    with pytest.raises(ValueError, match="operated flights lack an arrival delay"):
        clean.validate(corrupted, "corrupt_operated")


def test_departure_hour_handles_midnight():
    """BTS encodes 00:00 as 2400; it must land in hour 0, not hour 24."""
    raw = synth.make_flights(days=3, tails=4, seed=1)
    raw.loc[raw.index[:5], "CRSDepTime"] = 2400
    prepared = clean.apply_schema(raw)
    assert prepared["dep_hour"].isin(range(24)).all()
    assert (prepared.loc[prepared.index[:5], "dep_hour"] == 0).all()


def test_panel_summary_covers_every_year(panel):
    summary = clean.summarise_panel(panel)
    assert set(summary["year"]) == set(panel["year"].unique())
    assert (summary["completed_flights"] > 0).all()


def test_fixture_paths_never_shadow_downloaded_files(monkeypatch):
    """The fixture must not write where the real download lands.

    Sharing one path meant a fixture run left a 15-row synthetic airport table
    in data/raw/reference/, after which acquire_airports(force=False) saw an
    existing file and skipped the real 86k-row download.
    """
    monkeypatch.setenv(config.MODE_ENV, "sample")
    sample_path = config.airports_file()
    monkeypatch.setenv(config.MODE_ENV, "full")
    full_path = config.airports_file()

    assert sample_path != full_path
    assert "raw" not in sample_path.parts
    assert "raw" in full_path.parts
