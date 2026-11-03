"""Layout: the static frame of the dashboard.

The page is written, not assembled. Reading order, top to bottom:

1. **What is loaded** - a banner when the data is the synthetic fixture, then the
   title and the scope.
2. **The standfirst** - the question the page answers and the method it uses, in
   four sentences, before any control.
3. **The controls and the KPIs** - one filter set, one overview.
4. **What the data says** - the three claims, each with the number that carries
   it. This block used to sit *below* the eight panels, where it was reachable
   only by scrolling past the entire grid; the argument now precedes the evidence.
5. **The evidence** - eight panels, each with a line saying how to read it and a
   sentence saying what it shows for the current filter.
6. **What this page cannot say** - provenance, the attribution floor, the
   stability of the clusters, the model's ceiling. A reader is entitled to the
   limits at the same size as the claims.

Overview first, then filter, then detail on demand - Shneiderman's ordering. Every
control changes the whole page rather than one panel, which is what makes the
three claims above the grid a summary of the eight panels below it.
"""

from __future__ import annotations

from datetime import datetime

from dash import dcc, html

import captions
import data_access as data
from panels.cluster import quality_line
from team01 import config, schema

PANEL_STYLE = {
    "background": "#FFFFFF",
    "border": "1px solid #E3E8ED",
    "borderRadius": "10px",
    "padding": "14px 16px 10px",
    "boxShadow": "0 1px 2px rgba(16,24,40,0.04)",
}

GRAPH_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

SOURCE_LINE = "BTS Reporting Carrier On-Time Performance (transtats.bts.gov)"

STAND_LEAD = (
    "Late flights are not one phenomenon. A flight can be late because its crew "
    "was late, because the airport's traffic flow collapsed, or because the "
    "aircraft it was waiting for was itself late - and BTS charges every delay "
    "minute to one of five causes. This page asks three questions of that "
    "attribution: which causes actually carry the minutes, how unevenly those "
    "minutes sit across flights, and whether the average delay describes a "
    "typical flight at all."
)

DEFAULT_MONTHS = list(range(1, 13))


def kpi_card(item: dict) -> html.Div:
    return html.Div(
        [
            html.Div(item["label"], className="kpi-label"),
            html.Div(item["value"], className="kpi-value"),
            html.Div(item.get("note", ""), className="kpi-note"),
        ],
        className="kpi-card",
    )


def panel(title: str, read: str, graph_id: str, finding_id: str | None = None,
          initial: str = "", height: str = "320px",
          aria: str | None = None, extra: list | None = None) -> html.Div:
    """One card: title, how to read it, chart, what it shows, optional footer slot.

    The graph is wrapped in a labelled container because a Plotly canvas carries
    no accessible name of its own; eight unnamed canvases is eight silent panels
    to a screen reader.

    ``initial`` is the caption for the unfiltered frame, computed at build time.
    Rendering it server-side means the argument survives a page load before the
    callback has run, and a reader who never touches a control still gets it.
    """
    graph = dcc.Graph(id=graph_id, config=GRAPH_CONFIG, style={"height": height})
    wrapper = html.Div(graph, role="img",
                       **{"aria-label": aria or f"{title}. {read}"})
    children = [
        html.Div(title, className="panel-title"),
        html.Div(read, className="panel-read"),
        dcc.Loading(wrapper, type="circle", delay_show=220),
    ]
    if extra:
        children.extend(extra)
    if finding_id:
        children.append(html.Div(initial, id=finding_id, className="panel-find"))
    return html.Div(children, style=PANEL_STYLE)


def _fixture_banner(meta: dict) -> html.Div | None:
    """Sample mode is a smoke fixture, and the page has to say so at the top."""
    if meta.get("mode") != "sample":
        return None
    return html.Div([
        html.Span("Synthetic", className="fixture-tag"),
        html.Span("Smoke fixture built from the BTS schema. Every number on this "
                  "page is simulated - it demonstrates the layout, it is not a "
                  "finding."),
    ], className="fixture-banner")


