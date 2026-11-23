"""07 - Figure inventory, redraw, and the printed contact sheet.

    python src/scripts/07_figures.py            # inventory only
    python src/scripts/07_figures.py --redraw   # re-render every figure first

Two jobs, because they answer the same question at different times.

``--redraw`` rebuilds the whole figure set from the committed tables and
metrics in seconds - no flight panel, no model fitting. It exists because a
design change should not require a 6 GB rebuild, and because ``make figures``
used to only check that files were present.

Without the flag this is the submission gate: it reports which figure the report
names is missing. A stale figure used to be discovered after the deadline as a
broken link; here it is a blank cell.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import config, figures, viz  # noqa: E402

EXPECTED = [
    "01_cause_waffle",
    "02_monthly_composition",
    "03_carrier_bars",
    "04_percentile_band",
    "05_lorenz",
    "06_distance_bands",
    "07_state_tiles",
    "08_cascade_hour",
    "09_silhouette",
    "10_cluster_scatter",
    "11_importance",
    "12_hour_response",
    "14_mean_bar_vs_band",
    "15_temporal_validation",
    "16_inference_evidence",
]

# The synthetic fixture cannot produce these two. Figure 15 reads the year-by-year holdout
# table and figure 16 reads the conditional R² ladder; neither artefact exists in sample mode,
# because the fixture panel has one year and no configured model ladder. Treating them as
# missing would make `make smoke` - the documented no-download demo - fail on a correct run,
# so the expectation is mode-aware instead. The full run still requires all fifteen.
FIXTURE_EXEMPT = {"15_temporal_validation", "16_inference_evidence"}

# Four panels, not six: at six the cluster projection had to be shrunk until its
# labels were unreadable, which defeats the purpose of putting it on the page.
SHEET = ["04_percentile_band", "05_lorenz", "06_distance_bands", "12_hour_response"]

# Prefer a real screenshot of the running application over a contact sheet of
# its panels: the report should show the product, not a reconstruction of it.
DASHBOARD_SHOT = "13_dashboard"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--redraw", action="store_true",
                        help="re-render every figure from outputs/ before checking")
    parser.add_argument("--only", nargs="+", default=None,
                        help="redraw a subset by figure name")
    args = parser.parse_args()

    print(config.summarise())

    if args.redraw or args.only:
        targets = args.only or list(figures.FIGURES)
        print(f"\nredrawing {len(targets)} figure(s) from committed artefacts")
        figures.redraw_all(targets)

    expected = list(EXPECTED)
    exempt = sorted(FIXTURE_EXEMPT) if config.mode() == "sample" else []
    for name in exempt:
        expected.remove(name)

    found, missing = [], []
    for name in expected:
        path = config.FIG_DIR / f"{name}.png"
        if path.exists():
            found.append(path)
            print(f"  ok      {name:28s} {path.stat().st_size/1024:7.1f} KB")
        else:
            missing.append(name)
            print(f"  MISSING {name}")

    shot = config.FIG_DIR / f"{DASHBOARD_SHOT}.png"
    if shot.exists():
        print(f"  ok      {DASHBOARD_SHOT:28s} {shot.stat().st_size/1024:7.1f} KB "
              f"(screenshot of the running app)")
    else:
        sheet = [str(config.FIG_DIR / f"{name}.png") for name in SHEET
                 if (config.FIG_DIR / f"{name}.png").exists()]
        if sheet:
            viz.fig_dashboard_snapshot(sheet)
            print("  note    no dashboard screenshot found - contact sheet written instead")

    for name in exempt:
        print(f"  n/a     {name:28s} needs the full panel; not built in sample mode")

    print(f"\n{len(found)}/{len(expected)} figures present")
    if missing:
        print("run: python src/scripts/07_figures.py --redraw")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
