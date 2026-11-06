"""Tail behaviour and concentration.

The pilot project's most quotable finding was that the mean delay (+7.1 min)
and the median (-6.0 min) tell different stories, and that the worst 1% of
flights carry a quarter of all delay minutes. This module turns those two
sentences into reproducible statistics:

* ``percentile_profile``  - the distribution, including the percentile at which
  the mean sits, which is the cleanest one-number argument against reporting
  an average.
* ``lorenz``              - the concentration curve plus the Gini-style
  coefficient and the top-1% share.
* ``mean_vs_tail``        - whether the "mean understates the tail" hypothesis
  actually holds across months. In the pilot it did not (r = 0.998), and a
  reported null result is worth more than an unreported one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

PERCENTILES = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]


def percentile_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Arrival-delay percentiles with the mean and its own percentile rank."""
    delay = df["arr_delay"].dropna().to_numpy(dtype="float32")
    if delay.size == 0:
        return pd.DataFrame(columns=["statistic", "value"])

    rows = [{"statistic": f"p{p}", "value": round(float(np.percentile(delay, p)), 2)}
            for p in PERCENTILES]
    mean = float(delay.mean())
    rows.append({"statistic": "mean", "value": round(mean, 2)})
    rows.append({"statistic": "median", "value": round(float(np.median(delay)), 2)})
    rows.append({"statistic": "mean_percentile_rank",
                 "value": round(float((delay < mean).mean() * 100), 1)})
    rows.append({"statistic": "share_late_15",
                 "value": round(float((delay >= 15).mean()), 5)})
    rows.append({"statistic": "share_late_60",
                 "value": round(float((delay >= 60).mean()), 5)})
    rows.append({"statistic": "share_late_180",
                 "value": round(float((delay >= 180).mean()), 5)})
    return pd.DataFrame(rows)


def severe_shares(df: pd.DataFrame) -> dict:
    """Shares of completed flights above the reporting and the severe thresholds."""
    delay = df["arr_delay"].dropna()
    return {
        "flights": int(delay.size),
        "share_late_15": round(float((delay >= 15).mean()), 5),
        "share_late_60": round(float((delay >= 60).mean()), 5),
        "share_late_180": round(float((delay >= 180).mean()), 5),
    }


def lorenz(df: pd.DataFrame, sample_rows: int | None = None,
           seed: int | None = None, points: int = 101) -> dict:
    """Concentration of positive delay minutes across flights.

    Flights are ordered from the worst offender down, so the curve answers
    "what share of minutes sits in the worst x% of flights". ``sample_rows``
    caps memory: sorting seventy million floats is possible but pointless when
    a fixed-seed sample reproduces the coefficient to three decimals.
    """
    delay = df["arr_delay_min"].to_numpy(dtype="float64", copy=True)
    delay = np.nan_to_num(delay, nan=0.0)
    delay = np.clip(delay, 0, None)

    if sample_rows and delay.size > sample_rows:
        rng = np.random.default_rng(config.seed() if seed is None else seed)
        delay = delay[rng.choice(delay.size, size=sample_rows, replace=False)]

    total = delay.sum()
    if total <= 0:
        return {"curve": pd.DataFrame(), "gini": np.nan, "top1_share": np.nan}

    ordered = np.sort(delay)[::-1]
    cumulative = np.cumsum(ordered) / total
    share_of_flights = np.arange(1, ordered.size + 1) / ordered.size

    grid = np.linspace(0, 1, points)
    curve = pd.DataFrame({
        "share_of_flights": grid,
        "share_of_minutes": np.interp(grid, np.r_[0, share_of_flights],
                                      np.r_[0, cumulative]),
    })

    # Gini on the ascending order: 1 - 2 * area under the Lorenz curve.
    ascending = np.sort(delay)
    cum = np.cumsum(ascending) / total
    area = np.trapezoid(np.r_[0, cum], np.r_[0, share_of_flights])
    gini = float(1 - 2 * area)

    # Share of minutes produced by the worst 1% of flights.
    top1_cut = max(int(np.ceil(ordered.size * 0.01)), 1)
    top1_share = float(ordered[:top1_cut].sum() / total)

    return {
        "curve": curve,
        "gini": round(gini, 4),
        "top1_share": round(top1_share, 4),
        "top5_share": round(float(ordered[: max(int(np.ceil(ordered.size * 0.05)), 1)].sum() / total), 4),
        "flights": int(ordered.size),
    }


def mean_vs_tail(df: pd.DataFrame, by: str = "month") -> dict:
    """Correlate mean delay with severe-delay share across groups.

    High correlation (the pilot found r = 0.998) means the mean and the tail
    move together at this level of aggregation: the "mean hides the tail"
    claim holds for individual flights but not between months. Reporting that
    honestly is a finding, not a failure.
    """
    grouped = df.groupby(by, observed=True)["arr_delay"]
    frame = pd.DataFrame({
        "mean_delay": grouped.mean(),
        "share_delayed_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    }).reset_index()

    if len(frame) < 3:
        # A one-month download gives a single group, so no correlation exists.
        # The verdict key is always present: callers print it unconditionally.
        return {"table": frame, "pearson_r": np.nan, "spearman_r": np.nan,
                "verdict": f"not testable with {len(frame)} group(s)"}

    pearson = float(frame["mean_delay"].corr(frame["share_delayed_60"]))
    spearman = float(frame["mean_delay"].corr(frame["share_delayed_60"], method="spearman"))
    return {
        "table": frame,
        "pearson_r": round(pearson, 4),
        "spearman_r": round(spearman, 4),
        "verdict": "no paradox" if pearson > 0.95 else "divergence present",
    }


def monthly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Mean, median, p90 and severe share per month - the percentile-band figure."""
    grouped = df.groupby("month", observed=True)["arr_delay"]
    table = pd.DataFrame({
        "mean": grouped.mean().round(2),
        "median": grouped.median().round(2),
        "p90": grouped.quantile(0.90).round(1),
        "p99": grouped.quantile(0.99).round(1),
        "share_delayed_60": grouped.apply(lambda s: float((s >= 60).mean())).round(4),
        "flights": grouped.size(),
    }).reset_index()
    table["month_label"] = table["month"].map(
        dict(enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1))
    )
    return table


def delay_burden(df: pd.DataFrame) -> dict:
    """How many minutes the average flight contributes, and how unevenly."""
    delay = df["arr_delay_min"].fillna(0).to_numpy(dtype="float64")
    positive = delay[delay > 0]
    return {
        "flights": int(delay.size),
        "total_positive_minutes": round(float(positive.sum()), 0),
        "mean_minutes_per_flight": round(float(delay.mean()), 3),
        "mean_minutes_per_delayed_flight": round(float(positive.mean()), 3),
        "delayed_flight_share": round(float(positive.size / delay.size), 4),
    }
