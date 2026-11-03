"""Build and optionally execute the narrative notebooks.

    python notebooks/build_notebooks.py            # write the .ipynb files
    python notebooks/build_notebooks.py --execute  # write and run them

Why a builder rather than seven hand-edited notebooks: a notebook that only works
because a kernel still holds an old variable is a trap for the marker, and a
notebook whose output was pasted by hand cannot be checked at all. Generating them
from source and executing in a fresh kernel means the committed outputs are the
outputs of a clean run.

The notebooks are deliberately thin. Anything that computes a result lives in
``src/team01``; the notebook narrates, prints and plots. That is what makes the
same numbers reproducible from a script as well as from a notebook.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

PREAMBLE = """\
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from team01 import config, io, clean

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 40)
print(config.summarise())"""


def md(text: str) -> tuple[str, str]:
    return "markdown", text.strip()


def code(text: str) -> tuple[str, str]:
    return "code", text.strip()


NOTEBOOKS: list[dict] = [
    {
        "name": "01_Data_Preparation",
        "cells": [
            md("""
# 01 · Data preparation and validation

**Question.** Is the data complete and internally consistent before anything is
claimed from it?

This notebook does three things: it loads the panel for the active mode, runs the
validation checks, and prints the cause-field coverage that scopes every later
statement. No figure here — this stage exists so the next five can be trusted.
"""),
            code(PREAMBLE),
            md("""
## 1.1 Load and validate

`clean.validate` counts rows, duplicates, missingness and threshold coverage. It
raises on a duplicate rate above 0.1% or on more than 5% missing arrival delays,
because either would make the panel unusable rather than merely noisy.
"""),
            code("""
raw = io.load_flights()
checks = clean.validate(raw, f"panel_{config.mode()}")
pd.Series(checks, name="value").to_frame()"""),
            md("""
## 1.2 The three row populations

Mixing these up is the classic error in this dataset: cause shares describe
*delayed* flights, while means and percentiles describe *completed* flights.
"""),
            code("""
panel = clean.completed(raw)
universe = clean.attribution_universe(raw)

print(f"reported rows          {len(raw):>12,}")
print(f"completed flights      {len(panel):>12,}  ({len(panel)/len(raw):.1%} of reported)")
print(f"attribution universe   {len(universe):>12,}  ({len(universe)/len(panel):.1%} of completed)")"""),
            md("""
## 1.3 Coverage of the cause fields

BTS publishes the five cause-minute fields only above 15 minutes of arrival delay.
The check is direct: coverage should be 0% below the threshold and about 100% above
it, in every year.
"""),
            code("""
from team01 import attribution

attribution.threshold_audit(raw)"""),
            md("""
## 1.4 Per-year summary

What a reader needs before any trend line: how many flights, how late, and how
often severe.
"""),
            code("""
clean.summarise_panel(raw)"""),
        ],
    },
    {
        "name": "02_Attribution",
        "cells": [
            md("""
# 02 · Where the delay minutes come from

**RQ1.** How are reported delay minutes distributed across the five BTS causes, and
how stable is that composition across the panel?

The pilot year gave a 75/25 split between airline-controlled and system-imposed
minutes. A single year cannot separate a structure from a one-year shock, so the
split is reported with a bootstrap interval and recomputed per year.
"""),
            code(PREAMBLE),
            code("""
from team01 import attribution, viz

raw = io.load_flights()
panel = clean.completed(raw)
universe = clean.attribution_universe(raw)

totals = attribution.cause_totals(universe)
totals[["cause", "family", "minutes", "share"]]"""),
            md("""
## 2.1 The headline split, with an interval

The resampling unit is the **operating day**, not the flight: flights delayed by one
storm are not independent, so a flight-level bootstrap would produce an interval far
too narrow.
"""),
            code("""
split = attribution.family_split(universe)
interval = attribution.bootstrap_family_share(universe)

print(f"internal share  {interval['share']:.3f}  "
      f"[{interval['ci_low']:.3f}, {interval['ci_high']:.3f}]  "
      f"over {interval['days']} operating days")
print(f"late aircraft   {split['late_aircraft_share']:.1%} of attributed minutes")"""),
            md("""
## 2.2 Is the composition stable?

Ten years of a small move is the interesting question: if the interval for one year
clears the interval for another, that is a structural break rather than noise.
"""),
            code("""
attribution.stability_by_year(universe, bootstrap=True, reps=200)"""),
            md("""
## 2.3 The figure

A unit waffle, because the question is part-to-whole and the cells can be labelled
individually. Area is a weak channel, so the shares are written in the legend rather
than read off the shape.
"""),
            code("""
viz.fig_cause_waffle(totals)"""),
        ],
    },
    {
        "name": "03_Tail_And_Concentration",
        "cells": [
            md("""
# 03 · The tail, and how concentrated it is

**Question.** Does the average describe the passenger experience?

Two statistics answer it: the percentile at which the mean sits, and a Lorenz curve
over positive delay minutes.
"""),
            code(PREAMBLE),
            code("""
