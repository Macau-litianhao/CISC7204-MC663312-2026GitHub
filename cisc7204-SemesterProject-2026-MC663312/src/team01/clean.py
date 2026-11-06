"""Type coercion, derived time fields and data-quality validation.

Three responsibilities, in this order:

1. ``apply_schema`` - translate BTS CamelCase into the project schema, coerce
   types, and derive the time fields every later stage assumes exists.
2. ``validate``      - count rows, duplicates, missingness and the 15-minute
   cause-field coverage. The result is a plain dict so it can be written to
   ``outputs/tables/validation_<year>.csv`` and quoted in the report.
3. ``completed`` / ``attribution_universe`` - the two row populations the
   analysis uses. Mixing them up is the classic error in this dataset: cause
   shares describe delayed flights only, whereas means and percentiles describe
   every completed flight.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------
def apply_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Rename, coerce and enrich a raw BTS frame. Idempotent.

    The early return tests for the *derived* fields, not for ``flight_date``:
    a frame that has been renamed but not enriched would otherwise be returned
    unchanged, which is exactly the trap that hides a broken duration column.
    """
    if {"flight_date", "dep_hour", "sched_dep_dt"} <= set(df.columns):
        return df

    missing = [c for c in schema.USECOLS if c not in df.columns]
    if missing:
        raise KeyError(f"source file is missing expected columns: {missing}")

    out = df.rename(columns=schema.RENAME)
    out = out[[c for c in schema.RENAME.values() if c in out.columns]]

    for column, dtype in schema.DTYPES.items():
        if column in out.columns:
            out[column] = out[column].astype(dtype)

    out["flight_date"] = pd.to_datetime(out["flight_date"], errors="coerce")

    # crs_dep_time is an integer HHMM (855, 1900, 2400). 2400 is midnight at
    # the end of the day; taking it modulo 24 keeps it in hour 0 rather than
    # inventing hour 24, which would break the ordered hour axis.
    hours = (out["crs_dep_time"] // 100) % 24
    minutes = out["crs_dep_time"] % 100
    out["dep_hour"] = hours.astype("int8")
    out["dep_minute"] = minutes.astype("int8")

    midnight = out["flight_date"]
    out["sched_dep_dt"] = (
        midnight + pd.to_timedelta((out["crs_dep_time"] == 2400).astype("int8"), unit="D")
        + pd.to_timedelta(hours, unit="h")
        + pd.to_timedelta(minutes, unit="m")
    )
    out["sched_arr_dt"] = out["sched_dep_dt"] + pd.to_timedelta(
        out["crs_elapsed"].fillna(0), unit="m"
    )
    # Actual arrival is only defined for completed legs; NaT elsewhere, which
    # is exactly what the cascade calculation needs.
    out["actual_arr_dt"] = out["sched_arr_dt"] + pd.to_timedelta(
        out["arr_delay"], unit="m"
    )

    out["month_name"] = out["month"].map(
        dict(enumerate(schema.MONTH_LABELS, start=1))
    ).astype("category")
    out["dow_name"] = out["dow"].map(
        dict(enumerate(schema.DOW_LABELS, start=1))
    ).astype("category")

    return out


def completed(df: pd.DataFrame) -> pd.DataFrame:
    """Flights that actually operated and have a known arrival delay.

    The result is tagged so a second ``completed()`` call returns it unchanged
    instead of copying ~60M rows again. ``attribution_universe`` and
    ``summarise_panel`` both call ``completed()`` on a frame a script has just
    completed, and on the full panel that redundant copy is the difference
    between fitting in memory and OOM.
    """
    if df.attrs.get("_team01_completed"):
        return df
    mask = (
        (df["cancelled"].fillna(0) == 0)
        & (df["diverted"].fillna(0) == 0)
        & df["arr_delay"].notna()
    )
    out = df.loc[mask]
    out.attrs["_team01_completed"] = True
    return out


def attribution_universe(df: pd.DataFrame, threshold: float | None = None) -> pd.DataFrame:
    """Completed flights at or above the BTS cause-reporting threshold.

    BTS publishes the five cause-minute fields only for flights delayed by at
    least 15 minutes. Every cause-share statement in the project is scoped to
    this frame; counts, means and percentiles use ``completed`` instead.
    """
    limit = config.threshold() if threshold is None else threshold
    base = completed(df)
    return base.loc[base["arr_delay"] >= limit]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate(df: pd.DataFrame, stage: str, expected_rows: int | None = None) -> dict:
    """Data-quality checks for one table. Returns a flat, CSV-friendly dict.

    ``stage`` is a short label (``"raw_2024"``, ``"panel"``, ``"sample"``) used
    only for reporting. Hard failures raise; soft issues are counted and
    reported so that a decade of data can show one bad year without stopping
    the pipeline.
    """
    threshold = config.threshold()
    total = len(df)
    result: dict[str, object] = {"stage": stage, "rows": total}

    if expected_rows is not None:
        result["expected_rows"] = expected_rows
        result["row_match"] = bool(total == expected_rows)

    keys = [c for c in schema.KEY_COLUMNS if c in df.columns]
    if not keys:
        raise KeyError(
            "duplicate check needs the project schema; run apply_schema first "
            f"(missing all of {schema.KEY_COLUMNS})"
        )
    dup_mask = df.duplicated(subset=keys)
    result["duplicate_rows"] = int(dup_mask.sum())
    result["duplicate_rate"] = round(float(dup_mask.mean()) if total else 0.0, 6)

    required = [c for c in schema.REQUIRED_FOR_ANALYSIS if c in df.columns]
    result["missing_required_cells"] = int(df[required].isna().sum().sum())

    # An arrival delay is only *supposed* to exist for an operated leg. A
    # cancelled or diverted flight never arrives, so its ``arr_delay`` is blank
    # by design — February 2015's winter storms and March 2020's lockdowns each
    # cancelled far more than 5% of flights, and neither is a data defect. The
    # defect we must catch is an operated flight whose arrival delay went
    # missing, so the two counts below are separated on purpose.
    operated = (
        (df["cancelled"].fillna(0) == 0)
        & (df["diverted"].fillna(0) == 0)
    )
    result["arr_delay_na_total"] = int(df["arr_delay"].isna().sum())
    result["missing_arr_delay"] = int((operated & df["arr_delay"].isna()).sum())

    finished = completed(df)
    result["completed_rows"] = int(len(finished))
    result["cancelled_rows"] = int((df["cancelled"].fillna(0) == 1).sum())
    result["diverted_rows"] = int((df["diverted"].fillna(0) == 1).sum())

    if len(finished):
        result["mean_arr_delay"] = round(float(finished["arr_delay"].mean()), 3)
        result["median_arr_delay"] = round(float(finished["arr_delay"].median()), 3)
        result["share_delayed_60"] = round(
            float((finished["arr_delay"] >= 60).mean()), 5
        )

    # Coverage of the cause fields is the check that keeps the attribution
    # section honest: it must be ~0 below the threshold and ~1 above it.
    cause_cols = [c for c in schema.CAUSE_COLUMNS if c in df.columns]
    if cause_cols and len(finished):
        has_cause = finished[cause_cols].notna().all(axis=1)
        above = finished["arr_delay"] >= threshold
        below = ~above
        result["cause_coverage_above_threshold"] = round(
            float(has_cause[above].mean()) if above.any() else np.nan, 6
        )
        result["cause_coverage_below_threshold"] = round(
            float(has_cause[below].mean()) if below.any() else np.nan, 6
        )
        result["flights_above_threshold"] = int(above.sum())

    result["year_min"] = int(df["year"].min())
    result["year_max"] = int(df["year"].max())

    # A duplicate rate above 0.1%, or an arrival delay missing on more than 5%
    # of *operated* rows, means the source file is suspect; both are hard
    # failures. The denominator is operated flights, not all rows: a cancelled
    # leg's blank arrival delay is not missing data, it is the correct value.
    if total and result["duplicate_rate"] > 0.001:
        raise ValueError(
            f"{stage}: duplicate rate {result['duplicate_rate']:.4%} exceeds 0.1%"
        )
    operated_total = int(operated.sum())
    if operated_total and result["missing_arr_delay"] / operated_total > 0.05:
        raise ValueError(
            f"{stage}: more than 5% of operated flights lack an arrival delay"
        )

    return result


def summarise_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Per-year row counts and headline statistics, for the validation report."""
    base = completed(df)
    grouped = base.groupby("year", observed=True)
    report = pd.DataFrame({
        "completed_flights": grouped.size(),
        "mean_arr_delay": grouped["arr_delay"].mean().round(3),
        "median_arr_delay": grouped["arr_delay"].median().round(3),
        "share_delayed_15": grouped["arr_delay"].apply(
            lambda s: float((s >= 15).mean())
        ).round(5),
        "share_delayed_60": grouped["arr_delay"].apply(
            lambda s: float((s >= 60).mean())
        ).round(5),
    })
    if {"cancelled"}.issubset(df.columns):
        report["cancelled_flights"] = df.groupby("year", observed=True)["cancelled"].apply(
            lambda s: int((s.fillna(0) == 1).sum())
        )
    return report.reset_index()


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove repeated legs, keeping the first occurrence."""
    keys = [c for c in schema.KEY_COLUMNS if c in df.columns]
    if not keys:
        return df
    before = len(df)
    out = df.drop_duplicates(subset=keys, keep="first")
    removed = before - len(out)
    if removed:
        print(f"[clean] dropped {removed:,} duplicate rows")
    return out
