# US Domestic Flight Delay Drivers

**CISC7204 Data Science and Data Visualisation — Class K, Team 01**

**Panel.** Ten years of US domestic flights, January 2015 through December 2024,
from the Bureau of Transportation Statistics *Reporting Carrier On-Time
Performance* tables: **63,079,392 rows**, of which **61,689,698 completed
flights** (cancelled 1,239,523, diverted 149,829), across **20 reporting
carriers**. Every number below is read from `outputs/metrics/` and
`outputs/tables/`; the matching figure is named in each section.

---

## 1. Where do delay minutes come from, and is the mix stable?

BTS charges every delay minute of a flight that arrives at least 15 minutes late
to exactly one of five causes. Grouped into what the airline itself controls
(*carrier* plus *late aircraft*) versus what the system controls (*National
Aviation System*, *weather*, *security*), the split over the whole panel is:

- **73.3%** of attributed delay minutes are **airline-controlled**, against
  **26.7%** system-controlled. A 400-replication, day-clustered bootstrap gives a
  95% interval of **[73.0%, 73.6%]**, so the headline is precise, not a sampling
  artefact (`attribution.json`).
- **Late aircraft alone is the single largest cause at 38.8%** — larger than all
  three system causes combined. This is the project's central fact, and it
  motivates Research Question 2 (`figures/01_cause_waffle`, `03_carrier_bars`).

The mix is **stable but not constant**. The airline-controlled share runs from
**69.7% (2018) to 77.4% (2022)** — a 7.7-point swing, mostly the 2021–2022
post-recovery years, and 2020 is the one year where *late aircraft* collapses
(29.2% against a 38–40% norm) because the COVID schedule cuts cascades even
while weather and airspace keep their share. One year therefore cannot speak for
ten; the printed figure pins its axis to 0–100% so the swing is visible rather
than exaggerated (`attribution.json` → `stability`, `figures/02_monthly_composition`).

## 2. How much delay is inherited within the day?

A flight is a *rotation* when its tail number flew an earlier segment the same
day; the delay that segment handed on is *inherited* delay.

- **6.0% of flights** are second-or-later segments (180,464 rotations).
- Within those, **17.1% of positive delay minutes are inherited** from the
  earlier segment (`tail.json` → `cascade`, `figures/08_cascade_hour`).

The inherited share climbs through the operating day as the first wave's
disruptions propagate into the afternoon and evening banks — the same hours
where the hour-of-day risk in Research Question 4 peaks. Inherited delay is
therefore concentrated in the same flights the model can partly see coming.

## 3. Do airports fall into distinct archetypes?

k-means on the standardised airport feature matrix (delay severity, cause mix,
seasonality, volume), chosen k = 5 by the highest silhouette score with every
cluster meeting a minimum size (`clusters.json` → `sweep`). The 195 airports
split into five groups (`figures/09_silhouette`, `10_cluster_scatter`):

| Cluster | Archetype | Mean delay | P90 delay | 60+ min share |
|---|---|---|---|---|
| C4 | Mid-size, cascade-dominated (strong seasonality) | 12.4 | 61.2 | 10.3% |
| C2 | Major hub, mixed-cause | 5.7 | 40.4 | 6.8% |
| C1 | Mid-size, weather-exposed | 5.5 | 35.1 | 6.6% |
| C3 | Mid-size, airspace-constrained | 3.3 | 32.4 | 5.9% |
| C0 | Mid-size, cascade-dominated (airline-controlled) | 2.2 | 25.7 | 4.5% |

The groups are **descriptive, not a typology**: a 10-draw bootstrap stability
check returns **ARI 0.69** (min 0.46), below the 0.70 bar, so the partition is
labelled *unstable — report with caution*. The archetypes are read as regions of
feature space, not as classes an airport belongs to.

## 4. How well can delay risk be ranked, and can a reader act on it?

Two questions sit behind this one: *what drives the average*, and *can we rank
flights before departure*.

**What drives the average.** A panel OLS with year and COVID-era controls and
108 factor terms reaches **R² = 0.0218** on a 600,000-flight sample. Sequential
R² attributes 43.8% of that small signal to **departure hour**, 18.4% to month,
and 16.1% to carrier; distance is negligible (`models.json` → `ranking`,
`figures/11_importance`). Excluding 2020–2021 moves the mean only +4.54 → +5.52
minutes and leaves R² at 0.02, so the pandemic is a level shift, not the source
of the model's ceiling.

**Can we rank flights.** A time-ordered holdout (train to 2024-06-30, test from
2024-07-01, base rate 6.1% of flights arriving 60+ minutes late) gives logistic
regression **ROC AUC 0.685** and gradient boosting **0.691**
(`models.json` → `risk`, `figures/12_hour_response`). Against a coin flip's 0.50
this is real signal, but a PR-AUC of ~0.14 says the model cannot separate the
rare bad flight from the crowd well enough to act on. The honest conclusion is a
**negative result**: observable pre-departure fields rank delay risk only
weakly, and the strongest factor — hour of day — is something a schedule already
knows, not something a model discovers.

## 5. Limitations

Four limits shape how each result should be read, and each is independent of the
others:

1. **Observational, not causal.** The panel is administrative records; the
   *carrier* vs *late aircraft* split is reported by airlines, not measured, and
   the internal/system grouping inherits BTS's attribution rather than an
   independent audit.
2. **Cause minutes are a subset.** The five cause fields exist only for flights
   arriving at least 15 minutes late, so every cause share describes *delayed*
   flights, not all flights.
3. **The clustering is unstable.** ARI 0.69 (against a 0.70 bar) means the
   five-group partition should not be quoted as a discovered structure.
4. **The model's ceiling is low.** R² ≈ 0.02 for the mean and PR-AUC ≈ 0.14 for
   severe delay are reported as they are, not softened.

## Summary

The minutes are **airline-controlled (73.3%)**, the single largest cause is
**late aircraft (38.8%)**, and a measurable part of that is **inherited within
the day (17.1% of rotation minutes)**. The delay is **concentrated** — the worst
1% of flights carry 25% of all positive delay minutes (Gini 0.876) — which is
why the **mean (+4.5 min) and the median (−6.0 min) tell different stories**.
Airports sort into five useful archetypes, but not a stable typology. And the
honest answer to "can we predict it?" is **not well enough to act on**: the best
model reaches AUC 0.69 against a 6.1% base rate, and its strongest driver,
departure hour, is already visible on any timetable.