def _header(meta: dict) -> html.Div:
    """Title left, what is loaded on the right."""
    total = meta.get("total_rows") or meta.get("rows", 0)
    scope = (f"{total:,} flights · "
             f"{len(meta.get('years', []))} years · "
             f"{len(meta.get('carriers', []))} carriers")
    return html.Div([
        html.Div([
            html.H1("US Domestic Flight Delay Drivers", className="app-title"),
            html.Div(
                "CISC7204 Data Science and Data Visualization - Class K, Team 01",
                className="app-subtitle",
            ),
        ]),
        html.Div(scope, className="app-note"),
    ], className="app-header")


def _standfirst() -> html.Div:
    """The question, stated before the first control.

    A dashboard that opens on a filter bar is asking the reader to do the
    framing. This block does it for them, and it names the method - BTS's own
    attribution - because that is what licenses every cause share on the page.
    """
    return html.Div([
        html.P(STAND_LEAD, className="lede-lead"),
        html.P([
            "Choose a year, a carrier or a range of months and every panel below "
            "recomputes. Hover for exact values; click a bubble on the map to hold "
            "one airport. ",
            html.A("How the numbers are made ↓", href="#method",
                   className="lede-link"),
        ], className="lede-meta"),
    ], className="lede")


def _filters(meta: dict) -> html.Div:
    years = meta["years"]
    return html.Div([
        html.Div([
            html.Label("Year", className="filter-label"),
            dcc.Dropdown(
                id="filter-year",
                options=[{"label": "All years", "value": "all"}]
                        + [{"label": str(y), "value": y} for y in years],
                # "All years" is the default because the panel is a ten-year
                # panel: opening on a single year hid the thing the project is
                # about behind a dropdown nobody had a reason to open.
                value="all",
                clearable=False,
            ),
        ], className="filter-cell"),
        html.Div([
            html.Label("Carrier", className="filter-label"),
            dcc.Dropdown(
                id="filter-carrier",
                options=[{"label": c, "value": c} for c in meta["carriers"]],
                value=[],
                multi=True,
                placeholder="All reporting carriers",
            ),
        ], className="filter-cell filter-cell-wide"),
        html.Div([
            html.Label("Months", className="filter-label"),
            dcc.RangeSlider(
                id="filter-months",
                min=1, max=12, step=1, value=[1, 12],
                marks={i: schema.MONTH_LABELS[i - 1] for i in range(1, 13)},
                allowCross=False,
            ),
        ], className="filter-cell filter-cell-slider"),
    ], className="filter-bar")


def _band_head(title: str, note: str) -> html.Div:
    """Section heading: a claim-sized title and one line of orientation."""
    return html.Div([
        html.H2(title, className="band-title"),
        html.P(note, className="band-note"),
    ], className="band-head")


def _findings() -> html.Section:
    """The three claims, above the evidence that supports them."""
    return html.Section([
        _band_head(
            "What the data says",
            "Three claims the eight panels below support, recomputed for the "
            "current filter. Each one is a number and the sentence it licenses.",
        ),
        html.Div(id="insight-strip", className="insight-strip"),
    ], className="band", id="findings")


