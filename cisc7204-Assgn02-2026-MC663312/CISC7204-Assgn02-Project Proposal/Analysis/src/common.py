"""
common.py - Shared paths, constants and plotting helpers for the
CISC7204 Assignment 02 pair project (Class K, Pair 14).

Keeping these in one module means every notebook and the Dash app read the
same file, the same colour codes and the same category order, so figures in
the proposal are consistent with the dashboard.

Author: LI Tianhao (mc663312), LI Yingfang (mc661599)
"""

from pathlib import Path

import matplotlib as mpl
import pandas as pd

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FIG_DIR = BASE_DIR / "figures"
OUT_DIR = BASE_DIR / "outputs"

for _d in (RAW_DIR, PROCESSED_DIR, FIG_DIR, OUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

FLIGHTS_PARQUET = PROCESSED_DIR / "flights_2024.parquet"
AIRPORTS_CSV = RAW_DIR / "airports.csv"

# --------------------------------------------------------------------------
# Data source
# --------------------------------------------------------------------------
# Bureau of Transportation Statistics (BTS), Reporting Carrier On-Time
# Performance. One zip per month, each holding one CSV (110 fields).
BTS_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_{month}.zip"
)
YEAR = 2024

# OurAirports public domain airport reference (coordinates + names).
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# --------------------------------------------------------------------------
# Columns
# --------------------------------------------------------------------------
# Only 39 of the 110 available fields are needed. Everything dropped is either
# a diversion detail (Div1..Div5*) or an identifier we never visualise.
USECOLS = [
    "Year", "Month", "DayofMonth", "DayOfWeek", "FlightDate",
    "Reporting_Airline", "Origin", "OriginCityName", "OriginState",
    "Dest", "DestCityName", "DestState",
    "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15",
    "TaxiOut", "TaxiIn",
    "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15",
    "Cancelled", "CancellationCode", "Diverted",
    "CRSElapsedTime", "ActualElapsedTime", "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay",
    "LateAircraftDelay",
]

# float32 for every measure: delay minutes never need float64 precision and
# this halves memory on a 7-million-row table.
DTYPES = {
    "Year": "int16", "Month": "int8", "DayofMonth": "int8", "DayOfWeek": "int8",
    "Reporting_Airline": "category", "Origin": "category",
    "OriginCityName": "category", "OriginState": "category",
    "Dest": "category", "DestCityName": "category", "DestState": "category",
    "CRSDepTime": "int32", "DepTime": "float32",
    "DepDelay": "float32", "DepDelayMinutes": "float32", "DepDel15": "float32",
    "TaxiOut": "float32", "TaxiIn": "float32",
    "CRSArrTime": "int32", "ArrTime": "float32",
    "ArrDelay": "float32", "ArrDelayMinutes": "float32", "ArrDel15": "float32",
    "Cancelled": "float32", "CancellationCode": "category", "Diverted": "float32",
    "CRSElapsedTime": "float32", "ActualElapsedTime": "float32",
    "Distance": "float32",
    "CarrierDelay": "float32", "WeatherDelay": "float32",
    "NASDelay": "float32", "SecurityDelay": "float32",
    "LateAircraftDelay": "float32",
}

# --------------------------------------------------------------------------
# Delay cause taxonomy  (this is the analytical backbone of the project)
# --------------------------------------------------------------------------
# BTS attributes every minute of arrival delay to exactly one of five causes.
# We group them into two families, which is what the research question asks:
#   INTERNAL = minutes the airline itself can control
#   SYSTEM   = minutes imposed by weather, air-traffic control or security
CAUSE_COLS = ["CarrierDelay", "LateAircraftDelay", "NASDelay",
              "WeatherDelay", "SecurityDelay"]

# Short aliases used as column names after a groupby().sum(), because
# "LateAircraftDelay" repeated in six aggregate tables gets unreadable.
MINS = {
    "CarrierDelay": "min_carrier",
    "LateAircraftDelay": "min_late_ac",
    "NASDelay": "min_nas",
    "WeatherDelay": "min_weather",
    "SecurityDelay": "min_security",
}

# BTS publishes the five delay-cause minutes only for flights whose arrival
# delay reaches this threshold. Verified in notebook 01: coverage is exactly
# 0% below 15 minutes and 1,449,964/1,449,966 (99.9999%) at or above it, so
# every attribution figure in this project is defined on the >= 15 minute
# universe.
ATTRIBUTION_THRESHOLD_MIN = 15

CAUSE_LABELS = {
    "CarrierDelay": "Carrier (internal)",
    "LateAircraftDelay": "Late aircraft (internal)",
    "NASDelay": "Air traffic / NAS (system)",
    "WeatherDelay": "Extreme weather (system)",
    "SecurityDelay": "Security (system)",
}

CAUSE_FAMILY = {
    "CarrierDelay": "Internal",
    "LateAircraftDelay": "Internal",
    "NASDelay": "System",
    "WeatherDelay": "System",
    "SecurityDelay": "System",
}

# Blue family = airline-controllable, warm/sage = externally imposed.
# Chosen so the two families stay distinguishable in greyscale print as well.
CAUSE_COLORS = {
    "CarrierDelay": "#2A6F97",
    "LateAircraftDelay": "#61A5C2",
    "NASDelay": "#E9C46A",
    "WeatherDelay": "#8AB17D",
    "SecurityDelay": "#B5838D",
}
FAMILY_COLORS = {"Internal": "#2A6F97", "System": "#E9A23B"}
ACCENT = "#C1442E"      # used to highlight the "bad news" series
MUTED = "#9AA5B1"
INK = "#22303C"

# --------------------------------------------------------------------------
# Plot defaults
# --------------------------------------------------------------------------
mpl.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.edgecolor": "#4A5568",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": "#4A5568",
    "ytick.color": "#4A5568",
    "legend.frameon": False,
})


def save_fig(fig, name: str, tight: bool = True) -> Path:
    """Save a figure to figures/ at 300 dpi and return the path."""
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight" if tight else None,
                facecolor="white")
    print(f"[saved] {path}")
    return path


def load_flights(columns=None) -> pd.DataFrame:
    """Load the cleaned 2024 flight table (built by src/01_ingest.py)."""
    if not FLIGHTS_PARQUET.exists():
        raise FileNotFoundError(
            f"{FLIGHTS_PARQUET} not found - run src/01_ingest.py first."
        )
    return pd.read_parquet(FLIGHTS_PARQUET, columns=columns)


def load_airports() -> pd.DataFrame:
    """Airport coordinates from OurAirports, restricted to US airports."""
    ap = pd.read_csv(AIRPORTS_CSV, usecols=[
        "ident", "name", "type", "latitude_deg", "longitude_deg",
        "iso_country", "iso_region", "municipality",
    ])
    ap = ap[(ap["iso_country"] == "US")
            & (ap["type"].isin(["large_airport", "medium_airport",
                                "small_airport"]))]
    return ap
