"""Airport archetypes: k-means with a silhouette-selected k, plus a Ward check.

Why clustering is a defensible stage here rather than a decorative one:

* The features are heterogeneous (departures span three orders of magnitude,
  shares sit in [0,1], minutes run to the hundreds), so they are log-transformed
  where needed and standardised before any distance is computed.
* k is not chosen by preference. The sweep reports silhouette, Calinski-Harabasz
  and Davies-Bouldin for k = 3..8, and the selected k is the one that maximises
  silhouette while keeping every cluster above the minimum size.
* The Ward dendrogram is a second, independent structure; the cophenetic
  correlation says whether the dendrogram is a faithful summary of the distance
  matrix at all.
* Cluster stability is reported as mean adjusted Rand index across subsamples,
  because a k-means solution that changes when a third of the airports are
  removed is a description of the sample, not of the airports.

Labels are generated from the cluster's z-scores rather than hand-assigned, so
re-running the pipeline on a new year produces new names instead of stale ones.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_score)
from sklearn.preprocessing import StandardScaler

from . import config, schema


# --------------------------------------------------------------------------
# Matrix preparation
# --------------------------------------------------------------------------
def feature_frame(airports: pd.DataFrame) -> pd.DataFrame:
    """Select and transform the clustering features.

    ``n_dep`` is logged because the distance between 20k and 40k departures
    should not count ten times as much as the distance between 200k and 220k.
    """
    frame = airports[[c for c in schema.AIRPORT_FEATURES if c in airports.columns]].copy()
    for column in schema.LOG_FEATURES:
        if column in frame.columns:
            frame[column] = np.log10(frame[column].clip(lower=1))
    return frame


def scaled_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, StandardScaler]:
    scaler = StandardScaler()
    matrix = scaler.fit_transform(frame.to_numpy(dtype="float64"))
    return matrix, scaler


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------
def sweep_k(airports: pd.DataFrame, k_min: int | None = None,
            k_max: int | None = None, random_state: int | None = None) -> pd.DataFrame:
    """Score every candidate k. Returns one row per k with three criteria."""
    low = int(config.get("cluster.k_min", 3) if k_min is None else k_min)
    high = int(config.get("cluster.k_max", 8) if k_max is None else k_max)
    n_init = int(config.get("cluster.n_init", 25))
    rs = int(config.get("cluster.random_state", 42) if random_state is None else random_state)

    frame = feature_frame(airports)
    matrix, _ = scaled_matrix(frame)

    rows = []
    for k in range(low, high + 1):
        if k >= len(frame):
            continue
        model = KMeans(n_clusters=k, n_init=n_init, random_state=rs)
        labels = model.fit_predict(matrix)
        sizes = np.bincount(labels)
        rows.append({
            "k": k,
            "silhouette": round(float(silhouette_score(matrix, labels)), 4),
            "calinski_harabasz": round(float(calinski_harabasz_score(matrix, labels)), 1),
            "davies_bouldin": round(float(davies_bouldin_score(matrix, labels)), 4),
            "inertia": round(float(model.inertia_), 1),
            "smallest_cluster": int(sizes.min()),
            "largest_cluster": int(sizes.max()),
        })
    return pd.DataFrame(rows)


def choose_k(sweep: pd.DataFrame, min_cluster_size: int | None = None) -> int:
    """Highest silhouette among k whose smallest cluster is still meaningful.

    The floor comes from ``cluster.min_cluster_size`` so that the figure, which
    annotates the rejected peak, and this rule cannot drift apart.
    """
    floor = int(config.get("cluster.min_cluster_size", 3)
                if min_cluster_size is None else min_cluster_size)
    usable = sweep[sweep["smallest_cluster"] >= floor]
    if usable.empty:
        return int(sweep.loc[sweep["silhouette"].idxmax(), "k"])
    return int(usable.loc[usable["silhouette"].idxmax(), "k"])


def pc_variance(airports: pd.DataFrame, random_state: int | None = None) -> list[float]:
    """Share of the standardised variance held by the two plotted components.

    A PCA scatter without this number invites the reader to treat the axes as
    two real dimensions. On nine standardised features a first axis worth 30%
    means most of what separates the airports is folded into the five dimensions
    that were dropped, and the picture is a shadow rather than a map.
    """
    rs = int(config.get("cluster.random_state", 42) if random_state is None else random_state)
    frame = feature_frame(airports)
    matrix, _ = scaled_matrix(frame)
    pca = PCA(n_components=2, random_state=rs).fit(matrix)
    return [round(float(value), 3) for value in pca.explained_variance_ratio_]


def fit(airports: pd.DataFrame, k: int, random_state: int | None = None
        ) -> tuple[pd.DataFrame, np.ndarray, KMeans]:
    """Fit k-means and attach the cluster label to the airport table."""
    rs = int(config.get("cluster.random_state", 42) if random_state is None else random_state)
    n_init = int(config.get("cluster.n_init", 25))
    frame = feature_frame(airports)
    matrix, _ = scaled_matrix(frame)

    model = KMeans(n_clusters=k, n_init=n_init, random_state=rs)
    labels = model.fit_predict(matrix)

    out = airports.copy()
    out["cluster"] = labels
    coords = PCA(n_components=2, random_state=rs).fit_transform(matrix)
    out["pc1"], out["pc2"] = coords[:, 0], coords[:, 1]
    return out, matrix, model


# --------------------------------------------------------------------------
# Structure checks
# --------------------------------------------------------------------------
def ward_check(airports: pd.DataFrame) -> dict:
    """Ward linkage on the same distance matrix, with cophenetic correlation."""
    frame = feature_frame(airports)
    matrix, _ = scaled_matrix(frame)
    distance = pdist(matrix, metric="euclidean")
    tree = linkage(distance, method="ward")
    correlation, _ = cophenet(tree, distance)
    return {
        "linkage": tree,
        "cophenetic_correlation": round(float(correlation), 4),
        "n_airports": int(len(frame)),
    }


def stability(airports: pd.DataFrame, k: int, draws: int = 10,
              fraction: float = 0.8, seed: int | None = None) -> dict:
    """Mean adjusted Rand index between the full fit and subsample refits."""
    rng = np.random.default_rng(config.seed() if seed is None else seed)
    frame = feature_frame(airports)
    matrix, _ = scaled_matrix(frame)
    reference = KMeans(n_clusters=k, n_init=25, random_state=0).fit_predict(matrix)

    scores = []
    n = len(matrix)
    for _ in range(draws):
        pick = rng.choice(n, size=int(n * fraction), replace=False)
        sub_labels = KMeans(n_clusters=k, n_init=25, random_state=0).fit_predict(matrix[pick])
        scores.append(adjusted_rand_score(reference[pick], sub_labels))

    return {
        "mean_ari": round(float(np.mean(scores)), 4),
        "min_ari": round(float(np.min(scores)), 4),
        "draws": draws,
        "subsample_fraction": fraction,
        "verdict": "stable" if np.mean(scores) >= 0.7 else "unstable - report with caution",
    }


# --------------------------------------------------------------------------
# Profiling and naming
# --------------------------------------------------------------------------
def profiles(airports: pd.DataFrame, labels_col: str = "cluster") -> pd.DataFrame:
    """Mean of every raw feature per cluster (before scaling, for readability)."""
    features = [c for c in schema.AIRPORT_FEATURES if c in airports.columns]
    table = airports.groupby(labels_col, observed=True)[features].mean()
    table["airports"] = airports.groupby(labels_col, observed=True).size()
    return table.reset_index()


def z_profiles(airports: pd.DataFrame, labels_col: str = "cluster") -> pd.DataFrame:
    """Cluster means expressed as z-scores against the airport population."""
    features = [c for c in schema.AIRPORT_FEATURES if c in airports.columns]
    population_mean = airports[features].mean()
    population_std = airports[features].std().replace(0, np.nan)
    table = airports.groupby(labels_col, observed=True)[features].mean()
    return ((table - population_mean) / population_std).reset_index()


def _descriptor(row: pd.Series) -> str:
    """Two-part name: scale first, then the dominant risk signature."""
    scale = "High-volume airport" if row.get("n_dep", 0) > 0.8 else (
        "Regional field" if row.get("n_dep", 0) < -0.6 else "Mid-size airport"
    )

    severity = row.get("share_delayed_60", 0)
    if row.get("share_weather", 0) > 0.7:
        risk = "weather-exposed"
    elif row.get("share_nas", 0) > 0.7:
        risk = "airspace-constrained"
    elif row.get("share_late_aircraft", 0) > 0.6:
        risk = "high late-aircraft share"
    elif severity < -0.5:
        risk = "low-risk"
    elif severity > 0.6:
        risk = "tail-heavy"
    else:
        risk = "mixed-cause"

    return f"{scale}, {risk}"


def name_clusters(airports: pd.DataFrame, labels_col: str = "cluster") -> dict[int, str]:
    """Generate a readable archetype name per cluster, unique within the table.

    The descriptor buckets a cluster into one scale and one risk signature, so
    two genuinely different groups can land on the same two words - in the
    fixture, "Mid-size airport, mixed-cause" described both C1 and C2, and a
    legend with two identical entries makes the colour the only thing carrying
    the distinction. Colliding names are qualified by the feature that separates
    the cluster most from the airport population, and by the cluster id if that
    is still not enough.
    """
    z = z_profiles(airports, labels_col).set_index(labels_col)
    base = {int(cluster): _descriptor(row) for cluster, row in z.iterrows()}
    counts = Counter(base.values())
    names = {
        cluster: (f"{name} ({_standout(z.loc[cluster])})" if counts[name] > 1 else name)
        for cluster, name in base.items()
    }
    repeated = Counter(names.values())
    for cluster, name in list(names.items()):
        if repeated[name] > 1:
            names[cluster] = f"{name} C{cluster}"
    return names


def _standout(row: pd.Series) -> str:
    """The feature where this cluster sits furthest from the population mean."""
    phrases = {
        "n_dep": "high volume",
        "mean_arr_delay": "long average delay",
        "p90_arr_delay": "heavy tail",
        "share_delayed_60": "frequent severe delay",
        "share_internal": "high carrier + late-aircraft share",
        "share_late_aircraft": "late-aircraft driven",
        "share_nas": "airspace-bound",
        "share_weather": "high reported weather share",
        "seasonal_amplitude": "strong seasonality",
        "hub_stratum": "airport physical-type proxy",
    }
    scores = {key: abs(float(row.get(key, 0) or 0)) for key in phrases if key in row}
    if not scores:
        return "unnamed"
    return phrases[max(scores, key=scores.get)]


def cluster_table(airports: pd.DataFrame, labels_col: str = "cluster") -> pd.DataFrame:
    """Profile table with generated names and the member airports listed."""
    table = profiles(airports, labels_col)
    names = name_clusters(airports, labels_col)
    table["archetype"] = table[labels_col].map(names)

    order = table.sort_values("share_delayed_60", ascending=False)[labels_col].tolist()
    table["display_order"] = table[labels_col].map({c: i for i, c in enumerate(order)})
    table = table.sort_values("display_order").drop(columns="display_order")

    members = (
        airports.sort_values("n_dep", ascending=False)
        .groupby(labels_col, observed=True)["origin"]
        .apply(lambda s: ", ".join(s.head(6)))
        .rename("largest_members")
    )
    return table.merge(members, on=labels_col, how="left")


def save(airports: pd.DataFrame, path=None) -> object:
    """Write the labelled airport table for the dashboard to read."""
    target = path or config.airports_clustered_file()
    target = config.ensure_parent(target if hasattr(target, "parent") else target)
    columns = ["origin", "name", "municipality", "latitude_deg", "longitude_deg",
               "cluster", "archetype", "pc1", "pc2", *schema.AIRPORT_FEATURES]
    keep = [c for c in columns if c in airports.columns]
    airports[keep].to_csv(target, index=False)
    print(f"[cluster] wrote {len(airports)} labelled airports -> {target}")
    return target
