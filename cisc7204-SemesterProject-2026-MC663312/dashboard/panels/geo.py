"""One map instead of two: states as the fill, airports as the bubbles.

The 2026-11-02 review (P1-1, P1-3) found two of the eight panels drawing the
same geography twice, each with its own colour scale and neither with a size
anchor. The two views answer different questions - the fill says where the
delay is worst, the bubbles say where the traffic is - so they belong in one
frame, not in two panels.

The split of channels is deliberate: fill carries delay, bubble size carries
volume, and nothing carries colour twice. Two colour scales on one map invite
the reader to compare a state's fill to an airport's fill, which encodes
nothing.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

import data_access as data
import labels
from team01 import schema

from .theme import FAINT, LAND, MUTED, empty, finish

# Bubble diameter in px. The floor keeps the smallest airport visible against
# the state fill; the ceiling stops the largest from swallowing its neighbours.
BUBBLE_MIN = 5.0
BUBBLE_MAX = 26.0


def _bubble_sizes(flights, reference: float) -> np.ndarray:
    """Diameter in px; area is proportional to departures, clamped at reference.

    Linear in *diameter* rather than in area: the size legend is drawn from this
    same function, so the reference circles and the marks share one mapping and
    a reader can compare them directly instead of estimating.
    """
    ratio = np.clip(np.asarray(flights, dtype=float) / max(float(reference), 1.0),
                    0.0, 1.0)
    return BUBBLE_MAX * np.sqrt(ratio)


def _volume_label(value: float) -> tuple[float, str]:
    """Round a departure count to two significant figures and suffix the scale.

    The fixture's airports run 2.8k-4.2k departures while the real panel runs
    into the hundreds of thousands, so a fixed rounding step is wrong at one end
    or the other: rounding to the nearest ten thousand turns every fixture
    airport into "0k". Two significant figures is scale-free and still reads as
    a round number at both ends.
    """
    unit, suffix = (1e6, "M") if value >= 1e6 else ((1e3, "k") if value >= 1e3 else (1.0, ""))
    scaled = value / unit
    digits = 1 if scaled < 10 else 0
    rounded = round(scaled, digits)
    text = f"{rounded:.{digits}f}"
    if digits:
        text = text.rstrip("0").rstrip(".")
    return rounded * unit, f"{text}{suffix}"


def geo_figure(frame, selected_airport=None) -> go.Figure:
    """State mean delay as a sequential fill, airport volume as bubble size."""
    profile = data.state_profile(frame)
    if profile.empty:
        return empty("No completed flights in this filter")

    clusters = data.airport_clusters()
    if clusters is None or "latitude_deg" not in clusters.columns:
        return empty("Airport coordinates come from the clustering stage")

    airports = data.airport_profile(frame).merge(
        clusters[["origin", "latitude_deg", "longitude_deg"]], on="origin", how="inner").dropna(subset=["latitude_deg", "longitude_deg"])
    if airports.empty:
        return empty("No airport in this filter has coordinates")

    peak = float(airports["flights"].max())
    sizes = _bubble_sizes(airports["flights"], peak)

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=profile["origin_state"], locationmode="USA-states",
        # YlOrRd, not RdBu_r + zmid: every state mean is positive, so the blue
        # half of a diverging scale is unreachable and half the resolvable
        # colours are spent on values that cannot occur.
        z=profile["mean"], colorscale="RdBu_r", zmin=-15, zmax=15, zmid=0,
        marker={"line": {"width": 0.6, "color": "white"}},
        customdata=np.stack([profile["flights"], profile["share_60"]], axis=-1),
        hovertemplate=("%{location}<br>mean %{z:.1f} min"
                       "<br>%{customdata[0]:,.0f} flights"
                       "<br>60+ share %{customdata[1]:.1%}<extra></extra>"),
        colorbar={
            "title": {"text": "mean delay (min), fixed -15 to +15", "side": "top"},
            "orientation": "h", "y": -0.13, "yanchor": "top",
            "x": 0.5, "xanchor": "center",
            "thickness": 8, "len": 0.45, "outlinewidth": 0,
            "tickfont": {"size": 9.5, "color": MUTED},
        },
    ))
    fig.add_trace(go.Scattergeo(
        lon=airports["longitude_deg"], lat=airports["latitude_deg"],
        text=airports["origin"], mode="markers", name="airports",
        # One fixed colour: volume is already encoded by size, so colour here
        # would be a second scale saying the same thing less accurately.
        marker={"size": sizes, "color": schema.OKABE_ITO["blue"],
                "opacity": 0.82, "line": {"width": [3 if code == selected_airport else .8 for code in airports["origin"]], "color": ["#b85b00" if code == selected_airport else "white" for code in airports["origin"]]}},
        customdata=np.stack([airports["mean"], airports["share_60"],
                             airports["flights"], [labels.airport_label(code) for code in airports["origin"]]], axis=-1),
        hovertemplate=("%{customdata[3]}<br>mean %{customdata[0]:.1f} min"
                       "<br>%{customdata[1]:.1%} delayed 60+"
                       "<br>%{customdata[2]:,.0f} departures<extra></extra>"),
        showlegend=False,
    ))
    fig.update_geos(scope="usa", showlakes=False, bgcolor="white",
                    landcolor=LAND, subunitcolor="white")

    # Size legend, bottom-left. Drawn with text glyphs in paper coordinates
    # rather than geo coordinates: the geo projection rescales with the card's
    # aspect ratio, so a lon/lat anchor would drift out of the blank corner at
    # some widths, while paper coordinates stay in the same corner at every
    # width. A ring is the glyph that survives a light fill behind it.
    fig.add_annotation(
        x=0.045, y=0.40, xref="paper", yref="paper", showarrow=False,
        text="departures", xanchor="left", yanchor="bottom",
        font={"size": 9.5, "color": MUTED},
    )
    quantiles = airports["flights"].quantile([0.25, 0.5]).tolist() + [peak]
    for row, raw in enumerate(quantiles):
        value, label = _volume_label(float(raw))
        y = 0.08 + 0.11 * row
        fig.add_annotation(
            x=0.045, y=y, xref="paper", yref="paper", showarrow=False,
            text="\u25cf", xanchor="center", yanchor="middle",
            # The glyph fills about 0.7 of its em box, so scale up to match the
            # marker diameter the bubbles are actually drawn at.
            font={"size": 1.4 * float(_bubble_sizes([value], peak)[0]),
                  "color": schema.OKABE_ITO["blue"]},
        )
        fig.add_annotation(
            x=0.075, y=y, xref="paper", yref="paper", showarrow=False,
            text=label, xanchor="left", yanchor="middle",
            font={"size": 9.5, "color": MUTED},
        )

    # Grey reads as "no fill", which would otherwise be indistinguishable from
    # a very low mean: YlOrRd's pale end is close to the land colour.
    fig.add_annotation(
        x=0.99, y=0.02, xref="paper", yref="paper", showarrow=False,
        text="grey = no mapped state value<br>fixed scale saturates beyond ±15 min", xanchor="right", yanchor="bottom",
        font={"size": 9.5, "color": FAINT},
    )

    # The bottom margin carries the horizontal colorbar and nothing else; the
    # map fills the rest of the card (the geo panel container is taller than the
    # default 320px so a U.S. map is not squashed flat). finish() replaces the
    # base margin wholesale, so it has to be handed in rather than set on the
    # figure.
    return finish(fig, margin={"l": 0, "r": 0, "t": 6, "b": 58})
