# US Domestic Flight Delay Drivers

CISC7204 · Class K · Team 01 · reviewed product version 0.4.0

An analysis of reported flight-delay causes, the long tail of arrival delays,
exploratory airport groups, and the limits of severe-delay risk ranking.
The linked Dash application supports comparison by year, carrier, months and airport.

## Reading the dashboard

The opening summary updates with the active sample filters. Read the main story in
three steps: distribution and reported causes, time patterns, then airports and
carriers. Search carrier names, airport names, cities or codes. The compact section
navigation keeps the current selection visible and links back to the filters.

Each chart labels its scope. The map retains all airports for navigation, the
carrier comparison retains all carriers, and airport groups and model validation
are fixed references. The selected airport has an orange outline. Technical
analysis, chart-reading instructions, methods and a plain-language glossary expand
on demand. Negative delay means early arrival; p90 is the point by which 90% of
completed flights arrive relative to schedule.

## Current evidence

- Source panel: 2015–2024, 61,689,698 completed flights. Geography includes BTS
  territory codes; it is not labelled a verified 50-state-plus-DC subset.
- Dashboard: a reproducible 400,000 completed-flight sample. Filtered counts and
  percentages describe this sample, not the entire panel. Narrow filters can be sparse.
- Airport metadata: 195/195 reviewed airports have matched coordinates.
  Physical airport type is a proxy, not an FAA passenger-enplanement hub class.
- Exploratory groups: k=4, subsample ARI=0.713.
  Labels describe regions of feature space; they do not establish causal airport types.
- Temporal risk holdout starts 2024-07-01; n=22,998.
  Training event rate 6.09%; test event rate 6.77%.

| Model | ROC AUC | Average precision | Brier error (lower is better) |
|---|---:|---:|---:|
| Constant training rate | 0.5000 | 0.0677 | 0.06313 |
| Logistic | 0.6857 | 0.1452 | 0.06104 |
| Gradient boosting | 0.6897 | 0.1470 | 0.06103 |

Calibration curves and baseline scores appear in the dashboard's fixed model-evidence
section. Ranking ability and modest baseline improvement do not guarantee an
accurate probability or arrival time for an individual flight.

## Quick start

```bash
python -m pip install -r requirements.lock.txt
python dashboard/app.py
python -m pytest tests -q
```

`requirements.lock.txt` records validated direct dependency versions on Python 3.14
Windows. It is not a full transitive environment lock. `environment.yml` mirrors
these direct versions. The application uses Dash 4 component styles.

Raw and processed data are excluded from Git. For a new checkout, acquire the real
panel before launching the real-data dashboard:

```bash
python run_all.py --stage data
python run_all.py --stage pipeline
```

For a no-download synthetic demonstration, `python run_all.py --stage smoke` builds
fixture outputs. **It overwrites shared figures and result files with synthetic
outputs.** Use a separate checkout/directory for smoke runs. Do not quote fixture
numbers as empirical findings.

## Reviewed rebuild

```bash
python run_all.py --stage review --part airports
python run_all.py --stage review --part models
python run_all.py --stage review --part rotations --tails 256
```

The reviewed airport rebuild reuses unchanged full-panel numerical airport
aggregates, then recomputes metadata and clustering. The model rebuild streams a
uniform completed-flight sample. The rotation rebuild selects whole aircraft
histories; timezone reference data is downloaded when absent. Existing source
validation counts are checked before accepting the model sample.

## Research questions and limits

1. **Reported causes:** how are cause minutes distributed and how does composition
   vary? Carrier plus late-aircraft is a descriptive grouping, not airline control.
2. **Turnaround pressure:** what shortfall occurs under a minimum-turnaround
   assumption? Complete sampled aircraft records are matched in UTC. This estimate
   is not a causal partition of realised arrival delay. The old 17.1% attribution
   estimate is superseded. See `outputs/metrics/rotation_pressure.json` for sample,
   exclusions, 15/25/45-minute sensitivity and compatibility-field definitions.
3. **Airport groups:** how do scale, delay tail and reported cause mix differ?
   Coordinates and airport physical types use explicit code mappings and documented
   historical aliases. Group names and k are regenerated, not fixed in advance.
4. **Risk ranking:** how much do observable pre-departure factors add to a baseline?
   Training-only category mappings, temporal holdout, calibration and baseline error
   are reported. Permutation importance is neither SHAP nor a causal contribution.

Cancellation/diversion risk is excluded from completed-flight outcomes. NOAA weather
observations are a planned extension and do not enter these models. Missing source
legs, uncertain DST times, historical airport reference changes and unmeasured
operational conditions limit the rotation analysis. Expanding-window checks for 2019, 2020, 2022 and 2024 are reported in
`outputs/metrics/temporal_validation.json`. This separate specification omits year
and COVID controls. In 2020, probability error is worse than the constant-rate
baseline despite AUC above 0.5. Real-user evaluation remains outstanding.

## Product structure

| Directory | Contents |
|---|---|
| `src/team01` | Analysis, acquisition, metadata joins, UTC sequence analysis and models |
| `src/scripts` | Stage entry points including reviewed rebuild 08 |
| `dashboard` | Linked sample views and fixed holdout evidence |
| `notebooks` | Seven executable analysis narratives; saved outputs cleared after corrections |
| `config` | Parameters and source-documented historical airport aliases |
| `data` | Source documentation/checksums; large local datasets ignored by Git |
| `outputs` | CSV results, strict JSON metrics and metadata audit |
| `figures` | Generated analytical figures; contact sheet is not a UI screenshot |
| `tests` | Arithmetic, data-contract and defect regression checks |
| `docs/standards` | Technical and visual conventions, validation contract |

Course reports, reviews, proposals, meeting records, videos and submission packages
belong in sibling Semester Project folders and are excluded from this product.
Original data sources and licences are documented in `data/README.md`.
See [validation contract](docs/standards/validation.md) before interpreting results.

Team: AO KIT I, LI YING FANG, HO MAN HOU, WU PEI YE, LI TIAN HAO, SAVIDI AVRAM.

## Browser acceptance and robustness (6 November 2026)

Browser checks passed at 1440, 1024 and 390 px widths: year/carrier/month controls,
keyboard month and airport selection, map click, shared airport URL restoration,
reset and empty-filter feedback. These are simulated viewport checks, not physical
phone or screen-reader certification. A real screenshot is `figures/13_dashboard.png`;
`13_dashboard_snapshot.png` is separately labelled as an analytical contact sheet.

Monthly cause composition is accompanied by observed severe-delay risk, so the
worst-month task can be answered without repeatedly changing twelve filters.
Airport selection is available both on the map and through a keyboard-accessible
search. Map fill covers 50 states plus DC; territory flights remain in KPIs.

```bash
python run_all.py --stage temporal
```

The fixed-sample expanding-window evaluation uses no future-year training records.
Weekly-block intervals describe baseline-relative Brier improvement conditional
on the sample and fitted models; these folds were not used for tuning.
Turnaround pressure now includes an aircraft-cluster bootstrap interval, conditional
on sequence coverage, timezone reference and the minimum-turn assumption.
The source-wide airport-code coverage audit flags ISN/TKI active-reference gaps and
ISN's missing timezone instead of inventing historical data.
