"""
data_access.py - One place where the dashboard turns the cube into numbers.

The dashboard must never read the 7-million-row parquet: it filters the
pre-aggregated cube and *recomputes* metrics from sums. Only summable measures
can live in a cube, which is why the dashboard reports mean delay and tail
probabilities (both summable) rather than median or p90 (not summable).

Author: LI Tianhao (mc663312), LI Yingfang (mc661599)
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from common import CAUSE_COLS, MINS, PROCESSED_DIR

CARRIER_NAME = {
    "9E": "Endeavor Air", "AA": "American", "AS": "Alaska", "B6": "JetBlue",
    "DL": "Delta", "F9": "Frontier", "G4": "Allegiant", "HA": "Hawaiian",
    "MQ": "Envoy Air", "NK": "Spirit", "OH": "PSA Airlines", "OO": "SkyWest",
    "UA": "United", "WN": "Southwest", "YX": "Republic",
}

MONTH_NAME = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
              7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

DIST_BANDS = ["<250", "250-500", "500-750", "750-1k", "1k-1.5k",
              "1.5k-2.5k", ">2.5k"]

SUM_COLS = ["flights", "sum_delay", "sum_delay_min", "n60", "n180",
            "min_total"] + CAUSE_COLS


@lru_cache(maxsize=1)
def load_cube() -> pd.DataFrame:
    """The full (month x carrier x hour x band) cube, loaded once."""
    agg = pd.read_pickle(PROCESSED_DIR / "aggregates.pkl")
    cube = agg["cube"].copy()
    cube["dist_band"] = pd.Categorical(cube["dist_band"], categories=DIST_BANDS,
                                       ordered=True)
    cube["carrier_name"] = (cube["Reporting_Airline"].astype(str)
                            .map(CARRIER_NAME)
                            .fillna(cube["Reporting_Airline"].astype(str)))
    return cube


@lru_cache(maxsize=1)
def headline() -> pd.Series:
    return pd.read_pickle(PROCESSED_DIR / "aggregates.pkl")["headline"]


@lru_cache(maxsize=1)
def load_state_cube() -> pd.DataFrame:
    """Second cube: same measures, but grouped by destination state.

    It exists so the dashboard's state panel can honour the month, carrier and
    hour filters instead of showing a national picture underneath a local
    filter.
    """
    agg = pd.read_pickle(PROCESSED_DIR / "aggregates.pkl")
    cube = agg["cube_state"].copy()
    cube["carrier_name"] = (cube["Reporting_Airline"].astype(str)
                            .map(CARRIER_NAME)
                            .fillna(cube["Reporting_Airline"].astype(str)))
    return cube


def _apply(df: pd.DataFrame, months, carriers, hours, bands) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if months:
        mask &= df["Month"].isin(months)
    if carriers:
        mask &= df["Reporting_Airline"].astype(str).isin(carriers)
    if hours:
        lo, hi = hours
        mask &= df["dep_hour"].between(lo, hi)
    if bands and "dist_band" in df.columns:
        mask &= df["dist_band"].isin(bands)
    return df[mask]


def slice_cube(months=None, carriers=None, hours=None, bands=None) -> pd.DataFrame:
    """Apply the dashboard filters to the band cube. None means no restriction."""
    return _apply(load_cube(), months, carriers, hours, bands)


def slice_state(months=None, carriers=None, hours=None) -> pd.DataFrame:
    """Apply the same filters to the state cube."""
    return _apply(load_state_cube(), months, carriers, hours, None)


def kpis(sub: pd.DataFrame) -> dict:
    """Aggregate the filtered cube into the numbers shown on the cards."""
    total = sub[SUM_COLS].sum()
    flights = total["flights"]
    if not flights:
        return {"flights": 0, "mean_delay": np.nan, "pct60": np.nan,
                "pct180": np.nan, "internal_share": np.nan,
                "min_total": 0, "delay_min_per_flight": np.nan}
    return {
        "flights": int(flights),
        "mean_delay": total["sum_delay"] / flights,
        "pct60": total["n60"] / flights * 100,
        "pct180": total["n180"] / flights * 100,
        "internal_share": ((total["CarrierDelay"] + total["LateAircraftDelay"])
                           / total["min_total"] * 100
                           if total["min_total"] else np.nan),
        "min_total": float(total["min_total"]),
        "delay_min_per_flight": float(total["min_total"] / flights),
    }


def by_dimension(sub: pd.DataFrame, dim: str) -> pd.DataFrame:
    """Group the filtered cube by one dimension and recompute the metrics."""
    grouped = sub.groupby(dim, observed=True)[SUM_COLS].sum().reset_index()
    grouped = grouped[grouped["flights"] > 0]
    grouped["mean_delay"] = grouped["sum_delay"] / grouped["flights"]
    grouped["pct60"] = grouped["n60"] / grouped["flights"] * 100
    grouped["pct180"] = grouped["n180"] / grouped["flights"] * 100
    grouped["delay_min_per_flight"] = grouped["min_total"] / grouped["flights"]
    grouped["internal_share"] = np.where(
        grouped["min_total"] > 0,
        (grouped["CarrierDelay"] + grouped["LateAircraftDelay"])
        / grouped["min_total"] * 100, np.nan)
    return grouped


def cause_shares(sub: pd.DataFrame) -> pd.DataFrame:
    """Cause minutes as percentages, in the canonical cause order."""
    totals = sub[CAUSE_COLS].sum()
    denom = totals.sum()
    shares = ((totals / denom * 100).to_numpy() if denom
              else np.zeros(len(totals)))
    return pd.DataFrame({
        "cause": [c.replace("Delay", "") for c in CAUSE_COLS],
        "column": CAUSE_COLS,
        "share": shares,
        "minutes": totals.to_numpy(),
    })
