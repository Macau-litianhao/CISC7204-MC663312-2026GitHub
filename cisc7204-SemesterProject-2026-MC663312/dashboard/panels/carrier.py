"""Carrier comparison: mean delay against the 90th percentile, one row per carrier.

The page shipped a Carrier filter with nothing to compare the selection against -
a control that implies a comparison the page never draws. This panel is the other
half of that control, so it always receives a frame that is *not* filtered by
carrier: if it were, the panel would show one row and the selection would be the
only thing in it.

A dumbbell rather than two bar charts, because the gap between the dots is the
finding. A carrier can sit at the fleet-average mean and still be the one that
ruins a connecting passenger's day one flight in ten; that is a different
operational problem from being uniformly mediocre, and two separate bars ask the
reader to measure each dot against the axis instead of the two dots against each
other.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
import labels
from team01 import schema

from .theme import (
    AXIS_LINE,
    FAINT,
    GRID,
    INK,
    LEGEND_BELOW,
    LEGEND_MARGIN,
    MUTED,
    ORANGE_DARK,
    empty,
    finish,
)

MEAN_COLOR = schema.OKABE_ITO["blue"]
TAIL_COLOR = ORANGE_DARK

# A dot pair reads as one object at 9 px and as two specks at 5.5. The dimmed
# row drops below the base size so the selected row keeps the visual weight
# without having to grow much beyond it.
DOT_SIZE = 9.0
DOT_SIZE_ACTIVE = 9.5
DOT_SIZE_DIM = 5.5

LABEL_SIZE = 10.5
LABEL_SIZE_ACTIVE = 11.0
VALUE_SIZE = 9.5


def carrier_figure(frame, selected: list[str] | None = None) -> go.Figure:
    """Dumbbell of mean and p90 arrival delay per carrier.

    ``frame`` must not be filtered by carrier (see the module docstring).
    ``selected`` is the carrier filter's current value; it only changes emphasis,
    never the set of rows. Carriers absent from the profile - the thin ones
    dropped by ``min_flights`` - are ignored rather than dimming the whole chart.
    """
    if frame.empty:
        return empty("No carrier has enough flights in this filter")

    profile = data.carrier_profile(frame)
    if profile.empty:
        return empty("No carrier has enough flights in this filter")

    codes = profile["carrier"].astype(str).tolist()
    means = profile["mean"].astype(float).tolist()
    p90s = profile["p90"].astype(float).tolist()
    medians = profile["median"].astype(float).tolist()
    shares = profile["share_60"].astype(float).tolist()
    flights = profile["flights"].astype(int).tolist()

    chosen = {str(c) for c in (selected or [])} & set(codes)
    has_selection = bool(chosen)
    # Row order follows ``carrier_profile`` (mean ascending). Row 0 is the best
    # carrier and is pinned to the top by the reversed y range below.
    rows = [float(i) for i in range(len(codes))]
    active = [(not has_selection) or code in chosen for code in codes]
    picked = [has_selection and code in chosen for code in codes]

    def tint(colour: str, dim: str) -> list[str]:
        return [colour if on else dim for on in active]

    # Without a selection every dot is the same size; with one, only the picked
    # rows keep their weight, which is what makes the comparison read as
    # "this carrier against the rest" rather than "these two carriers".
    if has_selection:
        sizes = [DOT_SIZE_ACTIVE if on else DOT_SIZE_DIM for on in picked]
    else:
        sizes = [DOT_SIZE] * len(codes)

    fig = go.Figure()

    # 1. Connector: the interval between the two dots, which is the reading we
    #    want (a long line is a heavy tail, not a high average). Split in two
    #    traces when a selection is active, because ``line.color`` takes one
    #    colour per trace and the dimmed rows need a paler one.
    def connector(pick: list[bool], colour: str) -> go.Scatter:
        span_x: list[float | None] = []
        span_y: list[float | None] = []
        for row, mean, tail, keep in zip(rows, means, p90s, pick):
            if keep:
                span_x += [mean, tail, None]
                span_y += [row, row, None]
        return go.Scatter(
            x=span_x, y=span_y, mode="lines",
            line={"color": colour, "width": 1.5},
            hoverinfo="skip", showlegend=False,
        )

    fig.add_trace(connector(active, AXIS_LINE))
    if has_selection:
        fig.add_trace(connector([not on for on in active], GRID))

    # Whatever the two dots leave out - median, severe share, sample size - so a
    # hover answers "compared with what?" without a second panel.
    details = [[m, s, f, c, mu] for m, s, f, c, mu in
               zip(medians, shares, flights, [labels.carrier_label(c) for c in codes], means)]

    # 2. Mean dot.
    fig.add_trace(go.Scatter(
        x=means, y=rows, mode="markers", name="Mean delay",
        marker={"color": tint(MEAN_COLOR, FAINT),
                "size": sizes, "line": {"width": 0}},
        customdata=details,
        hovertemplate=("<b>%{customdata[3]}</b><br>"
                       "mean %{x:+.1f} min<br>"
                       "median %{customdata[0]:+.1f} min<br>"
                       "60+ min %{customdata[1]:.1%}<br>"
                       "%{customdata[2]:,} flights<extra></extra>"),
    ))

    # 3. p90 dot. The ninetieth percentile, not the maximum: a maximum is one
    #    flight (one storm, one diversion) and says nothing repeatable about a
    #    carrier, while p90 is "the worst of every ten flights" and therefore a
    #    level a passenger can actually plan around.
    fig.add_trace(go.Scatter(
        x=p90s, y=rows, mode="markers", name="90th percentile",
        marker={"color": tint(TAIL_COLOR, FAINT),
                "size": sizes, "line": {"width": 0}},
        customdata=details,
        hovertemplate=("<b>%{customdata[3]}</b><br>"
                       "90th pct %{x:+.0f} min<br>"
                       "mean %{customdata[4]:+.1f} min<br>"
                       "60+ min %{customdata[1]:.1%}<extra></extra>"),
    ))

    upper = max(max(p90s) * 1.10, 1.0)

    for row, tail, on in zip(rows, p90s, active):
        # Value at the right-hand dot, so the tail is readable without hovering.
        fig.add_annotation(
            x=tail, y=row, xref="x", yref="y",
            text=f"{tail:+.0f}", showarrow=False,
            xanchor="left", xshift=7, yanchor="middle",
            font={"size": VALUE_SIZE, "color": MUTED if on else FAINT},
        )

    # Carrier names are annotations rather than axis tick labels: tickfont is a
    # single font for the whole axis, so it cannot bold one row and grey another,
    # and "which one did I select" is the only reason this panel exists.
    for row, code, selected_row, on in zip(rows, codes, picked, active):
        fig.add_annotation(
            x=0, y=row, xref="paper", yref="y",
            text=f"<b>{code}</b>" if selected_row else code,
            showarrow=False, xanchor="right", xshift=-8, yanchor="middle",
            font={
                "size": LABEL_SIZE_ACTIVE if selected_row else LABEL_SIZE,
                "color": INK if selected_row else (MUTED if on else FAINT),
            },
        )

    # 4. Reference line: the mean over every flight in the filter, not the mean
    #    of the per-carrier means. The latter weights a 900-flight regional
    #    carrier and a 60 000-flight network carrier equally, so it is not the
    #    average flight and does not match the KPI card one row above this panel.
    weighted_mean = float(frame["arr_delay"].mean())
    fig.add_vline(x=weighted_mean, layer="below",
                  line={"color": FAINT, "width": 1, "dash": "dash"})
    fig.add_annotation(
        x=weighted_mean, y=-0.55, xref="x", yref="y",
        text="all carriers", showarrow=False,
        xanchor="left", xshift=6, yanchor="middle",
        font={"size": VALUE_SIZE, "color": FAINT},
    )

    fig.update_layout(
        legend=LEGEND_BELOW,
        hovermode="closest",
        # One unit of empty space above row 0 holds the reference-line label
        # without pushing the top row into it or borrowing the top margin the
        # legend already needs.
        yaxis={
            "range": [len(codes) - 0.4, -0.95],
            "showgrid": False, "zeroline": False,
            "showticklabels": False, "ticks": "",
        },
        xaxis={
            "title": "Arrival delay (minutes)",
            "range": [0, upper], "rangemode": "tozero",
        },
    )
    # Height is fixed to match the panel container in layouts.py. The full panel
    # has 20 reporting carriers; at the old 320px that is 16px a row, where the
    # 9px dots and 10.5px labels would collide. 560px gives each row about 25px,
    # so a filter that keeps all 20 carriers stays legible, and the thinner
    # sample fixture merely gets more air between rows.
    return finish(fig, height=560, margin=LEGEND_MARGIN)
