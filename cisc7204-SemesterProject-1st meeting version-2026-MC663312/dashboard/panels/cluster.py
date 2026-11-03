"""Airport archetypes projected onto the first two principal components.

A scatter of coloured groups reads as a discovered typology. The printed
``10_cluster_scatter`` therefore carries k, silhouette and bootstrap ARI in its
title; the web panel used to show the same dots with none of the caveats, which
is the one kind of inconsistency that gets a report questioned - the same claim
stated two different ways. The quality line is read from the JSON that stage 05
already writes, never retyped, so the page cannot quote a number the file does
not contain.

The legend moved from a hard-coded ``y=-0.24`` to ``LEGEND_BELOW`` +
``LEGEND_MARGIN``: at that offset the three-row legend sat on top of the
"Principal component 1" title.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

import data_access as data
from team01 import config, schema

from .theme import INK, LEGEND_BELOW, LEGEND_MARGIN, MUTED, empty, finish


@lru_cache(maxsize=1)
def quality_line() -> str:
    """The cluster solution's own quality measures, as one line of text.

    Cached because a filter change rebuilds every panel while the file is a
    build artifact: it cannot change while the page is up, and re-reading it on
    every keystroke would put disk I/O inside the callback.

    Anything missing from the file is left out of the line rather than filled
    with a placeholder - a dashboard that prints "silhouette = n/a" invites the
    reader to assume a number exists somewhere.
    """
    path = Path(config.METRIC_DIR) / "clusters.json"
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""

    bits: list[str] = []
    chosen_k = payload.get("chosen_k")
    if chosen_k is not None:
        bits.append(f"k = {int(chosen_k)}")
        # The sweep is the only place the chosen k's silhouette appears; the
        # top-level object keeps the choice, not its score.
        row = next((r for r in payload.get("sweep", []) if r.get("k") == chosen_k), None)
        if row and row.get("silhouette") is not None:
            bits.append(f"silhouette = {float(row['silhouette']):.2f}")
    ari = (payload.get("stability") or {}).get("mean_ari")
    if ari is not None:
        bits.append(f"bootstrap ARI = {float(ari):.2f}")
    return "   ·   ".join(bits)


def cluster_figure(frame) -> go.Figure:
    clusters = data.airport_clusters()
    if clusters is None:
        return empty("Run src/scripts/05_clusters.py to build the archetypes")
    if "pc1" not in clusters.columns:
        return empty("Cluster projection not found in outputs/tables")

    palette = [schema.OKABE_ITO["blue"], schema.OKABE_ITO["orange"],
               schema.OKABE_ITO["green"], schema.OKABE_ITO["purple"],
               schema.OKABE_ITO["vermillion"], schema.OKABE_ITO["sky"]]

    # Label each archetype's two busiest airports, not the global top eight. On
    # the real panel the global top eight collapse into one cluster (six of them
    # are major hubs in the same region of feature space) and their codes stack
    # on top of each other; two per cluster keeps the labels spread across the
    # plot while still naming a reader's anchor points (ATL, ORD, DFW, SEA...).
    labelled = set(
        clusters.sort_values("n_dep", ascending=False)
        .groupby("cluster")
        .head(2)["origin"]
    )

    fig = go.Figure()
    for i, (cluster, chunk) in enumerate(clusters.groupby("cluster")):
        label = chunk["archetype"].iloc[0] if "archetype" in chunk.columns else "archetype"
        fig.add_trace(go.Scatter(
            x=chunk["pc1"], y=chunk["pc2"], mode="markers",
            marker={"size": 8 + 26 * (chunk["n_dep"] / clusters["n_dep"].max()),
                    "color": palette[i % len(palette)], "opacity": 0.8,
                    "line": {"width": 0.5, "color": "white"}},
            name=f"C{int(cluster)} - {label}",
            customdata=np.stack([chunk["mean_arr_delay"], chunk["share_delayed_60"],
                                 chunk["n_dep"], chunk["origin"].astype(str)], axis=-1),
            hovertemplate=("<b>%{customdata[3]}</b><br>mean delay %{customdata[0]:.1f} min"
                           "<br>60+ share %{customdata[1]:.1%}"
                           "<br>%{customdata[2]:,.0f} departures<extra></extra>"),
        ))

    # The codes are annotations rather than a "markers+text" trace. A text trace
    # offsets its label by the marker's radius, which places a 34px hub label
    # back inside the bubble it is meant to label; an annotation takes a fixed
    # pixel offset and a white halo, so the code sits above the bubble and stays
    # legible even where two clusters crowd together (the 2026-11-03 review).
    hubs = clusters[clusters["origin"].isin(labelled)]
    max_dep = float(clusters["n_dep"].max())
    for _, hub in hubs.iterrows():
        diameter = 8.0 + 26.0 * (float(hub["n_dep"]) / max_dep)
        fig.add_annotation(
            x=hub["pc1"], y=hub["pc2"], text=str(hub["origin"]),
            showarrow=False, yshift=diameter / 2 + 14,
            # yanchor="auto" flips to "top" for points in the upper half, which
            # hangs the text downward off the anchor - back onto the bubble it
            # was trying to clear. "bottom" pins the text to grow upward.
            yanchor="bottom",
            bgcolor="rgba(255,255,255,0.88)", borderpad=1,
            font={"size": 8.5, "color": INK},
        )

    # Labels sit above their markers, so the data range is not the plot range:
    # without padding the top hub's code is cut by the frame. 0.30 covers a
    # 34px bubble plus its label; 0.10 horizontally holds the side codes clear.
    y_pad = 0.30 * (clusters["pc2"].max() - clusters["pc2"].min())
    x_pad = 0.10 * (clusters["pc1"].max() - clusters["pc1"].min())

    fig.update_layout(legend=LEGEND_BELOW)
    fig.update_xaxes(title_text="Principal component 1", showgrid=False,
                     range=[clusters["pc1"].min() - x_pad, clusters["pc1"].max() + x_pad])
    fig.update_yaxes(title_text="Principal component 2", showgrid=False,
                     range=[clusters["pc2"].min() - y_pad, clusters["pc2"].max() + y_pad])
    return finish(fig, margin=LEGEND_MARGIN)
