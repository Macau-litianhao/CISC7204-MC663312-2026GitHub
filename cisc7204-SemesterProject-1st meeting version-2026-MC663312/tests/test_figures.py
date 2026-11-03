"""Tests for the presentation layer.

A figure that raises is worse than no figure: it takes the whole notebook down.
These tests call each builder with the fixture and assert the file appears, and
they check the two design rules the report claims to follow - a fixed colour per
cause, and 100 cells in the waffle.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import pytest

from team01 import attribution, cluster, config, features, schema, tail, viz


def test_waffle_allocates_exactly_one_hundred_cells(universe):
    totals = attribution.cause_totals(universe)
    counts = viz._waffle_counts(totals)
    assert sum(counts.values()) == 100
    assert all(value >= 0 for value in counts.values())


def test_waffle_keeps_a_cell_for_the_smallest_cause(universe):
    totals = attribution.cause_totals(universe)
    counts = viz._waffle_counts(totals)
    assert counts["min_security"] >= 1


def test_cause_colours_come_from_the_oken_ito_palette():
    """One fixed colour per cause, and every colour is in the shared palette."""
    for column in schema.CAUSE_COLUMNS:
        assert schema.CAUSE_COLORS[column] in schema.OKABE_ITO.values()


def test_each_builder_writes_a_file(universe, completed, figure_dir, airport_reference):
    totals = attribution.cause_totals(universe)
    composition = attribution.composition_by(universe, "month")
    # The floor is explicit here: this fixture is thirty simulated days, so the
    # registered 5,000-flight floor would (correctly) refuse to draw anything.
    carriers = attribution.carrier_table(universe, min_flights=50)
    monthly = tail.monthly_profile(completed)
    concentration = tail.lorenz(completed, sample_rows=20_000, seed=1)
    bands = completed.assign(band=features.distance_band(completed))
    band_table = bands.groupby("band", observed=True)["arr_delay"].agg(
        ["mean", lambda s: s.quantile(0.9)]).reset_index()
    band_table.columns = ["band", "mean", "p90"]
    states = completed.groupby("origin_state", observed=True)["arr_delay"].mean()

    legs = features.leg_sequence(completed)
    cascade = features.cascade_summary(legs, completed)

    matrix = features.airport_feature_matrix(completed, airport_reference,
                                             min_departures=50)
    sweep = cluster.sweep_k(matrix, k_min=2, k_max=4)
    labelled, _, _ = cluster.fit(matrix, 3)
    importance = __import__("pandas").DataFrame(
        {"factor": models_factor_order(), "importance": [0.4, 0.3, 0.2, 0.1, 0.0],
         "share": [0.4, 0.3, 0.2, 0.1, 0.0]})

    produced = [
        viz.fig_cause_waffle(totals),
        viz.fig_monthly_composition(composition),
        viz.fig_carrier_bars(carriers),
        viz.fig_percentile_band(monthly),
        viz.fig_lorenz(concentration),
        viz.fig_distance_bands(band_table),
        viz.fig_state_tile(states),
        viz.fig_cascade_hour(cascade["hourly"]),
        viz.fig_silhouette(sweep, 3),
        viz.fig_cluster_scatter(labelled),
        viz.fig_importance(importance),
        viz.fig_hour_response(
            __import__("pandas").DataFrame(
                {"dep_hour": range(24),
                 "mean_predicted_risk": [0.05] * 24,
                 "flights": [100] * 24}), threshold=60),
    ]
    assert all(produced)
    assert len(list(figure_dir.glob("*.png"))) >= len(produced)


def test_carrier_floor_refuses_an_empty_table(universe):
    """A floor above every carrier must raise, not draw an empty axis.

    The old behaviour returned a zero-row frame, ``fig_carrier_bars`` drew
    nothing on auto-scaled axes, and the blank PNG reached the report looking
    like a rendering failure rather than a configuration error.
    """
    with pytest.raises(ValueError, match="attributed flights"):
        attribution.carrier_table(universe, min_flights=10_000_000)
    with pytest.raises(ValueError, match="empty table"):
        viz.fig_carrier_bars(universe.iloc[0:0])


def test_dashboard_figures_build_without_a_server(completed, airport_reference):
    """The figure builders are pure functions of a frame; no Flask needed."""
    import sys
    from pathlib import Path

    dashboard = Path(__file__).resolve().parents[1] / "dashboard"
    sys.path.insert(0, str(dashboard))
    try:
        import callbacks
        import data_access
    except Exception as error:                  # pragma: no cover - import guard
        pytest.skip(f"dashboard modules unavailable: {error}")

    frame = completed
    builders = [callbacks.cause_figure, callbacks.monthly_figure,
                callbacks.hourly_figure, callbacks.distribution_figure,
                callbacks.cluster_figure, callbacks.lorenz_figure,
                callbacks.geo_figure]
    for builder in builders:
        figure = builder(frame)
        assert figure is not None
    assert data_access.kpis(frame)


def models_factor_order():
    from team01 import models
    return models.FACTOR_ORDER


def _dashboard_modules():
    """Import the dashboard modules the way the app does, once per call."""
    import sys
    from pathlib import Path

    dashboard = Path(__file__).resolve().parents[1] / "dashboard"
    if str(dashboard) not in sys.path:
        sys.path.insert(0, str(dashboard))
    import callbacks
    import data_access
    import narrative

    return callbacks, data_access, narrative


def test_url_state_round_trips():
    """What the controls write must parse back to the same three values.

    The URL and the controls are updated by two callbacks that close a loop. Any
    asymmetry between writing and reading - a different month separator, a
    sorted carrier list that comes back unsorted - makes them rewrite each other
    on every keystroke.
    """
    callbacks, _, _ = _dashboard_modules()
    cases = [("all", [], [1, 12]), (2024, ["AA", "DL"], [6, 8]), (2019, [], [3, 3])]
    for year, carriers, months in cases:
        search = callbacks._build_search(year, carriers, months)
        assert callbacks._parse_search(search) == (year, carriers, months)


def test_lorenz_curve_is_a_concentration_curve(completed):
    """Anchor the two properties the Lorenz panel claims: it starts at the
    origin, ends at 100%, never falls, and its top-1% share is a real share."""
    _, data, _ = _dashboard_modules()
    curve = data.lorenz_curve(completed)
    assert curve["x"][0] == 0 and curve["y"][0] == 0
    assert curve["y"][-1] == pytest.approx(1.0)
    assert all(b >= a - 1e-12 for a, b in zip(curve["y"], curve["y"][1:]))
    assert 0 < curve["top"][0.01] <= 1
    assert 0 <= curve["gini"] < 1


def test_insight_strip_degrades_to_one_line_when_empty(completed):
    """An empty filter must not print a stale percentage."""
    _, _, narrative = _dashboard_modules()
    empty = completed.iloc[0:0]
    items = narrative.insights(empty)
    assert len(items) == 1
    assert items[0]["value"] == "-"
