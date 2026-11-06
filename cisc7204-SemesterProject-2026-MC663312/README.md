# US Domestic Flight Delay Drivers

CISC7204 · Class K · Team 01 · reviewed product version 0.5.0

An analysis of reported flight-delay causes, the long tail of arrival delays,
exploratory airport groups, and the limits of severe-delay risk ranking.
The linked Dash application supports comparison by year, carrier, months and airport.

## Reading the dashboard

The opening summary updates with the active sample filters. Read the main story in
three steps: distribution and reported causes, time patterns, then airports and
carriers. Search carrier names, airport names, cities or codes. The compact section
navigation keeps the current selection visible and links back to the filters.

Each chart labels its scope. The map ignores the airport selector and displays up to 120 busiest sampled
airports with coordinates; other origins remain available in search. The
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
- Exploratory groups: k=4, subsample ARI=0.756.
  Labels describe regions of feature space; they do not establish causal airport types.
- Temporal risk holdout starts 2024-07-01; n=23,128.
  Training event rate 6.09%; test event rate 6.75%.

| Model | ROC AUC | Average precision | Brier error (lower is better) |
|---|---:|---:|---:|
| Constant training rate | 0.5000 | 0.0675 | 0.06294 |
| Logistic | 0.6858 | 0.1368 | 0.06100 |
| Gradient boosting | 0.6914 | 0.1403 | 0.06090 |

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
fixture outputs in isolated `outputs/tables/sample`, `outputs/metrics/sample` and
`figures/sample` directories. Real reference files and empirical outputs remain
separate. Do not quote fixture numbers as empirical findings.

## Reviewed rebuild

```bash
python run_all.py --stage review --part airports
python run_all.py --stage review --part models
python run_all.py --stage review --part rotations --tails 256
```

The reviewed airport rebuild streams the source anew and regenerates validation,
reconciled cause totals, tail summaries and airport features before clustering.
The model rebuild uniformly samples 600,000 completed flights for inference,
then draws explicit seeded quantile/risk subsamples. OLS uses reference coding,
full-column-rank validation and operating-day clustered covariance. Quantile
regression targets signed arrival delay; its coefficients are point estimates.
Joint factor-block importance and conditional drop-one R² are non-additive
associations. The rotation rebuild selects whole aircraft source histories.

The canonical full `pipeline` includes temporal validation, reference audit and
supplementary monthly/distance and sensitivity checks. JSON results bind source,
configuration and reference content hashes; readers reject stale results.
`config/reference_snapshots.json` pins reference content. Restore a matching
snapshot or deliberately review/update that registry and rebuild when sources
change; silently accepting updated upstream references is not supported.

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
   Training-only reference-category mappings, temporal holdout, calibration and baseline error
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


## Correctness audit fixes (6 November 2026, v0.5.0)

- Acquisition merges only the requested successfully written year files and replaces
  the formal panel atomically. Single-year runs cannot absorb stale staging years.
- Inference contrasts use recorded reference levels and a full-rank design. OLS
  errors cluster by operating day; HC1 output naming has been retired. Quantile
  coefficients refer to signed arrival delay and carry no significance claim.
- The reported cause population requires complete, nonnegative minutes reconciling
  within one minute. Six unreported records and one unreconciled record are excluded
  and documented in `cause_quality_exclusions.csv`; this is not zero imputation.
- Airport subsample stability uses the actual configured fit as reference and refits
  preprocessing within each subsample. It does not establish natural airport types.
- A strict 200-flight carrier display floor applies even when no carrier qualifies.
  Full-mode temporal splits fail on invalid boundaries; demo fallback separates dates.
- `supplementary.json` records tail sensitivity and a common-support AA/DL comparison.
  Only a limited subset has common support; this is not an airline-wide causal ranking.
- Large raw datasets are not bundled. Matching content hashes detect input differences;
  they do not recover unavailable historical records or certify BTS source correctness.
