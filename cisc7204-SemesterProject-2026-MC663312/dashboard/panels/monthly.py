"""Monthly cause composition as a stacked area.

The legend used to be pinned at a hard-coded ``y=-0.28``. That number was tuned
for one card width: at 601px the legend fitted on one line, at 511px it wrapped
to two and the second line was cut by the card's bottom border (2026-11-02
review). ``LEGEND_BELOW`` with ``LEGEND_MARGIN`` reserves the space instead of
guessing the offset, so wrapping stays inside the figure at any width.

The y range is pinned to the full 0-100%: these are shares, and a range that
re-fitted to each filter would make a 2-point drift look like a regime change
between two filters that a reader is trying to compare.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
from team01 import schema

from .theme import LEGEND_BELOW, LEGEND_MARGIN, empty, finish


def monthly_figure(frame) -> go.Figure:
    shares = data.composition_by_month(frame)
    if shares.dropna(how="all").empty:
        return empty("No attributed minutes in this filter")

    fig = go.Figure()
    months = list(shares.index)
    for cause in schema.CAUSE_COLUMNS:
        if cause not in shares.columns:
            continue
        fig.add_trace(go.Scatter(
            x=months, y=shares[cause].to_numpy(),
            mode="lines", stackgroup="one", name=schema.CAUSE_LABELS[cause],
            line={"width": 0.6, "color": schema.CAUSE_COLORS[cause]},
            hovertemplate="%{y:.1%}<extra>" + schema.CAUSE_LABELS[cause] + "</extra>",
        ))
    fig.update_layout(legend=LEGEND_BELOW)
    fig.update_xaxes(tickmode="array", tickvals=months,
                     ticktext=[schema.MONTH_LABELS[m - 1] for m in months],
                     title_text="")
    fig.update_yaxes(title_text="Share of minutes", range=[0, 1],
                     tickformat=".0%")
    return finish(fig, margin=LEGEND_MARGIN)
