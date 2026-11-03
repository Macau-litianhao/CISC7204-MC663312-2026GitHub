"""Risk surface: share of 60+ minute arrivals by month and departure hour.

**Not mounted.** The 2026-11-02 rebuild gave this slot to the carrier comparison:
the same surface already exists as the printed figure ``12_risk_heatmap``, and the
blank-cell semantics ("no flights" rendered as pale yellow, next to "0% risk")
were the least honest panel on the page. Kept because it is the only working
month-by-hour view in the codebase; import it if the panel returns.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
from team01 import schema

from .theme import empty, finish


def risk_figure(frame) -> go.Figure:
    matrix = data.risk_matrix(frame)
    if matrix.dropna(how="all").empty:
        return empty("Not enough flights in this filter to estimate risk")

    fig = go.Figure(go.Heatmap(
        z=matrix.to_numpy(), x=list(range(1, 13)), y=list(matrix.index),
        # YlOrRd, not Magma: a low risk must read as pale, not as black. Magma's
        # dark low end makes "no severe delay" look identical to "no data".
        colorscale="YlOrRd", zmin=0,
        colorbar={"title": "share", "thickness": 10, "len": 0.7,
                  "tickformat": ".0%"},
        hovertemplate="hour %{y}, month %{x}<br>%{z:.2%} delayed 60+<extra></extra>",
    ))
    fig.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                     ticktext=schema.MONTH_LABELS, title_text="")
    fig.update_yaxes(title_text="Scheduled departure hour", autorange="reversed",
                     tickmode="array", tickvals=[0, 3, 6, 9, 12, 15, 18, 21])
    return finish(fig)
