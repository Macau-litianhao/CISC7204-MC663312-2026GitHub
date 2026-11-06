"""Modelling: factor ranking, tail regression, risk classification.

Three models, each answering a different question and each reported with its
own honest ceiling:

* ``incremental_r2``      - which observable factor explains most of the
  variation in delay length? Sequential R-squared over five blocks, in a fixed
  order, so the numbers add up and the order is stated rather than implied.
* ``quantile_regression`` - what moves the *ninetieth percentile* rather than
  the mean? A factor can be irrelevant on average and decisive in the tail.
  Estimated as a linear program (HiGHS), which returns point estimates but no
  standard errors; the tail argument therefore rests on coefficient sign and
  relative size, and the table carries no p-value rather than a fabricated one.
* ``risk_classifier``     - baseline logistic against histogram gradient
  boosting, with a time-based holdout so no information travels backwards.

The models rank patterns. They do not promise an arrival time: the pilot's
R-squared of 0.029 and AUC of 0.679 are the ceiling for five observable
factors, and the report says so in the limitations instead of in a footnote.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, QuantileRegressor
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             roc_auc_score)
from sklearn.preprocessing import StandardScaler

from . import config

# Order matters: factors are added left to right and the incremental R-squared
# of each block is measured against everything before it. Hour first, because
# the within-day cycle is the strongest single signal in the pilot.
FACTOR_ORDER = ["dep_hour", "month", "carrier", "origin", "distance"]

CATEGORICAL_FACTORS = ["dep_hour", "month", "carrier", "origin"]
NUMERIC_FACTORS = ["distance"]


def control_names() -> list[str]:
    """Panel controls: nuisance terms that enter every model, not research factors."""
    return [c for c in config.panel_controls()]


def active_controls(frame: pd.DataFrame, names: list[str] | None = None) -> list[str]:
    """Controls that can actually vary in ``frame``.

    A control with one level is a column of a single value: it is removed from
    the design matrix anyway, and keeping it in the label would claim that a
    model absorbed a COVID effect the fixture never contains.
    """
    return [name for name in (names if names is not None else control_names())
            if name in frame.columns and frame[name].nunique(dropna=False) > 1]


def _is_control(term: str, names: list[str] | None = None) -> bool:
    """True for a control's own dummies, e.g. ``year_2019`` or ``covid_era``."""
    for name in (names if names is not None else control_names()):
        if term == name or term.startswith(f"{name}_"):
            return True
    return False


# --------------------------------------------------------------------------
# Sampling and splitting
# --------------------------------------------------------------------------
def take_sample(df: pd.DataFrame, rows: int | None = None,
                seed: int | None = None) -> pd.DataFrame:
    """Fixed-seed sample so every reported number is reproducible."""
    limit = int(config.get("sampling.ols_rows", 600_000) if rows is None else rows)
    rng = np.random.default_rng(config.seed() if seed is None else seed)
    if len(df) <= limit:
        return df
    idx = rng.choice(len(df), size=limit, replace=False)
    return df.iloc[np.sort(idx)]


# Factors whose level count grows with the panel. Origin airports are the only
# one: a ten-year national panel has 350+ of them, the rest are bounded.
HIGH_CARDINALITY_FACTORS = {"origin"}


def _limit_levels(series: pd.Series, top_k: int) -> pd.Series:
    """Keep the ``top_k`` most frequent levels, pool the rest into ``other``.

    One-hot encoding every origin in a full panel yields 350+ columns. Quantile
    regression solves a weighted least squares problem on every IRLS iteration,
    so its cost scales with the column count, not only the row count: at 376
    columns it does not converge in any usable time. Tail airports are
    individually rare, so pooling them costs little and keeps the matrix near
    90 columns. The cut is by frequency of the frame passed in, so the training
    and holdout frames agree as long as they are carved from the same table.
    """
    if top_k <= 0 or series.nunique() <= top_k:
        return series
    # Cast out of category first: ``where`` cannot assign a new label to a
    # categorical column, because the category set is fixed.
    plain = series.astype("object")
    keep = plain.value_counts().head(top_k).index
    return plain.where(plain.isin(keep), "other")


