# CISC7204 Data Visualization – Coursework Portfolio

## Overview

This repository showcases my coursework outcomes for **CISC7204 Data Visualization**. It provides the Jupyter Notebook documents and datasets used to complete the assignments, together with the resulting visualisations and supporting materials, and closes with the team semester project.

**Student:** Li Tianhao  
**Student ID:** MC663312  
**Course:** CISC7204 Data Visualization  
**Academic Year:** 2026  
**Institution:** University of Macau

## Repository Contents

| Folder | Assignment | Contents |
|---|---|---|
| [`cisc7204-Assgn01-2026-MC663312/`](cisc7204-Assgn01-2026-MC663312/) | Assignment 1 | Module 01–06 lab notebooks, assignment datasets, and the preliminary project proposal (stroke paradox analysis). |
| [`cisc7204-Assgn02-2026-MC663312/`](cisc7204-Assgn02-2026-MC663312/) | Assignment 2 | Module 01–05 lab notebooks and their screen shots, the Dash project spaces, and the revised pair project proposal (Pair 14) together with the BTS flight-delay analysis behind it. |
| [`cisc7204-SemesterProject-2026-MC663312/`](cisc7204-SemesterProject-2026-MC663312/) | Semester project (Class K, Team 01) | Ten years of US domestic flights (61,689,698 completed): delay attribution, within-day cascade, airport archetypes, gradient-boosted prediction, a linked eight-panel Dash dashboard, and the submitted proposal, minutes and five-minute video. |

## Assignment 2 structure

```
cisc7204-Assgn02-2026-MC663312/
├── Module01/ … Module05/        lab notebooks (.ipynb), Dash project sources,
│                                and Screen Shots/ for each lab
├── CISC7204-Assgn02-Project Proposal/
│   ├── CISC7204-Assgn02-Pair14-RevisedProjectProposal.docx
│   └── Analysis/                notebooks, figures and Dash app behind the proposal
├── .gitignore
└── _README_工作空间说明.md
```

## Semester project structure

```
cisc7204-SemesterProject-2026-MC663312/
├── src/team01/                  analysis package: attribution, cascade, clustering,
│                                models, visualisation, schema and IO
├── src/scripts/                 numbered pipeline stages 01–07; one command
│                                regenerates every figure and metric
├── dashboard/                   eight-panel linked Dash application (year / carrier /
│                                month filters recompute every panel)
├── tests/                       53 tests, written as claims rather than syntax checks
├── notebooks/                   exploration notebooks with stored outputs
├── outputs/                     the .json metrics and .csv tables the report quotes
├── figures/                     14 delivered figures
├── docs/
│   ├── proposal/                submitted proposal (PDF, 10 pages, 15-page limit)
│   ├── meeting-minutes/         minutes 01 against the course template (12 sections)
│   ├── audit/                   reproducible audits, dashboard review, tutor review
│   ├── standards/               the coding and visualisation rules the work follows
│   └── video/                   five-minute project video, script, production plan and deck
├── data/                        only checksums.sha256 and README.md are committed;
│                                `make data` and `make sample` rebuild the rest
├── Makefile                     setup / sample / data / pipeline / figures / dashboard / test
└── .gitignore
```

Raw BTS flight data (6.2 GB of raw and processed Parquet) is **not** included in
this repository; `.gitignore` excludes it. `data/checksums.sha256` records exactly
which files the reported numbers were built from, and the analysis notebooks
document the download and preparation steps instead. Nothing under `data/` is
committed, because both the real panel and the synthetic fixture are one command
away.

## Reproducing the semester project

```bash
pip install -r cisc7204-SemesterProject-2026-MC663312/requirements.txt
cd cisc7204-SemesterProject-2026-MC663312

make smoke       # whole pipeline on a synthetic fixture: seconds, no download
make test        # 53 tests
make dashboard   # http://127.0.0.1:8050, served from the fixture

make data        # optional: the real ten-year panel (~6 GB, needs network)
make pipeline    # then every analysis stage on the real panel
make figures     # and all 14 figures
```

`make smoke` writes `data/sample/flights_sample.parquet` through
`src/scripts/00_make_sample.py`. That fixture is **synthetic** — it exists so the
pipeline, the dashboard and the tests can run before a download, and its numbers
must never be quoted as results. Everything in `outputs/` and `figures/` was
computed on the real ten-year panel.

## Tools used

Python, pandas, NumPy, Matplotlib, Seaborn, Folium, Plotly, Dash, scikit-learn,
SciPy, Jupyter Notebook, pytest, edge-tts and ffmpeg (for the project video).
