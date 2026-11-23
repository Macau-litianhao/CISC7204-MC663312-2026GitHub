# Codebook — US Domestic Flight Delay Drivers

CISC7204 · Class K · Team 01 · product version 0.5.0 · protocol `audit-corrected-v0.5`

This codebook documents every field the project reads, every field it derives, the
population rules that decide which rows are analysable, and the known limits of each
measure. It is written so that a reader who has never seen the repository can tell
what a number means before quoting it.

---

## 1. Sources

| ID | Source | Provider | Role in the project |
|---|---|---|---|
| D1 | Reporting Carrier On-Time Performance, 1987–present (110 published fields) | U.S. Bureau of Transportation Statistics (BTS) | Primary flight-level panel, 2015-01-01 to 2024-12-31 |
| D2 | `airports.csv` | OurAirports | Coordinates, airport type, municipality for the 195 reviewed airports |
| D3 | Airport aliases and IANA time zones | Project reference files | Crosswalk from BTS codes to reference codes; local-time handling for the rotation analysis |
| D4 | NOAA ISD hourly weather | NOAA NCEI | **Planned extension only.** Not an input to any number in this report |
| D5 | BTS Air Carrier Statistics (Form 41 traffic) | BTS | **Reference check only.** Used to sanity-check carrier-level volume, not joined to the panel |

Only D1 and D2 enter the analysis. D4 and D5 appear in the proposal as planned or
supporting sources and are labelled as such wherever they are mentioned.

### Row populations

| Population | Rows | Definition |
|---|---:|---|
| Source rows | 63,079,392 | Every record delivered for 2015–2024 |
| Completed flights | 61,689,698 | `cancelled = 0` and `diverted = 0`; the analysis panel |
| Cancelled | 1,239,523 | `cancelled = 1`; no arrival delay exists |
| Diverted | 149,829 | `diverted = 1`; arrival airport differs from scheduled |
| Cause-eligible | 11,454,282 | Completed flights with at least one non-null BTS cause field, i.e. flights arriving **15 or more minutes late** |
| Cause-retained | 11,454,275 | Cause-eligible rows whose five cause minutes reconcile to the reported arrival delay |

Two reconciliation rules matter:

1. A cause-eligible row is **retained** only if `CarrierDelay + WeatherDelay + NASDelay +
   SecurityDelay + LateAircraftDelay` equals `ArrDelayMinutes`. 7 rows fail this test and
   are excluded; the residual across the whole panel is 1,314 minutes.
2. A delayed flight with **no** cause attribution stays in the panel for delay
   distribution work but contributes nothing to cause shares. Cause shares therefore
   describe *attributed minutes on delayed flights*, never all flights.

---

## 2. Flight-level fields (BTS → snake_case)

The 37 of 110 published fields the project uses. Translation happens once, in
`schema.RENAME`; no other module renames columns.

