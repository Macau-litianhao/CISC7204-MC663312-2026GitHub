"""06 - Modelling: factor ranking, tail regression, risk classification.

    python src/scripts/06_models.py [--rows 400000]

Reports three things and states the ceiling of each:

* which factor explains most of the variation in delay length (sequential R²);
* what moves the ninetieth percentile (quantile regression);
* how well severe-delay risk can be ranked on a time-based holdout
  (logistic baseline versus gradient boosting, with permutation importance).

Nothing here is presented as a flight-level predictor. The R² and AUC values in
outputs/metrics/models.json are the evidence for that limitation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from team01 import clean, config, features, io, models, viz  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=None,
                        help="override models.gbm_rows for a quicker run")
    args = parser.parse_args()

    print(config.summarise())
    panel = features.add_panel_controls(clean.completed(io.load_flights()))
    controls = models.active_controls(panel)
    print(f"panel controls: {controls} "
          f"(COVID share {panel['covid_era'].mean():.1%} of flights)")

    print("\nFactor ranking (sequential R-squared)")
    ranking = models.incremental_r2(panel)
    print(ranking.to_string(index=False))
    print(f"model R-squared = {ranking.attrs.get('model_r2')} "
          f"on {ranking.attrs.get('rows'):,} sampled flights")

    ols = models.ols_with_robust_errors(panel)
    quantile = models.quantile_regression(panel, quantile=0.9)
    print(f"\nOLS(HC1) R² = {ols['r2']}; quantile-90 pseudo R² = {quantile['pseudo_r2']}")

    risk = models.risk_classifier(panel, threshold=60, rows=args.rows)
    split = risk["split"]
    print(f"\nRisk model, time split: train to {split['train_last_date']}, "
          f"test from {split['actual_test_start']} "
          f"({risk['test_rows']:,} test flights, base rate {risk['base_rate']:.3%})")
    if split["fallback_to_chronological_80_20"]:
        print(f"  note: {split['requested_start']} is outside the panel, so the "
              "split fell back to a chronological 80/20")
    for name, metrics in risk["models"].items():
        if name == "importance":
            continue
        print(f"  {name:20s} AUC {metrics['roc_auc']:.3f}  "
              f"PR-AUC {metrics['pr_auc']:.3f}  Brier {metrics['brier']:.4f}")

    # The headline numbers are quoted with the pandemic years and without them.
    # One version alone would hide how much of the average is 2021.
    sensitivity = models.sensitivity_exclude_years(panel)

    tables = config.ensure_dir("paths.tables")
    ranking.to_csv(tables / "factor_incremental_r2.csv", index=False)
    ols["table"].to_csv(tables / "ols_hc1_coefficients.csv", index=False)
    quantile["table"].to_csv(tables / "quantile90_coefficients.csv", index=False)
    risk["hour_response"].to_csv(tables / "risk_by_hour.csv", index=False)
    pd.json_normalize(
        [{"set": "with_all_years", **sensitivity["with_excluded"]},
         {"set": "excluding_selected_years", **sensitivity["without_excluded"]}]
    ).to_csv(tables / "sensitivity_excluded_years.csv", index=False)

    viz.fig_importance(pd.DataFrame(risk["models"]["importance"]))
    viz.fig_hour_response(risk["hour_response"], threshold=60)

    models.save_metrics({
        "mode": config.mode(),
        "controls": controls,
        "ranking": ranking.to_dict(orient="records"),
        "model_r2": ranking.attrs.get("model_r2"),
        "ols": {k: v for k, v in ols.items() if k != "table"},
        "quantile90": {"pseudo_r2": quantile["pseudo_r2"], "rows": quantile["rows"]},
        "risk": risk,
        "sensitivity": sensitivity,
    }, "models")

    print(f"\n[06] tables -> {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
