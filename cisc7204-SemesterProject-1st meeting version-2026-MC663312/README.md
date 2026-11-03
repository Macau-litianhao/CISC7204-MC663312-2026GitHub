# US Domestic Flight Delay Drivers

**CISC7204 Data Science and Data Visualization — Semester Project — Class K, Team 01**

AO KIT I (MC660004) · LI YING FANG (MC661599) · HO MAN HOU (MC661647) ·
WU PEI YE (MC661846) · LI TIAN HAO (MC663312) · SAVIDI AVRAM (MC664364)

> **Version: 1st-meeting snapshot (2026-11-03, tag `v1.0-1st-meeting`).**
> Frozen for the 5 November checkpoint — proposal, first meeting minutes and
> introductory video. Actively revised in this same folder for the final
> presentation and the 12 December submission; later commits are the continuing work.

An end-to-end, reproducible analysis of delay in U.S. domestic air travel: where
delay minutes come from, how they are inherited within the operating day, which
airport archetypes exist, which factors govern delay length and severe-delay
risk, and how a linked web tool can communicate that to a non-specialist.

> **Research questions**
>
> **RQ1** How are reported delay minutes distributed across the five BTS causes, and how stable is that
> composition across 2015–2024?
> **RQ2** How much of the delay observed in a given hour is inherited from earlier legs of the same
> aircraft, and at which airports does that cascade concentrate?
> **RQ3** Do U.S. airports fall into distinct delay-risk archetypes once size and cause mix are considered
> together, and what separates them?
> **RQ4** Given route, departure hour and month, how well can delay risk be ranked, and can a linked web
> tool let a non-specialist act on that ranking?

---

## Status

| Component | State |
|---|---|
| Proposal (PDF, 9 pp) | `docs/proposal/CISC7204-Team01-ProjectProposal.pdf` — 5 datasets D1–D5 with full links, region and domain stated in §4 |
| Pipeline (7 stages) | Implemented and runnable; run end-to-end on the full ten-year panel (`TEAM01_MODE=full`) |
| Dashboard (8 panels) | Implemented; runs locally on Dash + Plotly. Shared-view URLs (`?year=&carrier=&months=`), click-to-drill on the map, a findings band above the grid, finding-as-title panels, a "what a passenger can keep in mind" close, per-panel captions and a method/limits section |
| Tests | 53 passing (`python -m pytest tests -q`) |
| Real panel (2015–2024) | **Downloaded and analysed.** 63,079,392 rows / 61,689,698 completed flights, 20 reporting carriers, 2015–2024. Every `figures/`, `outputs/` and dashboard number now comes from `TEAM01_MODE=full` |
| Final report | Drafted — `reports/report.md` (four research questions + limitations); the PDF build and the six individual uploads remain |

The pilot numbers quoted in the proposal come from the Assignment 02 year (2024)
and are **not** reproduced from this repository's fixture. Anything produced in
`TEAM01_MODE=sample` is labelled as a layout demonstration.

---

## Quick start

```bash
python -m pip install -r requirements.txt      # or: conda env create -f environment.yml

# 1. Ten minutes, no download: build a synthetic fixture and run every stage
python run_all.py --stage smoke

# 2. Launch the dashboard against whatever the last stage produced
python dashboard/app.py                        # http://127.0.0.1:8050

# 3. The real thing (≈4 GB download, one to three hours depending on network)
python run_all.py --stage data                 # BTS monthly zips + OurAirports
python run_all.py --stage pipeline             # every analysis stage
```

`make` targets mirror these exactly (`make smoke`, `make data`, `make pipeline`,
`make dashboard`, `make test`); `run_all.py` exists because `make` is not
installed on a default Windows machine.

**If the dashboard renders as a small card in one corner of the window**, the
page is not broken: the browser is holding a site-specific zoom level for
`127.0.0.1`. Press `Ctrl` + `0` to reset it to 100%, or open
`http://localhost:8050` instead (a different origin, so it starts at 100%).
The layout is capped at 1440 px wide on purpose — two columns of charts at
that width keeps every panel near the aspect ratio the figures were designed
for; stretching it to an ultrawide monitor would flatten the curves.

---

## Repository map