def design_matrix(df: pd.DataFrame, factors: list[str] | None = None,
                  reference: pd.DataFrame | None = None,
                  controls: list[str] | None = None) -> pd.DataFrame:
    """One-hot design matrix with a constant, aligned to a reference if given.

    Alignment matters for the holdout: a carrier that appears in the test set
    but not in the training set must not silently create a new column, so the
    training frame's columns are reindexed onto the test frame with zeros.

    ``controls`` appends the panel controls (year fixed effects, COVID era) as a
    block. They are dropped one level each, because a full set of year dummies
    plus a constant is exactly collinear; each research factor also drops a recorded reference level,
    so coefficient contrasts are identifiable.

    Columns that never vary are removed afterwards. A single-year panel, or a
    fixture without a pandemic year, otherwise carries a control that is
    perfectly collinear with the constant - harmless for OLS with a
    pseudo-inverse, fatal for the linear program that solves the quantile
    regression.
    """
    factors = FACTOR_ORDER if factors is None else list(factors)
    control_list = control_names() if controls is None else list(controls)
    control_list = [c for c in control_list if c in df.columns]
    # A control is recognised by name even when it is passed as a plain factor
    # (the cumulative ranking does that), so the reference level is always
    # dropped for every categorical factor and control.
    top_k = int(config.get("models.origin_top_k", 50))
    learned_levels = reference.attrs.get("factor_levels", {}) if reference is not None else {}
    factor_levels = {}
    parts = []
    for factor in factors + control_list:
        if factor in NUMERIC_FACTORS:
            parts.append(df[[factor]].astype("float64"))
        else:
            if factor in HIGH_CARDINALITY_FACTORS:
                if reference is not None:
                    keep = learned_levels.get(factor)
                    if keep is None:
                        raise ValueError(f"Training category mapping missing for {factor}")
                    column = df[factor].astype('object').where(df[factor].isin(keep), 'other')
                else:
                    column = _limit_levels(df[factor], top_k)
                    factor_levels[factor] = [v for v in column.unique() if v != 'other']
            else:
                column = df[factor]
            # Freeze ALL categorical levels, including the dropped control
            # baseline. A one-year holdout must not drop its only year dummy.
            if reference is None:
                levels = sorted(pd.Series(column).dropna().unique().tolist())
                factor_levels[factor] = levels
            else:
                levels = learned_levels.get(factor, [])
            column = pd.Categorical(column, categories=levels)
            dummies = pd.get_dummies(column, prefix=factor, dtype="float64",
                                     drop_first=True)
            dummies.index = df.index
            parts.append(dummies)

    matrix = pd.concat(parts, axis=1)
    matrix = sm.add_constant(matrix, has_constant="add")

    constant = [c for c in matrix.columns
                if c != "const" and float(matrix[c].std(ddof=0)) == 0.0]
    if constant and reference is None:
        matrix = matrix.drop(columns=constant)

    if reference is not None:
        matrix = matrix.reindex(columns=reference.columns, fill_value=0.0)
        matrix["const"] = 1.0
    matrix = matrix.astype("float64")
    matrix.attrs['factor_levels'] = learned_levels if reference is not None else factor_levels
    return matrix


# --------------------------------------------------------------------------
# Factor ranking
# --------------------------------------------------------------------------
def incremental_r2(df: pd.DataFrame, rows: int | None = None,
                   seed: int | None = None) -> pd.DataFrame:
    """Univariate and sequential R-squared for each factor block.

    The panel controls close the table as a final block rather than being
    folded into the factors. They are not an explanation of delay - nobody
    argues that a flight is late because the calendar says 2021 - but they do
    lift the explained share, and a decomposition that silently omitted them
    would leave the model R-squared unexplained by its own rows.
    """
    sample = take_sample(df, rows, seed)
    target = sample["arr_delay"].astype("float64")
    controls = active_controls(sample)

    univariate: dict[str, float] = {}
    for factor in FACTOR_ORDER:
        matrix = design_matrix(sample, [factor], controls=[])
        fitted = sm.OLS(target, matrix).fit()
        univariate[factor] = float(fitted.rsquared)

    cumulative: list[dict] = []
    previous = 0.0
    for i in range(1, len(FACTOR_ORDER) + 1):
        factors = FACTOR_ORDER[:i]
        matrix = design_matrix(sample, factors, controls=[])
        r2 = float(sm.OLS(target, matrix).fit().rsquared)
        factor = FACTOR_ORDER[i - 1]
        cumulative.append({
            "factor": factor,
            "univariate_r2": univariate[factor],
            "cumulative_r2": r2,
            "incremental_r2": r2 - previous,
        })
        previous = r2

    if controls:
        matrix = design_matrix(sample, FACTOR_ORDER + controls, controls=[])
        r2 = float(sm.OLS(target, matrix).fit().rsquared)
        cumulative.append({
            "factor": "panel controls (" + ", ".join(controls) + ")",
            "univariate_r2": float("nan"),
            "cumulative_r2": r2,
            "incremental_r2": r2 - previous,
        })
        previous = r2

    table = pd.DataFrame(cumulative)
    total = table["incremental_r2"].sum()
    table["share_of_explained"] = (table["incremental_r2"] / total).round(4) if total else 0.0
    table.attrs["model_r2"] = round(previous, 4)
    table.attrs["rows"] = int(len(sample))
    table.attrs["controls"] = controls
    return table


