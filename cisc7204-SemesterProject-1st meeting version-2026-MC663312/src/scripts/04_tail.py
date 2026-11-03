"""04 - Tail behaviour, concentration and the within-day cascade.

    python src/scripts/04_tail.py [--cascade-sample 3000000]

Three outputs: the percentile profile that argues against reporting an average,
the Lorenz curve that shows how concentrated the minutes are, and the cascade
measurement that turns "late aircraft" from a label into a mechanism.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from team01 import clean, config, features, io, models, tail, viz  # noqa: E402


def distance_bands(panel: pd.DataFrame) -> pd.DataFrame:
    """Mean and p90 delay per route-distance band."""
    work = panel.assign(band=features.distance_band(panel))
    grouped = work.groupby("band", observed=True)["arr_delay"]
    table = pd.DataFrame({
        "mean": grouped.mean().round(2),
        "p90": grouped.quantile(0.90).round(2),
        "flights": grouped.size(),
    }).reset_index()
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cascade-sample", type=int, default=3_000_000,
                        help="rows used for the rotation reconstruction")
    args = parser.parse_args()

    print(config.summarise())
    panel = clean.completed(io.load_flights())

    profile = tail.percentile_profile(panel)
    severe = tail.severe_shares(panel)
    concentration = tail.lorenz(panel)
    burden = tail.delay_burden(panel)
    monthly = tail.monthly_profile(panel)
    paradox = tail.mean_vs_tail(panel, by="month")
    bands = distance_bands(panel)

    tables = config.ensure_dir("paths.tables")
    profile.to_csv(tables / "percentile_profile.csv", index=False)
    monthly.to_csv(tables / "monthly_profile.csv", index=False)
    bands.to_csv(tables / "distance_bands.csv", index=False)
    if not concentration["curve"].empty:
        concentration["curve"].to_csv(tables / "lorenz_curve.csv", index=False)

    print("\nPercentiles (minutes)")
    print(profile.to_string(index=False))
    print(f"\nConcentration: Gini {concentration['gini']:.3f}, "
          f"worst 1% -> {concentration['top1_share']:.1%} of minutes")
    print(f"Mean vs tail across months: r = {paradox['pearson_r']:.3f} "
          f"({paradox['verdict']})")

    # Cascade: the rotation reconstruction needs the tail number and the actual
    # arrival time of the previous leg, so it is run on a bounded sample.
    sample = panel
    if args.cascade_sample and len(panel) > args.cascade_sample:
        sample = models.take_sample(panel, args.cascade_sample)
    legs = features.leg_sequence(sample)
    cascade = features.cascade_summary(legs, sample)

    cascade["hourly"].to_csv(tables / "cascade_by_hour.csv", index=False)
    cascade["by_airport"].to_csv(tables / "cascade_by_airport.csv", index=False)

    print(f"\nCascade: {cascade['rotation_share_of_flights']:.1%} of flights are "
          f"second-or-later legs; inherited share {cascade['inherited_share']:.1%}")

    viz.fig_percentile_band(monthly)
    viz.fig_mean_bar_vs_band(monthly)
    viz.fig_lorenz(concentration)
    viz.fig_distance_bands(bands)
    viz.fig_cascade_hour(cascade["hourly"])

    models.save_metrics({
        "mode": config.mode(),
        "percentiles": profile.to_dict(orient="records"),
        "severe": severe,
        "concentration": {k: v for k, v in concentration.items() if k != "curve"},
        "burden": burden,
        "mean_vs_tail": {"pearson_r": paradox["pearson_r"],
                         "spearman_r": paradox["spearman_r"],
                         "verdict": paradox["verdict"]},
        "cascade": {k: v for k, v in cascade.items()
                    if k not in ("hourly", "by_airport")},
        "cascade_by_hour": cascade["hourly"].to_dict(orient="records"),
    }, "tail")

    print(f"\n[04] tables -> {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
