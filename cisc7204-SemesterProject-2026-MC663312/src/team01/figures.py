"""Rebuild every figure from committed artefacts, without the flight panel.

The analysis stages each draw their own figures at the end, which is the right
place for them - the code that computes a number is the code that should plot
it. But it means there was no way to re-render a figure after a design change
without re-running a stage over the 6 GB panel, and ``make figures`` only
checked that the files existed. A reviewer who wanted a different colour ramp
had to rebuild the analysis to get it.

This module closes that gap. Every figure is a pure function of the tables in
``outputs/tables`` and the metrics in ``outputs/metrics``, all of which are
committed, so the whole figure set can be redrawn in seconds:

    python src/scripts/07_figures.py --redraw

Two entry points, one source of truth: the stage scripts pass in their live
frames, this module passes in the saved ones, and both call the same functions
in :mod:`team01.viz`. Nothing here recomputes a statistic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pandas as pd

from . import cluster, config, viz


def _table(name: str) -> pd.DataFrame:
    return pd.read_csv(config.TABLE_DIR / f"{name}.csv")


def _metric(name: str) -> dict:
    path = config.METRIC_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _state_values() -> pd.Series:
    frame = _table("mean_delay_by_state")
    return frame.set_index("origin_state")["mean_arr_delay"]


def _concentration() -> dict:
    tail = _metric("tail")["concentration"]
    curve = _table("lorenz_curve")
    return {"gini": tail["gini"], "top1_share": tail["top1_share"], "curve": curve}


def _cluster_names() -> dict[int, str]:
    meta = _metric("clusters")
    return {int(row["cluster"]): row["archetype"] for row in meta["archetypes"]}


def _cluster_stats(labelled: pd.DataFrame) -> dict:
    meta = _metric("clusters")
    k = int(meta["chosen_k"])
    sweep = _table("cluster_k_sweep")
    row = sweep.loc[sweep["k"] == k].iloc[0]
    return {
        "k": k,
        "silhouette": float(row["silhouette"]),
        "ari": float(meta["stability"]["mean_ari"]),
        "airports": int(len(labelled)),
        "pc_variance": cluster.pc_variance(labelled),
    }


def draw(name: str) -> str:
    """Draw one figure by registry name and return its path."""
    if name not in FIGURES:
        raise KeyError(f"{name} is not in the figure registry")
    return FIGURES[name]()


def redraw_all(only: list[str] | None = None) -> list[str]:
    names = only or list(FIGURES)
    return [draw(name) for name in names]


FIGURES: dict[str, Callable[[], str]] = {
    "01_cause_waffle": lambda: viz.fig_cause_waffle(_table("cause_totals")),
    "02_monthly_composition": lambda: viz.fig_monthly_composition(
        _table("composition_by_month")),
    "03_carrier_bars": lambda: viz.fig_carrier_bars(_table("carrier_table")),
    "04_percentile_band": lambda: viz.fig_percentile_band(_table("monthly_profile")),
    "05_lorenz": lambda: viz.fig_lorenz(_concentration()),
    "06_distance_bands": lambda: viz.fig_distance_bands(_table("distance_bands")),
    "07_state_tiles": lambda: viz.fig_state_tile(
        _state_values(), metric_label="Mean arrival delay (min)"),
    "08_cascade_hour": lambda: viz.fig_cascade_hour(
        _table("cascade_by_hour"),
        min_turnaround=int(_metric("rotation_pressure").get("min_turnaround_minutes", 25))),
    "09_silhouette": lambda: viz.fig_silhouette(
        _table("cluster_k_sweep"), int(_metric("clusters")["chosen_k"])),
    "10_cluster_scatter": lambda: viz.fig_cluster_scatter(
        _table("airport_clusters"), _cluster_names(),
        stats=_cluster_stats(_table("airport_clusters"))),
    "11_importance": lambda: viz.fig_importance(_table("risk_permutation_importance")),
    "12_hour_response": lambda: viz.fig_hour_response(
        pd.DataFrame(_metric("risk_evaluation")["risk"]["hour_response"]), threshold=60),
    "14_mean_bar_vs_band": lambda: viz.fig_mean_bar_vs_band(_table("monthly_profile")),
    "15_temporal_validation": lambda: viz.fig_temporal_validation(
        _table("temporal_validation")),
    "16_inference_evidence": lambda: viz.fig_inference_evidence(
        _metric("risk_evaluation")["risk"], _metric("risk_evaluation")["risk"].get(
            "conditional_r2") or _table("factor_conditional_r2").to_dict("records")),
}
