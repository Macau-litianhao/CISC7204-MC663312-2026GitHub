# Data dictionary

Everything downstream of `src/team01/clean.py` speaks the column names below.
The BTS originals are kept in one place, `src/team01/schema.py::RENAME`, so a
reader can always trace a column back to the published field.

---

## 1. What is in this directory

| Path | Content | Committed |
|---|---|---|
| `raw/flights/` | BTS monthly archives, `On_Time_<year>_<month>.zip` | No (re-downloadable) |
| `raw/weather/` | NOAA ISD hourly observations per station | No |
| `raw/reference/` | `airports.csv` from OurAirports | No (small, re-downloadable) |
| `interim/` | Merge and filter intermediates | No |
| `processed/flights.parquet` | Typed panel, one row per reported leg | No |
| `processed/weather_hourly.parquet` | Hourly weather keyed by station and hour | No |
| `processed/airport_features.parquet` | Airport feature matrix for clustering | No |
| `sample/flights_sample.parquet` | Synthetic fixture in the same schema | No |
| `checksums.sha256` | SHA-256 of every raw file used | Yes |

Data is excluded from version control because it is hundreds of megabytes and
fully reproducible from the URLs below. The checksum manifest is what preserves
the claim that a reported number came from a specific file.

---

## 2. Sources

| Source | Publisher | Licence | Access |
|---|---|---|---|
| Reporting Carrier On-Time Performance | U.S. Bureau of Transportation Statistics | U.S. federal data, redistributable | `https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip` |
| Airline On-Time Performance: Delay Cause | BTS | U.S. federal data | `https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp` |
| Integrated Surface Database (hourly) | NOAA NCEI | U.S. federal data, public domain | `https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database` |
| `airports.csv` | OurAirports | Public domain dedication | `https://davidmegginson.github.io/ourairports-data/airports.csv` |

No personal data is processed. No ethics approval is required for public
aggregate operational data.

---

## 3. Flight table columns

37 of the 110 published BTS fields are retained. Types are chosen for a
seventy-million-row table: `float32` for minutes, `category` for identifiers,
`int8`/`int16` for calendar fields.

### Identity and time

| Column | Type | BTS field | Notes |
|---|---|---|---|
| `year` | int16 | `Year` | 2015–2024 |
| `quarter` | int8 | `Quarter` | 1–4 |
| `month` | int8 | `Month` | 1–12 |
| `day` | int8 | `DayofMonth` | 1–31 |
| `dow` | int8 | `DayOfWeek` | 1 = Monday |
| `flight_date` | datetime64 | `FlightDate` | Local scheduled date |
| `carrier` | category | `Reporting_Airline` | Two-letter IATA code |
| `tail_number` | category | `Tail_Number` | Aircraft registration; the key to the cascade |
| `origin`, `dest` | category | `Origin`, `Dest` | Three-letter airport codes |
| `origin_city`, `dest_city` | category | `OriginCityName`, `DestCityName` | |
| `origin_state`, `dest_state` | category | `OriginState`, `DestState` | Two-letter state |
| `crs_dep_time`, `crs_arr_time` | int32 | `CRSDepTime`, `CRSArrTime` | **HHMM integer**, 2400 = midnight |
| `dep_hour` | int8 | derived | `(crs_dep_time // 100) % 24`, so 2400 → 0 |
| `dep_minute` | int8 | derived | `crs_dep_time % 100` |
| `sched_dep_dt`, `sched_arr_dt` | datetime64 | derived | Scheduled departure and arrival |
| `actual_arr_dt` | datetime64 | derived | `sched_arr_dt + arr_delay`; NaT if not completed |

### Delay measures

| Column | Type | BTS field | Notes |
|---|---|---|---|
| `dep_delay`, `arr_delay` | float32 | `DepDelay`, `ArrDelay` | Minutes; negative = early |
| `dep_delay_min`, `arr_delay_min` | float32 | `DepDelayMinutes`, `ArrDelayMinutes` | Negative values clipped to 0 |
| `dep_del15`, `arr_del15` | float32 | `DepDel15`, `ArrDel15` | 1 = at least 15 minutes late |
| `taxi_out`, `taxi_in` | float32 | `TaxiOut`, `TaxiIn` | Minutes on the ground |
| `crs_elapsed`, `actual_elapsed` | float32 | `CRSElapsedTime`, `ActualElapsedTime` | Block minutes |
| `distance` | float32 | `Distance` | Statute miles, great-circle |

### Status

| Column | Type | BTS field | Notes |
|---|---|---|---|
| `cancelled` | float32 | `Cancelled` | 1 = cancelled |
| `cancellation_code` | category | `CancellationCode` | A carrier, B weather, C NAS, D security |
| `diverted` | float32 | `Diverted` | 1 = diverted |

### Delay causes

Attributed minutes, one cause per minute, published **only** for arrival delays
of at least 15 minutes.

| Column | Type | BTS field | Family |
|---|---|---|---|
| `min_carrier` | float32 | `CarrierDelay` | Internal |
| `min_late_aircraft` | float32 | `LateAircraftDelay` | Internal |
| `min_nas` | float32 | `NASDelay` | System |
| `min_weather` | float32 | `WeatherDelay` | System |
| `min_security` | float32 | `SecurityDelay` | System |

"Internal" means the operating carrier can control the minutes; "system" means
they were imposed by weather, air-traffic control or security. The 75/25 split in
the proposal is the sum of these two families.

---

## 4. Row populations

