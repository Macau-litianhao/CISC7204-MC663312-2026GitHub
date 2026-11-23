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

import textwrap

import matplotlib
matplotlib.use("Agg")                       # headless: notebooks and CI both

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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


def _line_height(fig, fontsize: float = 7.5) -> float:
    """One text line as a fraction of the figure height.

    The stamp and the caption used to be separated by a hard-coded 0.030 of the
    canvas, which is right for a 5-inch figure and wrong for a 9-inch one: on the
    wide figures the source line printed through the second line of the caption.
    Deriving the offset from the font size and the actual figure height makes the
    two agree at every size.
    """
    return (fontsize * 1.45 / 72.0) / max(fig.get_figheight(), 0.1)


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
    line = _line_height(fig)
    fig.text(0.005, caption_y - caption_lines * line - line * 0.35, text,
             fontsize=7.5, color=colour, ha="left", va="top",
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

    The text is hard-wrapped to the figure width instead of being handed to
    matplotlib's ``wrap=True``. Left to itself, an over-long caption extends the
    tight bounding box to the right: the saved canvas grows by the overhang and
    the axes end up occupying the left half of the file. Wrapping here means the
    canvas is always the figure, and the line count is known, so the source
    stamp below it can be placed exactly.
    """
    chars = max(40, int(fig.get_figwidth() * 72 / (7.5 * 0.50)))
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=chars, break_long_words=False) or [""])
    fig._caption_y = y
    fig._caption_lines = len(lines)
    fig.text(0.005, y, "\n".join(lines), fontsize=7.5, color=schema.TEXT_GREY,
             ha="left", va="top")


def _row_major(handles: list, labels: list[str], ncol: int) -> tuple[list, list[str]]:
    """Reorder legend entries so a multi-column key reads left to right.

    ``matplotlib`` fills a legend column by column, so five ranked causes in two
    columns are read as 39%, 5%, 35%, 0%, 21% - the ranking the figure exists to
    show is destroyed by the layout. Passing the entries back in column-major
    order is the only way to get row-major reading without a custom handler.
    """
    if ncol <= 1 or len(handles) <= ncol:
        return handles, labels
    rows = int(np.ceil(len(handles) / ncol))
    order: list[int] = []
    for row in range(rows):
        for col in range(ncol):
            index = col * rows + row
            if index < len(handles):
                order.append(index)
    return [handles[i] for i in order], [labels[i] for i in order]


def _robust_limits(values: pd.Series, low_q: float = 2.0, high_q: float = 98.0) -> tuple[float, float]:
    """Percentile-clipped range, so one airport or one state cannot set the scale.

    A single outlier at 24 minutes against a body of data between 1 and 7 is
    enough to make a sequential ramp useless: every ordinary tile lands in the
    same pale bin and the map stops ranking anything. Clipping at the 2nd/98th
    percentile keeps the ramp informative; the out-of-range value is still
    printed at full size on the tile, and the colourbar grows a triangular
    extension, so nothing is hidden - only the scale is made proportional.
    """
    clean = pd.Series(values).dropna()
    if clean.empty:
        return 0.0, 1.0
    low = float(np.nanpercentile(clean, low_q))
    high = float(np.nanpercentile(clean, high_q))
    if not np.isfinite(high) or high <= low:
        high = float(clean.max())
        low = float(clean.min())
    if high <= low:
        high = low + 1.0
    return low, high


#: Field names as they appear in ``risk_permutation_importance.csv`` mapped to
#: the words a reader of the report already knows. A figure in a submitted
#: report should not print ``dep_hour`` - that is an implementation detail that
#: leaks into the argument and makes the axis look like a log file.
_HUMAN_FACTOR = {
    "dep_hour": "Departure hour",
    "month": "Calendar month",
    "carrier": "Airline",
    "origin": "Origin airport",
    "distance": "Route distance",
    "panel_controls": "Panel controls",
    "year": "Calendar year",
    "covid_era": "COVID era flag",
}


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

    # A cause rounded to zero cells has no square on the grid. Keeping it in the
    # key leaves a colour the reader can never find, which reads as a rendering
    # fault; the share is still reported, in the caption, as "<1%".
    shown = [k for k in order if shares.get(k, 0) > 0]
    hidden = [k for k in order if shares.get(k, 0) == 0]
    handles = [
        Rectangle((0, 0), 1, 1, facecolor=schema.CAUSE_COLORS[k], edgecolor="white")
        for k in shown
    ]
    labels = [
        f"{schema.CAUSE_LABELS_LONG[k]}  {shares.get(k, 0):d}%"
        for k in shown
    ]
    handles, labels = _row_major(handles, labels, 2)
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=2, fontsize=9, columnspacing=1.6)
    ax.set_title("Where the delay minutes come from\n"
                 "One cell = 1% of attributed minutes", pad=14)
    below = "".join(f"{schema.CAUSE_LABELS_LONG[k]} < 1%; " for k in hidden)
    _caption(fig, "BTS cause minutes, flights delayed \u2265 15 min. "
                  "Carrier + late aircraft is descriptive, not airline control. "
                  f"{below}".rstrip())
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
    # A cause whose share rounds to nothing draws no band. Keeping it in the key
    # leaves a colour the reader can never find anywhere on the chart - the same
    # defect the waffle had, and it reads as a rendering fault rather than as a
    # category with a negligible share.
    visible = [c for c in pivot.columns if float(pivot[c].fillna(0).sum()) > 1e-9]
    for cause in visible:
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
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=4,
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
    # 0.30 in per carrier rather than 0.34: twenty bars at the old pitch ran to
    # 8.4 in, which at report width is a full page for one ranking. The pitch
    # still clears a 8.5 pt label, so nothing collides.
    fig, ax = plt.subplots(figsize=(7.2, 0.30 * len(data) + 1.5))
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
    # The ratio is reported at every spread, not only when it is tight. A reader
    # looking at twenty bars of a similar length will assume the gap at the top
    # is the story unless the number that bounds it is on the page.
    ratio = (f"Top-to-bottom ratio is {spread:.2f}: the full range across "
             f"{len(data)} carriers is {(data['minutes_per_flight'].max() - data['minutes_per_flight'].min()):.1f} minutes. ")
    _caption(fig, "Attribution universe only (arrival delay \u2265 15 min). "
                  f"Carriers below {floor:,} attributed flights are omitted. "
                  f"{ratio}Dashed line = the same ratio for every carrier shown.",
             y=-0.02)
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
    ax.axhline(0, color=schema.ZERO_LINE, lw=0.8, zorder=5)
    ax.set_title("The average is not the typical flight\n"
                 "Arrival delay by month (minutes)")
    # Headroom so the legend never sits on top of the p90 line.
    low, high = ax.get_ylim()
    ax.set_ylim(low, high + (high - low) * 0.22)
    ax.legend(loc="upper left", ncol=4, fontsize=8.5)
    _clean(ax, "", "Arrival delay (min)")

    # The zero line carries the whole argument, so it is labelled rather than
    # left as a hairline the eye can miss between the fill and the grid.
    ax.annotate("schedule", xy=(0.02, 0), xycoords=("axes fraction", "data"),
                xytext=(2, -11), textcoords="offset points", fontsize=7.4,
                color=schema.MUTED, style="italic", ha="left")

    ax2.bar(x, profile["share_delayed_60"], color=schema.OKABE_ITO["orange"],
            width=0.72, label="Share delayed 60+ min")
    # One decimal place on a 4-9% axis prints noise as information, and letting
    # the auto-locator choose the steps produced 0, 2, 5, 8, 10 - a ladder whose
    # rungs are uneven. Two points, integer labels.
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(0.02))
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(schema.MONTH_LABELS)
    _clean(ax2, "", "Delayed 60+ min")

    peak = profile.loc[profile["share_delayed_60"].idxmax()]
    ax2.annotate(f"June-July peak: {peak['share_delayed_60']:.1%}",
                 xy=(float(peak["month"]), float(peak["share_delayed_60"])),
                 xytext=(0, 6), textcoords="offset points", ha="center",
                 fontsize=8.2, color=schema.INK, weight="bold")
    low2, high2 = ax2.get_ylim()
    ax2.set_ylim(low2, high2 * 1.22)

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
    # The zero line is the finding, so it goes above the fill. Drawn at zorder 1
    # it disappeared under the median-to-p90 band exactly where the reader needs
    # to see the median sitting below it.
    ax_b.axhline(0, color=schema.INK, lw=1.0, zorder=6)
    ax_b.annotate("0 min: schedule", xy=(1.0, 0), xytext=(3, -5),
                  textcoords="offset points", fontsize=7.4, color=schema.TEXT_GREY,
                  style="italic", ha="left", va="top", zorder=7)

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
    ax_b.set_title("B \u00b7 Same months, distribution kept\nThe median never crosses zero")
    _clean(ax_b, "", "Arrival delay (min)")

    # Two panels side by side are read as a like-for-like comparison unless the
    # scales are stated. Panel B has to carry negative values, so the axes
    # cannot match; saying so on the panel is cheaper than being accused of
    # zooming the right-hand chart to win the argument.
    a_low, a_high = ax_a.get_ylim()
    b_low, b_high = ax_b.get_ylim()
    for axis, text in ((ax_a, f"scale 0 to {a_high:.0f} min"),
                       (ax_b, f"scale {b_low:.0f} to {b_high:.0f} min")):
        axis.annotate(text, xy=(0.99, 0.975), xycoords="axes fraction",
                      ha="right", va="top", fontsize=7.2, color=schema.TEXT_GREY)

    _caption(fig, "Both panels plot the same table. A bar per month cannot show that "
                  "the median never crosses zero, so it cannot show that the average "
                  "flight is not the typical one. The vertical scales differ by "
                  "necessity - panel B must show values below zero - so the comparison "
                  "is about which lines are present, not about bar height.")
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
    # The legend used to sit in the lower-right of the gap, exactly where the
    # gap's area - the visual definition of the Gini number in the title - is
    # read. Moving it into the empty middle keeps the shaded region intact.
    ax.legend(loc="center left", bbox_to_anchor=(0.11, 0.56), fontsize=8.5)
    _clean(ax, "Share of flights, worst first", "Share of delay minutes")
    _caption(fig, "Positive arrival-delay minutes only: a flight that arrived early "
                  "contributes zero, which is why the curve is flat at the origin.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 6. Near-null effect: distance bands
# --------------------------------------------------------------------------
def fig_distance_bands(bands: pd.DataFrame, name: str = "06_distance_bands"):
    """Mean and p90 by distance band, on separate panels with separate scales.

    These two series differ by a factor of eight (about 5 minutes against about
    38). On one shared axis the p90 sets the scale and the mean flattens into a
    horizontal line at the bottom - which destroys the very reading the figure
    exists to support, that the mean barely moves. Two panels, each zero-based
    and each using its own range, keep both gradients visible without truncating
    either axis. The caption states that the scales differ, because two panels
    side by side otherwise invite a direct visual comparison.
    """
    fig, (ax_mean, ax_tail) = plt.subplots(
        1, 2, figsize=(9.6, 3.9), gridspec_kw={"wspace": 0.26})
    x = np.arange(len(bands))
    labels = bands["band"].tolist()

    ax_mean.plot(x, bands["mean"], marker="o", ms=6, color=schema.OKABE_ITO["blue"], lw=2)
    for xi, yi in zip(x, bands["mean"]):
        ax_mean.annotate(f"{yi:.1f}", (xi, yi), xytext=(0, 9),
                         textcoords="offset points", ha="center", fontsize=8.4,
                         color=schema.OKABE_ITO["blue"])
    ax_mean.set_ylim(0, float(bands["mean"].max()) * 1.42)
    ax_mean.set_title("A \u00b7 Mean delay\nMoves by a few minutes only")
    _clean(ax_mean, "", "Delay (min)")

    ax_tail.plot(x, bands["p90"], marker="s", ms=6, color=schema.OKABE_ITO["orange"],
                 lw=2, ls="--")
    for xi, yi in zip(x, bands["p90"]):
        ax_tail.annotate(f"{yi:.0f}", (xi, yi), xytext=(0, 9),
                         textcoords="offset points", ha="center", fontsize=8.4,
                         color=schema.OKABE_ITO["orange"])
    ax_tail.set_ylim(0, float(bands["p90"].max()) * 1.30)
    ax_tail.set_title("B \u00b7 90th percentile\nSame shape, much larger values")
    _clean(ax_tail, "", "Delay (min)")

    # The absolute span, without a relative gloss. An earlier draft reported it
    # as a share of the mean (78%), which is arithmetically true and rhetorically
    # wrong: it makes a swing between 2.4 and 5.6 minutes sound like a large
    # effect, and this figure is the one arguing that it is not.
    span = float(bands["mean"].max() - bands["mean"].min())
    ax_mean.annotate(f"span {span:.1f} min\n({bands['mean'].min():.1f} to "
                     f"{bands['mean'].max():.1f})",
                     xy=(0.02, 0.97), xycoords="axes fraction", ha="left",
                     va="top", fontsize=8.4, color=schema.INK, weight="bold")

    for ax in (ax_mean, ax_tail):
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_xlabel("Route distance band (statute miles)")
    _caption(fig, "Panels A and B use independent, both zero-based vertical scales: "
                  "the two series differ by roughly 8x, so a shared axis would hide "
                  "the mean entirely. These raw groups mix routes, carriers and "
                  "schedules; they do not isolate the effect of distance.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 7. Geography: state tile grid
# --------------------------------------------------------------------------
STATE_TILES: dict[str, tuple[int, int]] = {
    # Row 0 is the northern edge, row 6 the southern; columns run west to east.
    # The earlier layout put Illinois on the Canadian border and Rhode Island
    # in the same row as Washington State, which reads as a geography error to
    # anyone who knows the map - and this figure's whole claim is that the
    # positions are a fair substitute for one.
    "AK": (0, 0), "ME": (0, 10),
    "WA": (1, 0), "ID": (1, 1), "MT": (1, 2), "ND": (1, 3), "MN": (1, 4),
    "WI": (1, 5), "MI": (1, 6), "NY": (1, 8), "VT": (1, 9), "NH": (1, 10),
    "OR": (2, 0), "NV": (2, 1), "WY": (2, 2), "SD": (2, 3), "IA": (2, 4),
    "IL": (2, 5), "IN": (2, 6), "OH": (2, 7), "PA": (2, 8), "NJ": (2, 9),
    "MA": (2, 10),
    "CA": (3, 0), "UT": (3, 1), "CO": (3, 2), "NE": (3, 3), "MO": (3, 4),
    "KY": (3, 5), "WV": (3, 6), "VA": (3, 7), "MD": (3, 8), "DE": (3, 9),
    "CT": (3, 10),
    "AZ": (4, 1), "NM": (4, 2), "KS": (4, 3), "AR": (4, 4), "TN": (4, 5),
    "NC": (4, 6), "SC": (4, 7), "DC": (4, 8), "RI": (4, 10),
    "OK": (5, 2), "LA": (5, 3), "MS": (5, 4), "AL": (5, 5), "GA": (5, 6),
    "HI": (6, 0), "TX": (6, 2), "FL": (6, 9),
}


def fig_state_tile(values: pd.Series, name: str = "07_state_tiles",
                   metric_label: str = "Mean arrival delay (min)"):
    """Equal-weight state tile grid on a percentile-clipped scale.

    A choropleth gives large rural states visual dominance regardless of
    traffic. The tile grid keeps every state the same size and is the reason it
    is the default geographic view in this project.

    Two scale decisions carry the figure. First, the ramp is clipped at the 2nd
    and 98th percentile: one state at 24 minutes against a body between -1 and
    11 drove every other tile into the same pale bin, so the map could not rank
    anything. The clipped value keeps its true number on the tile, in bold, and
    the colourbar grows a triangular extension - the scale is made proportional,
    nothing is hidden. Second, a diverging ramp is used only when the data
    genuinely straddles zero by more than a quarter of its span; a single state
    at -0.5 minutes is not a reason to spend half the ramp on values that
    cannot occur.
    """
    values = values.dropna()
    if values.empty:
        raise ValueError("fig_state_tile received no state values")

    # The panel carries a couple of non-state reporting codes (TT covers the
    # Pacific territories). They have no tile, so leaving them in the series
    # would let a code the map cannot draw set the range for the codes it can.
    outside_codes = [str(code) for code in values.index if code not in STATE_TILES]
    values = values[[code for code in values.index if code in STATE_TILES]]

    low, high = float(values.min()), float(values.max())
    # Only the upper tail is clipped. Clipping the floor as well put a warning
    # triangle on Alaska at -0.5 minutes, which is the minimum of a distribution
    # rather than an anomaly - a marker that fires on the ordinary smallest
    # value trains the reader to ignore it.
    clip_low = low
    clip_high = float(np.nanpercentile(values, 98))
    span = max(clip_high - clip_low, 1e-9)
    diverging = low < -0.25 * span
    tolerance = 0.02 * span

    if diverging:
        limit = float(np.nanmax(np.abs([clip_low, clip_high]))) or 1.0
        norm = matplotlib.colors.TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
        cmap = plt.get_cmap(schema.DIVERGING_CMAP)
        scale_note = "diverging scale, zero at the midpoint"
    else:
        norm = matplotlib.colors.Normalize(vmin=clip_low, vmax=clip_high)
        norm.clip = True
        cmap = plt.get_cmap(schema.SEQUENTIAL_CMAP)
        scale_note = f"sequential scale, values above {clip_high:.1f} clamp to the top colour"

    clipped_states = values[values > clip_high + tolerance]

    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    missing: list[str] = []
    for state, (row, col) in STATE_TILES.items():
        value = values.get(state, np.nan)
        if pd.isna(value):
            missing.append(state)
        # The no-data grey has to be visible against white, or "no qualifying
        # flights" reads as "an empty cell I forgot to fill".
        face = schema.NO_DATA if pd.isna(value) else cmap(norm(value))
        ax.add_patch(Rectangle((col, 6 - row), 0.92, 0.92, facecolor=face,
                               edgecolor="white", linewidth=1.2))
        # The label has to survive both ends of the ramp: white on the dark end,
        # ink on the pale end, decided per tile instead of once for the figure.
        rgba = matplotlib.colors.to_rgba(face) if not pd.isna(value) else None
        dark_tile = rgba is not None and _luminance(rgba) < 0.45
        label_colour = "white" if dark_tile else schema.INK
        ax.text(col + 0.46, 6 - row + 0.60, state, ha="center", va="center",
                fontsize=8, fontweight="bold", color=label_colour)
        if not pd.isna(value):
            beyond = bool(value > clip_high + tolerance)
            marker = "\u25b2 " if beyond else ""
            ax.text(col + 0.46, 6 - row + 0.26, f"{marker}{value:.1f}",
                    ha="center", va="center", fontsize=6.8,
                    color=label_colour, fontweight="bold" if beyond else "normal")

    ax.set_xlim(-0.1, 11.1)
    ax.set_ylim(-0.1, 7.1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{metric_label} by origin state")
    scalar = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    extend = "max" if len(clipped_states) else "neither"
    bar = fig.colorbar(scalar, ax=ax, fraction=0.025, pad=0.01, extend=extend)
    bar.set_label(metric_label, fontsize=8)
    bar.ax.tick_params(labelsize=7)

    beyond_text = ""
    if len(clipped_states):
        names = ", ".join(f"{s} {clipped_states[s]:.1f}" for s in clipped_states.index)
        beyond_text = f"\u25b2 = above the clipped range ({names}). "
    grey_text = f"Grey = no qualifying flights ({', '.join(missing)}). " if missing else ""
    code_text = (f"Not mapped: {', '.join(outside_codes)} (no state tile). "
                 if outside_codes else "")
    _caption(fig, f"Equal-area tiles: one state, one cell. {grey_text}"
                  f"{beyond_text}{code_text}{scale_note.capitalize()}.")
    return save(fig, name)


def _luminance(rgba: tuple[float, float, float, float]) -> float:
    """Relative luminance of an RGB triple, for choosing a readable label colour."""
    red, green, blue = rgba[:3]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


# --------------------------------------------------------------------------
# 8. Within-day cascade
# --------------------------------------------------------------------------
def fig_cascade_hour(hourly: pd.DataFrame, name: str = "08_cascade_hour", min_turnaround: int = 25):
    """Turnaround pressure by hour, in units a reader can check.

    The upper panel used to be labelled "Turnaround pressure (min)" while its
    axis ran to 500,000 - the values are minutes summed over every flight in the
    hour, not minutes per flight. Two different quantities shared one word, so
    the axis was wrong by five orders of magnitude in the unit a reader would
    assume. The series is now plotted in millions of minutes and named as a
    total; the per-flight reading is the lower panel's job.
    """
    floor = config.min_hour_flights()
    enough = hourly['flights'].fillna(0) >= floor
    fig, (ax, ratio) = plt.subplots(2, 1, figsize=(8.4, 6.0), sharex=True)
    millions = hourly['inherited_min'] / 1e6
    ax.bar(hourly['dep_hour'], millions, color=schema.OKABE_ITO['sky'], width=0.78)
    _clean(ax, '', 'Total inherited minutes (millions)')
    ax.set_title('Hypothetical turnaround pressure by local hour\n'
                 'Complete sampled aircraft sequences; UTC matching')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

    # Hours with no complete sequence are not zero, they are absent. The
    # lower panel's masked line leaves a gap; without a mark the gap reads as a
    # plotting artefact rather than as missing input.
    present = set(hourly.loc[enough, 'dep_hour'].astype(int))
    absent = [h for h in range(24) if h not in present]
    for hour in absent:
        ax.axvspan(hour - 0.42, hour + 0.42, color=schema.NO_DATA, alpha=0.55, zorder=0)
    if absent and len(absent) <= 4:
        first = absent[0]
        ax.annotate(f"no complete\nsequences at {first:02d}:00",
                    xy=(first, float(millions.max()) * 0.55), ha="center",
                    fontsize=7.4, color=schema.TEXT_GREY)

    ratio.plot(hourly['dep_hour'], hourly['inherited_share'].where(enough),
               color=schema.ACCENT, marker='o', ms=3.2, lw=2)
    ratio.set_ylim(bottom=0)
    _clean(ratio, 'Scheduled departure hour (origin local time)',
           'Pressure / arrival-delay ratio')
    ratio.set_xticks(range(0, 24, 2))
    ratio.set_xlim(-0.8, 23.8)

    # The raw maximum of this ratio sits at 03:00, where a few hundred flights
    # make one long turnaround look like a system-wide pattern. The peak is
    # therefore taken over hours that carry at least a quarter of the busiest
    # hour's traffic, so the annotation marks the evening build-up rather than
    # an artefact of thin volume.
    valid = hourly.loc[enough]
    if not valid.empty:
        busy = valid.loc[valid['flights'] >= 0.25 * valid['flights'].max()]
        pool = busy if not busy.empty else valid
        peak = pool.loc[pool['inherited_share'].idxmax()]
        ratio.annotate(f"evening peak {peak['dep_hour']:02.0f}:00 "
                       f"({peak['inherited_share']:.2f})",
                       xy=(float(peak['dep_hour']), float(peak['inherited_share'])),
                       xytext=(-6, -20), textcoords='offset points', ha='right',
                       fontsize=8.2, color=schema.INK,
                       arrowprops={'arrowstyle': '-', 'color': schema.ARROW_GREY, 'lw': 0.8})

    fig.subplots_adjust(hspace=.28, bottom=.20)
    _caption(fig, f'{min_turnaround}-minute assumed minimum turn; not causal arrival attribution. '
                  f'Upper panel is a total over flights, not per flight. Ratios may exceed 1. '
                  f'Line hidden below {floor:,.0f} flights/hour.')
    return save(fig, name)


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

    # A 0.05-wide axis turns 0.232 against 0.198 into a cliff. Without an
    # absolute reference the figure claims a strong optimum where the literature
    # calls anything below 0.25 weak structure; drawing the threshold inside the
    # same frame is what keeps the choice honest - k = 4 is the least weak
    # option, not a well-separated one.
    ax.axhline(0.25, color=schema.MUTED, ls="--", lw=1.0, zorder=1)
    ax.annotate("0.25 = upper bound for weak structure\n(Kaufman & Rousseeuw); "
                "every k sits below it",
                xy=(float(sweep["k"].min()), 0.25), xytext=(4, -4),
                textcoords="offset points", fontsize=7.6, color=schema.TEXT_GREY,
                va="top", ha="left")
    low = float(sweep["silhouette"].min())
    ax.set_ylim(low - 0.004, 0.263)
    ax.margins(x=0.06)
    _clean(ax, "Number of clusters", "Silhouette (higher is better)")
    _caption(fig, "Highest silhouette among k whose smallest cluster holds at least "
                  f"{floor} airports; the Ward dendrogram is the second check. "
                  "Because no k clears 0.25, the groups are read as a description "
                  "of the traffic mix, not as a taxonomy.")
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
    palette = [schema.OKABE_ITO["blue"], schema.OKABE_ITO["vermillion"],
               schema.OKABE_ITO["green"], schema.OKABE_ITO["purple"],
               schema.OKABE_ITO["sky"], schema.OKABE_ITO["yellow"]]

    fig, ax = plt.subplots(figsize=(7.9, 5.9))
    top = max(float(airports["n_dep"].max()), 1.0)
    for i, (cluster, chunk) in enumerate(airports.groupby("cluster", observed=True)):
        color = palette[i % len(palette)]
        # Area scaled from a floor: at the old 72-point ceiling the smallest
        # airports drew a dot two pixels wide, so "a dot exists here" and "an
        # airport with traffic exists here" looked the same.
        size = 26 + 300 * (chunk["n_dep"] / top)
        label = f"C{cluster}" + (f" \u00b7 {names[cluster]}" if names and cluster in names else "")
        label = f"{label}  (n={len(chunk)})"
        ax.scatter(chunk["pc1"], chunk["pc2"], s=size, color=color, alpha=0.82,
                   edgecolor="white", linewidth=0.7, label=label, zorder=3)

    # The projection is dominated by a handful of very small airports, so the
    # frame is clipped to the 0.5-99.5 percentile on both components. Without
    # it 95% of the canvas held empty space and the 195 airports were compressed
    # into a thumb-sized smudge; the clipped points are counted in the caption.
    x_lo, x_hi = _robust_limits(airports["pc1"], 0.5, 99.5)
    y_lo, y_hi = _robust_limits(airports["pc2"], 0.5, 99.5)
    x_pad = (x_hi - x_lo) * 0.14
    y_pad = (y_hi - y_lo) * 0.14
    ax.set_xlim(x_lo - x_pad, x_hi + x_pad * 1.8)
    ax.set_ylim(y_lo - y_pad, y_hi + y_pad)
    outside = int(((airports["pc1"] < x_lo) | (airports["pc1"] > x_hi)
                   | (airports["pc2"] < y_lo) | (airports["pc2"] > y_hi)).sum())

    # Eight codes, pushed outwards along the line from the centroid, with a
    # leader. Twelve free-floating labels in one blob were unreadable; a radial
    # push keeps every label outside the dense core instead of on top of it.
    cx, cy = float(airports["pc1"].median()), float(airports["pc2"].median())
    for rank, (_, row) in enumerate(airports.nlargest(8, "n_dep").iterrows()):
        dx = float(row["pc1"]) - cx
        dy = float(row["pc2"]) - cy
        norm = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        reach = 26 + 7 * (rank % 3)
        ax.annotate(row["origin"], (float(row["pc1"]), float(row["pc2"])),
                    xytext=(dx / norm * reach, dy / norm * reach),
                    textcoords="offset points", fontsize=7.4, color=schema.INK,
                    ha="left" if dx >= 0 else "right", va="center", zorder=6,
                    bbox={"boxstyle": "round,pad=0.16", "facecolor": "white",
                          "edgecolor": "none", "alpha": 0.72},
                    arrowprops={"arrowstyle": "-", "color": schema.ARROW_GREY,
                                "lw": 0.6, "shrinkA": 0, "shrinkB": 2})

    # Bubble size is a third encoding and has to be legible on its own: without
    # a size key the reader knows the dots differ but not by how much.
    _size_legend(ax, airports, top)

    title = "Exploratory airport groups in a two-dimensional projection"
    quality = _cluster_quality_line(stats)
    if quality:
        title = f"{title}\n{quality}"
    ax.set_title(title, fontsize=10.5, linespacing=1.6)
    # The archetype names are long, so the key goes under the axes in two
    # columns instead of into a corner: every in-plot corner holds at least one
    # airport, and a legend parked on top of a point hides data to explain data.
    handles, labels = ax.get_legend_handles_labels()
    handles, labels = _row_major(handles, labels, 2)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.005),
               ncol=2, fontsize=8.0, markerscale=0.8, frameon=False,
               columnspacing=2.0, handletextpad=0.5)
    variance = (stats or {}).get("pc_variance") or []
    axis_x = "Principal component 1"
    axis_y = "Principal component 2"
    if len(variance) >= 2:
        axis_x = f"Principal component 1 ({variance[0]:.0%} of variance)"
        axis_y = f"Principal component 2 ({variance[1]:.0%} of variance)"
    _clean(ax, axis_x, axis_y, grid_axis="both")
    _caption(fig, "Bubble area = departures. Axes are the first two principal "
                  "components of the standardised feature matrix"
                  + (f"; {outside} extreme airports are outside the frame. " if outside else ". ")
                  + "k is chosen by silhouette and re-checked against airport "
                  "subsamples, so the groups are read as a description, not a "
                  "fixed typology.",
             y=-0.125)
    return save(fig, name)


def _size_legend(ax, airports: pd.DataFrame, top: float | None = None):
    """Three bubble sizes at the quarter, half and maximum, as a labelled key."""
    if "n_dep" not in airports or airports["n_dep"].max() <= 0:
        return
    top = float(top or airports["n_dep"].max())
    marks = [top * 0.25, top * 0.5, top]
    handles = [
        ax.scatter([], [], s=26 + 300 * (value / top), color=schema.MUTED,
                   alpha=0.6, edgecolor="white", linewidth=0.7)
        for value in marks
    ]
    # "3,430k departures" is a unit nobody writes: past a million the key
    # switches to millions so the numbers match the way the report quotes them.
    if top >= 1e6:
        labels = [f"{value / 1e6:,.1f}M departures" for value in marks]
    else:
        labels = [f"{value / 1e3:,.0f}k departures" for value in marks]
    key = ax.legend(handles, labels, loc="lower right", fontsize=7.2,
                    title="Volume", title_fontsize=7.6, framealpha=0.93,
                    edgecolor="white", labelspacing=1.2, borderpad=0.7)
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
    data = importance.sort_values("importance", ascending=True).copy()
    data["label"] = [ _HUMAN_FACTOR.get(str(f), str(f).replace("_", " ").title())
                      for f in data["factor"] ]
    fig, ax = plt.subplots(figsize=(6.9, 3.5))
    colours = [schema.ACCENT if i == len(data) - 1 else schema.OKABE_ITO["blue"]
               for i in range(len(data))]
    ax.barh(data["label"], data["importance"], color=colours, height=0.62)
    for y, (_, row) in enumerate(data.iterrows()):
        value = float(row["importance"])
        spread = float(row.get("std", 0))
        # The top bar ends inside the label column; an opaque pad keeps the
        # number off the bar edge without a white block over the axis.
        ax.text(value + float(data["importance"].max()) * 0.012, y,
                f"{value:.3f} \u00b1 {spread:.3f}", va="center", fontsize=8.5,
                color=schema.INK, zorder=4,
                bbox={"boxstyle": "square,pad=0.10", "facecolor": "white",
                      "edgecolor": "none", "alpha": 0.85})
    ax.set_title("What the risk model actually uses\nPermutation importance (AUC drop)")
    ax.margins(x=0.16)
    _clean(ax, "Mean AUC decrease under joint factor-block shuffling", "", grid_axis="x")
    _caption(fig, "Bar length and labels show mean AUC drop under joint block shuffling. "
                  "Non-additive model reliance, not causal contribution. \u00b1 is the "
                  "shuffle standard deviation, not a sampling confidence interval.")
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
    risk = response["mean_predicted_risk"].astype(float)
    counts = response["flights"].astype(float)
    fig, ax = plt.subplots(figsize=(7.9, 4.2))

    # A line without an interval invites the reader to take a one-point dip
    # between 16:00 and 17:00 as a finding. The binomial band on the binned
    # share is a cheap, honest approximation - it ignores within-hour
    # correlation, so it is narrower than the truth, which is why the caption
    # says "at least this wide" rather than quoting it as a confidence cover.
    se = np.sqrt(np.clip(risk * (1 - risk) / counts, 0, None))
    ax.fill_between(hours, np.clip(risk - 1.96 * se, 0, 1), risk + 1.96 * se,
                    color=schema.ACCENT, alpha=0.14, lw=0, zorder=2,
                    label="Approximate 95% band")
    ax.plot(hours, risk, color=schema.ACCENT, lw=2.2, marker="o", ms=4, zorder=3)

    ax.set_xlim(int(hours.min()) - 1, int(hours.max()) + 1)
    ax.set_xticks(range(int(hours.min()), int(hours.max()) + 1, 2))
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_title(f"Modelled risk of arriving {threshold}+ minutes late, by departure hour")

    peak = response.loc[risk.idxmax()]
    ax.annotate(f"peak {int(peak['dep_hour']):02d}:00 \u00b7 {float(peak['mean_predicted_risk']):.1%}",
                xy=(float(peak["dep_hour"]), float(peak["mean_predicted_risk"])),
                xytext=(0, 12), textcoords="offset points", ha="center",
                fontsize=8.4, color=schema.INK, weight="bold")
    ax.legend(loc="upper left", fontsize=8.2)
    _clean(ax, "Scheduled departure hour", f"Modelled risk (\u2265 {threshold} min)")
    _caption(fig, "Holdout flights only. Each point is the mean predicted probability in "
                  "that hour; the band is a binomial approximation, so the true interval is "
                  "at least this wide. Dips inside the band are binning noise, not findings.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 11. Out-of-sample behaviour and coefficient evidence
# --------------------------------------------------------------------------
def fig_temporal_validation(result: pd.DataFrame, years: list[int] | None = None,
                            name: str = "15_temporal_validation"):
    """Expanding-window results on a real year axis, with the baseline drawn in.

    The years tested here are 2019, 2020, 2022 and 2024 - the panel has no 2021
    or 2023 folds. Placed on a categorical axis those four points sit at equal
    spacing, so the figure quietly claims a regular annual walk forward that the
    protocol never performed. A numeric axis makes the two-year gap visible.

    The 2020 point is the finding: Brier gain turns negative, which means the
    model did worse than predicting the training base rate in the year the
    pandemic emptied the schedule. It is annotated rather than smoothed away.
    """
    data = result.loc[result["model"] != "constant_train_rate"].copy()
    if data.empty:
        return ""
    data["test_year"] = data["test_year"].astype(int)
    years = sorted(years or data["test_year"].unique().tolist())
    series = [("logistic", "Logistic", schema.OKABE_ITO["blue"], "o"),
              ("gradient_boosting", "Gradient boosting", schema.OKABE_ITO["vermillion"], "s")]

    fig, (ax_auc, ax_brier) = plt.subplots(
        1, 2, figsize=(10.4, 4.2), gridspec_kw={"wspace": 0.26})

    for key, label, colour, marker in series:
        part = data.loc[data["model"] == key].sort_values("test_year")
        if part.empty:
            continue
        ax_auc.plot(part["test_year"], part["roc_auc"], marker=marker, ms=5,
                    color=colour, lw=2, label=label)
        ax_brier.errorbar(part["test_year"], part["brier_gain"],
                          yerr=[part["brier_gain"] - part["gain_ci_low"],
                                part["gain_ci_high"] - part["brier_gain"]],
                          marker=marker, ms=5, color=colour, lw=2, capsize=3.5,
                          label=label)

    ax_auc.axhline(0.5, color=schema.MUTED, ls="--", lw=1.0)
    ax_auc.annotate("chance (0.50)", xy=(years[0], 0.5), xytext=(0, 4),
                    textcoords="offset points", fontsize=7.6, color=schema.TEXT_GREY,
                    va="bottom")
    ax_auc.set_ylim(0.45, 0.80)
    ax_auc.set_title("A \u00b7 Ranking quality holds\nAUC dips in 2020, recovers by 2024")
    ax_auc.set_ylabel("ROC AUC")
    ax_auc.legend(loc="lower right", fontsize=8.4)

    ax_brier.axhline(0, color=schema.INK, lw=1.0)
    ax_brier.set_title("B \u00b7 Calibration fails in 2020\nNegative = worse than the base rate")
    ax_brier.set_ylabel("Brier improvement over constant baseline")
    # A light field under zero states the finding before the reader parses it.
    low, high = ax_brier.get_ylim()
    ax_brier.axhspan(low, 0, color=schema.SYNTHETIC_RED, alpha=0.06, zorder=0)
    ax_brier.set_ylim(low, high * 1.18)
    ax_brier.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))
    ax_brier.annotate("2020: both models\nfall below the base rate",
                      xy=(2020, float(data.loc[data["test_year"] == 2020, "brier_gain"].min())),
                      xytext=(0, -26), textcoords="offset points", ha="center",
                      fontsize=7.8, color=schema.INK,
                      arrowprops={"arrowstyle": "-", "color": schema.ARROW_GREY, "lw": 0.8})

    for axis in (ax_auc, ax_brier):
        axis.set_xticks(years)
        axis.set_xticklabels([str(y) for y in years])
        axis.set_xlim(min(years) - 0.55, max(years) + 0.55)
        axis.set_xlabel("Held-out calendar year")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=schema.GRID, linewidth=0.6)
        axis.set_axisbelow(True)

    _caption(fig, "Expanding training window, whole test calendar year, training-only "
                  "preprocessing, fixed hyper-parameters. Years are placed at their true "
                  "distance: the panel contains no 2021 or 2023 fold. Bars are a paired "
                  "calendar-week resampling interval, 1,000 draws.")
    return save(fig, name)


def fig_inference_evidence(risk: dict, conditional: list[dict],
                           name: str = "16_inference_evidence"):
    """Calibration and conditional R-squared, drawn rather than screenshotted.

    This figure used to be a browser capture of the dashboards's Method tab. A
    screenshot carries the navigation bar, a scrollbar and a clipped table, and
    it cannot be regenerated by anyone who runs the pipeline; the previous
    appendix credited it to a notebook that never produced it. Both panels are
    now built from ``risk_evaluation.json`` and ``factor_conditional_r2.csv``,
    so the figure rebuilds with the analysis.
    """
    calibration = (risk or {}).get("calibration") or {}
    if not calibration:
        return ""

    fig, (ax_cal, ax_r2) = plt.subplots(
        1, 2, figsize=(10.6, 4.2),
        gridspec_kw={"wspace": 0.30, "width_ratios": [1.0, 1.12]})

    limit = 0.0
    for key, label, colour in (("logistic", "Logistic", schema.OKABE_ITO["blue"]),
                               ("gradient_boosting", "Gradient boosting",
                                schema.OKABE_ITO["vermillion"])):
        rows = calibration.get(key) or []
        if not rows:
            continue
        predicted = [float(r["predicted"]) for r in rows]
        observed = [float(r["observed"]) for r in rows]
        limit = max([limit, *predicted, *observed])
        ax_cal.plot(predicted, observed, marker="o", ms=4.2, lw=1.8,
                    color=colour, label=label)

    limit = limit * 1.10 if limit else 0.2
    ax_cal.plot([0, limit], [0, limit], ls=":", lw=1.0, color=schema.EQUALITY_LINE,
                label="Perfect calibration")
    ax_cal.set_xlim(0, limit)
    ax_cal.set_ylim(0, limit)
    ax_cal.xaxis.set_major_locator(mticker.MultipleLocator(0.05))
    ax_cal.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax_cal.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax_cal.set_title("A \u00b7 Calibration on holdout flights\nPoints on the diagonal are honest",
                    fontsize=10.5)
    _clean(ax_cal, "Mean predicted probability", "Observed frequency")
    ax_cal.legend(loc="upper left", fontsize=8.2)

    table = pd.DataFrame(conditional)
    if not table.empty:
        table = table.sort_values("drop_one_r2", ascending=True).copy()
        table["label"] = [_HUMAN_FACTOR.get(str(f), str(f).replace("_", " ").title())
                          for f in table["factor"]]
        ax_r2.barh(table["label"], table["drop_one_r2"],
                   color=schema.OKABE_ITO["green"], height=0.62)
        for y, value in enumerate(table["drop_one_r2"]):
            ax_r2.text(float(value), y, f"  {float(value):.4f}", va="center",
                       fontsize=8.2, color=schema.INK)
        full = float(table["full_model_r2"].iloc[0])
        ax_r2.set_title("B \u00b7 Conditional association\n"
                        "R\u00b2 fall with the block removed", fontsize=10.5)
        ax_r2.margins(x=0.30)
        # The full-model R-squared belongs beside the bars, not in the title: a
        # second title line long enough to hold it overflows the panel and lands
        # on its neighbour, which is what happened on the first attempt.
        ax_r2.annotate(f"full model R\u00b2 = {full:.4f}",
                       xy=(0.98, 0.04), xycoords="axes fraction", ha="right",
                       fontsize=8.0, color=schema.TEXT_GREY)
        _clean(ax_r2, "Fall in R\u00b2 with the factor removed", "", grid_axis="x")

    _caption(fig, "Calibration bins are descriptive holdout checks, not a fitted "
                  "recalibration. Panel B removes one factor block at a time while "
                  "calendar controls stay in: these are non-additive associations, "
                  "not shares of a decomposition and not causal effects.")
    return save(fig, name)


# --------------------------------------------------------------------------
# 12. Dashboard export (static companion for the report)
# --------------------------------------------------------------------------
def fig_dashboard_snapshot(figures: list[str], name: str = "13_dashboard_snapshot",
                           cols: int = 2, cell_width: float = 6.0):
    """Contact sheet of analysis panels, packed to each image's own aspect ratio.

    The previous version gave every cell the same height and then asked
    ``imshow`` to fit the image inside it, which letterboxes twice: once
    horizontally, once vertically. Six panels in a 3x2 grid left roughly a fifth
    of the canvas empty and shrank the cluster projection to text that could not
    be read at print size. Row heights are now derived from the images' aspect
    ratios, so the sheet is as tall as its content and nothing is scaled below
    legibility.
    """
    paths = [p for p in figures if p]
    if not paths:
        return ""
    images = [plt.imread(path) for path in paths]
    aspects = [im.shape[1] / max(im.shape[0], 1) for im in images]
    rows = int(np.ceil(len(paths) / cols))

    row_heights: list[float] = []
    for row in range(rows):
        chunk = aspects[row * cols:(row + 1) * cols]
        row_heights.append(cell_width / min(chunk))

    header, footer = 0.62, 0.72
    fig_w = cols * cell_width * 1.04
    fig_h = sum(row_heights) * 1.04 + header + footer
    fig = plt.figure(figsize=(fig_w, fig_h))
    grid = fig.add_gridspec(rows, cols, height_ratios=row_heights,
                            hspace=0.10, wspace=0.03,
                            left=0.012, right=0.988,
                            top=1 - header / fig_h, bottom=footer / fig_h)
    for index, image in enumerate(images):
        ax = fig.add_subplot(grid[index // cols, index % cols])
        ax.imshow(image)
        ax.set_anchor("C")
        ax.axis("off")
    fig.suptitle("Analysis figure overview \u00b7 panels reproduced at report scale, "
                 "not a dashboard screenshot", fontsize=11, fontweight="bold",
                 x=0.012, ha="left", y=1 - 0.30 / fig_h)
    return save(fig, name)