| BTS field | Project field | Type | Meaning and unit | Notes on use |
|---|---|---|---|---|
| `Year` | `year` | int | Calendar year of the scheduled flight date | Panel control; also the temporal-validation split unit |
| `Quarter` | `quarter` | int | 1–4 | Reported only; not a model factor |
| `Month` | `month` | int | 1–12 | Model factor; monthly composition figures |
| `DayofMonth` | `day` | int | 1–31 | Used to build `flight_date` |
| `DayOfWeek` | `dow` | int | 1 = Monday … 7 = Sunday | Descriptive only |
| `FlightDate` | `flight_date` | date | Scheduled local departure date | Operating-day key for clustered covariance and paired resampling |
| `Reporting_Airline` | `carrier` | category | Two-letter BTS carrier code (20 carriers) | Model factor; carrier comparison; reference level `9E` |
| `Tail_Number` | `tail_number` | string | Aircraft registration, e.g. `N12345` | Rotation reconstruction; blank on some records |
| `Origin` | `origin` | category | Three-letter origin airport code | Model factor; airport clustering; reference level `ATL` |
| `OriginCityName` | `origin_city` | string | Origin city and state as published | Search in the dashboard |
| `OriginState` | `origin_state` | category | Two-letter state or BTS territory code | State tile figure. **Includes PR/VI and other territory codes; not a verified 50-states-plus-DC subset** |
| `Dest` | `dest` | category | Three-letter destination airport code | Rotation linking, distance bands |
| `DestCityName` | `dest_city` | string | Destination city and state | Descriptive |
| `DestState` | `dest_state` | category | Destination state or territory code | Descriptive |
| `CRSDepTime` | `crs_dep_time` | hhmm | Scheduled local departure time | Source of `dep_hour` |
| `DepTime` | `dep_time` | hhmm | Actual local departure time | Descriptive; `2400` is a valid value |
| `DepDelay` | `dep_delay` | minutes | Departure delay, negative = early | Descriptive |
| `DepDelayMinutes` | `dep_delay_min` | minutes | Departure delay floored at zero | Turnaround pressure calculation |
| `DepDel15` | `dep_del15` | 0/1 | Departure 15+ minutes late | Descriptive |
| `TaxiOut` | `taxi_out` | minutes | Gate departure to wheels-off | Descriptive |
| `TaxiIn` | `taxi_in` | minutes | Wheels-on to gate arrival | Descriptive |
| `CRSArrTime` | `crs_arr_time` | hhmm | Scheduled local arrival time | Schedule reconstruction across time zones |
| `ArrTime` | `arr_time` | hhmm | Actual local arrival time | Descriptive |
| `ArrDelay` | `arr_delay` | minutes | Arrival delay, negative = early | Primary outcome; signed target of the quantile regression |
| `ArrDelayMinutes` | `arr_delay_min` | minutes | Arrival delay floored at zero | Concentration, Lorenz curve, burden totals |
| `ArrDel15` | `arr_del15` | 0/1 | Arrival 15+ minutes late | Severity threshold 1 |
| `Cancelled` | `cancelled` | 0/1 | Flight cancelled | Population filter |
| `CancellationCode` | `cancellation_code` | A/B/C/D | Carrier / weather / NAS / security | Descriptive only; cancelled rows leave the panel |
| `Diverted` | `diverted` | 0/1 | Flight diverted | Population filter |
| `CRSElapsedTime` | `crs_elapsed` | minutes | Scheduled gate-to-gate time | Time-zone-safe elapsed reference |
| `ActualElapsedTime` | `actual_elapsed` | minutes | Actual gate-to-gate time | UTC reconstruction for rotations |
| `Distance` | `distance` | miles | Great-circle route distance | Model factor; distance bands |
| `CarrierDelay` | `min_carrier` | minutes | Attributed to the carrier | Cause family "internal" |
| `WeatherDelay` | `min_weather` | minutes | Attributed to extreme weather | Cause family "system" |
| `NASDelay` | `min_nas` | minutes | Attributed to the National Airspace System | Cause family "system" |
| `SecurityDelay` | `min_security` | minutes | Attributed to security | Cause family "system" |
| `LateAircraftDelay` | `min_late_aircraft` | minutes | Attributed to a previous flight of the same aircraft | Cause family "internal"; single largest cause |

### Cause taxonomy

The five published cause minutes are grouped into two families for reporting:

| Family | Fields | Interpretation |
|---|---|---|
| Internal | `min_carrier` + `min_late_aircraft` | Attributed by the operating carrier to itself or to its own earlier flight |
| System | `min_nas` + `min_weather` + `min_security` | Attributed to airspace, weather or security |

This grouping is **descriptive**. It encodes how carriers report, not an independent
audit of controllability, and it must not be read as "airline fault" versus "not
airline fault".

---

## 3. Derived fields