from team01 import tail, viz

panel = clean.completed(io.load_flights())

tail.percentile_profile(panel)"""),
            md("""
## 3.1 Concentration

The curve is read by position, which is the most accurate encoding available. The
top-1% share is written on the figure because a reader would otherwise estimate it.
"""),
            code("""
concentration = tail.lorenz(panel, sample_rows=2_000_000)
print(f"Gini-style coefficient {concentration['gini']:.3f}")
print(f"worst 1% of flights   -> {concentration['top1_share']:.1%} of delay minutes")
print(f"worst 5% of flights   -> {concentration['top5_share']:.1%} of delay minutes")

viz.fig_lorenz(concentration)"""),
            md("""
## 3.2 Does the mean hide the tail *between* months?

The pilot found r = 0.998 across months: the mean and the severe share move
together at that level of aggregation. That is a null result, and it is reported
rather than dropped — the "mean hides the tail" claim holds for individual flights,
not between monthly averages.
"""),
            code("""
paradox = tail.mean_vs_tail(panel, by="month")
print(f"Pearson r  {paradox['pearson_r']:+.3f}")
print(f"Spearman r {paradox['spearman_r']:+.3f}")
print(f"verdict    {paradox['verdict']}")

paradox["table"]"""),
            code("""
viz.fig_percentile_band(tail.monthly_profile(panel))"""),
        ],
    },
    {
        "name": "04_Cascade",
        "cells": [
            md("""
# 04 · Delay inherited within the operating day

**RQ2.** How much of the delay observed in a given hour is inherited from earlier
legs of the same aircraft?

BTS reports `LateAircraftDelay` as a cause, which is a label rather than a
mechanism. Reconstructing the aircraft rotation turns it into a quantity: the
previous leg's delay minus the scheduled turnaround buffer is the delay the next leg
cannot avoid.
"""),
            code(PREAMBLE),
            code("""
from team01 import features, models, viz

panel = clean.completed(io.load_flights())
sample = models.take_sample(panel, 3_000_000)

legs = features.leg_sequence(sample)
cascade = features.cascade_summary(legs, sample)

print(f"rotations                    {cascade['rotations']:,}")
print(f"share of flights             {cascade['rotation_share_of_flights']:.1%}")
print(f"inherited share of delay     {cascade['inherited_share']:.1%}")"""),
            md("""
## 4.1 The arithmetic, on one aircraft

A rotation counts only when the aircraft continues from where it landed and the
scheduled ground time is plausible (15 minutes to 24 hours). The inherited minutes
are `previous delay − (scheduled turn − 25-minute minimum turn)`.
"""),
            code("""
example = legs.loc[legs["is_rotation"]].head(6)
example[["tail_number", "origin", "prev_arr_delay", "scheduled_turn",
         "ground_time_actual", "inherited_min"]]"""),
            md("""
## 4.2 Where it concentrates

Second-or-later legs late in the day inherit the most: the buffer is consumed by
mid-afternoon and every subsequent leg carries the delay forward.
"""),
            code("""
cascade["hourly"][["dep_hour", "flights", "mean_inherited", "inherited_share"]].tail(10)"""),
            code("""
viz.fig_cascade_hour(cascade["hourly"])"""),
        ],
    },
    {
        "name": "05_Clustering",
        "cells": [
            md("""
# 05 · Airport archetypes

**RQ3.** Do U.S. airports fall into distinct delay-risk archetypes once size and
cause mix are considered together?

Clustering is reported with its selection evidence — a silhouette sweep, a Ward
cross-check and a subsample stability score — because a k-means solution that
changes when a third of the airports are removed describes the sample, not the
airports.
"""),
            code(PREAMBLE),
            code("""
from team01 import cluster, features, viz

panel = clean.completed(io.load_flights())
airports = io.load_airports()

matrix = features.airport_feature_matrix(panel, airports, min_departures=2000)
print(f"{len(matrix)} airports x {matrix.shape[1]} columns")
matrix.head(3)"""),
            code("""
sweep = cluster.sweep_k(matrix)
chosen = cluster.choose_k(sweep)
print(f"chosen k = {chosen}")
sweep"""),
            code("""
labelled, _, _ = cluster.fit(matrix, chosen)
names = cluster.name_clusters(labelled)
labelled["archetype"] = labelled["cluster"].map(names)

print(f"Ward cophenetic correlation {cluster.ward_check(matrix)['cophenetic_correlation']}")
print(cluster.stability(matrix, chosen))

cluster.cluster_table(labelled)[["cluster", "archetype", "airports",
                                 "mean_arr_delay", "share_delayed_60",
                                 "largest_members"]]"""),
            code("""
viz.fig_silhouette(sweep, chosen)
viz.fig_cluster_scatter(labelled, names)"""),
        ],
    },
    {
        "name": "06_Modelling",
        "cells": [
            md("""
# 06 · Which factor matters, and how well risk can be ranked

**RQ4.** Given route, departure hour and month, how well can delay risk be ranked?

