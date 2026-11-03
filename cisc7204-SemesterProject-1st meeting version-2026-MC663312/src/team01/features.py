"""Feature engineering: the within-day cascade and the airport feature matrix.

Two derived structures carry most of the new analytical content of the team
project, and both are built here rather than inside a notebook so that the
dashboard uses exactly the same definition as the report.

Cascade
-------
BTS reports ``min_late_aircraft`` as a cause, which is a label rather than a
mechanism. Reconstructing the aircraft rotation turns it into a quantity: for
each tail number ordered by scheduled departure, the delay of the previous leg
minus the scheduled turnaround buffer is the delay that the next leg *cannot*
avoid. Summing that over a day gives the inherited share of the delay observed.

Airport matrix
--------------
One row per origin airport, ten features covering scale, central tendency, tail
risk, cause mix, seasonality and hub stratum. This is the input to the clustering
stage, and the reason clustering is defensible: the features are on different
scales, standardised before the distance is computed, and reported with a
silhouette score instead of a fixed k.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calendar fields used by seasonal and weekday comparisons."""
    out = df
    out["year_month"] = out["flight_date"].dt.to_period("M")
    out["week"] = out["flight_date"].dt.isocalendar().week.astype("int16")
    # Ordered hour axis: 0-23 read clockwise, which is what a line cascade needs.
    out["dep_hour"] = out["dep_hour"].astype("int8")
    return out


def add_panel_controls(df: pd.DataFrame) -> pd.DataFrame:
    """Columns that absorb the panel's two regime breaks.

    A ten-year panel is not one population. Traffic collapsed in 2020-2021 and
    the delay mix collapsed with it, so a pooled coefficient is a weighted
    average of two regimes presented as a single number. Two controls fix that
    without throwing the years away:

    ``year``       a fixed effect per calendar year, absorbing the long trend;
    ``covid_era``  a dummy for 2020-03-01 to 2021-12-31, absorbing the break
                   that a linear trend cannot describe.

    The years stay in the panel because they are the only observations of an
    extreme operating condition, and the sensitivity analysis recomputes the
    headline numbers without them rather than choosing one version silently.
    """
    out = df
    if "year" not in out.columns:
        out["year"] = out["flight_date"].dt.year.astype("int16")

    start = pd.Timestamp(config.get("panel.covid_start", "2020-03-01"))
    end = pd.Timestamp(config.get("panel.covid_end", "2021-12-31"))
    out["covid_era"] = (
        (out["flight_date"] >= start) & (out["flight_date"] <= end)
    ).astype("int8")
    return out


def distance_band(df: pd.DataFrame, bins: int = 5) -> pd.Series:
    """Quantile bands of route distance, labelled in statute miles."""
    labels = ["<500", "500-900", "900-1400", "1400-2000", ">2000"]
    if bins != 5:
        return pd.qcut(df["distance"], q=bins, duplicates="drop")
    edges = [-np.inf, 500, 900, 1400, 2000, np.inf]
    return pd.cut(df["distance"], bins=edges, labels=labels, right=False)