```text
Team01-FlightDelay-Project/
├── README.md                     this file
├── requirements.txt              pip dependencies
├── environment.yml               conda environment for exact reproduction
├── Makefile                      one target per stage
├── run_all.py                    same stages without make
├── config/
│   └── project.yaml              single source of truth: years, seeds, paths, thresholds
├── data/
│   ├── README.md                 data dictionary, sources, licences, thresholds
│   ├── raw/                      BTS zips, OurAirports CSV (git-ignored)
│   ├── interim/                  merge and filter intermediates (git-ignored)
│   ├── processed/                flights.parquet, airport_features.parquet (git-ignored)
│   └── sample/                   synthetic fixture for tests and demos
├── src/
│   ├── team01/                   importable package
│   │   ├── config.py             settings loader and path resolution
│   │   ├── schema.py             column schema, cause taxonomy, colour constants
│   │   ├── io.py                 downloads, Parquet I/O, checksum manifest
│   │   ├── clean.py              type coercion, derived time fields, validation
│   │   ├── features.py           cascade reconstruction, airport feature matrix
│   │   ├── attribution.py        cause split, bootstrap interval, stability
│   │   ├── tail.py               percentiles, Lorenz, mean-versus-tail test
│   │   ├── cluster.py            k sweep, k-means, Ward check, stability, naming
│   │   ├── models.py             sequential R², quantile regression, risk models
│   │   ├── viz.py                figure library (one function per figure)
│   │   └── synth.py              synthetic fixture with the real schema
│   └── scripts/                  stage entry points 00–07
├── notebooks/                    seven narrative notebooks + build_notebooks.py
├── dashboard/
│   ├── app.py                    entry point, document shell (lang="en")
│   ├── layouts.py                static frame: banner, standfirst, filters, 8 panels, method
│   ├── callbacks.py              URL state, drill-down, one filter set → 8 panels + captions
│   ├── narrative.py              the three claims (with question labels), computed per filter
│   ├── captions.py               one "what this shows" sentence per panel, same-source aggregates
│   ├── data_access.py            cached frame, aggregates, filters
│   ├── panels/                   one module per panel + theme.py (shared tokens)
│   └── assets/                   style.css (frame, controls) + narrative.css
├── figures/                      01–14, 300 dpi, regenerated by stage 03–07
├── outputs/
│   ├── tables/                   CSV results quoted in the report
│   └── metrics/                  JSON summaries read by the dashboard
├── docs/
│   ├── proposal/                 submitted PDF and source DOCX
│   ├── meeting-minutes/          template + minutes 01
│   ├── video/                    five-minute script
│   ├── forum/                    the two required forum posts
│   ├── standards/                naming, code style, visualisation rules
│   └── submission-checklist.md   pre-submission gate
├── tests/                        53 tests over the data, analysis, figure, caption and takeaway layers
└── reports/                      final report (`report.md` drafted) and exported submission package
```

---

## Scope: region and domain category

| | |
|---|---|
| **Region** | United States of America — all 50 states plus the District of Columbia, including Alaska, Hawaii and four time zones. U.S. territories and international legs are excluded, so every row is a scheduled domestic passenger flight departing from and arriving at a U.S. airport. Descriptive context covers 2007–2024; the analysis panel covers 2015–2024. Results are reported at national, state (origin state) and airport (origin airport) level. |
| **Domain category** | Transportation — commercial aviation (airline operations and air-traffic performance). Unit of observation: one flight leg. Outcome: arrival delay in minutes and its heavy tail. Candidate drivers: operating carrier, both airports, the leg's position in the aircraft's day, the calendar, and surface weather. |
| **Short form** | United States and transportation / commercial aviation. |

---

## Data

Five public datasets, none requiring a login or an API key. All links re-checked
on 2 November 2026 (HTTP 200).

| ID | Dataset and publisher | Role | Coverage | Full URL |
|---|---|---|---|---|
| D1 | Reporting Carrier On-Time Performance, 1987–present — U.S. Bureau of Transportation Statistics | Primary flight-level records (110 published fields, 37 retained) | 12 monthly files per year, 2015–2024, ≈70 M legs | <https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ> |
| D2 | Airline On-Time Performance: Delay Cause — BTS | National cause-share cross-check on our per-flight attribution | Monthly aggregates, 2003–present | <https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp> |
| D3 | Integrated Surface Database (hourly) — NOAA NCEI | Hourly weather at origin airports (wind, visibility, precipitation, ceiling, temperature) | 40 busiest origin airports × 10 years | <https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database> · access: <https://www.ncei.noaa.gov/data/global-hourly/access/> |
| D4 | `airports.csv` — OurAirports (public domain) | Coordinates, state, type and scheduled-service flag for maps and the hub stratum | ≈75,000 airports worldwide, filtered to U.S. | <https://davidmegginson.github.io/ourairports-data/airports.csv> |
| D5 | Air Traffic by the Numbers / Passenger Boarding data — FAA | Validates the hub stratum derived from D4 | Annual, U.S. commercial-service airports | <https://www.faa.gov/air_traffic/by_the_numbers> · <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger> |

Direct monthly archive for D1 (substitute year and month):

```text
https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip
```

**Reporting-threshold note.** BTS publishes the five cause-minute fields only for
flights delayed by at least 15 minutes. The pilot verified this directly:
1,449,964 of 1,449,966 flights at or above the threshold carry a complete cause
breakdown (99.9999%), and none below it. Every cause statement in this project is
scoped to that attribution universe; counts, means and percentiles use all
completed flights. `src/scripts/02_validate.py` repeats the check per year.

All five sources (D1–D5) are public and none needs a login or an API key: D1, D2
and D5 are U.S. federal publications, D3 is U.S. federal data in the public
domain, D4 is a public-domain dedication. No personal data is processed. Raw
files are excluded from version control and are re-downloadable from documented
URLs; a SHA-256 manifest (`data/checksums.sha256`) records the exact files behind
any reported result.

---

## How the pipeline runs