Three models, each with its own honest ceiling: sequential R² to rank factors, a
quantile regression for the tail, and a time-based holdout classifier for risk.
"""),
            code(PREAMBLE),
            code("""
from team01 import models, viz

panel = clean.completed(io.load_flights())

ranking = models.incremental_r2(panel)
print(f"model R-squared {ranking.attrs['model_r2']} on {ranking.attrs['rows']:,} sampled flights")
ranking"""),
            md("""
## 6.1 The tail moves differently

A factor can be irrelevant on average and decisive at the ninetieth percentile, so
the same design is fitted at q = 0.9.
"""),
            code("""
quantile = models.quantile_regression(panel, quantile=0.9)
print(f"pseudo R-squared {quantile['pseudo_r2']}")
quantile["table"].head(8)"""),
            md("""
## 6.2 Risk classification on a time holdout

Logistic baseline against histogram gradient boosting. The split is chronological, so
no later month trains an earlier one. Both are reported: a reader needs to see how
much the tree model actually adds, and here it is little — five observable factors
rank risk weakly, and that is the finding.
"""),
            code("""
risk = models.risk_classifier(panel, threshold=60)
print(f"test set starts {risk['split']['actual_test_start']} "
      f"(requested {risk['split']['requested_start']}), "
      f"base rate {risk['base_rate']:.3%}")

pd.DataFrame({name: metrics for name, metrics in risk["models"].items()
              if name != "importance"}).T"""),
            code("""
viz.fig_importance(pd.DataFrame(risk["models"]["importance"]))
viz.fig_hour_response(risk["hour_response"], threshold=60)"""),
        ],
    },
    {
        "name": "07_Visual_Audit",
        "cells": [
            md("""
# 07 · Visual audit

**Question.** Does every figure earn its place?

A table of figures against the encoding they use and the question they answer,
following `docs/standards/viz-guidelines.md`. This is the section that turns "we
made charts" into "each chart is a decision".
"""),
            code(PREAMBLE),
            code("""
audit = pd.DataFrame([
    ("01 cause waffle", "area, labelled", "part-to-whole", "01_cause_waffle"),
    ("02 monthly composition", "stacked area", "composition over time", "02_monthly_composition"),
    ("03 carrier bars", "sorted bars, direct labels", "ranked comparison", "03_carrier_bars"),
    ("04 percentile band", "position with band", "distribution", "04_percentile_band"),
    ("05 lorenz", "position", "concentration", "05_lorenz"),
    ("06 distance bands", "position, flat lines", "near-null effect", "06_distance_bands"),
    ("07 state tiles", "colour + label", "geography, equal weight", "07_state_tiles"),
    ("08 cascade hour", "position + bar", "within-day mechanism", "08_cascade_hour"),
    ("09 silhouette", "position", "selection evidence", "09_silhouette"),
    ("10 cluster scatter", "position + area", "similarity", "10_cluster_scatter"),
    ("11 importance", "length", "model explanation", "11_importance"),
    ("12 hour response", "position", "actionable risk", "12_hour_response"),
], columns=["figure", "encoding", "question", "file"])

audit["exists"] = [ (config.FIG_DIR / f"{name}.png").exists() for name in audit["file"] ]
audit[["figure", "encoding", "question", "exists"]]"""),
            md("""
## 7.1 What would be different with a weaker encoding

Three deliberate substitutions, recorded so the choice can be defended in the viva:

- A **bar of monthly means** replaced by a percentile band, because the mean sits
  above the median in every month.
- A **choropleth** relegated to second place behind an equal-area tile grid, because
  a choropleth gives large rural states visual weight unrelated to traffic.
- A **univariate R² bar chart** replaced by sequential incremental R², because the
  interesting number is the contribution after the other factors are in the model.
"""),
            code("""
missing = audit.loc[~audit["exists"], "figure"].tolist()
print("missing figures:", missing or "none - run python src/scripts/07_figures.py")"""),
        ],
    },
]


def build(spec: dict) -> Path:
    notebook = nbf.v4.new_notebook()
    notebook.cells = [
        nbf.v4.new_markdown_cell(source) if kind == "markdown" else nbf.v4.new_code_cell(source)
        for kind, source in spec["cells"]
    ]
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3", "language": "python", "name": "python3",
    }
    notebook.metadata["language_info"] = {"name": "python"}
    target = HERE / f"{spec['name']}.ipynb"
    nbf.write(notebook, target)
    print(f"[built] {target.name}")
    return target


def execute(target: Path) -> None:
    notebook = nbf.read(target, as_version=4)
    client = NotebookClient(notebook, timeout=1800, kernel_name="python3",
                            resources={"metadata": {"path": str(HERE)}})
    client.execute()
    nbf.write(notebook, target)
    print(f"[ran]   {target.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    for spec in NOTEBOOKS:
        target = build(spec)
        if args.execute:
            execute(target)
    print(f"\n{len(NOTEBOOKS)} notebooks in {HERE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
