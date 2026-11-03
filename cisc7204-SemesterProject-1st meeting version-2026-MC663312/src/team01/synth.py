"""Synthetic fixture with the real BTS schema.

Why this exists: the real panel is a multi-gigabyte download, and a test suite
or a code review cannot wait for it. The fixture reproduces the *structure* that
the pipeline depends on - a rotating aircraft, a within-day cascade, a cause
split that only exists above the 15-minute threshold - so a smoke run exercises
every branch of the code without pretending to be evidence.

Numbers produced from the fixture are never quoted in the report. The dashboard
and the notebooks label the mode, and ``config.mode()`` returns ``sample`` while
this data is in use.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema

# A compact but realistic airport set: three large hubs, four medium, three small.
AIRPORTS: list[tuple[str, str, str, float, float, str]] = [
    ("ATL", "Atlanta, GA", "GA", 33.6407, -84.4277, "large_airport"),
    ("ORD", "Chicago, IL", "IL", 41.9742, -87.9073, "large_airport"),
    ("DFW", "Dallas/Fort Worth, TX", "TX", 32.8998, -97.0403, "large_airport"),
    ("DEN", "Denver, CO", "CO", 39.8561, -104.6737, "large_airport"),
    ("LAX", "Los Angeles, CA", "CA", 33.9416, -118.4085, "large_airport"),
    ("JFK", "New York, NY", "NY", 40.6413, -73.7781, "large_airport"),
    ("SEA", "Seattle, WA", "WA", 47.4502, -122.3088, "medium_airport"),
    ("MSP", "Minneapolis, MN", "MN", 44.8848, -93.2223, "medium_airport"),
    ("DTW", "Detroit, MI", "MI", 42.2162, -83.3554, "medium_airport"),
    ("PHX", "Phoenix, AZ", "AZ", 33.4342, -112.0116, "medium_airport"),
    ("BNA", "Nashville, TN", "TN", 36.1263, -86.6774, "medium_airport"),
    ("AUS", "Austin, TX", "TX", 30.1975, -97.6664, "medium_airport"),
    ("BOI", "Boise, ID", "ID", 43.5644, -116.2228, "small_airport"),
    ("FSD", "Sioux Falls, SD", "SD", 43.5820, -96.7419, "small_airport"),
    ("BTV", "Burlington, VT", "VT", 44.4719, -73.1533, "small_airport"),
    ("MHT", "Manchester, NH", "NH", 42.9326, -71.4357, "small_airport"),
]

CARRIERS = ["AA", "DL", "UA", "WN", "B6", "AS", "NK", "F9", "G4", "HA"]

# The fixture is written in raw BTS column names so that apply_schema - and
# therefore the rename map - is exercised by every smoke run.
_CAUSE_RAW = [{v: k for k, v in schema.RENAME.items()}[c] for c in schema.CAUSE_COLUMNS]

# Monthly multipliers: a summer peak and a December bump, as in the real data.
MONTH_EFFECT = np.array([-1.5, -1.8, -0.6, 0.4, 0.8, 2.6,
                         3.4, 3.0, 0.2, -0.4, -0.9, 2.2])


def _great_circle(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in statute miles."""
    from math import asin, cos, radians, sin, sqrt
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * asin(sqrt(h))


_COORDS = {code: (lat, lon) for code, _, _, lat, lon, _ in AIRPORTS}
_CITY = {code: city for code, city, _, _, _, _ in AIRPORTS}
_STATE = {code: state for code, _, state, _, _, _ in AIRPORTS}


def _distance(origin: str, dest: str) -> float:
    return max(_great_circle(_COORDS[origin], _COORDS[dest]), 80.0)


def make_airport_reference() -> pd.DataFrame:
    """OurAirports-compatible reference table for the fixture airports."""
    rows = [
        {
            "ident": code, "name": f"{city.split(',')[0]} International",
            "type": kind, "latitude_deg": lat, "longitude_deg": lon,
            "iso_country": "US", "iso_region": f"US-{state}",
            "municipality": city.split(",")[0], "scheduled_service": "yes",
        }
        for code, city, state, lat, lon, kind in AIRPORTS
    ]
    return pd.DataFrame(rows)