| Stage | Script | Produces |
|---|---|---|
| 0 | `00_make_sample.py` | Synthetic fixture in the real schema (`TEAM01_MODE=sample`) |
| 1 | `01_acquire.py` | Raw zips → typed Parquet, per-file validation, checksum manifest |
| 2 | `02_validate.py` | Row counts, duplicates, missingness, threshold coverage per year |
| 3 | `03_attribution.py` | Cause split + bootstrap interval, stability by year, Figures 01–03, 07 |
| 4 | `04_tail.py` | Percentiles, Lorenz curve, mean-vs-tail test, cascade, Figures 04–06, 08 |
| 5 | `05_clusters.py` | Airport feature matrix, k sweep, clusters, Ward check, Figures 09–10 |
| 6 | `06_models.py` | Sequential R², OLS(HC1), quantile-90, risk classifiers, Figures 11–12 |
| 7 | `07_figures.py` | Figure inventory check and the contact sheet (Figure 13) |

Every stage reads `config/project.yaml` and writes to `outputs/tables`,
`outputs/metrics` and `figures`. Stages 3–6 also write a JSON metrics file that
the dashboard reads, so a number on screen and a number in the report come from
the same computation.

### What the models claim, and what they do not

- Sequential R² ranks the five observable factors. It is a description of
  explained variance, not a causal claim: BTS cause minutes are a reported
  partition assigned by the carrier.
- Quantile regression at the 90th percentile answers "what moves the tail".
- Year fixed effects and a COVID-era dummy enter every model as controls, because
  a pooled ten-year coefficient otherwise blends two different regimes.
- The risk classifiers rank flights. The full-panel ceiling (R² 0.022, AUC 0.685
  against a 6.1% base rate) says five observable factors cannot promise an
  arrival time, and the report says so in the limitations rather than in a
  footnote.
- Clustering is reported with a silhouette-selected k, a Ward cross-check, a
  cophenetic correlation and a subsample stability score. An unstable solution is
  labelled unstable instead of being presented as an airport taxonomy.

---

## Reproducibility contract

1. **One place for parameters.** Years, seeds, thresholds, sample sizes and paths
   live in `config/project.yaml`. No stage hard-codes a path.
2. **Fixed seeds.** Every sample and every stochastic model takes its seed from
   the config, so two runs produce identical numbers.
3. **Data provenance.** `data/checksums.sha256` records the SHA-256 of every raw
   file used.
4. **Tests before submission.** `python -m pytest tests -q` must pass; the suite
   protects the claims (threshold scoping, cascade arithmetic, concentration,
   matrix alignment), not just the syntax.
5. **A clean-run claim.** `python run_all.py --stage smoke` rebuilds everything
   from an empty `outputs/` in under two minutes, which is how a stale figure is
   caught before it reaches the report.

---

## Conventions

Naming, code style and visualisation rules are written down rather than assumed:
[`docs/standards/naming-conventions.md`](docs/standards/naming-conventions.md),
[`docs/standards/code-style.md`](docs/standards/code-style.md),
[`docs/standards/viz-guidelines.md`](docs/standards/viz-guidelines.md).

In short: `snake_case` everywhere, stages numbered `00`–`07`, figures numbered by
the order they appear in the report, one fixed colour per delay cause, and no
figure that shows a mean without the distribution behind it.

---

## Team and roles

| Member | Roles | Responsibility |
|---|---|---|
| AO KIT I | Team Coordinator, Project Tracker | Agendas and chairing, task board, milestones, dependency map, risk log, drives submissions |
| LI YING FANG | Project Developer (lead) | Data pipeline, notebook and repository structure, reproducibility script, dashboard engineering, leads code review |
| HO MAN HOU | Team Scribe | Minutes, decision log, scope-change log, repository folder conventions and naming |
| WU PEI YE | Team Reporter, Team Liaison | Proposal narrative, introductory video script and edit, instructor liaison, final submission package |
| LI TIAN HAO | Project Analyst, Quality Reviewer | Research question, data sources, preparation and analysis, interpretation and limitations; the quality gate |
| SAVIDI AVRAM | Project Developer | Figures, visualisations and interactive outputs (map, archetypes), ten-year scaling, weather join |

Roles rotate at the midpoint of the project.

---

## Limitations

1. **Observational, not causal.** BTS cause minutes are a reported partition.
2. **One panel, one country.** U.S. domestic only; no international legs.
3. **Weather is a planned covariate.** `features.merge_weather` is implemented and
   exercised on the fixture, but the ten-year ISD extraction is not yet in the
   pipeline, so the weather signal is the carrier-reported cause share only.
4. **Prediction is ranking.** R² and AUC values are reported, not hidden.
5. **Two regimes, controlled.** 2020–2021 stay in the panel behind a COVID dummy
   and year fixed effects, and every headline statistic is recomputed with both
   years excluded (`outputs/tables/sensitivity_excluded_years.csv`). The report
   shows the size of the shift instead of choosing one version of the average.

---

## Attribution

Coursework for CISC7204, University of Macau, 2026/2027. Data © the respective
U.S. federal agencies and OurAirports contributors. Code written by Team 01 under
the course's academic-integrity rules; third-party libraries are cited in the
proposal's reference list.
