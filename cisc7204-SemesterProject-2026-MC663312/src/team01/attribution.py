"""Delay attribution: where the minutes come from, and whether that is stable.

The pilot grouped carrier + late-aircraft minutes against other reported causes.
These are descriptive categories, not control or responsibility. A single year cannot tell a structural pattern from a
one-year operational shock, so this module attaches a bootstrap interval to the
split and recomputes it year by year.

Resampling unit = the operating day, not the flight. Flights on the same day at
the same airport are not independent (one storm delays hundreds of them), so a
flight-level bootstrap would produce an interval that is far too narrow.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema


def cause_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Total attributed minutes and share per cause, ordered by size."""
    df, _ = cause_population(df)
    totals = df[schema.CAUSE_COLUMNS].sum().rename("minutes").to_frame()
    totals["cause"] = totals.index.map(schema.CAUSE_LABELS)
    totals["family"] = totals.index.map(schema.CAUSE_FAMILY)
    totals["share"] = totals["minutes"] / totals["minutes"].sum()
    return totals.sort_values("minutes", ascending=False).reset_index(names="cause_key")


def family_split(df: pd.DataFrame) -> dict:
    """The headline 75/25 split, with the numbers behind it."""
    df, _ = cause_population(df)
    totals = df[schema.CAUSE_COLUMNS].sum()
    internal = float(totals[["min_carrier", "min_late_aircraft"]].sum())
    system = float(totals[["min_nas", "min_weather", "min_security"]].sum())
    grand = internal + system
    return {
        "attributed_minutes": round(grand, 1),
        "internal_minutes": round(internal, 1),
        "system_minutes": round(system, 1),
        "internal_share": round(internal / grand, 4) if grand else np.nan,
        "system_share": round(system / grand, 4) if grand else np.nan,
        "late_aircraft_share": round(float(totals["min_late_aircraft"]) / grand, 4)
        if grand else np.nan,
    }


def bootstrap_family_share(df: pd.DataFrame, reps: int | None = None,
                           seed: int | None = None) -> dict:
    """Percentile bootstrap of the internal share, resampling whole days."""
    df, _ = cause_population(df)
    draws = int(config.get("sampling.bootstrap_reps", 400) if reps is None else reps)
    rng = np.random.default_rng(config.seed() if seed is None else seed)

    daily = (
        df.assign(
            internal=df["min_carrier"] + df["min_late_aircraft"],
            system=df["min_nas"] + df["min_weather"] + df["min_security"],
        )
        .groupby("flight_date", observed=True)[["internal", "system"]]
        .sum()
    )
    if daily.empty:
        return {"share": np.nan, "ci_low": np.nan, "ci_high": np.nan, "reps": 0}

    internal = daily["internal"].to_numpy(dtype="float64")
    total = internal + daily["system"].to_numpy(dtype="float64")
    n = len(internal)

    shares = np.empty(draws)
    for i in range(draws):
        pick = rng.integers(0, n, n)
        denominator = total[pick].sum()
        shares[i] = internal[pick].sum() / denominator if denominator else np.nan

    shares = shares[np.isfinite(shares)]
    return {
        "share": round(float(internal.sum() / total.sum()), 4),
        "ci_low": round(float(np.percentile(shares, 2.5)), 4),
        "ci_high": round(float(np.percentile(shares, 97.5)), 4),
        "reps": int(draws),
        "days": int(n),
    }