def ols_with_robust_errors(df: pd.DataFrame, rows: int | None = None,
                           seed: int | None = None) -> dict:
    """Reference-coded full-factor OLS with day-clustered covariance.

    Operating-day clustered covariance permits shared daily shocks and
    heteroskedasticity. It is not a causal model and does not absorb all serial dependence.
    """
    sample = take_sample(df, rows, seed)
    matrix = design_matrix(sample)
    names = [c for c in matrix.columns if c != "const" and not _is_control(c)]
    target = sample["arr_delay"].astype("float64")
    _assert_full_rank(matrix)
    if sample["flight_date"].nunique() < 20:
        raise ValueError("At least 20 day clusters required for inference")
    fitted = sm.OLS(target, matrix).fit(cov_type="cluster",
        cov_kwds={"groups": sample["flight_date"]})

    summary = pd.DataFrame({
        "term": matrix.columns,
        "coef": fitted.params.values,
        "std_err": fitted.bse.values,
        "t": fitted.tvalues.values,
        "p_value": fitted.pvalues.values,
    })
    # Year dummies and the COVID dummy are fitted but not tabulated: they are
    # in the model to absorb the trend, not to be read as findings. Reporting
    # them would fill the table with nine rows that say "time passes".
    summary = summary[(summary["term"] != "const") & ~summary["term"].map(_is_control)]
    summary = summary.reindex(summary["coef"].abs().sort_values(ascending=False).index)
    return {
        "table": summary.head(40).reset_index(drop=True),
        "r2": round(float(fitted.rsquared), 4),
        "r2_adj": round(float(fitted.rsquared_adj), 4),
        "rows": int(len(sample)),
        "controls": active_controls(sample),
        "factor_terms": len(names),
        "covariance": "operating-day clustered",
        "reference_levels": {k: v[0] for k,v in matrix.attrs["factor_levels"].items() if v},
        "design_rank": int(np.linalg.matrix_rank(matrix.to_numpy())),
    }


def quantile_regression(df: pd.DataFrame, quantile: float = 0.9,
                        rows: int | None = None, seed: int | None = None) -> dict:
    """Quantile regression at ``quantile`` - what moves the tail, not the mean.

    Solved as a linear program through HiGHS, not by IRLS. The IRLS path in
    statsmodels needs one weighted least squares solve per iteration, and on
    the real panel's 92-column design it hit its 5,000-iteration cap without
    converging: 133 s for 50,000 rows and still moving. HiGHS returns the exact
    optimum in about a third of that time, which is what makes this stage
    runnable on the full panel at all.

    A linear program yields point estimates only, so there is no ``p_value``
    column. The tail argument in the report rests on the sign and relative size
    of the coefficients, which are readable without one - and reporting an
    invented significance level would be worse than reporting none.
    """
    sample = take_sample(df, rows or int(config.get("sampling.tail_rows", 250_000)), seed)
    matrix = design_matrix(sample)
    feature_names = [c for c in matrix.columns if c != "const"]
    _assert_full_rank(matrix)
    target = sample["arr_delay"].astype("float64").to_numpy()

    # sklearn fits its own intercept, so the constant column must come out.
    fitted = QuantileRegressor(quantile=quantile, alpha=0.0, solver="highs",
                               fit_intercept=True).fit(matrix[feature_names].to_numpy(),
                                                       target)

    table = pd.DataFrame({"term": feature_names, "coef": fitted.coef_})
    # Controls stay in the fit and out of the table, for the same reason as in
    # the OLS: they absorb the calendar, they are not a finding about delay.
    table = table[~table["term"].map(_is_control)]
    table = table.reindex(table["coef"].abs().sort_values(ascending=False).index)

    # Koenker-Machado pseudo R-squared, same definition statsmodels reports:
    # the check loss of the fitted model against that of an intercept-only fit.
    # rho_tau(u) = u * (tau - I(u < 0)) for both terms, so the residual and the
    # centred target enter with the same sign convention.
    residual = target - fitted.predict(matrix[feature_names].to_numpy())
    rho = float(np.mean(np.where(residual >= 0, quantile * residual,
                                 (quantile - 1.0) * residual)))
    baseline = float(np.quantile(target, quantile))
    centred = target - baseline
    rho0 = float(np.mean(np.where(centred >= 0, quantile * centred,
                                  (quantile - 1.0) * centred)))

    return {
        "quantile": quantile,
        "table": table.head(30).reset_index(drop=True),
        "rows": int(len(sample)),
        "pseudo_r2": round(1.0 - rho / rho0, 4) if rho0 else float("nan"),
        "solver": "highs",
        "target": "signed arr_delay",
        "reference_levels": {k:v[0] for k,v in matrix.attrs["factor_levels"].items() if v},
        "controls": active_controls(sample),
    }


