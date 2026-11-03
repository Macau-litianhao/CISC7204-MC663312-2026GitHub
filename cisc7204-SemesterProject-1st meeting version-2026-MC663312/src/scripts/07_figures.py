"""07 - Figure inventory and the printed dashboard contact sheet.

    python src/scripts/07_figures.py

Checks that every figure named in the report exists, reports its size, and
composes the contact sheet that goes into the written report. Running this after
``make figures`` is how a stale figure gets caught before submission: a missing
file shows up as a blank cell, not as a broken link discovered after the
deadline.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import config, viz  # noqa: E402

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
]

SHEET = ["02_monthly_composition", "04_percentile_band", "05_lorenz",
         "08_cascade_hour", "10_cluster_scatter", "12_hour_response"]

# Prefer a real screenshot of the running application over a contact sheet of
# its panels: the report should show the product, not a reconstruction of it.
DASHBOARD_SHOT = "13_dashboard"


def main() -> int:
    print(config.summarise())
    found, missing = [], []
    for name in EXPECTED:
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

    print(f"\n{len(found)}/{len(EXPECTED)} figures present")
    if missing:
        print("run: " + " && ".join(
            ["python src/scripts/03_attribution.py",
             "python src/scripts/04_tail.py",
             "python src/scripts/05_clusters.py",
             "python src/scripts/06_models.py"]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