def composition_by(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Stacked-composition input: minute shares of the five causes per group."""
    df, _ = cause_population(df)
    sums = df.groupby(by, observed=True)[schema.CAUSE_COLUMNS].sum()
    shares = sums.div(sums.sum(axis=1).replace(0, np.nan), axis=0)
    long = (
        shares.reset_index()
        .melt(id_vars=by, var_name="cause_key", value_name="share")
    )
    long["cause"] = long["cause_key"].map(schema.CAUSE_LABELS)
    long["family"] = long["cause_key"].map(schema.CAUSE_FAMILY)
    return long


def stability_by_year(df: pd.DataFrame, bootstrap: bool = True,
                      reps: int = 200) -> pd.DataFrame:
    """Per-year internal/system share, with an optional interval per year.

    Ten years of an 8-point move is the interesting question: if the interval
    for 2020 clears the interval for 2019, the pandemic year is a genuine
    structural break rather than noise.
    """
    rows = []
    for year, chunk in df.groupby("year", observed=True):
        split = family_split(chunk)
        row = {
            "year": int(year),
            "attributed_minutes": split["attributed_minutes"],
            "internal_share": split["internal_share"],
            "system_share": split["system_share"],
            "late_aircraft_share": split["late_aircraft_share"],
        }
        if bootstrap:
            interval = bootstrap_family_share(chunk, reps=reps)
            row["ci_low"] = interval["ci_low"]
            row["ci_high"] = interval["ci_high"]
        rows.append(row)
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def carrier_table(df: pd.DataFrame, min_flights: int | None = None) -> pd.DataFrame:
    """Carrier comparison: volume, share of minutes and cause mix.

    The floor is read from ``attribution.carrier_min_flights`` (with a fixture
    override) rather than defaulted in the signature: this frame is the
    *attribution universe* - flights delayed 15 minutes or more - which is about
    a fifth of the panel. A hard 5,000 there emptied the table on the fixture
    and silently produced a blank bar chart, so the number now lives in
    ``config/project.yaml`` next to a comment that says which frame it applies
    to.
    """
    df, _ = cause_population(df)
    floor = int(min_flights if min_flights is not None
                else config.get_for_mode("attribution.carrier_min_flights", 5000))
    grouped = df.groupby("carrier", observed=True)
    table = pd.DataFrame({
        "flights": grouped.size(),
        "delay_minutes": grouped[schema.CAUSE_COLUMNS].sum().sum(axis=1),
    })
    cause_sums = grouped[schema.CAUSE_COLUMNS].sum()
    total = cause_sums.sum(axis=1).replace(0, np.nan)
    table["internal_share"] = (
        cause_sums["min_carrier"] + cause_sums["min_late_aircraft"]
    ) / total
    table["late_aircraft_share"] = cause_sums["min_late_aircraft"] / total
    table["minutes_per_flight"] = table["delay_minutes"] / table["flights"]
    dropped = int((table["flights"] < floor).sum())
    largest = int(table["flights"].max()) if len(table) else 0
    table = table[table["flights"] >= floor]
    if table.empty:
        raise ValueError(
            f"no carrier reaches {floor:,} attributed flights "
            f"(largest has {largest:,}); lower attribution.carrier_min_flights"
        )
    print(f"[attribution] carriers kept {len(table)}/{len(table) + dropped} "
          f"at a {floor:,}-flight floor")
    return table.sort_values("minutes_per_flight", ascending=False).reset_index()


def threshold_audit(df: pd.DataFrame) -> pd.DataFrame:
    """Coverage of the cause fields per year, above and below the threshold.

    This is the table the report cites when it says every cause statement is
    scoped to the delayed-flight universe.
    """
    rows = []
    # The BTS rule puts cause minutes on an arrival delay of 15 minutes or more
    # only. These two coverage columns are the evidence for every sentence in
    # the report that starts with "attributed minutes".
    for year, completed in df.groupby("year", observed=True):
        above = completed["arr_delay"] >= config.threshold()
        has_cause = completed[schema.CAUSE_COLUMNS].notna().all(axis=1)
        rows.append({
            "year": int(year),
            "completed": int(len(completed)),
            "above_threshold": int(above.sum()),
            "coverage_above": round(_mean_or_nan(has_cause[above]), 6),
            "coverage_below": round(_mean_or_nan(has_cause[~above]), 6),
        })
    return pd.DataFrame(rows)


def _mean_or_nan(values: pd.Series) -> float:
    """Mean of a possibly empty boolean slice, as a float (NaN when empty)."""
    return float(values.mean()) if len(values) else np.nan


def cause_population(df, tolerance=1.):
    delayed=df.loc[df.arr_delay.ge(config.threshold())]
    values=delayed[schema.CAUSE_COLUMNS].astype('float64')
    known=values.notna().all(axis=1)&np.isfinite(values).all(axis=1)&values.ge(0).all(axis=1)
    reconciled=values.sum(axis=1,min_count=len(schema.CAUSE_COLUMNS)).sub(delayed.arr_delay).abs().le(tolerance)
    good=known&reconciled
    out=delayed.loc[good].copy()
    out[schema.CAUSE_COLUMNS]=values.loc[good]
    return out, {'eligible':len(delayed),'incomplete_or_invalid':int((~known).sum()),
                 'unreconciled':int((known&~reconciled).sum()),'retained':len(out),
                 'unexplained_arrival_minutes':float(delayed.loc[~good,'arr_delay'].sum())}