Three different denominators appear in the report. Confusing them is the classic
error in this dataset, so each has a named function.

| Population | Definition | Function | Used for |
|---|---|---|---|
| Reported | Every row in the BTS files | — | Coverage and cancellation counts |
| Completed | `cancelled = 0`, `diverted = 0`, `arr_delay` not null | `clean.completed` | Means, medians, percentiles, severe shares |
| Attribution universe | Completed **and** `arr_delay >= 15` | `clean.attribution_universe` | Every cause-share statement |

---

## 5. Airports reference

`raw/reference/airports.csv` keeps `ident`, `name`, `type`, coordinates,
`iso_country`, `iso_region`, `municipality` and `scheduled_service`, restricted to
US airports of type `large_airport`, `medium_airport` or `small_airport`.
`type` maps to the ordinal `hub_stratum` used in clustering (3 / 2 / 1).

---

## 6. Airport feature matrix

`processed/airport_features.parquet`, one row per origin airport with at least
`cluster.min_departures` departures.

| Feature | Definition |
|---|---|
| `n_dep` | Completed departures in the panel |
| `mean_arr_delay` | Mean arrival delay (minutes) |
| `p90_arr_delay` | Ninetieth percentile arrival delay |
| `share_delayed_60` | Share of arrivals at least 60 minutes late |
| `share_internal` | Internal cause minutes ÷ total attributed minutes |
| `share_late_aircraft` | Late-aircraft minutes ÷ total attributed minutes |
| `share_nas` | NAS minutes ÷ total attributed minutes |
| `share_weather` | Weather minutes ÷ total attributed minutes |
| `year` | Calendar year (panel control, fitted but not tabulated) |
| `covid_era` | 1 for 2020-03-01 to 2021-12-31, else 0 (panel control) |
| `seasonal_amplitude` | Worst monthly mean minus best monthly mean |
| `hub_stratum` | 3 = large, 2 = medium, 1 = small airport |

`n_dep` is log10-transformed before standardisation; without it, distance between
a 20k and a 40k airport would dominate the distance between 200k and 220k.

---

## 7. Known data characteristics

1. **15-minute threshold.** Cause fields are null below 15 minutes of arrival
   delay. Verified per year by stage 02; coverage is 0% below and ~100% above.
2. **Cancellations have no delay.** A cancelled flight has no arrival delay and no
   cause minutes; it is excluded from `completed` and counted separately.
3. **Diversions.** A diverted flight has no arrival delay at the scheduled
   destination; also excluded from `completed`.
4. **2400 as midnight.** BTS uses 2400 rather than 0000; naive integer division
   would create hour 24 and break any ordered hour axis.
5. **2020-2021.** Retained but controlled: `features.add_panel_controls` adds a
   `year` fixed effect and a `covid_era` dummy (2020-03-01 to 2021-12-31), and
   `models.sensitivity_exclude_years` recomputes every headline statistic with
   the years in `config/project.yaml::panel.sensitivity_exclude_years` removed.
   The comparison is written to `outputs/tables/sensitivity_excluded_years.csv`.
6. **Tail numbers are reused across days.** A rotation is only counted when the
   aircraft continues from the airport it landed at and the scheduled ground time
   is between 15 minutes and 24 hours (`features.leg_sequence`).

---

## 8. Synthetic fixture

`sample/flights_sample.parquet` is generated by `src/team01/synth.py`. It has the
real schema, real column types, a real rotation structure and a cause split that
respects the threshold, so it exercises every branch of the pipeline in seconds.

It is **not** evidence. It is calibrated to look plausible (mean delay ≈ +10 min,
median ≈ −2 min, ~8% delayed 60+ minutes) but its patterns come from the
generator, not from U.S. aviation. `config.mode()` returns `sample` while it is in
use, and the dashboard prints a banner saying so.



## Review corrections (6 November 2026)

Airport joins use explicit IATA/FAA codes, with documented historical aliases in
`config/airport_aliases.csv`. Physical airport type is a proxy, not FAA hub class.
`outputs/tables/airport_metadata_audit.csv` records the reviewed 195-airport match.

Rotation-pressure analysis samples whole aircraft histories and reconstructs UTC
from origin-local scheduled departure, IANA airport timezone and elapsed minutes.
Ambiguous/nonexistent DST times are excluded rather than guessed. Missing source
legs and historical timezone/airport changes remain limitations. Pressure estimates
are not a causal allocation of arrival delay; the old 17.1% estimate is superseded.

Timezone reference: https://github.com/mborsetti/airportsdata (MIT licence), raw
https://raw.githubusercontent.com/mborsetti/airportsdata/main/airportsdata/airports.csv .
Retrieved 2026-11-06; the source SHA-256 is in checksums.sha256. The reference does
not provide a complete history of closed airports, so unknown mappings are excluded.

Model risk results are a uniform 400,000-flight completed sample with a temporal
holdout, training-only category mappings, baseline error and descriptive calibration.
See `outputs/metrics/risk_evaluation.json`; training and test prevalence are distinct.
No weather observations are inputs to these models. No causal responsibility is
inferred from the five reported delay categories.

## Source-wide reference coverage audit

All 391 airport codes appearing as origin or destination in the original records
were checked. Current active-airport metadata matches 389, and the timezone
reference covers 390. ISN and TKI lack an active-airport reference; ISN lacks a
current timezone mapping. These are explicit reference gaps, not missing values
replaced with fabricated coordinates or zones. The reviewed 195-airport clustering
population is fully matched. See `airport_reference_coverage.csv` and its metrics JSON.
