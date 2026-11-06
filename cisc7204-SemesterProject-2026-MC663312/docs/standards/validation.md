# Validation and interpretation contract

## Airport metadata

Join BTS IATA/FAA codes to explicit reference codes, never ICAO `ident` directly.
Historical aliases are source-documented in `config/airport_aliases.csv`. Ambiguous
requested mappings fail. Unmatched airports are reported and excluded from
metadata-dependent clustering; their flight statistics are not silently deleted.
`hub_stratum` is a legacy name for physical airport type, not an FAA hub class.

## Rotation pressure

Production estimates use `rotation_pressure.analyse_file`: select aircraft tails
uniformly and retain all their source records, including cancelled/diverted legs.
UTC departure = local flight date + scheduled HHMM, localised at the origin.
UTC scheduled arrival = UTC departure + scheduled elapsed duration. Ambiguous or
nonexistent DST timestamps and unknown timezones are excluded, not guessed.
Continuity requires same aircraft, previous destination = origin, plausible ground
interval, and both legs completed. Missing source records remain a limitation.

The 15/25/45-minute minimum-turn assumptions estimate turnaround pressure, not
causal arrival-delay minutes. Pressure can exceed realised arrival delay because
of recovery. Legacy `inherited_*` fields remain for compatibility and are explicitly
labelled in metrics; they must not be presented as a causal attribution percentage.
Local scheduled hour is used for hourly comparisons, UTC for sequence matching.

## Risk models

Uniform completed-flight sampling is fixed-seed and verified against source row
counts. Category levels, rare-airport mappings and scaling are learned on training
records only. The primary temporal test begins 2024-07-01. Constant probabilities
use the training event rate and are scored on the test set. Report train/test
prevalence, ROC AUC, average precision, Brier error and calibration together.
The `pr_auc` key is retained as a legacy alias for average precision, not trapezoidal
PR area. Permutation importance is model-specific association, not SHAP or causality.
Heldout calibration is descriptive and is not used to refit the evaluated model.
Expanding-window 2019/2020/2022/2024 checks use a separately disclosed specification without year/COVID controls. The 2020 fold has negative Brier improvement; these folds are evaluation, not tuning data.

## Dashboard

KPI and most plots describe the bounded real-flight sample. Airport groups are a
fixed full-panel reference. The map retains the navigation population, while the
carrier comparison retains all carriers. Shared URL state includes airport.
Histogram end bars are explicit overflow groups; small hourly bins are hidden.
Static figure contact sheets are not screenshots of the running dashboard.

## Evidence

Run `python -m pytest tests -q` for arithmetic and regression checks, then exercise
the Dash HTTP state/panel callbacks with actual data. Backend timings are not
browser end-to-end performance. Real user testing and visual browser acceptance
must be recorded separately; neither is inferred from passing automated tests.

Browser acceptance is recorded in the sibling Teams Review/acceptance-2026-11-06 folder. Real-user task records remain blank until actual participants complete them.
