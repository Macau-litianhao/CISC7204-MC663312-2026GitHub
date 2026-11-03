"""Callbacks: one filter set drives every panel.

A single callback updates every figure. That is deliberate rather than lazy:
linked views are only convincing if they are genuinely linked, and a reader who
filters to one carrier must not be left with a cause panel showing all carriers.

Every figure recomputes its aggregate from the filtered frame. Nothing is
pre-rendered, so the dashboard cannot display a number that the report does not.

The builders themselves live in ``panels/`` - one module per panel - and are
re-exported here so callers (and the offline figure test) keep a single import.

Interaction grammar, in Shneiderman's order: the KPI strip is the overview, the
three controls are zoom-and-filter, and clicking a bubble on the map is
details-on-demand. The selected airport is held in a store rather than folded
into the carrier control, so "which airport am I looking at" survives a carrier
change - and it is echoed in the URL, so a link can carry the whole view.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

import data_access as data
import captions
import narrative
from layouts import kpi_card
from panels.carrier import carrier_figure
from panels.cause import cause_figure
from panels.cluster import cluster_figure
from panels.dist import distribution_figure
from panels.geo import geo_figure
from panels.hourly import hourly_figure
from panels.lorenz import lorenz_figure
from panels.monthly import monthly_figure

__all__ = [
    "register",
    "cause_figure", "monthly_figure", "hourly_figure", "distribution_figure",
    "cluster_figure", "lorenz_figure", "geo_figure", "carrier_figure",
]

DEFAULT_MONTHS = [1, 12]
HIDDEN = {"display": "none"}


# --------------------------------------------------------------------------
# URL state
# --------------------------------------------------------------------------
def _parse_search(search: str | None) -> tuple[int | str, list[str], list[int]]:
    """Read a query string back into the three control values.

    Idempotent by construction: whatever this returns must serialise back to the
    same string, or the two callbacks that share it would ping-pong forever.
    """
    query = parse_qs((search or "").lstrip("?"))
    year_raw = (query.get("year") or ["all"])[0]
    year: int | str = int(year_raw) if year_raw.isdigit() else "all"

    carriers = [c for c in (query.get("carrier") or [""])[0].split(",") if c]

    months = list(DEFAULT_MONTHS)
    span = (query.get("months") or [""])[0]
    if "-" in span:
        low, _, high = span.partition("-")
        if low.isdigit() and high.isdigit():
            months = [int(low), int(high)]
    return year, carriers, months


def _build_search(year, carriers, months) -> str:
    """Serialise the controls. Defaults are omitted so a plain URL stays clean."""
    parts: list[str] = []
    if year not in (None, "all", ""):
        parts.append(f"year={int(year)}")
    if carriers:
        parts.append("carrier=" + ",".join(sorted(str(c) for c in carriers)))
    low, high = (months or DEFAULT_MONTHS)
    if [int(low), int(high)] != DEFAULT_MONTHS:
        parts.append(f"months={int(low)}-{int(high)}")
    return ("?" + "&".join(parts)) if parts else ""


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------
def register(app) -> None:
    _register_url_state(app)
    _register_drilldown(app)
    _register_panels(app)


def _register_url_state(app) -> None:
    """Two callbacks that close a loop. Dash allows it as long as exactly one of
    them is prevented from firing on load; without that guard they would each
    retrigger the other forever."""

    @app.callback(
        Output("filter-year", "value"),
        Output("filter-carrier", "value"),
        Output("filter-months", "value"),
        Input("url", "search"),
    )
    def url_to_controls(search):
        return _parse_search(search)

    @app.callback(
        Output("url", "search"),
        Input("filter-year", "value"),
        Input("filter-carrier", "value"),
        Input("filter-months", "value"),
        prevent_initial_call=True,
    )
    def controls_to_url(year, carriers, months):
        return _build_search(year, carriers, months)


def _register_drilldown(app) -> None:
    @app.callback(
        Output("drill-airport", "data"),
        Input("fig-geo", "clickData"),
        State("drill-airport", "data"),
        prevent_initial_call=True,
    )
    def pick_airport(click, current):
        """Click a bubble to drill in, click it again to let go.

        Only the bubble trace is accepted: the choropleth underneath answers a
        state-level question, and silently turning a state click into an airport
        filter would select an airport the reader never pointed at.
        """
        points = (click or {}).get("points") or []
        if not points:
            raise PreventUpdate
        point = points[0]
        if point.get("curveNumber") != 1:
            raise PreventUpdate
        origin = point.get("text")
        if not origin:
            raise PreventUpdate
        return None if origin == current else origin

    @app.callback(
        Output("drill-airport", "data", allow_duplicate=True),
        Input("airport-clear", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_airport(_clicks):
        return None

    @app.callback(
        Output("airport-chip-label", "children"),
        Output("airport-chip-label", "style"),
        Output("airport-clear", "style"),
        Input("drill-airport", "data"),
    )
    def render_chip(origin):
        if not origin:
            return "", HIDDEN, HIDDEN
        return f"Airport: {origin}", None, None


def _register_panels(app) -> None:
    @app.callback(
        Output("kpi-strip", "children"),
        Output("fig-cause", "figure"),
        Output("fig-monthly", "figure"),
        Output("fig-hourly", "figure"),
        Output("fig-dist", "figure"),
        Output("fig-clusters", "figure"),
        Output("fig-lorenz", "figure"),
        Output("fig-geo", "figure"),
        Output("fig-carrier", "figure"),
        Output("insight-strip", "children"),
        Output("find-cause", "children"),
        Output("find-monthly", "children"),
        Output("find-hourly", "children"),
        Output("find-dist", "children"),
        Output("find-clusters", "children"),
        Output("find-lorenz", "children"),
        Output("find-geo", "children"),
        Output("find-carrier", "children"),
        Output("method-note", "children"),
        Input("filter-year", "value"),
        Input("filter-carrier", "value"),
        Input("filter-months", "value"),
        Input("drill-airport", "data"),
    )
    def update(year, carriers, months, airport):
        low, high = (months or DEFAULT_MONTHS)
        selected = list(range(int(low), int(high) + 1))

        # The map deliberately ignores the airport drill: it is the surface the
        # reader navigates on, and redrawing it with a single bubble would take
        # away the ability to pick a neighbour without clearing first.
        frame = data.apply_filters(year, carriers, selected)
        map_frame = frame
        panel_frame = frame[frame["origin"] == airport] if airport else frame

        # The carrier panel ignores the carrier filter for the same reason the
        # map ignores the airport drill: a comparison of one row is not one.
        carrier_frame = data.apply_filters(year, None, selected)
        if airport:
            carrier_frame = carrier_frame[carrier_frame["origin"] == airport]

        cards = [kpi_card(item) for item in data.kpis(panel_frame)]
        strip = [
            html.Div([
                html.Div(item["label"], className="insight-label"),
                html.Div(item["value"], className="insight-value"),
                html.Div(item["text"], className="insight-text"),
            ], className="insight-item")
            for item in narrative.insights(panel_frame)
        ]

        # The captions are computed from the same aggregates the figures drew, so
        # a sentence under a panel can never contradict the panel it sits under.
        found = captions.findings(panel_frame, carrier_frame)
        method = captions.method_note(panel_frame)

        return (
            cards,
            cause_figure(panel_frame),
            monthly_figure(panel_frame),
            hourly_figure(panel_frame),
            distribution_figure(panel_frame),
            cluster_figure(panel_frame),
            lorenz_figure(panel_frame),
            geo_figure(map_frame),
            carrier_figure(carrier_frame, selected=carriers),
            strip,
            found["cause"],
            found["monthly"],
            found["hourly"],
            found["dist"],
            found["clusters"],
            found["lorenz"],
            found["geo"],
            found["carrier"],
            method,
        )
