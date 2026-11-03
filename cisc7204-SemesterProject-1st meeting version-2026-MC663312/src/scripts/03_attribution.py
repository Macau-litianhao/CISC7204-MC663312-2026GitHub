"""03 - Attribution: where the delay minutes come from, and how stable that is.

    python src/scripts/03_attribution.py

Produces the headline split with a bootstrap interval, its stability across
years, the carrier table, the monthly composition, and four figures.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import attribution, clean, config, io, models, viz  # noqa: E402


def main() -> int:
    print(config.summarise())
    panel = clean.completed(io.load_flights())
    universe = clean.attribution_universe(panel)

    print(f"completed flights      : {len(panel):,}")
    print(f"attribution universe   : {len(universe):,} "
          f"({len(universe)/len(panel):.1%} of completed)")

    totals = attribution.cause_totals(universe)
    split = attribution.family_split(universe)
    interval = attribution.bootstrap_family_share(universe)
    stability = attribution.stability_by_year(universe, bootstrap=False)
    carriers = attribution.carrier_table(universe)
    composition = attribution.composition_by(universe, "month")

    tables = config.ensure_dir("paths.tables")
    totals.to_csv(tables / "cause_totals.csv", index=False)
    stability.to_csv(tables / "attribution_stability_by_year.csv", index=False)
    carriers.to_csv(tables / "carrier_table.csv", index=False)
    composition.to_csv(tables / "composition_by_month.csv", index=False)

    state_delay = (
        panel.groupby("origin_state", observed=True)["arr_delay"].mean().round(2)
    )
    state_delay.to_csv(tables / "mean_delay_by_state.csv", header=["mean_arr_delay"])

    print("\nFamily split")
    for key, value in split.items():
        print(f"  {key:22s} {value}")
    print(f"\nBootstrap: internal share {interval['share']:.3f} "
          f"[{interval['ci_low']:.3f}, {interval['ci_high']:.3f}] "
          f"over {interval['days']} operating days")

    viz.fig_cause_waffle(totals)
    viz.fig_monthly_composition(composition)
    viz.fig_carrier_bars(carriers)
    viz.fig_state_tile(state_delay, metric_label="Mean arrival delay (min)")

    models.save_metrics({
        "mode": config.mode(),
        "split": split,
        "bootstrap": interval,
        "stability": stability.to_dict(orient="records"),
        "attribution_universe": int(len(universe)),
        "completed_flights": int(len(panel)),
    }, "attribution")

    print(f"\n[03] tables -> {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
