"""The delay distribution itself, with the median and mean marked.

The two reference lines used to carry their labels as ``add_vline``
annotations. Plotly parks those *above* the plot area, and the card only
reserves 8px of top margin, so half of "median -1" was cut off by the card edge
in the 2026-11-02 review - on the one figure that exists to make the
"the mean is misleading" argument. The labels now sit inside the plot area, at
two different heights, so neither the card edge nor the other line can cover
them, whatever the card width.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from team01 import schema

from .theme import FAINT, empty, finish


def distribution_figure(frame) -> go.Figure:
    if frame.empty:
        return empty("No completed flights in this filter")
    delay = frame["arr_delay"]
    mean = float(frame["arr_delay"].mean())
    median = float(frame["arr_delay"].median())

    fig = go.Figure()
    edges = np.concatenate([[-np.inf], np.arange(-60, 245, 5), [np.inf]])
    counts, _ = np.histogram(delay, bins=edges)
    centres = np.concatenate([[-62.5], np.arange(-57.5, 240, 5), [242.5]])
    labels = ['< -60 min'] + [f'{int(v)} to {int(v+5)} min' for v in np.arange(-60,240,5)] + ['>= 240 min']
    fig.add_trace(go.Bar(
        x=centres, y=counts, width=4.7, customdata=labels, marker_color=schema.OKABE_ITO["sky"],
        opacity=0.85, name="Flights",
        hovertemplate="%{customdata}: %{y:,} flights<extra></extra>",
    ))
    fig.add_vline(x=0, line={"color": FAINT, "width": 1})
    fig.add_vline(x=median, line={"color": schema.OKABE_ITO["blue"], "width": 2})
    fig.add_vline(x=mean, line={"color": schema.ACCENT, "width": 2, "dash": "dash"})

    # Two heights, not one: in the sample fixture the median and the mean are
    # about 11 minutes apart, close enough that labels sharing a baseline
    # collide. Anchoring the median label to the right of its line and the mean
    # label to the left of its own pushes the two texts apart even when the
    # values converge. The colours follow the lines, so the label needs no
    # "solid/dashed" legend.
    fig.add_annotation(
        x=median, y=0.97, xref="x", yref="paper", xanchor="right", yanchor="top",
        text=f"median {median:+.0f}", showarrow=False,
        font={"size": 10.5, "color": schema.OKABE_ITO["blue"]},
        bgcolor="white", borderpad=2,
    )
    fig.add_annotation(
        x=mean, y=0.87, xref="x", yref="paper", xanchor="left", yanchor="top",
        text=f"mean {mean:+.0f}", showarrow=False,
        font={"size": 10.5, "color": schema.ACCENT},
        bgcolor="white", borderpad=2,
    )

    # Room for the labels: measured on the same 5-minute bins the histogram
    # draws, then given 14% headroom. Without it the tallest bar reaches the
    # annotations and the white label boxes punch holes in it.
    edges = np.arange(-60, 245, 5)
    peak = int(counts.max())

    fig.update_layout(bargap=0.05, showlegend=False)
    fig.update_xaxes(title_text="Arrival delay (min); end bars include overflow",
                     range=[-66,246], tickvals=[-62.5,0,60,120,180,242.5],
                     ticktext=['<−60','0','60','120','180','≥240'])
    fig.update_yaxes(title_text="Flights")
    if peak:
        fig.update_yaxes(range=[0, peak * 1.14])
    return finish(fig)
