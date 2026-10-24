"""
app.py - The interactive dashboard for the CISC7204 A02 pair project.

Run:
    python dashboard/app.py
then open http://127.0.0.1:8050

What it is for
--------------
The analysis answers "where do delay minutes come from". A reader who wants to
apply that answer needs to ask their own question: *my* airport, *my* month,
*my* departure window. The dashboard exists so that a non-specialist can
re-run the decomposition under their own filter instead of reading ours.

Design decisions worth defending in the report
----------------------------------------------
1. Three summary metrics side by side (mean, ≥60 min, ≥180 min) because
   notebook 03 showed the mean alone is unreadable as a level.
2. Every figure is recomputed from the cube under the current filter, not
   swapped between pre-rendered pictures.
3. The monthly panel deliberately ignores the month filter. It is a
   *navigation* chart - removing it would leave the user lost inside a single
   month with no context.

Author: LI Tianhao (mc663312), LI Yingfang (mc661599)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import data_access as da  # noqa: E402
from common import CAUSE_COLORS, CAUSE_COLS, CAUSE_LABELS, INK, MUTED  # noqa: E402

INK = "#22303C"
PANEL = "#FFFFFF"
BG = "#F4F6F8"
GRID = "#E3E8EC"

CARRIERS = (da.load_cube().drop_duplicates("Reporting_Airline")
            .sort_values("Reporting_Airline"))
CARRIER_OPTIONS = [
    {"label": f"{r.carrier_name} ({r.Reporting_Airline})",
     "value": r.Reporting_Airline}
    for r in CARRIERS.itertuples()
]
HOURS = sorted(da.load_cube()["dep_hour"].dropna().unique().tolist())

# The BTS field names mean nothing to a lay reader. These do.
PLAIN_CAUSE = {
    "LateAircraftDelay": "Late-arriving aircraft",
    "CarrierDelay": "Airline operations",
    "NASDelay": "Air traffic & congestion",
    "WeatherDelay": "Extreme weather",
    "SecurityDelay": "Security",
}

app = Dash(__name__, title="US Flight Delay Attribution 2024")
server = app.server

# ---------------------------------------------------------------- helpers
def kpi_card(label: str, value: str, note: str) -> html.Div:
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(note, className="kpi-note"),
    ], className="kpi")


def empty_fig(msg: str = "No flights match this filter") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=13,
                                                            color=MUTED))
    fig.update_layout(paper_bgcolor=PANEL, plot_bgcolor=PANEL,
                      xaxis_visible=False, yaxis_visible=False,
                      margin=dict(l=10, r=10, t=10, b=10), height=280)
    return fig


def base_layout(fig, height=300, legend=False):
    fig.update_layout(
        paper_bgcolor=PANEL, plot_bgcolor=PANEL, height=height,
        margin=dict(l=48, r=18, t=8, b=40),
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=INK),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=-0.32, x=0,
                    font=dict(size=9)),
        hoverlabel=dict(bgcolor="white", font_size=11),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False,
                     linecolor=GRID, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor=GRID, zeroline=False,
                     linecolor=GRID, tickfont=dict(size=10))
    return fig


def panel(title: str, sub: str, graph_id: str) -> html.Div:
    """A figure with a plain-language heading.

    The heading is not decoration: a reader who has never seen a flight-delay
    dataset needs one sentence telling them what they are looking at before
    the axes can mean anything.
    """
    return html.Div([
        html.Div([
            html.Div(title, className="panel-title"),
            html.Div(sub, className="panel-sub"),
        ], className="panel-head"),
        dcc.Graph(id=graph_id, config={"displayModeBar": False}),
    ], className="panel")


# ---------------------------------------------------------------- layout
app.layout = html.Div([
    html.Div([
        html.Div("US Domestic Flight Delay, 2024", className="title"),
        html.Div("Where do the delay minutes actually come from? "
                 "Filter the 7.08 million flights and watch the "
                 "attribution recompute.", className="subtitle"),
    ], className="header"),

    html.Div([
        html.Div([
            html.Label("Month", className="ctrl-label"),
            dcc.Dropdown(id="f-month", options=[
                {"label": da.MONTH_NAME[m], "value": m} for m in range(1, 13)
            ], multi=True, placeholder="All months", className="dd"),
        ], className="ctrl"),
        html.Div([
            html.Label("Reporting carrier", className="ctrl-label"),
            dcc.Dropdown(id="f-carrier", options=CARRIER_OPTIONS,
                         multi=True, placeholder="All carriers",
                         className="dd"),
        ], className="ctrl"),
        html.Div([
            html.Label("Scheduled departure window", className="ctrl-label"),
            dcc.RangeSlider(id="f-hour", min=min(HOURS), max=max(HOURS),
                            value=[min(HOURS), max(HOURS)], step=1,
                            marks={h: f"{h:02d}" for h in range(0, 24, 3)},
                            tooltip={"placement": "bottom"}),
        ], className="ctrl ctrl-wide"),
    ], className="controls"),

    html.Div(id="kpi-row", className="kpi-row"),

    html.Div([
        panel("Delay by month", "Mean delay and how often a flight loses an hour",
              "g-month"),
        panel("Where the delay minutes come from",
              "Share of all attributed delay minutes under this filter",
              "g-cause"),
        panel("Which airlines generate the most delay",
              "Minutes per flight, eight highest under this filter",
              "g-carrier"),
        panel("The evening cascade",
              "Mean delay by scheduled departure hour, 0-23",
              "g-hour"),
        panel("Trip length is almost irrelevant",
              "Mean delay by distance band",
              "g-band"),
        panel("Worst destination states",
              "Minutes per flight; colour = share the airline controls",
              "g-state"),
    ], className="grid"),

    html.Div([
        "Delay causes are published by the U.S. Bureau of Transportation "
        "Statistics only for flights delayed 15 minutes or more, so the "
        "attribution panels cover that subset (1.45 M of 7.08 M flights, "
        "93.7% of all delay minutes). Mean delay and tail probabilities use "
        "all completed flights. Source: BTS Reporting Carrier On-Time "
        "Performance, calendar year 2024.",
    ], className="footnote"),
], className="app")


# ---------------------------------------------------------------- callbacks
@app.callback(
    Output("kpi-row", "children"),
    Output("g-month", "figure"),
    Output("g-cause", "figure"),
    Output("g-carrier", "figure"),
    Output("g-hour", "figure"),
    Output("g-band", "figure"),
    Output("g-state", "figure"),
    Input("f-month", "value"),
    Input("f-carrier", "value"),
    Input("f-hour", "value"),
)
def update(months, carriers, hours):
    months = months or None
    carriers = carriers or None
    hours = tuple(hours) if hours else None

    sub = da.slice_cube(months=months, carriers=carriers, hours=hours)
    k = da.kpis(sub)

    if not k["flights"]:
        cards = [kpi_card("Flights", "0", "no data")] + [
            kpi_card(lbl, "-", "") for lbl in
            ["Mean arrival delay", "Delayed ≥ 60 min", "Delayed ≥ 180 min",
             "Internal share"]]
        blank = empty_fig()
        return cards, blank, blank, blank, blank, blank, blank

    cards = [
        kpi_card("Flights in view", f"{k['flights']:,}",
                 f"{k['flights'] / 7079061 * 100:.1f}% of 2024"),
        kpi_card("Mean arrival delay", f"{k['mean_delay']:+.1f} min",
                 "over completed flights"),
        kpi_card("Delayed ≥ 60 min", f"{k['pct60']:.2f}%",
                 "1 flight in "
                 f"{max(1, round(100 / max(k['pct60'], 1e-9))):,}"),
        kpi_card("Delayed ≥ 180 min", f"{k['pct180']:.2f}%",
                 "the tail that ruins a day"),
        kpi_card("Internal share", f"{k['internal_share']:.1f}%",
                 f"{k['delay_min_per_flight']:.1f} delay min per flight"),
    ]

    # --- monthly navigation chart: ignores the month filter on purpose -----
    nav = da.by_dimension(da.slice_cube(carriers=carriers, hours=hours),
                          "Month").sort_values("Month")
    fig_month = go.Figure()
    fig_month.add_bar(
        x=[da.MONTH_NAME[m] for m in nav["Month"]], y=nav["mean_delay"],
        marker_color=[common.ACCENT if (not months or m in months) else "#D8DEE3"
                      for m in nav["Month"]],
        name="Mean arrival delay", hovertemplate="%{x}: %{y:.2f} min<extra></extra>",
    )
    fig_month.add_scatter(
        x=[da.MONTH_NAME[m] for m in nav["Month"]], y=nav["pct60"],
        mode="lines+markers", name="Share ≥ 60 min (%)",
        yaxis="y2", line=dict(color=INK, width=1.8),
        marker=dict(size=4),
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
    )
    fig_month.update_layout(
        yaxis=dict(title="Mean delay (min)"),
        yaxis2=dict(title="Share ≥ 60 min (%)", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(size=10)),
        bargap=0.35, showlegend=True,
    )
    base_layout(fig_month, height=300, legend=True)
    fig_month.update_layout(legend=dict(orientation="h", y=-0.28, x=0))

    # --- cause composition-------------------------------------------------
    # Five separate rows, not a stacked bar: a 0.7% segment is invisible in a
    # 100% stack, and a non-specialist cannot compare segments of unequal
    # width anyway. Sorted bars answer "which one is biggest" immediately.
    shares = da.cause_shares(sub).sort_values("share")
    fig_cause = go.Figure(go.Bar(
        x=shares["share"],
        y=[PLAIN_CAUSE[c] for c in shares["column"]],
        orientation="h",
        marker_color=[CAUSE_COLORS[c] for c in shares["column"]],
        text=[f"{v:.1f}%" for v in shares["share"]],
        textposition="outside", cliponaxis=False,
        textfont=dict(size=11),
        hovertemplate="%{y}: %{x:.1f}% of attributed minutes<extra></extra>",
        showlegend=False,
    ))
    fig_cause.update_xaxes(
        range=[0, max(50.0, float(shares["share"].max()) * 1.25)],
        title="Share of delay minutes (%)")
    fig_cause.update_yaxes(tickfont=dict(size=10.5))
    fig_cause.update_layout(bargap=0.45, margin=dict(l=132, r=18, t=8, b=40))
    base_layout(fig_cause, height=300)
    fig_cause.update_layout(margin=dict(l=132, r=18, t=8, b=40))

    # --- carrier ranking ---------------------------------------------------
    car = da.by_dimension(sub, "carrier_name").nlargest(8,
                                                        "delay_min_per_flight")
    car = car.sort_values("delay_min_per_flight")
    fig_carrier = go.Figure(go.Bar(
        x=car["delay_min_per_flight"], y=car["carrier_name"], orientation="h",
        marker_color=[common.ACCENT if v > car["delay_min_per_flight"].median()
                      else "#8FA3B8" for v in car["delay_min_per_flight"]],
        customdata=np.stack([car["internal_share"], car["pct60"]], axis=-1),
        hovertemplate=("%{y}<br>%{x:.1f} delay min per flight<br>"
                       "internal share %{customdata[0]:.0f}%<br>"
                       "≥60 min %{customdata[1]:.1f}%<extra></extra>"),
    ))
    fig_carrier.update_xaxes(title="Delay minutes generated per flight")
    fig_carrier.update_layout(bargap=0.45, margin=dict(l=112, r=18, t=8, b=40))
    base_layout(fig_carrier, height=300)
    fig_carrier.update_layout(margin=dict(l=112, r=18, t=8, b=40))

    # --- departure-hour cascade --------------------------------------------
    hr = da.by_dimension(sub, "dep_hour").sort_values("dep_hour")
    fig_hour = go.Figure()
    fig_hour.add_bar(x=hr["dep_hour"], y=hr["mean_delay"],
                     marker_color="#8FA3B8", name="Mean delay")
    fig_hour.add_scatter(x=hr["dep_hour"], y=hr["pct60"], mode="lines+markers",
                         name="Share ≥ 60 min (%)", yaxis="y2",
                         line=dict(color=common.ACCENT, width=2))
    fig_hour.update_layout(
        yaxis=dict(title="Mean delay (min)"),
        yaxis2=dict(title="Share ≥ 60 min (%)", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(size=10)),
        showlegend=True, bargap=0.25,
    )
    fig_hour.update_xaxes(title="Scheduled departure hour", dtick=3)
    base_layout(fig_hour, height=300, legend=True)
    fig_hour.update_layout(legend=dict(orientation="h", y=-0.30, x=0))

    # --- distance bands ----------------------------------------------------
    bd = da.by_dimension(sub, "dist_band").sort_values("dist_band")
    fig_band = go.Figure(go.Bar(
        x=[str(b) for b in bd["dist_band"]], y=bd["mean_delay"],
        marker_color="#2A6F97",
        customdata=bd[["pct60", "internal_share"]],
        hovertemplate=("%{x} miles<br>mean %{y:.2f} min<br>"
                       "≥60 min %{customdata[0]:.2f}%<br>"
                       "internal %{customdata[1]:.0f}%<extra></extra>"),
    ))
    fig_band.update_yaxes(title="Mean arrival delay (min)")
    fig_band.update_xaxes(title="Distance band (miles)")
    base_layout(fig_band, height=300)

    # --- state panel: horizontal bar, same-size encoding as the tile map ---
    state_sub = da.slice_state(months=months, carriers=carriers, hours=hours)
    st = da.by_dimension(state_sub, "DestState").nlargest(
        12, "delay_min_per_flight")
    st = st.sort_values("delay_min_per_flight")
    fig_state = go.Figure(go.Bar(
        x=st["delay_min_per_flight"], y=st["DestState"], orientation="h",
        marker=dict(color=st["internal_share"], colorscale="RdBu",
                    cmin=50, cmax=90,
                    colorbar=dict(title="Internal<br>share %", thickness=9,
                                  len=0.7, tickfont=dict(size=9))),
        customdata=st[["pct60"]],
        hovertemplate=("%{y}<br>%{x:.1f} delay min per flight<br>"
                       "≥60 min %{customdata[0]:.1f}%<extra></extra>"),
    ))
    fig_state.update_xaxes(title="Delay minutes generated per flight")
    fig_state.update_layout(bargap=0.4, margin=dict(l=56, r=10, t=8, b=40))
    base_layout(fig_state, height=300)

    return (cards, fig_month, fig_cause, fig_carrier, fig_hour, fig_band,
            fig_state)


app.index_string = """<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<style>
  html, body { margin:0; padding:0; background:#F4F6F8;
    font-family: Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color:#22303C; }
  .app { max-width:1340px; margin:0 auto; padding:26px 22px 40px; }
  .header { padding-bottom:14px; border-bottom:2px solid #22303C;
    margin-bottom:18px; }
  .title { font-size:25px; font-weight:700; letter-spacing:-0.3px; }
  .subtitle { font-size:12.5px; color:#5A6B7B; margin-top:5px; }
  .controls { display:flex; gap:18px; background:#fff; padding:14px 16px;
    border-radius:8px; box-shadow:0 1px 3px rgba(16,24,40,.07);
    margin-bottom:16px; flex-wrap:wrap; }
  .ctrl { flex:1 1 220px; min-width:200px; }
  .ctrl-wide { flex:1.6 1 300px; }
  .ctrl-label { display:block; font-size:10.5px; font-weight:600;
    text-transform:uppercase; letter-spacing:.6px; color:#5A6B7B;
    margin-bottom:5px; }
  .dd { font-size:12px; }
  .kpi-row { display:grid; grid-template-columns:repeat(5,1fr); gap:12px;
    margin-bottom:16px; }
  .kpi { background:#fff; border-radius:8px; padding:13px 15px;
    box-shadow:0 1px 3px rgba(16,24,40,.07); border-left:3px solid #22303C; }
  .kpi-label { font-size:10.5px; text-transform:uppercase; letter-spacing:.5px;
    color:#5A6B7B; font-weight:600; }
  .kpi-value { font-size:22px; font-weight:700; margin-top:3px;
    letter-spacing:-0.5px; }
  .kpi-note { font-size:10.5px; color:#7A8794; margin-top:2px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .panel { background:#fff; border-radius:8px; padding:14px 16px 8px;
    box-shadow:0 1px 3px rgba(16,24,40,.07); }
  .panel-head { margin-bottom:2px; }
  .panel-title { font-size:12.5px; font-weight:700; }
  .panel-sub { font-size:10.5px; color:#7A8794; margin-top:1px; }
  .footnote { margin-top:18px; font-size:10.5px; color:#7A8794;
    line-height:1.55; border-top:1px solid #DFE4E9; padding-top:12px; }
  .Select-control, .Select-menu-outer { font-size:12px; }
</style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""


if __name__ == "__main__":
    print("Serving dashboard on http://127.0.0.1:8050")
    app.run(debug=False, port=8050)
