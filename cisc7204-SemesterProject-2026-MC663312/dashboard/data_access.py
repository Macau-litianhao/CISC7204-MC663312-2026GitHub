"""Dashboard data access: one cached frame, cheap filters, no recomputation on import.

The dashboard never re-reads the Parquet on a callback. It loads a bounded frame
once (``dashboard.max_rows``), and every panel filters that frame in memory. The
bound matters: a 70-million-row table in a browser-facing callback would make
each filter change take seconds, and a dashboard that lags is a dashboard nobody
uses. The sampled frame covers every completed flight in the filtered years at a
size where a filter change is bounded by measured backend timings; browser latency is separately unverified.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from team01 import config, io, schema, attribution, models  # noqa: E402

COLUMNS = [
    "year", "month", "day", "dow", "flight_date", "carrier", "origin",
    "origin_state", "dest", "dep_hour", "arr_delay", "arr_delay_min",
    "distance", "cancelled", "diverted",
    *schema.CAUSE_COLUMNS,
]


class DataUnavailable(RuntimeError):
    """Raised when no flight table exists for the active mode."""


@lru_cache(maxsize=1)
def load_frame() -> pd.DataFrame:
    """Bounded analysis frame, cached for the life of the process."""
    try:
        if config.mode() == "full" and not models.load_metrics("validation"):
            raise DataUnavailable("Build validated source evidence before starting the dashboard")
        limit = int(config.get("dashboard.max_rows", 400_000))
        source = config.flights_file()
        cache = source.parent / 'dashboard_sample.parquet'
        cache_meta = cache.with_suffix('.json')
        stat = source.stat()
        signature = {'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,
                     'seed':config.seed(),'limit':limit,'columns':COLUMNS,'sampling_version':3}
        try:
            valid = cache.exists() and json.loads(cache_meta.read_text(encoding='utf-8')) == signature
        except (OSError,ValueError):
            valid = False
        if valid:
            frame = pd.read_parquet(cache)
        else:
            frame = io.sample_completed(COLUMNS,limit)
            frame.to_parquet(cache,index=False)
            cache_meta.write_text(json.dumps(signature),encoding='utf-8')
    except FileNotFoundError as error:
        raise DataUnavailable(str(error)) from error

    frame = frame[(frame["cancelled"].fillna(0) == 0) & (frame["diverted"].fillna(0) == 0)]
    frame = frame[frame["arr_delay"].notna()]

    limit = int(config.get("dashboard.max_rows", 400_000))
    if len(frame) > limit:
        frame = frame.sample(limit, random_state=config.seed())
    return frame.sort_values("flight_date").reset_index(drop=True)


@lru_cache(maxsize=1)
def panel_completed() -> int:
    """Completed flights in the whole panel, not the dashboard sample.

    ``validation.json`` (stage 02) records the true count; the header and the
    method section quote it so the page never presents the bounded sample as the
    full panel. Falls back to the sampled size when the artefact is missing or
    belongs to another mode (e.g. the dashboard is opened before ``make
    validate`` ran, or after switching modes).
    """
    metric = Path(config.METRIC_DIR) / "validation.json"
    if metric.exists():
        try:
            payload = models.load_metrics("validation")
            if payload.get("mode") == config.mode():
                total = payload.get("completed_flights")
                if total:
                    return int(total)
        except (json.JSONDecodeError, ValueError):
            pass
    return int(len(load_frame()))


def available() -> dict:
    """Filter options and the true panel size for the layout.

    ``rows`` is the sampled frame the charts draw; ``total_rows`` is the full
    completed-flight count the header states. The two differ in full mode by
    design (``dashboard.max_rows``), and the page must not present the sample as
    if it were the panel.
    """
    frame = load_frame()
    return {
        "years": sorted(int(y) for y in frame["year"].unique()),
        "carriers": sorted(frame["carrier"].astype("string").unique().tolist()),
        "airports": sorted(frame['origin'].astype('string').unique().tolist()),
        "months": list(range(1, 13)),
        "rows": int(len(frame)),
        "total_rows": panel_completed(),
        "mode": config.mode(),
    }


def apply_filters(year: int | str | None, carriers: list[str] | None,
                  months: list[int] | None) -> pd.DataFrame:
    """Subset the cached frame. ``None`` or empty means 'no constraint'."""
    frame = load_frame()
    if year not in (None, "all", ""):
        frame = frame[frame["year"] == int(year)]
    if carriers:
        frame = frame[frame["carrier"].astype("string").isin(carriers)]
    if months:
        frame = frame[frame["month"].isin(months)]
    return frame


# --------------------------------------------------------------------------
# Panel aggregates
# --------------------------------------------------------------------------
def kpis(frame: pd.DataFrame) -> list[dict]:
    """Headline numbers, recomputed for the current filter.

    The flight count is a count of whatever frame it was handed. In full mode
    that frame is the bounded sample, not the panel, so labelling it
    "completed" put a second, much smaller total on the same screen as the
    header's 61.7 million and left the reader to guess whether one of them was
    wrong. The note now names the sample it came from.
    """
    if frame.empty:
        return [{"label": "No flights", "value": "-", "note": "adjust the filters"}]
    delay = frame["arr_delay"]
    return [
        {"label": "Flights", "value": f"{len(frame):,}",
         "note": _flights_note(len(frame))},
        {"label": "Mean delay", "value": f"{delay.mean():+.1f} min",
         "note": "negative = early; positive = late"},
        {"label": "Median delay", "value": f"{delay.median():+.1f} min",
         "note": "middle flight; negative = early"},
        {"label": "Delayed 60+", "value": f"{(delay >= 60).mean():.1%}",
         "note": "of sampled completed flights"},
        {"label": "p90 delay", "value": f"{delay.quantile(0.9):.0f} min",
         "note": "90% arrive by this; 10% later"},
    ]


def _flights_note(counted: int) -> str:
    """What the flight count on the first card actually counted.

    Three cases, and the note has to separate them or it answers nothing: the
    whole panel (sample mode off, or a sample as large as the panel), the whole
    sample (no filter), and a slice of the sample (a filter is active). Only
    the first may say "completed" without qualification.
    """
    try:
        sample = len(load_frame())
        total = panel_completed()
    except DataUnavailable:  # pragma: no cover - kpis only runs with a frame
        return "completed"
    if not (total and sample and total > sample):
        return "completed"
    if counted >= sample:
        return f"sample of {total / 1e6:.1f}M"
    return f"of {sample / 1000:.0f}k sample"


def cause_mix(frame: pd.DataFrame) -> pd.DataFrame:
    """Attributed minutes by cause, scoped to the reporting universe."""
    universe, _ = attribution.cause_population(frame)
    totals = universe[list(schema.CAUSE_COLUMNS)].sum()
    out = pd.DataFrame({
        "cause": [schema.CAUSE_LABELS_LONG[c] for c in totals.index],
        "cause_key": totals.index,
        "minutes": totals.values,
    })
    out["share"] = out["minutes"] / out["minutes"].sum() if out["minutes"].sum() else 0
    out["family"] = out["cause_key"].map(schema.CAUSE_FAMILY)
    return out.sort_values("minutes", ascending=False)


def monthly_profile(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby("month", observed=True)["arr_delay"]
    table = pd.DataFrame({
        "median": grouped.median(),
        "mean": grouped.mean(),
        "p90": grouped.quantile(0.90),
        "share_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    })
    return table.reindex(range(1, 13))


def composition_by_month(frame: pd.DataFrame) -> pd.DataFrame:
    """Monthly shares of the five causes, on the attribution universe only.

    Months with no attributed minutes are dropped rather than filled with zero:
    a zero-filled month would draw the stacked area down to the axis and read as
    "no delay", when the truth is "no data in this filter".
    """
    universe, _ = attribution.cause_population(frame)
    sums = universe.groupby("month", observed=True)[list(schema.CAUSE_COLUMNS)].sum()
    totals = sums.sum(axis=1)
    sums = sums[totals > 0]
    if sums.empty:
        return sums
    return sums.div(sums.sum(axis=1), axis=0)


def hourly_profile(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby("dep_hour", observed=True)["arr_delay"]
    table = pd.DataFrame({
        "mean": grouped.mean(),
        "share_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    })
    return table.reindex(range(24))


def state_profile(frame: pd.DataFrame) -> pd.DataFrame:
    """Map fill covers the 50 states plus DC; KPIs retain territory flights."""
    states = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
    frame=frame.loc[frame['origin_state'].isin(states)]
    grouped = frame.groupby("origin_state", observed=True)["arr_delay"]
    out = pd.DataFrame({
        "mean": grouped.mean(),
        "share_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    })
    return out.reset_index()


def airport_profile(frame: pd.DataFrame, top_n: int = 120) -> pd.DataFrame:
    grouped = frame.groupby("origin", observed=True)["arr_delay"]
    out = pd.DataFrame({
        "mean": grouped.mean(),
        "share_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    }).reset_index()
    return out.nlargest(top_n, "flights")


def risk_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Observed share delayed 60+ by month and departure hour."""
    pivot = (
        frame.assign(severe=(frame["arr_delay"] >= 60).astype("float32"))
        .pivot_table(index="dep_hour", columns="month", values="severe", aggfunc="mean")
        .reindex(index=range(24), columns=range(1, 13))
    )
    return pivot


