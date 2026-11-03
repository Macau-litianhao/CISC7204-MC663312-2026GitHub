"""Attributed delay minutes by cause, horizontal bars with share labels.

The share labels sit outside the bar ends, which is where the longest bar puts
its label past the plot edge and the card clips it. ``cliponaxis=False`` alone
only stops plotly from clipping the text at the axis line - the text still runs
into the paper margin - so the x range is also widened to 1.16x the longest bar,
keeping the zero baseline exactly where ``rangemode="tozero"`` had it. A
non-zero start would make the bars' lengths lie about their ratios.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
from team01 import schema

from .theme import empty, finish


def cause_figure(frame) -> go.Figure:
    mix = data.cause_mix(frame)
    if mix.empty or mix["minutes"].sum() == 0:
        return empty("No flights at or above the 15-minute threshold in this filter")

    mix = mix.sort_values("minutes")
    # Millions keep the tick labels readable on the ten-year panel; the axis
    # title carries the unit either way.
    values = mix["minutes"] / 1e6 if mix["minutes"].max() > 1e6 else mix["minutes"]

    fig = go.Figure(go.Bar(
        x=values,
        y=mix["cause"],
        orientation="h",
        marker={"color": [schema.CAUSE_COLORS[k] for k in mix["cause_key"]],
                "line": {"width": 0}},
        text=[f"{s:.1%}" for s in mix["share"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,.0f} minutes<extra></extra>",
    ))
    fig.update_layout(showlegend=False, bargap=0.42)
    fig.update_xaxes(title_text="Attributed delay minutes",
                     range=[0, float(values.max()) * 1.16])
    return finish(fig)