# --------------------------------------------------------------------------
# Within-day cascade
# --------------------------------------------------------------------------
def leg_sequence(df: pd.DataFrame, min_turnaround_min: int = 25) -> pd.DataFrame:
    """Attach previous-leg delay and the unavoidable inherited delay.

    ``min_turnaround_min`` is the shortest workable ground time for a domestic
    narrow-body rotation (deplaning, cleaning, fuelling, boarding). A previous
    leg that lands inside that window transfers delay; one that lands earlier
    does not.

    Returns a copy with four new columns:
        prev_arr_delay    minutes late the same aircraft arrived on its last leg
        scheduled_turn    scheduled ground time between the two legs (minutes)
        ground_time_actual actual ground time achieved (minutes)
        inherited_min     delay the leg could not avoid (>= 0)
    """
    columns = ["tail_number", "flight_date", "sched_dep_dt", "sched_arr_dt",
               "actual_arr_dt", "arr_delay", "origin", "dest", "carrier",
               "dep_hour", "cancelled", "diverted"]
    work = df[[c for c in columns if c in df.columns]].copy()

    work = work.sort_values(["tail_number", "sched_dep_dt"], kind="mergesort")
    grouped = work.groupby("tail_number", observed=True, sort=False)

    work["prev_arr_delay"] = grouped["arr_delay"].shift(1)
    work["prev_actual_arr_dt"] = grouped["actual_arr_dt"].shift(1)
    work["prev_sched_arr_dt"] = grouped["sched_arr_dt"].shift(1)
    work["prev_dest"] = grouped["dest"].shift(1)

    work["scheduled_turn"] = (
        (work["sched_dep_dt"] - work["prev_sched_arr_dt"]).dt.total_seconds() / 60
    )
    work["ground_time_actual"] = (
        (work["sched_dep_dt"] - work["prev_actual_arr_dt"]).dt.total_seconds() / 60
    )

    # A rotation is only valid when the aircraft continues from where it landed
    # and the gap is a plausible ground time rather than a multi-day park.
    continues = (
        work["origin"].astype("string") == work["prev_dest"].astype("string")
    ).fillna(False)
    plausible = work["scheduled_turn"].between(15, 24 * 60)
    work["is_rotation"] = continues & plausible

    inherit = work["prev_arr_delay"] - (work["scheduled_turn"] - min_turnaround_min)
    work["inherited_min"] = np.where(
        work["is_rotation"], np.clip(inherit.fillna(0), 0, None), 0.0
    )
    work["inherited_min"] = work["inherited_min"].astype("float32")

    return work


def cascade_summary(legs: pd.DataFrame, df: pd.DataFrame) -> dict:
    """Panel-level answer to RQ2: how much delay is inherited, and where."""
    rotations = legs.loc[legs["is_rotation"] & legs["arr_delay"].notna()]
    total_delay = float(rotations["arr_delay"].clip(lower=0).sum())
    inherited = float(rotations["inherited_min"].sum())
    share = inherited / total_delay if total_delay else np.nan

    # Hourly profile: share of positive delay minutes that were inherited.
    hourly = (
        rotations.assign(positive=rotations["arr_delay"].clip(lower=0))
        .groupby("dep_hour", observed=True)
        .agg(delay_min=("positive", "sum"), inherited_min=("inherited_min", "sum"),
             flights=("arr_delay", "size"))
    )
    hourly["inherited_share"] = (
        hourly["inherited_min"] / hourly["delay_min"].replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan).fillna(0.0).round(4)
    hourly["mean_inherited"] = (hourly["inherited_min"] / hourly["flights"]).round(2)

    by_airport = (
        rotations.assign(positive=rotations["arr_delay"].clip(lower=0))
        .groupby("origin", observed=True)
        .agg(delay_min=("positive", "sum"), inherited_min=("inherited_min", "sum"),
             rotations=("arr_delay", "size"))
    )
    by_airport["inherited_share"] = (
        by_airport["inherited_min"] / by_airport["delay_min"].replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan).fillna(0.0).round(4)
    by_airport = by_airport[by_airport["rotations"] >= 5000]
    by_airport = by_airport.sort_values("inherited_share", ascending=False)

    return {
        "rotations": int(len(rotations)),
        "rotation_share_of_flights": round(float(len(rotations) / len(df)), 5),
        "positive_delay_minutes": round(total_delay, 1),
        "inherited_minutes": round(inherited, 1),
        "inherited_share": round(share, 4) if pd.notna(share) else np.nan,
        "hourly": hourly.reset_index(),
        "by_airport": by_airport.reset_index(),
    }