@lru_cache(maxsize=1)
def airport_clusters() -> pd.DataFrame | None:
    """Labelled airports written by the clustering stage, if it has run."""
    path = config.airports_clustered_file()
    if not path.exists():
        return None
    models.load_metrics("clusters")
    return pd.read_csv(path)


def delay_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Binned delay histogram with the zero line marked."""
    return frame.loc[:, ["arr_delay"]].clip(-60, 240)


def lorenz_curve(frame: pd.DataFrame, points: int = 240) -> dict:
    """Cumulative share of positive delay minutes against share of flights.

    Flights are ranked worst first, so ``x = 0.01`` reads "the worst 1% of
    flights" and ``y`` is the share of all delay minutes they carry. Only
    positive minutes count: an early arrival does not offset a late one, which
    is why the curve can rise above the equality line at all.

    Returns points thinned for plotting plus the headline shares, so the panel
    and its annotation cannot disagree.
    """
    minutes = np.clip(frame["arr_delay"].to_numpy(dtype="float64"), 0.0, None)
    n = int(minutes.size)
    total = float(minutes.sum())
    if n == 0 or total <= 0:
        return {"x": [], "y": [], "top": {}, "gini": float("nan"),
                "n": n, "total_minutes": total}

    ordered = np.sort(minutes)[::-1]
    cum = np.cumsum(ordered) / total
    x = np.arange(1, n + 1) / n

    ascending = ordered[::-1]
    rank = np.arange(1, n + 1)
    gini = float(((2 * rank - n - 1) * ascending).sum() / (n * ascending.sum()))

    top = {share: float(cum[max(int(np.ceil(share * n)) - 1, 0)])
           for share in (0.01, 0.05, 0.10)}

    keep = np.unique(np.concatenate(
        [[0], np.linspace(0, n - 1, min(points, n)).astype(int)]))
    return {
        "x": np.concatenate([[0.0], x[keep]]).tolist(),
        "y": np.concatenate([[0.0], cum[keep]]).tolist(),
        "top": top,
        "gini": gini,
        "n": n,
        "total_minutes": total,
    }


def carrier_profile(frame: pd.DataFrame, min_flights: int = 200) -> pd.DataFrame:
    """Per-carrier mean, median and tail, thinnest carriers dropped.

    The dashboard used to offer a carrier filter with nothing to compare the
    selected carrier against. This is the other half of that control.
    """
    grouped = frame.groupby("carrier", observed=True)["arr_delay"]
    out = pd.DataFrame({
        "mean": grouped.mean(),
        "median": grouped.median(),
        "p90": grouped.quantile(0.90),
        "share_60": grouped.apply(lambda s: float((s >= 60).mean())),
        "flights": grouped.size(),
    }).reset_index()
    out = out[out["flights"] >= min_flights]
    return out.sort_values("mean").reset_index(drop=True)


