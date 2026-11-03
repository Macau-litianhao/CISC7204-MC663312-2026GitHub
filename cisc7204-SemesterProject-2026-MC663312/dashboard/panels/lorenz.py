"""Concentration: how much of the total delay the worst flights carry.

The report's central claim - delay is not spread evenly, the tail is the story
- had no panel on the dashboard. This is that panel, and it states the number
rather than leaving the reader to estimate it off the curve.

Definition, because a Lorenz curve can be built several ways:

* Only **positive** delay minutes enter. An early arrival does not cancel a
  late one; if it did, the total would be a net figure and the curve could not
  rise above the equality line at all, which would hide the very concentration
  being measured.
* Flights are sorted **worst first**, so ``x = 1%`` reads "the worst 1% of
  flights" instead of "the best 1%". Read left to right the curve then starts
  steep and flattens, which is the shape of the finding.
* ``y`` is the share of all positive delay minutes carried by that worst slice.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
from team01 import schema

from .theme import FAINT, INK, LEGEND_BELOW, LEGEND_MARGIN, MUTED, empty, finish

CURVE = schema.OKABE_ITO["blue"]


def _tint(hex_colour: str, alpha: float) -> str:
    """Hex token to an rgba string, so the fill stays bound to the palette."""
    red, green, blue = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red},{green},{blue},{alpha})"


def lorenz_figure(frame) -> go.Figure:
    curve = data.lorenz_curve(frame)
    if curve["n"] == 0 or curve["total_minutes"] <= 0:
        return empty("No delay minutes in this filter")

    top_1pct = curve["top"][0.01]
    gini = curve["gini"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve["x"], y=curve["y"], mode="lines",
        line={"width": 2.4, "color": CURVE},
        # A wash of the same hue, not a second colour: the fill only says where
        # the curve has already been, so it must not compete with it.
        fill="tozeroy", fillcolor=_tint(CURVE, 0.13),
        hovertemplate=("worst %{x:.1%} of flights<br>"
                       "%{y:.1%} of delay minutes<extra></extra>"),
        name="Positive delay minutes",
    ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines", name="Perfect equality",
        line={"width": 1, "color": FAINT, "dash": "dot"}, hoverinfo="skip",
    ))

    # The headline goes on the figure, not in a caption: a reader should not
    # have to measure the steep segment to recover the one number that makes
    # the argument. Text sits in the shaded area below the curve, where the
    # background is light enough for ink; the arrow returns to the point the
    # sentence describes.
    fig.add_annotation(
        x=0.012, y=top_1pct, ax=0.34, ay=0.52, axref="x", ayref="y",
        text=(f"Worst 1% of flights carry {top_1pct:.1%} of delay minutes"),
        showarrow=True, arrowhead=2, arrowsize=0.7, arrowwidth=1,
        arrowcolor=FAINT, xanchor="left", yanchor="middle",
        font={"size": 11, "color": INK},
    )
    fig.add_annotation(
        x=0.98, y=0.03, xref="paper", yref="paper", showarrow=False,
        text=f"Gini {gini:.2f}", xanchor="right", yanchor="bottom",
        font={"size": 10.5, "color": MUTED},
    )

    fig.update_layout(legend=LEGEND_BELOW)
    fig.update_xaxes(title_text="Share of flights, worst first",
                     range=[0, 1], tickformat=".0%", dtick=0.2)
    fig.update_yaxes(title_text="Cumulative share of delay minutes",
                     range=[0, 1], tickformat=".0%", dtick=0.2)
    return finish(fig, margin=LEGEND_MARGIN)
