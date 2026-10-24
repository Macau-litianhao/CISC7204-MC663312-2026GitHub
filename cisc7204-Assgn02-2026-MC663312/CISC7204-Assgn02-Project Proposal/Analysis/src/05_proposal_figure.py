"""
05_proposal_figure.py - the one figure that goes inside the proposal document.

Why a separate script instead of reusing fig01
---------------------------------------------
fig01 is built for a notebook, where it is shown at full width. Printed at the
7.6 cm a five-page proposal can spare, its legend ends up around 2 pt: the
colours survive, the labels do not. A figure that is unreadable at its final
size is decoration, not evidence, so this script redraws the same data for the
final size:

  * 5 rows x 20 columns instead of 10 x 10, so the block is wide and short and
    the bands stay legible when the width is halved;
  * no in-figure title (the document caption carries the title);
  * legend below in two columns, at a size tied to the printed width.

Usage
-----
    python 05_proposal_figure.py [width_cm]

The default 7.6 cm is a single column of a two-column layout. The proposal in
this repository prints it at 11.0 cm, i.e. two thirds of its 16.6 cm text
column, and the legend and cell gaps scale with the width so the figure stays
readable at whichever size is asked for:

    python 05_proposal_figure.py 11

Output: figures/fig16_proposal_waffle.png
"""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import common
from common import CAUSE_COLORS, CAUSE_LABELS

CM = 1 / 2.54
WIDTH_CM = float(sys.argv[1]) if len(sys.argv) > 1 else 7.6

# Everything below was tuned at 7.6 cm; the type and the canvas scale together
# so a wider figure gets correspondingly larger labels instead of more white
# space around the same 5.4 pt legend.
SCALE = WIDTH_CM / 7.6
LEGEND_PT = 5.4 * SCALE

# Short, print-friendly names: the notebook can afford "(internal)"; the
# printed width cannot, and the color already encodes the family.
SHORT = {
    "LateAircraftDelay": "Late aircraft",
    "CarrierDelay": "Carrier ops",
    "NASDelay": "ATC / congestion",
    "WeatherDelay": "Weather",
    "SecurityDelay": "Security",
}

df = pd.read_parquet(common.FLIGHTS_PARQUET,
                     columns=["ArrDelay", "ArrDelayMinutes"] + list(CAUSE_COLORS))
# The attribution universe is the set of flights BTS actually published causes
# for, not "delay >= 15": two flights cross the threshold without a cause row,
# and the document must quote the same denominator everywhere.
df = df[df["ArrDelay"].notna()]
att = df[df["CarrierDelay"].notna()]
totals = att[list(CAUSE_COLORS)].sum()
shares = totals / totals.sum() * 100
print(f"attributed flights: {len(att):,}")
print(shares.round(1).to_string())

# 100 cells, one per percentage point. Allocate whole cells by largest
# remainder so the counts still add to exactly 100.
raw = shares.to_numpy()
cells = np.floor(raw).astype(int)
for i in np.argsort(-(raw - cells))[: 100 - cells.sum()]:
    cells[i] += 1
# Largest cause first, so the eye lands on the biggest block at the top left.
order = list(shares.sort_values(ascending=False).index)

ROWS, COLS = 5, 20
grid = []
for cause, n in zip(order, cells):
    grid += [cause] * n
assert len(grid) == ROWS * COLS, len(grid)

fig, ax = plt.subplots(figsize=(WIDTH_CM * CM, 2.55 * SCALE * CM))
for i, cause in enumerate(grid):
    r, c = divmod(i, COLS)
    r = ROWS - 1 - r          # fill from the top row down
    ax.add_patch(plt.Rectangle((c + 0.06, r + 0.06), 0.88, 0.88,
                               facecolor=CAUSE_COLORS[cause], edgecolor="none"))
ax.set_xlim(0, COLS)
ax.set_ylim(0, ROWS)
ax.set_aspect("equal")
ax.axis("off")

handles, labels = [], []
for cause in order:
    handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=CAUSE_COLORS[cause]))
    # Security is 0.2%, i.e. smaller than one cell: say so rather than show a
    # legend colour that appears nowhere on the grid.
    tail = " (<1 cell)" if cells[order.index(cause)] == 0 else ""
    labels.append(f"{SHORT[cause]} {shares[cause]:.1f}%{tail}")
leg = ax.legend(handles, labels, loc="upper center",
                bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False,
                fontsize=LEGEND_PT, handlelength=0.9, handleheight=0.9,
                columnspacing=1.2, labelspacing=0.35, borderpad=0)
for t in leg.get_texts():
    t.set_color(common.INK)

out = common.FIG_DIR / "fig16_proposal_waffle.png"
fig.savefig(out, dpi=400, bbox_inches="tight", pad_inches=0.01)
print(f"[saved] {out}")
