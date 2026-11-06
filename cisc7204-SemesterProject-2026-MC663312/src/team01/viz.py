"""Figure library.

One function per figure, each written to ``figures/`` at 300 dpi. The design
rules from Section 6 of the proposal are enforced here rather than remembered:

* encoding follows the question - position for comparison, area only for
  part-to-whole with every cell labelled, colour only for categories;
* a cause keeps its colour across every figure (``schema.CAUSE_COLORS``);
* sequential scales are monotonic in lightness so they survive greyscale print;
* the mean is never drawn alone when the distribution is available.

Importing this module sets a shared matplotlib style; it does not import the
``matplotlib.pyplot`` global state, so notebooks and scripts can both use it.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")                       # headless: notebooks and CI both

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from . import config, schema

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": int(config.get("viz.dpi", 300)),
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 10,
    "axes.edgecolor": schema.AXIS_INK,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": schema.GRID,
    "grid.linewidth": 0.6,
    "xtick.color": schema.AXIS_INK,
    "ytick.color": schema.AXIS_INK,
    "legend.frameon": False,
})


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------
def save(fig, name: str) -> str:
    """Write a figure to figures/<name>.png and return the path as text."""
    _stamp_source(fig)
    target = config.ensure_parent(config.FIG_DIR / f"{name}.png")
    fig.savefig(target)
    from . import provenance
    import json
    target.with_suffix(".json").write_text(json.dumps({"run_signature":provenance.signature(),"image_sha256":provenance.file_digest(target)},indent=2),encoding="utf-8")
    plt.close(fig)
    print(f"[viz] {target.name}")
    return str(target)


def _stamp_source(fig):
    """Provenance line under every figure, plus a corner tag in fixture mode.

    Applied in ``save`` rather than inside ``_caption`` because two figures
    (the Lorenz curve and the dashboard contact sheet) build their own layout
    and never call ``_caption``. A figure pasted into a report or a slide
    outlives the script that produced it, so it has to carry its own source.

    In sample mode the stamp is deliberately loud. The fixture has the same
    schema as the real panel, which is exactly why a screenshot of it can be
    mistaken for a real result if nothing on the image says otherwise.
    """
    synthetic = config.mode() == "sample"
    if synthetic:
        text = ("SYNTHETIC FIXTURE - same schema as BTS, values simulated; "
                "not a BTS result")
        colour = schema.SYNTHETIC_RED
    else:
        text = "Source: BTS Reporting Carrier On-Time Performance, transtats.bts.gov"
        colour = schema.TEXT_GREY

    # The caption may have been pushed down to clear a legend that sits under
    # the axes, so the stamp follows the caption instead of assuming it starts
    # at -0.02. Figure coordinates, so the offset is a fraction of the canvas
    # height; 0.030 clear a 7.5 pt line at the heights used here.
    caption_y = float(getattr(fig, "_caption_y", -0.02))
    caption_lines = int(getattr(fig, "_caption_lines", 1))
    fig.text(0.005, caption_y - 0.030 * caption_lines, text, fontsize=7.5,
             color=colour, ha="left", va="top",
             weight="bold" if synthetic else "normal")

    if synthetic:
        # A corner tag survives cropping better than a footer line does.
        fig.text(0.995, 1.012, "SYNTHETIC DATA", fontsize=8, color=colour,
                 ha="right", va="bottom", weight="bold",
                 bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
                       "edgecolor": colour, "linewidth": 0.9})


def _clean(ax, xlabel: str = "", ylabel: str = "", grid_axis: str | None = "y"):
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if grid_axis:
        ax.grid(axis=grid_axis, color=schema.GRID, linewidth=0.6, zorder=0)
        ax.set_axisbelow(True)
    return ax


def _caption(fig, text: str, y: float = -0.02):
    """A short caption inside the image, so a pasted figure stays readable.

    ``y`` moves the line down when a figure places a legend under the axes. The
    default put the caption straight through the cause-mix legend, and both
    lines became unreadable on the one figure whose job is to be read at a
    glance. ``_stamp_source`` follows whatever position is set here.
    """
    fig._caption_y = y
    fig._caption_lines = text.count("\n") + 1
    fig.text(0.005, y, text, fontsize=7.5, color=schema.TEXT_GREY, ha="left", va="top")


# --------------------------------------------------------------------------
# 1. Part-to-whole: unit waffle
# --------------------------------------------------------------------------
def _waffle_counts(totals: pd.DataFrame) -> dict[str, int]:
    """Allocate exactly 100 cells by largest remainder.

    Plain rounding can sum to 99 or 101, which draws a hole in the grid or
    silently drops the smallest cause. Largest remainder keeps the grid full and
    every cause visible.
    """
    raw = totals.set_index("cause_key")["share"] * 100
    counts = np.floor(raw).astype(int)
    shortfall = 100 - int(counts.sum())
    if shortfall > 0:
        order = (raw - counts).sort_values(ascending=False).index
        for key in order[:shortfall]:
            counts[key] += 1
    elif shortfall < 0:
        order = counts.sort_values(ascending=False).index
        for key in order[: -shortfall]:
            if counts[key] > 0:
                counts[key] -= 1
    return counts.to_dict()


def fig_cause_waffle(totals: pd.DataFrame, name: str = "01_cause_waffle"):
    """10x10 waffle: one cell = 1% of attributed delay minutes.

    Area is a weak channel, which is why every cell is drawn on a common grid
    and the shares are written into the legend rather than read off the shape.
    """
    shares = _waffle_counts(totals)
    order = totals["cause_key"].tolist()

    cells: list[str] = []
    for key in order:
        cells.extend([key] * int(shares.get(key, 0)))
    cells = (cells + [order[0]] * 100)[:100]

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    for index, key in enumerate(cells):
        row, col = divmod(index, 10)
        ax.add_patch(Rectangle((col, 9 - row), 0.94, 0.94,
                               facecolor=schema.CAUSE_COLORS[key],
                               edgecolor="white", linewidth=0.8))
    ax.set_xlim(-0.2, 10.1)
    ax.set_ylim(-0.2, 10.1)
    ax.set_aspect("equal")
    ax.axis("off")

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=schema.CAUSE_COLORS[k], edgecolor="white")
        for k in order
    ]
    labels = [
        f"{schema.CAUSE_LABELS_LONG[k]}  {shares.get(k, 0):d}%"
        for k in order
    ]
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=2, fontsize=9)
    ax.set_title("Where the delay minutes come from\n"
                 "One cell = 1% of attributed minutes", pad=14)
    _caption(fig, "BTS cause minutes, flights delayed >= 15 min. "
                  "Carrier + late aircraft is descriptive, not airline control.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 2. Ordered and cyclical: hour cascade, stacked area over months
# --------------------------------------------------------------------------
def fig_monthly_composition(long: pd.DataFrame, name: str = "02_monthly_composition"):
    """Stacked area of monthly cause shares. The 2020 dip is annotated, not hidden.

    The legend sits in a reserved band under the axes rather than at an arbitrary
    negative offset: at the old offset it was drawn at almost exactly the same
    height as the caption, and the two lines printed through each other. The
    bottom margin, the legend anchor and the caption height are therefore three
    numbers that have to agree, so they are set next to each other.
    """
    pivot = (
        long.pivot_table(index="month", columns="cause_key", values="share", aggfunc="mean")
        .reindex(columns=[c for c in schema.CAUSE_COLUMNS])
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    fig.subplots_adjust(bottom=0.30, top=0.84)
    bottom = np.zeros(len(pivot))
    for cause in pivot.columns:
        values = pivot[cause].fillna(0).to_numpy()
        ax.bar(pivot.index, values, bottom=bottom, width=0.78,
               color=schema.CAUSE_COLORS[cause], label=schema.CAUSE_LABELS[cause],
               edgecolor='white', linewidth=0.4)
        bottom += values
    ax.set_xlim(0.4, 12.6)
    ax.set_ylim(0, 1)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(schema.MONTH_LABELS)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Cause mix by month\nShare of attributed delay minutes")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=5,
              fontsize=8.5, columnspacing=1.3, handlelength=1.1)
    _clean(ax, "", "", grid_axis=None)
    # A hundred-percent stack shows composition, not movement: a band that
    # shifts by a point and a half is invisible at this width. Saying the
    # largest month-to-month move in the caption is what turns "it looks flat"
    # into the finding "it is flat to within 1.4 points".
    swing = float((pivot.max() - pivot.min()).max() * 100) if len(pivot) > 1 else 0.0
    _caption(fig, "Shares sum to 100% within each month; colours are fixed per cause. "
                  f"No cause moves more than {swing:.1f} points across the year.",
             y=0.055)
    return save(fig, name)


# --------------------------------------------------------------------------
# 3. Ranked comparison: carrier minutes per flight
# --------------------------------------------------------------------------
def fig_carrier_bars(table: pd.DataFrame, name: str = "03_carrier_bars"):
    """Horizontal bars ordered by delay burden, with direct value labels.

    An empty table used to draw an empty axis: matplotlib auto-scales to
    ±0.06, every label still renders, and the file looks like a chart that
    simply failed to load. That is worse than a crash, because a crash stops the
    pipeline while a blank figure reaches the report. The guard below makes the
    failure loud at the point where the table is still small enough to inspect.
    """
    if table is None or table.empty:
        raise ValueError(
            "fig_carrier_bars received an empty table - the carrier floor in "
            "config/project.yaml is above every carrier's attributed flights"
        )
    data = table.sort_values("minutes_per_flight", ascending=True)
    fig, ax = plt.subplots(figsize=(7.2, 0.34 * len(data) + 1.6))
    colors = [schema.ACCENT if v == data["minutes_per_flight"].max() else schema.MUTED
              for v in data["minutes_per_flight"]]
    ax.barh(data["carrier"], data["minutes_per_flight"], color=colors, height=0.72)
    for y, value in enumerate(data["minutes_per_flight"]):
        # The reference line runs through the label column, so each value gets a
        # small opaque pad; without it five labels are struck through by a
        # dashed rule that is supposed to sit behind them.
        ax.text(value, y, f" {value:,.1f}", va="center", fontsize=8.5,
                color=schema.INK, zorder=4,
                bbox={"boxstyle": "square,pad=0.12", "facecolor": "white",
                      "edgecolor": "none", "alpha": 0.9})

    # The bar ranking answers "who is worst" only if the bars differ. A
    # reference line puts every carrier against the same baseline, so a
    # one-tenth-of-a-minute gap at the top stops being a story.
    overall = float(data["delay_minutes"].sum() / data["flights"].sum())
    ax.axvline(overall, color=schema.INK, lw=0.9, ls=(0, (4, 2)), zorder=1)
    ax.set_ylim(-0.6, len(data) - 0.05)
    ax.annotate(f"all carriers {overall:,.1f}", xy=(overall, len(data) - 0.32),
                xytext=(3, 0), textcoords="offset points", fontsize=7.6,
                color=schema.INK, va="center")

    ax.set_title("Attributed delay minutes per delayed flight")
    ax.margins(x=0.12)
    _clean(ax, "Minutes per delayed flight", "", grid_axis="x")
    floor = int(config.get_for_mode("attribution.carrier_min_flights", 5000))
    spread = float(data["minutes_per_flight"].max() / data["minutes_per_flight"].min())
    narrow = ("Carriers sit within "
              f"{(spread - 1) * 100:.0f}% of each other, so the order is a "
              "description, not a distinction. ") if spread < 1.15 else ""
    _caption(fig, "Attribution universe only (arrival delay >= 15 min). "
                  f"Carriers below {floor:,} attributed flights are omitted. "
                  f"{narrow}Dashed line = the same ratio for every carrier shown.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 4. Distribution: percentile band by month
# --------------------------------------------------------------------------
def fig_percentile_band(profile: pd.DataFrame, name: str = "04_percentile_band"):
    """Two stacked panels: the distribution, then the risk it implies.

    A single axis holding the p99 (often near 200 minutes) flattens the median
    and the mean into the same line and the figure stops communicating. Splitting
    the view keeps the percentile comparison readable and gives the severe-delay
    share its own scale, which is the number a traveller actually acts on.
    """
    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(8.4, 6.2), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.0], "hspace": 0.18},
    )
    x = profile["month"]

    ax.fill_between(x, profile["median"], profile["p90"], color=schema.OKABE_ITO["sky"],
                    alpha=0.28, label="Median to p90")
    ax.plot(x, profile["median"], color=schema.OKABE_ITO["blue"], lw=2.2, label="Median")
    ax.plot(x, profile["mean"], color=schema.ACCENT, lw=2, ls="--", label="Mean")
    ax.plot(x, profile["p90"], color=schema.OKABE_ITO["sky"], lw=1.6,
            label="90th percentile")
    ax.axhline(0, color=schema.ZERO_LINE, lw=0.8)
    ax.set_title("The average is not the typical flight\n"
                 "Arrival delay by month (minutes)")
    # Headroom so the legend never sits on top of the p90 line.
    low, high = ax.get_ylim()
    ax.set_ylim(low, high + (high - low) * 0.22)
    ax.legend(loc="upper left", ncol=4, fontsize=8.5)
    _clean(ax, "", "Arrival delay (min)")

    ax2.bar(x, profile["share_delayed_60"], color=schema.OKABE_ITO["orange"],
            width=0.72, label="Share delayed 60+ min")
    ax2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(schema.MONTH_LABELS)
    _clean(ax2, "", "Delayed 60+ min")

    _caption(fig, "Median stays below zero while the mean stays above it in every "
                  "month: the two describe different flights.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 4b. Encoding comparison: mean bars versus the distribution
# --------------------------------------------------------------------------
def fig_mean_bar_vs_band(profile: pd.DataFrame, name: str = "14_mean_bar_vs_band"):
    """The proposal's central claim, drawn twice from one table.

    The left panel is not a straw man. It follows every rule - zero baseline,
    labelled values, ordered months, a defensible grey - and it still cannot
    support the sentence a traveller needs, because twelve means cannot show
    that the average flight lands later than the typical flight. The right
    panel keeps the distribution the mean was computed from.

    Both panels are built from the same ``monthly_profile`` frame, so the
    comparison isolates the encoding rather than the data. That is the point:
    a defensible chart can still make the decision invisible.
    """
    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(11.8, 4.4),
        gridspec_kw={"wspace": 0.24, "width_ratios": [1.0, 1.3]},
    )
    x = profile["month"].to_numpy()
    mean = profile["mean"].to_numpy()
    median = profile["median"].to_numpy()
    p90 = profile["p90"].to_numpy()

    # --- Panel A: the chart most delay reports stop at ---------------------
    ax_a.bar(x, mean, width=0.72, color=schema.MUTED, zorder=3)
    for xi, yi in zip(x, mean):
        ax_a.text(xi, yi + 0.3, f"{yi:.1f}", ha="center", va="bottom",
                  fontsize=7.0, color=schema.INK)
    ax_a.set_ylim(0, float(mean.max()) * 1.20)
    ax_a.set_xticks(range(1, 13))
    ax_a.set_xticklabels(schema.MONTH_LABELS, fontsize=8.0)
    ax_a.set_title("A · One mean per month\nReads as a mild seasonal pattern")
    _clean(ax_a, "", "Arrival delay (min)")

    spread = float(mean.max() - mean.min())
    ax_a.annotate(f"Whole year spans {spread:.1f} min",
                  xy=(0.03, 0.94), xycoords="axes fraction", fontsize=8.5,
                  color=schema.INK, weight="bold", va="top")

    # --- Panel B: the same twelve months, distribution kept ----------------
    ax_b.fill_between(x, median, p90, color=schema.OKABE_ITO["sky"], alpha=0.24,
                      zorder=2)
    ax_b.plot(x, p90, color=schema.OKABE_ITO["sky"], lw=1.5, zorder=3)
    ax_b.plot(x, median, color=schema.OKABE_ITO["blue"], lw=2.3, zorder=4)
    ax_b.plot(x, mean, color=schema.ACCENT, lw=2.0, ls="--", zorder=5)
    ax_b.axhline(0, color=schema.ZERO_LINE, lw=0.9, zorder=1)

    # Direct labels on the right edge instead of a legend: the reader should
    # not have to travel to a box and back to learn which line is which.
    ax_b.set_xlim(0.6, 13.9)
    for value, label, colour in ((median[-1], "Median", schema.OKABE_ITO["blue"]),
                                 (mean[-1], "Mean", schema.ACCENT),
                                 (p90[-1], "90th pct", schema.OKABE_ITO["sky"])):
        ax_b.annotate(label, xy=(12.15, value), fontsize=8.6, color=colour,
                      va="center", ha="left", weight="bold")
    ax_b.annotate("median to p90 spread", xy=(6.0, (median[5] + p90[5]) / 2.0),
                  fontsize=7.8, color=schema.ANNOT_BLUE, ha="center", va="center",
                  style="italic")

    ax_b.set_xticks(range(1, 13))
    ax_b.set_xticklabels(schema.MONTH_LABELS, fontsize=8.0)
    ax_b.set_title("B · Same months, distribution kept\nThe median never crosses zero")
    _clean(ax_b, "", "Arrival delay (min)")

    _caption(fig, "Both panels plot the same table. A bar per month cannot show that "
                  "the median never crosses zero, so it cannot show that the average "
                  "flight is not the typical one.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 5. Concentration: Lorenz curve
# --------------------------------------------------------------------------
def fig_lorenz(result: dict, name: str = "05_lorenz"):
    """Cumulative share of delay minutes against the worst x% of flights."""
    curve = result.get("curve")
    if curve is None or curve.empty:
        return ""
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.plot([0, 1], [0, 1], color=schema.EQUALITY_LINE, lw=1, ls=":", label="Perfect equality")
    ax.plot(curve["share_of_flights"], curve["share_of_minutes"],
            color=schema.ACCENT, lw=2.2, label="Observed")
    ax.fill_between(curve["share_of_flights"], curve["share_of_flights"],
                    curve["share_of_minutes"], color=schema.ACCENT, alpha=0.12)

    top1 = result.get("top1_share", np.nan)
    # A full-height vline at 1% sits within two pixels of the y-axis and reads
    # as a doubled spine. The marker is a short guide from the axis to the curve
    # plus a dot on the curve, so it is unmistakably an annotation.
    ax.plot([0.01, 0.01], [0, top1], color=schema.MUTED, lw=0.8, ls="--", zorder=2)
    ax.scatter([0.01], [top1], s=22, color=schema.ACCENT, zorder=4)
    ax.annotate(f"Worst 1% of flights\n= {top1:.1%} of delay minutes",
                xy=(0.011, top1), xytext=(0.16, max(top1 - 0.22, 0.08)),
                fontsize=9, color=schema.INK,
                arrowprops={"arrowstyle": "->", "color": schema.ARROW_GREY, "lw": 0.9})

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Delay minutes are concentrated\n"
                 f"Gini coefficient {result.get('gini', float('nan')):.3f}")
    ax.legend(loc="lower right", fontsize=8.5)
    _clean(ax, "Share of flights, worst first", "Share of delay minutes")
    _caption(fig, "Positive arrival-delay minutes only: a flight that arrived early "
                  "contributes zero, which is why the curve is flat at the origin.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 6. Near-null effect: distance bands
# --------------------------------------------------------------------------
def fig_distance_bands(bands: pd.DataFrame, name: str = "06_distance_bands"):
    """Mean delay and p90 by distance band, with intervals instead of a trend line.

    The pilot's apparent distance effect disappeared once hour, month and
    carrier were controlled. This figure shows the raw gradient honestly and
    the near-flat shape is the argument, not an accident.
    """
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(bands))
    ax.plot(x, bands["mean"], marker="o", color=schema.OKABE_ITO["blue"],
            lw=2, label="Mean")
    ax.plot(x, bands["p90"], marker="s", color=schema.OKABE_ITO["orange"],
            lw=2, ls="--", label="90th percentile")
    ax.set_xticks(x)
    ax.set_xticklabels(bands["band"])
    ax.set_ylim(bottom=0)
    ax.set_title("Arrival delay by route distance band\nDescriptive groups, different flight mixes")
    ax.legend(loc="upper left", fontsize=9)
    _clean(ax, "Route distance band (statute miles)", "Delay (min)")
    _caption(fig, "These raw groups mix routes, carriers and schedules. "
                  "They do not isolate the effect of distance.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 7. Geography: state tile grid
# --------------------------------------------------------------------------
STATE_TILES: dict[str, tuple[int, int]] = {
    "AK": (0, 0), "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4),
    "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "RI": (2, 9), "MA": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4),
    "IN": (3, 5), "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4),
    "KY": (4, 5), "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
    "NC": (5, 6), "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 1), "LA": (6, 2), "MS": (6, 3), "AL": (6, 4), "GA": (6, 5),
    "HI": (7, 0), "TX": (7, 2), "FL": (7, 8),
}


def fig_state_tile(values: pd.Series, name: str = "07_state_tiles",
                   metric_label: str = "Mean arrival delay (min)"):
    """Equal-weight state tile grid.

    A choropleth gives large rural states visual dominance regardless of
    traffic. The tile grid keeps every state the same size and is the reason it
    is the default geographic view in this project; the dashboard adds a
    choropleth alongside it for magnitude reading, because only a real map can
    place airport bubbles.

    The scale is chosen from the data, not from the metric's name. Mean delay is
    non-negative, so a two-slope scale pinned at zero spent its entire blue half
    on values that cannot occur: every state landed between mid-orange and dark
    red and the differences that matter were invisible. A diverging scale is
    used only when the values actually straddle the midpoint.
    """
    values = values.dropna()
    if values.empty:
        raise ValueError("fig_state_tile received no state values")

    low, high = float(values.min()), float(values.max())
    if low < 0 < high:
        limit = float(np.nanmax(np.abs(values))) or 1.0
        norm = matplotlib.colors.TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
        cmap = plt.get_cmap(schema.DIVERGING_CMAP)
        scale_note = "zero is the midpoint"
    else:
        norm = matplotlib.colors.Normalize(vmin=min(low, 0.0), vmax=high)
        cmap = plt.get_cmap(schema.SEQUENTIAL_CMAP)
        scale_note = "sequential scale: the metric cannot be negative"

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    for state, (row, col) in STATE_TILES.items():
        value = values.get(state, np.nan)
        # The no-data grey has to be visible against white, or "no qualifying
        # flights" reads as "an empty cell I forgot to fill".
        face = schema.NO_DATA if pd.isna(value) else cmap(norm(value))
        ax.add_patch(Rectangle((col, 7 - row), 0.92, 0.92, facecolor=face,
                               edgecolor="white", linewidth=1.2))
        # The label has to survive both ends of the ramp: white on the dark end,
        # ink on the pale end, decided per tile instead of once for the figure.
        rgba = matplotlib.colors.to_rgba(face) if not pd.isna(value) else None
        dark_tile = rgba is not None and _luminance(rgba) < 0.45
        label_colour = "white" if dark_tile else schema.INK
        ax.text(col + 0.46, 7 - row + 0.60, state, ha="center", va="center",
                fontsize=8, fontweight="bold", color=label_colour)
        if not pd.isna(value):
            ax.text(col + 0.46, 7 - row + 0.26, f"{value:.1f}", ha="center",
                    va="center", fontsize=6.6, color=label_colour)

    ax.set_xlim(-0.1, 11.1)
    ax.set_ylim(-0.1, 8.1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{metric_label} by origin state")
    scalar = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    bar = fig.colorbar(scalar, ax=ax, fraction=0.025, pad=0.01)
    bar.set_label(metric_label, fontsize=8)
    bar.ax.tick_params(labelsize=7)
    _caption(fig, f"Equal-area tiles: one state, one cell. Grey = no qualifying "
                  f"flights. {scale_note.capitalize()}.")
    return save(fig, name)


def _luminance(rgba: tuple[float, float, float, float]) -> float:
    """Relative luminance of an RGB triple, for choosing a readable label colour."""
    red, green, blue = rgba[:3]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


# --------------------------------------------------------------------------
# 8. Within-day cascade
# --------------------------------------------------------------------------
def fig_cascade_hour(hourly: pd.DataFrame, name: str = "08_cascade_hour", min_turnaround: int = 25):
    """Separate aligned units; pressure is not a causal arrival-delay share."""
    floor=config.min_hour_flights()
    enough=hourly['flights'].fillna(0)>=floor
    fig,(ax,ratio)=plt.subplots(2,1,figsize=(8.4,6.0),sharex=True)
    ax.bar(hourly['dep_hour'],hourly['inherited_min'],color=schema.OKABE_ITO['sky'])
    _clean(ax,'','Turnaround pressure (min)')
    ax.set_title('Hypothetical turnaround pressure by local hour\nComplete sampled aircraft sequences; UTC matching')
    ratio.plot(hourly['dep_hour'],hourly['inherited_share'].where(enough),color=schema.ACCENT,marker='o',ms=3)
    ratio.set_ylim(bottom=0)
    _clean(ratio,'Scheduled departure hour · origin-local time','Pressure / arrival-delay ratio')
    ratio.set_xticks(range(0,24,2))
    fig.subplots_adjust(hspace=.25,bottom=.20)
    _caption(fig,f'{min_turnaround}-minute assumed minimum turn; not causal arrival attribution. Ratios may exceed 1. '
                 f'Line hidden below {floor:,.0f} flights/hour.')
    return save(fig,name)


# --------------------------------------------------------------------------
# 9. Clustering
# --------------------------------------------------------------------------
def fig_silhouette(sweep: pd.DataFrame, chosen_k: int, name: str = "09_silhouette"):
    """Selection evidence: silhouette by k, with the chosen k and the rejected peak.

    The sweep almost always peaks at a k whose smallest cluster is a singleton.
    Without saying so, the figure contradicts itself: a reader sees the maximum at
    k = 5 while the ring sits on k = 3 and concludes the choice was arbitrary. The
    rejection is therefore drawn on the axis, not explained in a caption.
    """
    floor = int(config.get("cluster.min_cluster_size", 3))
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    ax.plot(sweep["k"], sweep["silhouette"], marker="o",
            color=schema.OKABE_ITO["blue"], lw=2, zorder=3)

    peak = sweep.loc[sweep["silhouette"].idxmax()]
    if int(peak["k"]) != int(chosen_k) and int(peak["smallest_cluster"]) < floor:
        ax.scatter(peak["k"], peak["silhouette"], s=70, marker="x",
                   color=schema.MUTED, linewidth=1.8, zorder=5)
        ax.annotate(
            f"k = {int(peak['k'])} rejected -\n"
            f"smallest cluster = {int(peak['smallest_cluster'])}",
            xy=(float(peak["k"]), float(peak["silhouette"])),
            xytext=(26, 6), textcoords="offset points", fontsize=8,
            color=schema.MUTED, ha="left", va="bottom",
            arrowprops={"arrowstyle": "-", "color": schema.GRID, "lw": 0.8},
            bbox={"boxstyle": "square,pad=0.2", "facecolor": "white",
                  "edgecolor": "none", "alpha": 0.9},
        )

    chosen = sweep[sweep["k"] == chosen_k]
    if not chosen.empty:
        ax.scatter(chosen["k"], chosen["silhouette"], s=110, facecolor="none",
                   edgecolor=schema.ACCENT, linewidth=2, zorder=6)
        ax.annotate(f"k = {chosen_k}, chosen",
                    xy=(chosen_k, float(chosen["silhouette"].iloc[0])),
                    xytext=(9, 9), textcoords="offset points", fontsize=9,
                    color=schema.ACCENT, fontweight="bold")
    ax.set_xticks(sweep["k"])
    ax.set_title("Choosing k by silhouette score")
    ax.margins(y=0.24)
    _clean(ax, "Number of clusters", "Silhouette (higher is better)")
    _caption(fig, "Highest silhouette among k whose smallest cluster holds at least "
                  f"{floor} airports; the Ward dendrogram is the second check.")
    return save(fig, name)


def fig_cluster_scatter(airports: pd.DataFrame, names: dict[int, str] | None = None,
                        stats: dict | None = None,
                        name: str = "10_cluster_scatter"):
    """PCA projection of the standardised feature space, coloured by archetype.

    ``stats`` carries the solution's quality measures (k, silhouette, bootstrap
    ARI, airport count). They are printed in the title rather than kept in
    ``outputs/metrics/clusters.json``: a scatter of coloured groups reads as a
    discovered typology, and a reader who never sees the file has no way to
    judge whether the grouping survives resampling. Two lines of text are
    enough to stop the figure over-claiming.
    """
    palette = [schema.OKABE_ITO["blue"], schema.OKABE_ITO["orange"],
               schema.OKABE_ITO["green"], schema.OKABE_ITO["purple"],
               schema.OKABE_ITO["vermillion"], schema.OKABE_ITO["sky"],
               schema.OKABE_ITO["yellow"]]

    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    for i, (cluster, chunk) in enumerate(airports.groupby("cluster", observed=True)):
        color = palette[i % len(palette)]
        size = 72 * (chunk["n_dep"] / max(airports["n_dep"].max(), 1))
        label = f"C{cluster}" + (f" {names[cluster]}" if names and cluster in names else "")
        ax.scatter(chunk["pc1"], chunk["pc2"], s=size, color=color, alpha=0.75,
                   edgecolor="white", linewidth=0.5, label=label)

    # Label the twelve largest airports so the projection is readable.
    for _, row in airports.nlargest(12, "n_dep").iterrows():
        ax.annotate(row["origin"], (row["pc1"], row["pc2"]), fontsize=7,
                    color=schema.INK, xytext=(4, 3), textcoords="offset points")

    # Bubble size is a third encoding and has to be legible on its own: without
    # a size key the reader knows the dots differ but not by how much.
    _size_legend(ax, airports)

    title = "Exploratory airport groups in a two-dimensional projection"
    quality = _cluster_quality_line(stats)
    if quality:
        title = f"{title}\n{quality}"
    ax.set_title(title, fontsize=10.5, linespacing=1.6)
    # The archetype names are long, so the key goes under the axes in two
    # columns instead of into a corner: every in-plot corner holds at least one
    # airport, and a legend parked on top of a point hides data to explain data.
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.015),
               ncol=2, fontsize=7.6, markerscale=0.7, frameon=False,
               columnspacing=2.0, handletextpad=0.5)
    variance = (stats or {}).get("pc_variance") or []
    axis_x = "Principal component 1"
    axis_y = "Principal component 2"
    if len(variance) >= 2:
        axis_x = f"Principal component 1 ({variance[0]:.0%} of variance)"
        axis_y = f"Principal component 2 ({variance[1]:.0%} of variance)"
    _clean(ax, axis_x, axis_y, grid_axis="both")
    _caption(fig, "Bubble area = departures. Axes are the first two principal "
                  "components of the standardised feature matrix. k is chosen by "
                  "silhouette and re-checked against airport subsamples, so the "
                  "groups are read as a description, not a fixed typology.",
             y=-0.115)
    return save(fig, name)


def _size_legend(ax, airports: pd.DataFrame):
    """Three bubble sizes at the median and the extremes, as a labelled key."""
    if "n_dep" not in airports or airports["n_dep"].max() <= 0:
        return
    top = float(airports["n_dep"].max())
    marks = [top * 0.25, top * 0.5, top]
    handles = [
        ax.scatter([], [], s=72 * (value / top), color=schema.MUTED,
                   alpha=0.45, edgecolor="white", linewidth=0.5)
        for value in marks
    ]
    labels = [f"{value / 1000:,.0f}k departures" for value in marks]
    key = ax.legend(handles, labels, loc="lower right", fontsize=7,
                    title="Volume", title_fontsize=7.4, framealpha=0.92,
                    edgecolor="white", labelspacing=1.1, borderpad=0.7)
    key.get_title().set_color(schema.MUTED)
    ax.add_artist(key)


def _cluster_quality_line(stats: dict | None) -> str:
    """Title second line: the numbers that qualify the cluster solution."""
    if not stats:
        return ""
    bits: list[str] = []
    if stats.get("k") is not None:
        bits.append(f"k = {int(stats['k'])}")
    if stats.get("silhouette") is not None:
        bits.append(f"silhouette = {float(stats['silhouette']):.2f}")
    if stats.get("ari") is not None:
        bits.append(f"subsample ARI = {float(stats['ari']):.2f}")
    if stats.get("airports"):
        bits.append(f"{int(stats['airports'])} airports")
    return "   ·   ".join(bits)


# --------------------------------------------------------------------------
# 10. Model explanation
# --------------------------------------------------------------------------
def fig_importance(importance: pd.DataFrame, name: str = "11_importance"):
    """Permutation importance aggregated back to the five source factors."""
    data = importance.sort_values("importance", ascending=True)
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    ax.barh(data["factor"], data["importance"], color=schema.OKABE_ITO["blue"], height=0.62)
    for y, (_, row) in enumerate(data.iterrows()):
        value=float(row["importance"]);spread=float(row.get("std",0))
        ax.text(value,y,f" {value:.3f} ± {spread:.3f}",va="center",fontsize=8.5,color=schema.INK)
    ax.set_title("What the risk model actually uses\nPermutation importance (AUC drop)")
    ax.margins(x=0.15)
    _clean(ax, "Mean AUC decrease under joint factor-block shuffling", "", grid_axis="x")
    _caption(fig, "Bar length and labels show mean AUC drop under joint block shuffling. "
                  "Non-additive model reliance, not causal contribution. ± is shuffle SD, not a sampling CI.")
    return save(fig, name)


def fig_hour_response(response: pd.DataFrame, threshold: int,
                      name: str = "12_hour_response"):
    """Modelled severe-delay risk by scheduled departure hour.

    Three choices keep the reader from over-reading the wiggle: the x-axis is
    trimmed to hours that exist (nothing departs at 02:00, and an empty fifth of
    the axis invites the eye to extrapolate), the zero-fill is gone because a
    shaded area under a risk curve reads as a count, and the caption says the
    points are binned means of predicted probabilities with no interval attached,
    so a one-point dip between two hours is not a finding.
    """
    response = response.loc[response['flights'] >= config.min_hour_flights()]
    if response.empty:
        fig, ax = plt.subplots(figsize=(7.6, 4.0))
        ax.text(0.5, 0.5, 'Insufficient holdout flights per hour for a supported curve',
                transform=ax.transAxes, ha='center', wrap=True)
        ax.axis('off')
        return save(fig, name)
    hours = response["dep_hour"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.plot(hours, response["mean_predicted_risk"],
            color=schema.ACCENT, lw=2.2, marker="o", ms=4)
    ax.set_xlim(int(hours.min()) - 1, int(hours.max()) + 1)
    ax.set_xticks(range(int(hours.min()), int(hours.max()) + 1, 2))
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title(f"Modelled risk of arriving {threshold}+ minutes late, by departure hour")
    _clean(ax, "Scheduled departure hour", f"Modelled risk (>= {threshold} min)")
    _caption(fig, "Holdout flights only. Each point is the mean predicted probability "
                  "in that hour; no interval is drawn, so a one-point dip between "
                  "neighbouring hours is binning noise, not a finding.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 11. Dashboard export (static companion for the report)
# --------------------------------------------------------------------------
def fig_dashboard_snapshot(figures: list[str], name: str = "13_dashboard_snapshot"):
    """Contact sheet of the dashboard panels, for the printed report."""
    paths = [p for p in figures if p]
    if not paths:
        return ""
    count = len(paths)
    cols = 2 if count > 3 else 1
    rows = int(np.ceil(count / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(6.2 * cols, 3.4 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, path in zip(axes, paths):
        ax.imshow(plt.imread(path))
        ax.axis("off")
    for ax in axes[len(paths):]:
        ax.axis("off")
    fig.suptitle("Analysis figure overview · not a dashboard screenshot", fontsize=12,
                 fontweight="bold", x=0.01, ha="left")
    return save(fig, name)
