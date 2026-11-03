"""Delay by scheduled departure hour: 60+ share as bars, mean as a line.

Two fixes from the 2026-11-02 review:

* The x axis ran 0-24 with ``dtick=3`` while "departure hour" only takes 0-23,
  and almost nothing departs before 05:00 or after 22:00. Two empty thirds
  pushed the actual signal into the middle of the card, so the range is now
  clipped to the hours that carry flights and the ticks step by 2.
* The bars were Okabe-Ito orange at ``opacity=0.35``: 1.32:1 against white,
  below the 3:1 WCAG 1.4.11 asks of a graphical object, and on a projector they
  read as empty. ``ORANGE_DARK`` keeps the hue at 3.6:1, so the bars are solid
  and the encoding survives the room.
"""

from __future__ import annotations

import plotly.graph_objects as go

import data_access as data
from team01 import config, schema

from .theme import LEGEND_BELOW, MUTED, ORANGE_DARK, empty, finish


def hourly_figure(frame) -> go.Figure:
    profile = data.hourly_profile(frame)
    if profile["flights"].fillna(0).sum() == 0:
        return empty("No completed flights in this filter")

    # The mean is not plotted where almost nobody departed. In the fixture the
    # 22:00 hour holds 18 flights with a 0.4-minute mean, which draws a cliff
    # from 17 minutes to zero - a reader sees "delays vanish at night" when the
    # real statement is "18 flights is not a mean". The share bars stay: a 0%
    # share of 18 flights is still literally true.
    floor = float(config.get("viz.min_hour_flights", 200))
    mean = profile["mean"].where(profile["flights"].fillna(0) >= floor)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=profile.index, y=profile["share_60"], name="Delayed 60+ min",
        marker_color=ORANGE_DARK, opacity=1.0,
        hovertemplate="%{y:.1%}<extra>60+ min</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=profile.index, y=mean, name="Mean delay",
        mode="lines+markers", line={"color": schema.OKABE_ITO["blue"], "width": 2.4},
        marker={"size": 4}, yaxis="y2",
        hovertemplate="%{y:+.1f} min<extra>Mean</extra>",
    ))
    fig.update_layout(
        legend=LEGEND_BELOW,
        yaxis={"title": "Share 60+ min", "tickformat": ".0%"},
        # standoff keeps the right-hand title off the card edge, where it was
        # brushing the border in the narrow-card screenshots.
        yaxis2={"title": {"text": "Mean delay (min)", "standoff": 12},
                "overlaying": "y", "side": "right",
                "showgrid": False, "tickfont": {"size": 10.5, "color": MUTED}},
        xaxis={"title": "Scheduled departure hour", "dtick": 2, "range": [3.5, 23.5]},
    )
    # The right axis needs real margin, not just a standoff: standoff moves the
    # title away from the tick labels, but the tick labels themselves still sit
    # in the 16px the base margin leaves, so the title was being pushed into the
    # card border. 54px holds ticks plus a rotated title.
    return finish(fig, margin={"l": 46, "r": 54, "t": 8, "b": 62})