# --------------------------------------------------------------------------
# Risk classification
# --------------------------------------------------------------------------
def time_split(df: pd.DataFrame, holdout_start: str | None = None):
    """Never share a calendar date; production requires the requested boundary."""
    start = pd.Timestamp(holdout_start or config.get("models.holdout_start"))
    dates = pd.to_datetime(df["flight_date"], errors="raise").dt.normalize()
    if dates.isna().any():
        raise ValueError("Missing holdout dates")
    fallback = not dates.lt(start).any() or not dates.ge(start).any()
    if fallback:
        if config.mode() != 'sample':
            raise ValueError("Holdout boundary outside observed dates; change it explicitly")
        unique = np.sort(dates.unique())
        if len(unique) < 2:
            raise ValueError("At least two distinct dates required")
        start = pd.Timestamp(unique[max(1,min(len(unique)-1,int(.8*len(unique))))])
    train, test = df.loc[dates.lt(start)], df.loc[dates.ge(start)]
    assert train.flight_date.max() < test.flight_date.min()
    return train, test



def _binary_target(frame: pd.DataFrame, threshold: int) -> np.ndarray:
    return (frame["arr_delay"] >= threshold).to_numpy(dtype="int8")


def risk_classifier(df: pd.DataFrame, threshold: int = 60,
                    rows: int | None = None, seed: int | None = None) -> dict:
    """Logistic baseline versus histogram gradient boosting on a time holdout."""
    sample = take_sample(df, rows or int(config.get("sampling.gbm_rows", 400_000)), seed)
    train, test = time_split(sample)

    x_train = design_matrix(train)
    x_test = design_matrix(test, reference=x_train)
    y_train = _binary_target(train, threshold)
    y_test = _binary_target(test, threshold)

    base_rate = float(y_train.mean())
    results: dict[str, dict] = {}

    # Baseline: standardised linear model. Keeping it in the table is the point:
    # a reader needs to see how much the tree model actually adds.
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    logistic = LogisticRegression(max_iter=2000)
    logistic.fit(x_train_scaled, y_train)
    proba_logit = logistic.predict_proba(x_test_scaled)[:, 1]
    results["logistic"] = _classification_metrics(y_test, proba_logit, base_rate)
    results["logistic"]["features"] = int(x_train.shape[1])

    boosting = HistGradientBoostingClassifier(
        max_iter=int(config.get("models.gbm_estimators", 300)),
        learning_rate=float(config.get("models.gbm_learning_rate", 0.05)),
        max_depth=int(config.get("models.gbm_max_depth", 6)),
        early_stopping=True,
        validation_fraction=0.15,
        random_state=int(config.seed() if seed is None else seed),
    )
    boosting.fit(x_train, y_train)
    proba_gbm = boosting.predict_proba(x_test)[:, 1]
    results["gradient_boosting"] = _classification_metrics(y_test, proba_gbm, base_rate)
    results['constant_train_rate'] = _classification_metrics(
        y_test, np.full(len(y_test), base_rate), base_rate)
    from sklearn.calibration import calibration_curve
    calibration = {}
    for name, probabilities in [('logistic', proba_logit), ('gradient_boosting', proba_gbm)]:
        observed, predicted = calibration_curve(y_test, probabilities, n_bins=10, strategy='quantile')
        calibration[name] = [{'predicted': float(p), 'observed': float(o)} for p, o in zip(predicted, observed)]
    yearly = []
    for year in sorted(test['year'].unique()):
        mask = (test['year'].to_numpy() == year)
        if len(np.unique(y_test[mask])) == 2:
            yearly.append({'year': int(year), 'rows': int(mask.sum()),
                           **_classification_metrics(y_test[mask], proba_gbm[mask], base_rate)})

    # One common row permutation per factor block preserves valid one-hot states.
    grouped = block_importance(boosting, x_test, y_test)
    results["importance"] = grouped.to_dict(orient="records")

    response = binned_response(test, proba_gbm, "dep_hour")
    # The split is part of the result, not an implementation detail: "time-based
    # holdout" is a claim a reader should be able to check. The old field was
    # named holdout_start and held the last training date, which is a different
    # number, so the key is spelled out explicitly here.
    requested = str(config.get("models.holdout_start"))
    test_start = test["flight_date"].min()
    split = {
        "requested_start": requested,
        "actual_test_start": str(test_start.date()),
        "train_last_date": str(train["flight_date"].max().date()),
        "fallback_to_chronological_80_20": bool(not sample.flight_date.lt(pd.Timestamp(requested)).any() or not sample.flight_date.ge(pd.Timestamp(requested)).any()),
    }
    return {
        "threshold_min": threshold,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "base_rate": round(base_rate, 4),
        "test_base_rate": round(float(y_test.mean()), 6),
        "calibration": calibration,
        "yearly_test_metrics": yearly,
        "models": results,
        "hour_response": response,
        "split": split,
    }


