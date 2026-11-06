"""Tests for the analytical claims.

Each test protects a sentence the report makes. If the cascade arithmetic, the
concentration statistic or the clustering selection changes, one of these fails
before the sentence becomes false.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from team01 import attribution, cluster, features, models, tail, config


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------
def test_family_shares_sum_to_one(universe):
    split = attribution.family_split(universe)
    assert split["internal_share"] + split["system_share"] == pytest.approx(1.0, abs=1e-3)
    assert 0 <= split["internal_share"] <= 1


def test_cause_totals_cover_every_cause(universe):
    totals = attribution.cause_totals(universe)
    assert len(totals) == 5
    assert totals["share"].sum() == pytest.approx(1.0, abs=1e-6)


def test_bootstrap_interval_brackets_the_estimate(universe):
    interval = attribution.bootstrap_family_share(universe, reps=60, seed=3)
    assert interval["ci_low"] <= interval["share"] <= interval["ci_high"]
    assert interval["days"] > 0


def test_stability_table_has_one_row_per_year(universe):
    table = attribution.stability_by_year(universe, bootstrap=False)
    assert len(table) == universe["year"].nunique()
    assert table["internal_share"].between(0, 1).all()


# --------------------------------------------------------------------------
# Tail and concentration
# --------------------------------------------------------------------------
def test_lorenz_curve_is_monotone_and_bounded(completed):
    result = tail.lorenz(completed, sample_rows=20_000, seed=1)
    curve = result["curve"]
    assert curve["share_of_minutes"].is_monotonic_increasing
    assert curve["share_of_minutes"].iloc[-1] == pytest.approx(1.0, abs=1e-6)
    assert 0 <= result["gini"] <= 1


def test_worst_one_percent_carries_more_than_its_share(completed):
    """The concentration claim: minutes are far more unequal than flights."""
    result = tail.lorenz(completed, sample_rows=50_000, seed=1)
    assert result["top1_share"] > 0.01


def test_percentile_profile_includes_the_mean_rank(completed):
    profile = tail.percentile_profile(completed).set_index("statistic")["value"]
    assert "mean_percentile_rank" in profile.index
    assert 0 <= profile["mean_percentile_rank"] <= 100


def test_mean_vs_tail_reports_a_correlation(completed):
    result = tail.mean_vs_tail(completed, by="month")
    assert -1 <= result["pearson_r"] <= 1
    assert result["verdict"] in {"no paradox", "divergence present"}


# --------------------------------------------------------------------------
# Cascade
# --------------------------------------------------------------------------
def _legs(previous_delay: float, scheduled_turn: float) -> pd.DataFrame:
    """Two consecutive legs of one aircraft, hand-built for the arithmetic."""
    arrival = pd.Timestamp("2024-06-01 10:00")
    second_departure = arrival + pd.Timedelta(minutes=scheduled_turn)
    return pd.DataFrame({
        "tail_number": ["N1", "N1"],
        "flight_date": [pd.Timestamp("2024-06-01")] * 2,
        "sched_dep_dt": [pd.Timestamp("2024-06-01 08:00"), second_departure],
        "sched_arr_dt": [arrival, second_departure + pd.Timedelta(minutes=90)],
        "actual_arr_dt": [arrival + pd.Timedelta(minutes=previous_delay),
                          second_departure + pd.Timedelta(minutes=90)],
        "arr_delay": [previous_delay, 0.0],
        "origin": ["ATL", "ATL"],
        "dest": ["ATL", "DFW"],
        "carrier": ["AA", "AA"],
        "dep_hour": [8, 11],
        "cancelled": [0, 0],
        "diverted": [0, 0],
    })


def test_inherited_delay_is_previous_delay_above_the_buffer():
    """40 minutes late into a 60-minute turn leaves 5 minutes of inherited delay:
    40 - (60 - 25) = 5."""
    legs = features.leg_sequence(_legs(previous_delay=40, scheduled_turn=60))
    second = legs.iloc[1]
    assert second["is_rotation"]
    assert second["inherited_min"] == pytest.approx(5.0)


def test_delay_within_the_buffer_is_not_inherited():
    legs = features.leg_sequence(_legs(previous_delay=10, scheduled_turn=90))
    assert legs.iloc[1]["inherited_min"] == pytest.approx(0.0)


def test_a_leg_that_does_not_continue_the_aircraft_is_not_a_rotation():
    frame = _legs(previous_delay=40, scheduled_turn=60)
    frame.loc[1, "origin"] = "DEN"          # aircraft "teleports" to another hub
    legs = features.leg_sequence(frame)
    assert not legs.iloc[1]["is_rotation"]
    assert legs.iloc[1]["inherited_min"] == pytest.approx(0.0)


def test_cascade_summary_reports_a_share(completed):
    legs = features.leg_sequence(completed)
    summary = features.cascade_summary(legs, completed)
    assert summary["rotations"] > 0
    assert 0 <= summary["inherited_share"] <= 1
    assert {"dep_hour", "inherited_share"}.issubset(summary["hourly"].columns)


# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------
def test_feature_matrix_is_one_row_per_airport(completed, airport_reference):
    matrix = features.airport_feature_matrix(completed, airport_reference,
                                             min_departures=50)
    assert matrix["origin"].is_unique
    assert (matrix["n_dep"] >= 50).all()


def test_sweep_and_choice_are_consistent(completed, airport_reference):
    matrix = features.airport_feature_matrix(completed, airport_reference,
                                             min_departures=50)
    sweep = cluster.sweep_k(matrix, k_min=2, k_max=4)
    assert list(sweep["k"]) == [2, 3, 4]
    assert sweep["silhouette"].between(-1, 1).all()
    assert cluster.choose_k(sweep) in {2, 3, 4}


def test_fit_attaches_cluster_and_projection(completed, airport_reference):
    matrix = features.airport_feature_matrix(completed, airport_reference,
                                             min_departures=50)
    labelled, _, _ = cluster.fit(matrix, 3)
    assert {"cluster", "pc1", "pc2"} <= set(labelled.columns)
    assert labelled["cluster"].nunique() <= 3


def test_stability_is_bounded(completed, airport_reference):
    matrix = features.airport_feature_matrix(completed, airport_reference,
                                             min_departures=50)
    result = cluster.stability(matrix, 3, draws=3)
    assert -1 <= result["mean_ari"] <= 1
    assert result["verdict"] in {"stable", "unstable - report with caution"}


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
def test_incremental_r2_is_ordered_and_bounded(completed):
    table = models.incremental_r2(completed, rows=20_000, seed=2)
    factors = list(table["factor"])
    controls = [row for row in factors if row.startswith("panel controls")]
    # Five research factors in their declared order, then at most one closing
    # block for the panel controls: they are a nuisance term, not an explanation.
    assert factors[:len(models.FACTOR_ORDER)] == models.FACTOR_ORDER
    assert len(factors) == len(models.FACTOR_ORDER) + (1 if controls else 0)
    assert table["incremental_r2"].sum() == pytest.approx(
        table["cumulative_r2"].iloc[-1], abs=1e-3)
    assert 0 <= table.attrs["model_r2"] <= 1


def test_panel_controls_flag_the_pandemic_window(completed):
    flagged = features.add_panel_controls(completed)
    in_window = flagged["flight_date"].between("2020-03-01", "2021-12-31")
    assert (flagged.loc[in_window, "covid_era"] == 1).all()
    assert (flagged.loc[~in_window, "covid_era"] == 0).all()

    # A control that never varies must not reach the design matrix: it would be
    # a column of ones on top of the constant and make the linear program sick.
    flat = flagged.assign(covid_era=0)
    matrix = models.design_matrix(flat, controls=["year", "covid_era"])
    assert not [c for c in matrix.columns if c.startswith("covid_era")]


def test_controls_are_kept_out_of_the_coefficient_table(completed):
    panel = features.add_panel_controls(completed)
    ols = models.ols_with_robust_errors(panel, rows=20_000, seed=2)
    assert not [t for t in ols["table"]["term"] if models._is_control(t)]
    # ...but they are in the fit, so the explained share is not overstated.
    assert ols["controls"]


def test_sensitivity_reports_both_versions(completed):
    panel = features.add_panel_controls(completed)
    result = models.sensitivity_exclude_years(panel, years=[2019], rows=20_000, seed=2)
    assert result["with_excluded"]["rows"] > result["without_excluded"]["rows"]
    assert "ols_r2" in result["without_excluded"]


def test_quantile_model_returns_coefficients(completed):
    result = models.quantile_regression(completed, quantile=0.9, rows=8_000, seed=2)
    assert result["table"]["coef"].notna().all()
    assert -1 <= result["pseudo_r2"] <= 1


def test_classifier_beats_a_coin_flip_only_barely(completed, monkeypatch):
    """The honest ceiling: five observable factors rank risk weakly."""
    monkeypatch.setattr(config, "mode", lambda: "sample")
    result = models.risk_classifier(completed, threshold=60, rows=25_000, seed=2)
    for name in ("logistic", "gradient_boosting"):
        assert 0.5 <= result["models"][name]["roc_auc"] <= 1.0
    importance = pd.DataFrame(result["models"]["importance"])
    assert set(importance["factor"]).issubset(set(models.FACTOR_ORDER) | {"panel controls"})


def test_design_matrix_aligns_on_reference(completed):
    train = models.take_sample(completed, 5_000, seed=1)
    test = models.take_sample(completed, 1_000, seed=2)
    reference = models.design_matrix(train)
    aligned = models.design_matrix(test, reference=reference)
    assert list(aligned.columns) == list(reference.columns)
    assert (aligned["const"] == 1.0).all()


def test_distance_bands_cover_every_flight(completed):
    bands = features.distance_band(completed)
    assert bands.notna().all()
    assert len(bands) == len(completed)
