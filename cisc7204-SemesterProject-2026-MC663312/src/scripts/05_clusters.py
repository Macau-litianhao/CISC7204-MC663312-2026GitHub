"""05 - Airport archetypes: feature matrix, k selection, clusters, stability.

    python src/scripts/05_clusters.py

The threshold on departures is data-dependent: on the ten-year panel it is
20,000, on the smoke fixture it is a few hundred. The script lowers it until at
least eight airports qualify, and prints which threshold it used, because a
cluster solution over five airports is a description of five airports.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import clean, cluster, config, features, io, models, schema, viz  # noqa: E402


def build_matrix(panel, airports):
    """Feature matrix with a departure floor that adapts to the data volume."""
    floor = int(config.get("cluster.min_departures", 20000))
    while floor >= 50:
        matrix = features.airport_feature_matrix(panel, airports, min_departures=floor)
        if len(matrix) >= 8:
            print(f"[05] departure floor {floor:,} -> {len(matrix)} airports")
            return matrix
        floor //= 4
    raise SystemExit("[05] fewer than 8 airports qualify even at 50 departures")


def main() -> int:
    print(config.summarise())
    panel = clean.completed(io.load_flights())
    airports = io.load_airports()

    matrix = build_matrix(panel, airports)
    matrix = matrix.loc[matrix['metadata_matched'] & matrix['hub_stratum'].notna()].copy()
    matrix.to_parquet(config.ensure_parent(config.airport_features_file()), index=False)

    sweep = cluster.sweep_k(matrix)
    chosen = cluster.choose_k(sweep)
    labelled, _, _ = cluster.fit(matrix, chosen)
    names = cluster.name_clusters(labelled)
    labelled["archetype"] = labelled["cluster"].map(names)
    ward = cluster.ward_check(matrix)
    stability = cluster.stability(matrix, chosen)
    table = cluster.cluster_table(labelled)

    print("\nk sweep")
    print(sweep.to_string(index=False))
    print(f"\nchosen k = {chosen}; Ward cophenetic r = {ward['cophenetic_correlation']}; "
          f"stability ARI = {stability['mean_ari']} ({stability['verdict']})")

    print("\nArchetypes")
    print(table[["cluster", "archetype", "airports", "mean_arr_delay",
                 "share_delayed_60", "share_late_aircraft"]].to_string(index=False))

    tables = config.ensure_dir("paths.tables")
    sweep.to_csv(tables / "cluster_k_sweep.csv", index=False)
    table.to_csv(tables / "airport_archetypes.csv", index=False)
    cluster.save(labelled)

    viz.fig_silhouette(sweep, chosen)
    # The solution's quality measures travel with the figure. They used to live
    # only in outputs/metrics/clusters.json, which meant a slide reader saw a
    # tidy scatter and no evidence that the grouping survives resampling.
    chosen_row = sweep.loc[sweep["k"] == chosen].iloc[0]
    viz.fig_cluster_scatter(
        labelled, names,
        stats={"k": int(chosen),
               "silhouette": float(chosen_row["silhouette"]),
               "ari": float(stability["mean_ari"]),
               "airports": int(len(matrix)),
               "pc_variance": cluster.pc_variance(matrix)},
    )

    models.save_metrics({
        "mode": config.mode(),
        "chosen_k": int(chosen),
        "airports": int(len(matrix)),
        "sweep": sweep.to_dict(orient="records"),
        "ward": {"cophenetic_correlation": ward["cophenetic_correlation"]},
        "stability": stability,
        "archetypes": table.to_dict(orient="records"),
        "features": [c for c in schema.AIRPORT_FEATURES if c in matrix.columns],
    }, "clusters")

    print(f"\n[05] tables -> {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