def _classification_metrics(y_true: np.ndarray, proba: np.ndarray,
                            base_rate: float) -> dict:
    return {
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_true, proba)), 4),
        "average_precision": round(float(average_precision_score(y_true, proba)), 4),
        "test_base_rate": round(float(np.mean(y_true)), 6),
        "brier": round(float(brier_score_loss(y_true, proba)), 5),
        "base_rate": round(base_rate, 4),
    }


def binned_response(frame: pd.DataFrame, proba: np.ndarray, column: str,
                    bins: int | None = None) -> pd.DataFrame:
    """Observed-bin mean predicted risk; not a partial dependence intervention.

    Cheaper than a full PDP and easier to read: for an ordered column such as
    departure hour it is exactly the curve a traveller wants to see.
    """
    work = pd.DataFrame({"value": frame[column].to_numpy(), "proba": proba})
    if bins:
        work["value"] = pd.cut(work["value"], bins=bins)
    table = work.groupby("value", observed=True)["proba"].agg(["mean", "size"])
    table = table.rename(columns={"mean": "mean_predicted_risk", "size": "flights"})
    return table.reset_index().rename(columns={"value": column})


# --------------------------------------------------------------------------
# Sensitivity
# --------------------------------------------------------------------------
def sensitivity_exclude_years(df: pd.DataFrame, years: list[int] | None = None,
                              rows: int | None = None, seed: int | None = None) -> dict:
    """Recompute the headline statistics with the flagged years removed.

    ``config/project.yaml`` has claimed since the panel was designed that the
    results are repeated without the pandemic years, and nothing implemented
    it - the promise existed only as a comment. A flagged year that is never
    re-estimated around is a caveat, not a sensitivity analysis.

    The point of the comparison is the size of the shift, not a preferred
    version: if removing two years moves the mean more than the effect being
    reported, the pooled number is not worth quoting on its own.
    """
    excluded = [int(y) for y in (config.sensitivity_years() if years is None else years)]
    kept = df[~df["year"].isin(excluded)]

    def headline(frame: pd.DataFrame) -> dict:
        return {
            "rows": int(len(frame)),
            "mean_arr_delay": round(float(frame["arr_delay"].mean()), 2),
            "median_arr_delay": round(float(frame["arr_delay"].median()), 2),
            "share_delayed_15": round(float((frame["arr_delay"] >= config.threshold()).mean()), 4),
            "share_delayed_60": round(float((frame["arr_delay"] >= 60).mean()), 4),
        }

    with_excluded = headline(df)
    with_excluded["ols_r2"] = ols_with_robust_errors(df, rows, seed)["r2"]
    excluded_rows = int(len(df) - len(kept))

    if kept.empty:
        print(f"[models] sensitivity: no rows left after excluding {excluded}")
        return {"excluded_years": excluded, "excluded_rows": excluded_rows,
                "note": "no rows were removed; the comparison is not a test",
                "with_excluded": with_excluded, "without_excluded": {}, "delta": {}}

    without = headline(kept)
    without["ols_r2"] = ols_with_robust_errors(kept, rows, seed)["r2"]
    delta = {key: round(without[key] - with_excluded[key], 4)
             for key in without if key != "rows"}
    print(f"[models] sensitivity excluding {excluded}: "
          f"mean {with_excluded['mean_arr_delay']:+.2f} -> {without['mean_arr_delay']:+.2f} min, "
          f"R2 {with_excluded['ols_r2']} -> {without['ols_r2']}")

    # A fixture that contains neither year produces a table of exact zeros. Read
    # without this line, `sensitivity_excluded_years.csv` says "excluding the
    # pandemic changes nothing", which is a finding; what actually happened is
    # that there was nothing to exclude.
    note = ("no rows were removed, so a zero delta is arithmetic, not a result"
            if excluded_rows == 0 else "")
    if note:
        print(f"[models] sensitivity: {note}")
    return {"excluded_years": excluded, "excluded_rows": excluded_rows, "note": note,
            "with_excluded": with_excluded,
            "without_excluded": without, "delta": delta}


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------
def save_metrics(payload: dict, name: str) -> Path:
    """Write a JSON metrics file for the dashboard and the report."""
    target = config.ensure_parent(config.METRIC_DIR / f"{name}.json")
    from . import provenance
    payload={**payload,"artifact_sha256":provenance.artifact_fingerprints(name)}
    temporary=target.with_suffix(".json.part")
    temporary.write_text(json.dumps(json_safe({**payload, "run_signature": provenance.signature()}), indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(target)
    print(f"[models] metrics -> {target}")
    return target


def json_safe(value):
    """Lossless tabular records, explicit nulls; reject unsupported objects."""
    import math
    if isinstance(value, pd.DataFrame):
        return json_safe(value.to_dict(orient='records'))
    if isinstance(value, pd.Series):
        return json_safe(value.to_dict())
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f'Unsupported metrics value: {type(value).__name__}')


def load_metrics(name: str) -> dict:
    """Read a metrics file, returning an empty dict when it has not been built."""
    target = config.METRIC_DIR / f"{name}.json"
    if not target.exists():
        return {}
    from . import provenance
    return provenance.check(json.loads(target.read_text(encoding="utf-8")))


def _assert_full_rank(matrix):
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Missing or non-finite model predictors")
    if np.linalg.matrix_rank(matrix.to_numpy()) != matrix.shape[1]:
        raise ValueError("Design matrix rank deficient: inspect reference levels and controls")


def block_importance(estimator, x, y, repeats=5):
    """Joint one-hot-block shuffling, not a sum of individual dummy perturbations."""
    groups = {factor:[c for c in x if c == factor or c.startswith(factor+'_')]
              for factor in FACTOR_ORDER}
    groups['panel controls'] = [c for c in x if _is_control(c)]
    baseline = roc_auc_score(y, estimator.predict_proba(x)[:,1])
    rng = np.random.default_rng(config.seed())
    records=[]
    for factor, columns in groups.items():
        if not columns: continue
        drops=[]
        for _ in range(repeats):
            shuffled=x.copy()
            shuffled.loc[:,columns]=x.loc[:,columns].to_numpy()[rng.permutation(len(x))]
            drops.append(baseline-roc_auc_score(y,estimator.predict_proba(shuffled)[:,1]))
        records.append({'factor':factor,'importance':float(np.mean(drops)),
                        'std':float(np.std(drops,ddof=1)), 'repeats':repeats})
    table=pd.DataFrame(records).sort_values('importance',ascending=False)
    return table


def conditional_factor_r2(df, rows=None):
    sample=take_sample(df,rows)
    matrix=design_matrix(sample);_assert_full_rank(matrix)
    target=sample.arr_delay.astype(float)
    full=float(sm.OLS(target,matrix).fit().rsquared)
    records=[]
    for factor in FACTOR_ORDER:
        columns=[c for c in matrix if c==factor or c.startswith(factor+'_')]
        reduced=float(sm.OLS(target,matrix.drop(columns=columns)).fit().rsquared)
        records.append({'factor':factor,'drop_one_r2':full-reduced,'full_model_r2':full,
                        'interpretation':'conditional association; not additive or causal'})
    return pd.DataFrame(records)