def _grid(initial: dict[str, str]) -> html.Div:
    """Eight panels, in the order a reader asks the questions.

    Two maps became one: the state fill and the airport bubbles are two channels
    of the same geography, and drawing it twice cost a quarter of the grid while
    the concentration result - the project's strongest claim - had no panel at
    all.

    Each ``read`` line explains the encoding; each ``find-*`` slot receives the
    sentence that states the result, from ``captions``.
    """
    floor = config.min_hour_flights()
    return html.Div([
        panel("The airline controls most of the delay",
              "Bars are attributed minutes, longest at the top. Labels are each "
              "cause's share of the total; blue is airline-controlled, warm is not.",
              "fig-cause", "find-cause", initial=initial["cause"]),
        panel("The split barely moves across the year",
              "Stacked shares of the five causes, one column per month, always "
              "summing to 100%.",
              "fig-monthly", "find-monthly", initial=initial["monthly"]),
        panel("Severe-delay risk climbs through the day",
              f"Bars: share arriving 60+ min late. Line: mean delay, right axis - "
              f"not drawn below {floor:.0f} departures an hour.",
              "fig-hourly", "find-hourly", initial=initial["hourly"]),
        panel("The average hides the typical flight",
              "Completed flights in 5-minute bins. Solid line = median, dashed = "
              "mean; the distance between them is the argument.",
              "fig-dist", "find-dist", initial=initial["dist"]),
        panel("Airports sort into five delay profiles",
              "k-means on the standardised airport feature matrix, projected onto "
              "the first two components. Bubble size = departures. "
              + (quality_line() or "quality measures unavailable"),
              "fig-clusters", "find-clusters", initial=initial["clusters"]),
        panel("A few flights carry most of the delay",
              "Flights ranked worst first on the x axis; the y axis is the share of "
              "all positive delay minutes they carry. The diagonal is perfect "
              "equality.",
              "fig-lorenz", "find-lorenz", initial=initial["lorenz"]),
        panel("Delay and traffic are different maps",
              "State fill = mean delay; bubble size = departures; grey state = no "
              "flights in this filter; click an airport to drill in.",
              "fig-geo", "find-geo", initial=initial["geo"], height="560px",
              extra=[html.Div([
                  html.Span(id="airport-chip-label", className="chip"),
                  html.Button("clear", id="airport-clear", className="chip-clear",
                              n_clicks=0),
              ], className="airport-chip")]),
        panel("Which carrier you fly changes the delay",
              "One row per carrier: dot = mean, dot = 90th percentile, the line "
              "between them is the tail. Always against all carriers, not just the "
              "filtered ones.",
              "fig-carrier", "find-carrier", initial=initial["carrier"],
              height="560px"),
    ], className="grid")


def _method(meta: dict) -> html.Section:
    """What the page cannot say, at the size of the claim.

    Four cards, each one a limit a sceptical reader would otherwise have to
    discover alone. The numbers come from the artefacts (``clusters.json``,
    ``models.json``) rather than from this file, so a re-run that changes them
    changes the text.
    """
    floor = config.threshold()
    if meta.get("mode") == "sample":
        source = ("Every figure on this page is drawn from a synthetic fixture built "
                  "to the BTS schema "
                  f"({meta.get('rows', 0):,} rows over "
                  f"{len(meta.get('years', []))} years). The pipeline, the "
                  "thresholds and the wording are real work; the results are not "
                  "findings and must not be quoted as such.")
    else:
        total = meta.get("total_rows") or meta.get("rows", 0)
        sample = meta.get("rows", 0)
        source = (f"{total:,} completed flights loaded, "
                  f"{len(meta.get('years', []))} years, "
                  f"{len(meta.get('carriers', []))} reporting carriers. Source: "
                  f"{SOURCE_LINE}.")
        if sample and sample != total:
            source += (f" The interactive charts draw a {sample:,}-flight sample of "
                       f"that panel to stay responsive; the printed figures use the "
                       f"full panel.")

    cards = [
        ("Where the numbers come from", source),
        ("What a cause minute is",
         f"BTS reports the five cause fields only for flights that arrive at least "
         f"{floor:.0f} minutes late, and charges 100% of such a delay to one cause. "
         f"The cause ranking therefore describes delayed flights, not all flights, "
         f"and it inherits BTS's attribution rather than an independent audit. An "
         f"early arrival contributes zero delay minutes."),
        ("What the archetypes are not",
         captions.cluster_note()),
        ("How far the model gets",
         captions.model_note()),
        ("What the page leaves out",
         "Cancelled and diverted flights are excluded, so everything here describes "
         "flights that operated. No weather station data and no aircraft-rotation "
         "feed is joined, which is why 'late aircraft' is a label rather than a "
         "chain of causation."),
    ]
    items = [html.Div([html.H3(title, className="method-title"),
                       html.P(text, className="method-text")], className="method-card")
             for title, text in cards]
    return html.Section([
        _band_head(
            "What this page cannot say",
            "The limits that survive the data. Everything here is a property of the "
            "table or of the method, not a caveat about sample size.",
        ),
        html.Div([
            html.P(id="method-note", className="method-note",
                   children=captions.method_note(
                       data.apply_filters("all", None, DEFAULT_MONTHS))),
        ], className="method-lead"),
        html.Div(items, className="method-grid"),
    ], className="method", id="method")