| Field | Definition | Where it is built |
|---|---|---|
| `dep_hour` | `crs_dep_time` floored to the hour, 0–23, **origin local time** | `features.py` |
| `arr_delay_signed` | `arr_delay`, negative kept | `clean.py` |
| `late_15 / late_60 / late_180` | `arr_delay_min >= 15 / 60 / 180` | `tail.py` |
| `rotation` | 1 when the same `tail_number` flew an earlier segment earlier the same operating day | `rotation_pressure.py` |
| `turnaround_min` | Scheduled-to-actual gate gap between consecutive segments of one aircraft, in UTC | `rotation_pressure.py` |
| `turnaround_shortfall` | `max(0, min_turnaround − realised gap)`, with `min_turnaround = 25` minutes | `rotation_pressure.py` |
| `inherited_minutes` | Positive arrival-delay minutes on a rotation attributed to the shortfall handed over by the previous segment | `rotation_pressure.py` |
| `airport features` | Ten standardised airport-level features: mean and p90 arrival delay, 60+ share, cause-family shares, seasonal amplitude, departure volume, hub stratum | `features.py`, `airports.py` |
| `cluster` | k-means label (k = 4) on the standardised feature matrix | `cluster.py` |

### Rotation and inheritance: what the number is and is not

The rotation measure is an **assumed minimum-turnaround shortfall**, not realised
arrival delay. A 25-minute minimum turnaround is a project assumption, not a
regulatory or carrier-specific rule. `inherited_share = 29.15%` therefore answers:

> Of the positive arrival-delay minutes observed on sampled rotations, what share
> coincides with a turnaround gap shorter than 25 minutes?

It does not answer "how much delay did the previous flight cause". The ratio can,
in principle, exceed one under different assumptions. The 95% interval
[27.78%, 30.60%] is an aircraft-cluster percentile bootstrap over 1,000 draws and is
conditional on the sampled aircraft, the observed source records, the time-zone
reference and the 25-minute assumption. It is not a causal interval.

---

## 4. Sampling and model inputs

| Purpose | Sample | Rule |
|---|---|---|
| Dashboard | 400,000 completed flights | Fixed uniform sample, `seed = 20261105` |
| OLS / quantile regression | 600,000 (OLS) and 100,000 (q90) | Uniform inference sample, then explicit seeded subsamples |
| Risk classifier | 376,872 train / 23,128 test | Time-ordered split: train to 2024-06-30, test from 2024-07-01 |
| Temporal validation | Expanding window, whole test calendar year | Years 2019, 2020, 2022, 2024; training-only preprocessing; no tuning on folds |
| Rotation cascade | 256 aircraft tails of 9,487 available | Whole-aircraft histories, every record retained |

`seed = 20261105` is used wherever a sample is drawn. No figure in the report was
produced from the synthetic fixtures under `outputs/*/sample`.

---

## 5. Reference and coding conventions

- **OLS** uses reference coding with `dep_hour = 0`, `month = 1`, `carrier = 9E`,
  `origin = ATL`, `year = 2015`, `covid_era = 0`; 104 factor terms, 115 design
  columns, full-column-rank checked, operating-day clustered covariance.
- **Quantile regression** targets signed arrival delay at the 0.9 quantile; its
  coefficients are point estimates and are not interpreted as causal effects.
- **Permutation importance** is an AUC drop under repeated permutation (5 repeats).
  It is *not* SHAP and must not be labelled as such.
- **Missing values.** A missing cause field never becomes zero; a row with an
  incomplete cause block is excluded from cause shares rather than imputed.
- **Time zones.** Departure-hour summaries use origin-local scheduled hour.
  Aircraft sequences are matched in UTC, built from local schedule plus the IANA
  zone reference; 192 of 1,706,608 sampled rows lack a usable UTC anchor and are
  excluded from rotation arithmetic.

---

## 6. Known limits of the data itself

1. **Administrative, not experimental.** Every delay cause is reported by the
   carrier that operated the flight.
2. **Cause fields are conditional on lateness.** They exist only for flights
   arriving 15+ minutes late; 81.4% of completed flights have no cause block.
3. **Geography is not a clean national frame.** BTS territory codes appear in
   `origin_state`; the panel is not restricted to 50 states plus DC.
4. **The rotation sample is bounded.** 256 aircraft out of 9,487, chosen by seeded
   sample; missing adjacent legs and time-zone edge cases remain.
5. **Model ceiling is low by construction.** Pre-departure fields cannot see the
   inbound aircraft's actual delay, crew state or en-route weather.