# --------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------
def merge_weather(df: pd.DataFrame, weather: pd.DataFrame,
                  tolerance: str = "90min") -> pd.DataFrame:
    """As-of join of hourly observations to each scheduled departure.

    ``merge_asof`` is the right tool because the nearest observation before
    departure is the relevant one and both sides are time sorted. Without a
    weather file the function returns the input unchanged and says so, which
    keeps the weather stage optional (see Section 11 of the proposal).
    """
    if weather.empty:
        print("[features] no weather table found - weather covariates skipped")
        return df

    obs = weather.rename(columns={"station": "origin"}).copy()
    obs["obs_hour"] = pd.to_datetime(obs["obs_hour"])
    obs = obs.sort_values("obs_hour")

    work = df.sort_values("sched_dep_dt").copy()
    merged = pd.merge_asof(
        work, obs, left_on="sched_dep_dt", right_on="obs_hour", by="origin",
        direction="backward", tolerance=pd.Timedelta(tolerance),
    )
    weather_cols = [c for c in ("wind_speed_kt", "visibility_mi", "precip_mm", "temp_c")
                    if c in merged.columns]
    coverage = float(merged[weather_cols].notna().all(axis=1).mean()) if weather_cols else 0.0
    print(f"[features] weather coverage {coverage:.1%} across {len(weather_cols)} covariates")
    return merged


# --------------------------------------------------------------------------
# Airport feature matrix
# --------------------------------------------------------------------------
def airport_feature_matrix(df: pd.DataFrame, airports: pd.DataFrame,
                           min_departures: int | None = None,
                           sample_rows: int | None = None,
                           seed: int | None = None) -> pd.DataFrame:
    """One row per origin airport with the ten clustering features.

    ``sample_rows`` exists because a group-wise quantile over seventy million
    rows costs minutes; on the sample the tail estimates are within a minute of
    the full-panel values, which is stated in the report.
    """
    floor = int(config.get("cluster.min_departures", 20000) if min_departures is None
                else min_departures)
    rng = np.random.default_rng(config.seed() if seed is None else seed)
    base = df
    if sample_rows and len(base) > sample_rows:
        idx = rng.choice(len(base), size=sample_rows, replace=False)
        base = base.iloc[np.sort(idx)]

    grouped = base.groupby("origin", observed=True)
    features = pd.DataFrame({
        "n_dep": grouped.size(),
        "mean_arr_delay": grouped["arr_delay"].mean(),
        "p90_arr_delay": grouped["arr_delay"].quantile(0.90),
        "share_delayed_60": grouped["arr_delay"].apply(lambda s: float((s >= 60).mean())),
    })

    # Cause mix, defined on the attribution universe only.
    universe = base.loc[base["arr_delay"] >= config.threshold()]
    cause_sums = universe.groupby("origin", observed=True)[schema.CAUSE_COLUMNS].sum()
    total = cause_sums.sum(axis=1).replace(0, np.nan)
    features["share_internal"] = (
        (cause_sums["min_carrier"] + cause_sums["min_late_aircraft"]) / total
    )
    features["share_late_aircraft"] = cause_sums["min_late_aircraft"] / total
    features["share_nas"] = cause_sums["min_nas"] / total
    features["share_weather"] = cause_sums["min_weather"] / total

    # Seasonality: the spread between the worst and the best month.
    monthly = (
        base.groupby(["origin", "month"], observed=True)["arr_delay"].mean()
        .unstack("month")
    )
    features["seasonal_amplitude"] = monthly.max(axis=1) - monthly.min(axis=1)

    features = features[features["n_dep"] >= floor]
    features = features.join(
        airports.set_index("ident")[["latitude_deg", "longitude_deg", "type",
                                     "municipality", "name"]],
        how="left",
    )
    features["hub_stratum"] = features["type"].map(schema.HUB_STRATUM).astype("float32")

    # Airports missing from the reference file cannot be mapped; they are kept
    # with a neutral stratum so the clustering still sees their delay profile.
    features["hub_stratum"] = features["hub_stratum"].fillna(2.0)

    numeric = [c for c in schema.AIRPORT_FEATURES if c in features.columns]
    features[numeric] = features[numeric].fillna(features[numeric].median())

    return features.reset_index().rename(columns={"index": "origin"})