def _takeaway(items: list[dict]) -> html.Section:
    """What to do with the findings: three actions a passenger can take.

    The findings band reports the data; this band turns the same three numbers
    into advice. It is static on purpose - these are properties of the whole
    ten-year panel, not of the active filter, so a year or carrier change should
    not rewrite them. Every sentence closes by pointing at the limits rather
    than promising an arrival time, which is what keeps the advice honest.
    """
    cards = [html.Div([html.H3(item["title"], className="takeaway-title"),
                       html.P(item["text"], className="takeaway-text")],
                      className="takeaway-item")
             for item in items]
    return html.Section([
        _band_head(
            "What a passenger can keep in mind",
            "Three things to act on. Each is direction, not a promise - the "
            "limits in the next section say how far they go.",
        ),
        html.Div(cards, className="takeaway-strip"),
    ], className="band")


def _sample_note(meta: dict) -> html.Div | None:
    """One line under the KPI strip saying the page is drawn from a sample.

    The header names the panel and the cards name the sample, so without this
    line the two totals sit three centimetres apart with no explanation and the
    reader has to decide which one to disbelieve. Stating the fraction once is
    cheaper than repeating it on five cards.
    """
    sample = int(meta.get("rows") or 0)
    total = int(meta.get("total_rows") or sample)
    if not (total and sample and total > sample):
        return None
    return html.Div(
        f"Headline numbers and charts are computed on a random "
        f"{sample:,}-flight sample ({sample / total:.1%}) of the "
        f"{total:,}-flight completed panel, so a filter change answers "
        f"immediately. Every printed figure in the proposal uses the full panel.",
        className="kpi-caption", id="kpi-caption")


def build(meta: dict) -> html.Div:
    """Assemble the page. ``meta`` comes from ``data_access.available()``."""
    banner = _fixture_banner(meta)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    # The captions for the unfiltered frame, rendered into the first paint. They
    # are recomputed by the callback on every filter change; doing it once here
    # as well means the page says something even before Dash hydrates.
    opening = data.apply_filters("all", None, DEFAULT_MONTHS)
    initial = captions.findings(opening, opening)
    takeaway = captions.takeaways(opening)

    total = meta.get("total_rows") or meta.get("rows", 0)
    footer = html.Div([
        html.Span(f"Source: {SOURCE_LINE}"),
        html.Span(className="footer-dot", children="·"),
        html.Span(f"Mode: {meta.get('mode', 'unknown')} · "
                  f"{total:,} completed flights loaded · "
                  f"page generated {generated}"),
        html.Span(className="footer-dot", children="·"),
        html.A("Method and limits", href="#method", className="footer-link"),
    ], className="app-footer")

    children = [dcc.Location(id="url", refresh=False),
                dcc.Store(id="drill-airport")]
    children += [c for c in (banner, _header(meta)) if c is not None]
    children += [_standfirst(), _filters(meta)]
    children += [html.Div(id="kpi-strip", className="kpi-strip")]
    children += [n for n in (_sample_note(meta),) if n is not None]
    children += [
        _findings(),
        html.Section([
            _band_head(
                "The evidence",
                "Eight views of the same filtered table, in the order the questions "
                "are asked. The sentence under each panel states what it shows for "
                "the filter you have chosen.",
            ),
            _grid(initial),
        ], className="band"),
        _takeaway(takeaway),
        _method(meta),
        footer,
    ]
    return html.Div(children, className="app-shell")