def make_flights(days: int = 120, tails: int = 200, seed: int | None = None) -> pd.DataFrame:
    """Generate a rotation-based panel in raw BTS column names.

    Each aircraft flies up to three legs a day; the next leg's departure delay
    contains the previous leg's arrival delay minus the scheduled turnaround,
    which is what makes the cascade stage testable on the fixture.
    """
    rng = np.random.default_rng(config.seed() if seed is None else seed)

    years = [2019, 2023, 2024]
    dates = []
    # At least one day per year, otherwise asking for a two-day fixture would
    # silently produce an empty table instead of a small one.
    per_year = max(days // len(years), 1)
    for year in years:
        start = pd.Timestamp(f"{year}-01-01")
        offsets = rng.choice(np.arange(0, 360, 1), size=per_year, replace=False)
        dates.extend(start + pd.to_timedelta(np.sort(offsets), unit="D"))
    dates = sorted(pd.Timestamp(d) for d in dates)

    carrier_bias = dict(zip(CARRIERS, rng.normal(0, 2.2, len(CARRIERS))))
    hub_bias = {code: rng.normal(0, 2.0) for code, *_ in AIRPORTS}
    tail_numbers = [f"N{1000 + i:04d}" for i in range(tails)]

    records: list[dict] = []

    for date in dates:
        month = date.month
        dow = date.dayofweek + 1
        for tail in tail_numbers:
            legs = int(rng.integers(1, 4))
            origin = AIRPORTS[int(rng.integers(0, len(AIRPORTS)))][0]
            carrier = CARRIERS[int(rng.integers(0, len(CARRIERS)))]
            clock = float(rng.uniform(5.5, 9.0)) * 60          # minutes after midnight

            for leg in range(legs):
                # A rotation is contained in one operating day: chaining past
                # midnight would need the flight date to roll over as well.
                if clock > 23 * 60:
                    break
                dest = AIRPORTS[int(rng.integers(0, len(AIRPORTS)))][0]
                if dest == origin:
                    dest = "ATL" if origin != "ATL" else "ORD"

                distance = _distance(origin, dest)
                elapsed = int(round(distance / 7.6 + 32))

                # BTS stores clock times as HHMM integers, not minutes. Keeping
                # the rotation arithmetic in minutes and converting only here is
                # what stops the turnaround calculation drifting by an hour.
                dep_minutes = int(round(clock))
                hour = dep_minutes // 60
                crs_dep = hour * 100 + dep_minutes % 60
                arr_minutes = (dep_minutes + elapsed) % (24 * 60)
                crs_arr = (arr_minutes // 60) * 100 + arr_minutes % 60

                # Within-day cycle: delay accrues through the day.
                hour_effect = 0.0 if hour < 7 else 0.42 * (hour - 7)
                seasonal = MONTH_EFFECT[month - 1]
                # Two-component delay distribution, calibrated to the real
                # panel's shape: most flights land a few minutes early, a fifth
                # carry a long tail. A single symmetric noise term would give a
                # median above zero and no 60-minute outages to model.
                if rng.random() < 0.80:
                    noise = float(rng.normal(-8.0, 7.0))
                else:
                    noise = float(rng.exponential(55.0))

                inherited = 0.0
                if leg > 0:
                    inherited = max(0.0, prev_delay - max(prev_turn - 25, 0))

                dep_delay = (hour_effect + seasonal + carrier_bias[carrier]
                             + hub_bias[origin] + inherited + noise)
                dep_delay = float(np.clip(dep_delay, -28, 900))

                # Cancellations and diversions are rare but present, because the
                # pipeline filters them and the filter has to be exercised.
                cancelled = int(rng.random() < 0.018)
                diverted = int(0 < rng.random() < 0.0025)

                arr_delay = float(np.clip(dep_delay + rng.normal(0, 6), -45, 1200))

                record = {
                    "Year": date.year,
                    "Quarter": (month - 1) // 3 + 1,
                    "Month": month,
                    "DayofMonth": date.day,
                    "DayOfWeek": dow,
                    "FlightDate": date.strftime("%Y-%m-%d"),
                    "Reporting_Airline": carrier,
                    "Tail_Number": tail,
                    "Origin": origin,
                    "OriginCityName": _CITY[origin],
                    "OriginState": _STATE[origin],
                    "Dest": dest,
                    "DestCityName": _CITY[dest],
                    "DestState": _STATE[dest],
                    "CRSDepTime": crs_dep,
                    "DepTime": np.nan if cancelled else float(crs_dep + dep_delay),
                    "DepDelay": np.nan if cancelled else dep_delay,
                    "DepDelayMinutes": np.nan if cancelled else max(dep_delay, 0.0),
                    "DepDel15": np.nan if cancelled else float(dep_delay >= 15),
                    "TaxiOut": np.nan if cancelled else float(rng.uniform(10, 35)),
                    "TaxiIn": np.nan if cancelled else float(rng.uniform(4, 15)),
                    "CRSArrTime": crs_arr,
                    "ArrTime": np.nan if cancelled else float(crs_arr + arr_delay),
                    "ArrDelay": np.nan if (cancelled or diverted) else arr_delay,
                    "ArrDelayMinutes": np.nan if (cancelled or diverted) else max(arr_delay, 0.0),
                    "ArrDel15": np.nan if (cancelled or diverted) else float(arr_delay >= 15),
                    "Cancelled": float(cancelled),
                    "CancellationCode": "A" if cancelled else np.nan,
                    "Diverted": float(diverted),
                    "CRSElapsedTime": float(elapsed),
                    "ActualElapsedTime": np.nan if cancelled else float(elapsed + rng.normal(0, 3)),
                    "Distance": float(distance),
                }

                # Cause minutes exist only for flights at or above the threshold,
                # mirroring the BTS reporting rule exactly.
                if not cancelled and not diverted and arr_delay >= 15:
                    weights = rng.dirichlet([3.2, 2.6, 1.8, 1.1, 0.12])
                    if inherited > 5:
                        weights[1] += 0.22
                        weights = weights / weights.sum()
                    minutes = weights * arr_delay
                    for column, value in zip(_CAUSE_RAW, minutes):
                        record[column] = float(value)
                else:
                    for column in _CAUSE_RAW:
                        record[column] = np.nan

                records.append(record)

                prev_delay = arr_delay
                prev_turn = float(rng.uniform(40, 95))
                clock = dep_minutes + max(prev_turn, 30) + elapsed
                origin = dest

    frame = pd.DataFrame.from_records(records)
    print(f"[synth] generated {len(frame):,} synthetic legs over {len(dates)} days")
    return frame


def make_panel(days: int = 120, tails: int = 200,
               seed: int | None = None) -> pd.DataFrame:
    """Fixture in the project schema (raw names + apply_schema already applied)."""
    from .clean import apply_schema
    return apply_schema(make_flights(days=days, tails=tails, seed=seed))


def write_sample(path=None, seed: int | None = None) -> str:
    """Build the fixture and write it to data/sample/flights_sample.parquet."""
    target = path or config.ROOT / str(config.get("files.flights_sample_parquet"))
    target = config.ensure_parent(target)
    panel = make_panel(seed=seed)
    panel.to_parquet(target, index=False)
    print(f"[synth] wrote {len(panel):,} rows -> {target}")
    return str(target)
