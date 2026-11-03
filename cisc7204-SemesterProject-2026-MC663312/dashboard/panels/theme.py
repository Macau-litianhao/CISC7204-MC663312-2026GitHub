"""Figure tokens shared by every panel.

One source for colour, type and margins. Panels must not hard-code a hex value:
the 2026-11-02 review found three greys doing the same job (``#5A6673``,
``#6B7684``, ``#8894A0``) and two colorbar naming habits across adjacent panels.
A shared token file is the cheapest way to make that impossible rather than
merely discouraged.
"""

from __future__ import annotations

import plotly.graph_objects as go

INK = "#22303C"
MUTED = "#5A6673"
FAINT = "#8894A0"
GRID = "#E6EAEF"
AXIS_LINE = "#CBD3DB"
LAND = "#F4F6F8"

# Okabe-Ito orange at full saturation is 2.25:1 against white, and at the 0.35
# opacity the old hourly chart used it was 1.32:1 - below the 3:1 that WCAG
# 1.4.11 asks of a graphical object. This shade keeps the hue and reaches 3.6:1.
ORANGE_DARK = "#B26A00"

FONT = {"family": "Inter, Segoe UI, system-ui, sans-serif", "size": 12, "color": INK}

BASE_LAYOUT = {
    "font": FONT,
    "margin": {"l": 46, "r": 16, "t": 8, "b": 38},
    "paper_bgcolor": "white",
    "plot_bgcolor": "white",
    # Inverted hover chip: a solid dark background with light text. Plotly's
    # default is a translucent white chip whose grey tint reads as a grey box
    # with dark text against the map's light land fill; a solid dark chip keeps
    # the same contrast on white, on the land grey and on every coloured state.
    "hoverlabel": {
        "bgcolor": INK,
        "bordercolor": INK,
        "font": {"family": FONT["family"], "size": 12, "color": "#FFFFFF"},
    },
}

AXIS = {
    "gridcolor": GRID,
    "zerolinecolor": AXIS_LINE,
    "linecolor": AXIS_LINE,
    "tickfont": {"size": 10.5, "color": MUTED},
}

# Legend pinned below the plot area. Always pair it with LEGEND_MARGIN: a legend
# without reserved bottom space is a legend that lands on the axis title at wide
# widths and gets clipped by the card edge when the card narrows.
LEGEND_BELOW = {
    "orientation": "h",
    "yanchor": "top",
    "y": -0.16,
    "xanchor": "left",
    "x": 0,
    "font": {"size": 10, "color": MUTED},
    "bgcolor": "rgba(255,255,255,0.92)",
}

LEGEND_MARGIN = {"l": 46, "r": 16, "t": 10, "b": 62}

# Colorbar defaults: one thickness, one length, one title style across panels.
COLORBAR = {"thickness": 10, "len": 0.68, "outlinewidth": 0,
            "tickfont": {"size": 9.5, "color": MUTED}}


def finish(fig: go.Figure, height: int | None = None,
           margin: dict | None = None) -> go.Figure:
    """Apply the shared frame. ``margin`` replaces the base margin wholesale."""
    fig.update_layout(**BASE_LAYOUT)
    if margin:
        fig.update_layout(margin=margin)
    fig.update_xaxes(**AXIS)
    fig.update_yaxes(**AXIS)
    if height:
        fig.update_layout(height=height)
    return fig


def empty(message: str) -> go.Figure:
    """Placeholder so a missing stage degrades to a sentence, not a traceback."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       font={"size": 13, "color": MUTED},
                       x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        paper_bgcolor="white", plot_bgcolor="white",
    )
    return fig
