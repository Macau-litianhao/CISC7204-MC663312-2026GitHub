"""Column schema, cause taxonomy and colour constants.

The rest of the project speaks snake_case; BTS ships 110 CamelCase fields. The
translation happens exactly once, in ``RENAME``, and ``clean.apply_schema`` is
the only function allowed to use it. Keeping the raw names in one dict means a
typo in a column name fails at import time rather than three stages later.

Sources
-------
* BTS Reporting Carrier On-Time Performance (1987-present), 110 fields.
* OurAirports ``airports.csv`` for coordinates and airport type.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Fields requested from the BTS files
# --------------------------------------------------------------------------
# 37 of the 110 published fields are used. The dropped ones are diversion
# detail blocks (Div1..Div5*) and identifiers that are never visualised.
USECOLS: list[str] = [
    "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek", "FlightDate",
    "Reporting_Airline", "Tail_Number",
    "Origin", "OriginCityName", "OriginState",
    "Dest", "DestCityName", "DestState",
    "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15",
    "TaxiOut", "TaxiIn",
    "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15",
    "Cancelled", "CancellationCode", "Diverted",
    "CRSElapsedTime", "ActualElapsedTime", "Distance",
    "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay",
    "LateAircraftDelay",
]

RENAME: dict[str, str] = {
    "Year": "year",
    "Quarter": "quarter",
    "Month": "month",
    "DayofMonth": "day",
    "DayOfWeek": "dow",
    "FlightDate": "flight_date",
    "Reporting_Airline": "carrier",
    "Tail_Number": "tail_number",
    "Origin": "origin",
    "OriginCityName": "origin_city",
    "OriginState": "origin_state",
    "Dest": "dest",
    "DestCityName": "dest_city",
    "DestState": "dest_state",
    "CRSDepTime": "crs_dep_time",
    "DepTime": "dep_time",
    "DepDelay": "dep_delay",
    "DepDelayMinutes": "dep_delay_min",
    "DepDel15": "dep_del15",
    "TaxiOut": "taxi_out",
    "TaxiIn": "taxi_in",
    "CRSArrTime": "crs_arr_time",
    "ArrTime": "arr_time",
    "ArrDelay": "arr_delay",
    "ArrDelayMinutes": "arr_delay_min",
    "ArrDel15": "arr_del15",
    "Cancelled": "cancelled",
    "CancellationCode": "cancellation_code",
    "Diverted": "diverted",
    "CRSElapsedTime": "crs_elapsed",
    "ActualElapsedTime": "actual_elapsed",
    "Distance": "distance",
    "CarrierDelay": "min_carrier",
    "WeatherDelay": "min_weather",
    "NASDelay": "min_nas",
    "SecurityDelay": "min_security",
    "LateAircraftDelay": "min_late_aircraft",
}

# float32 for every measure: delay minutes never need float64 precision and the
# narrower type halves memory on a seventy-million-row panel.
DTYPES: dict[str, str] = {
    "year": "int16",
    "quarter": "int8",
    "month": "int8",
    "day": "int8",
    "dow": "int8",
    "carrier": "category",
    "tail_number": "category",
    "origin": "category",
    "origin_city": "category",
    "origin_state": "category",
    "dest": "category",
    "dest_city": "category",
    "dest_state": "category",
    "crs_dep_time": "int32",
    "dep_time": "float32",
    "dep_delay": "float32",
    "dep_delay_min": "float32",
    "dep_del15": "float32",
    "taxi_out": "float32",
    "taxi_in": "float32",
    "crs_arr_time": "int32",
    "arr_time": "float32",
    "arr_delay": "float32",
    "arr_delay_min": "float32",
    "arr_del15": "float32",
    "cancelled": "float32",
    "cancellation_code": "category",
    "diverted": "float32",
    "crs_elapsed": "float32",
    "actual_elapsed": "float32",
    "distance": "float32",
    "min_carrier": "float32",
    "min_weather": "float32",
    "min_nas": "float32",
    "min_security": "float32",
    "min_late_aircraft": "float32",
}

# Columns that must be non-null for a row to enter the completed-flight analysis.
REQUIRED_FOR_ANALYSIS: list[str] = [
    "flight_date", "carrier", "origin", "dest", "crs_dep_time",
    "arr_delay", "distance",
]

# Uniqueness key. BTS has no single primary key, so duplicate detection uses
# this combination, which is unique for a completed domestic leg.
KEY_COLUMNS: list[str] = [
    "flight_date", "carrier", "tail_number", "origin", "dest", "crs_dep_time",
]

# --------------------------------------------------------------------------
# Delay-cause taxonomy
# --------------------------------------------------------------------------
# BTS attributes every delay minute to exactly one of five causes. The project
# groups them into two families because that is what the research question asks:
#   Carrier + late aircraft = descriptive sum, not a claim of control
#   Other reported causes = NAS + weather + security
CAUSE_COLUMNS: list[str] = [
    "min_carrier",
    "min_late_aircraft",
    "min_nas",
    "min_weather",
    "min_security",
]

CAUSE_LABELS: dict[str, str] = {
    "min_carrier": "Carrier",
    "min_late_aircraft": "Late aircraft",
    "min_nas": "Air traffic / NAS",
    "min_weather": "Extreme weather",
    "min_security": "Security",
}

CAUSE_FAMILY: dict[str, str] = {
    "min_carrier": "Carrier + late aircraft",
    "min_late_aircraft": "Carrier + late aircraft",
    "min_nas": "Other reported causes",
    "min_weather": "Other reported causes",
    "min_security": "Other reported causes",
}

# Cause names as they appear in figures (with the family made explicit).
CAUSE_LABELS_LONG: dict[str, str] = {
    "min_carrier": "Carrier",
    "min_late_aircraft": "Late aircraft",
    "min_nas": "Air traffic / NAS",
    "min_weather": "Extreme weather",
    "min_security": "Security",
}

# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------
# Okabe-Ito (2008) palette: distinguishable under the common forms of
# colour-vision deficiency and still separable in greyscale print.
OKABE_ITO: dict[str, str] = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "grey": "#999999",
    "black": "#000000",
}

# One fixed colour per cause: a cause keeps its colour in every figure.
CAUSE_COLORS: dict[str, str] = {
    "min_carrier": OKABE_ITO["blue"],
    "min_late_aircraft": OKABE_ITO["sky"],
    "min_nas": OKABE_ITO["orange"],
    "min_weather": OKABE_ITO["green"],
    "min_security": OKABE_ITO["purple"],
}

FAMILY_COLORS: dict[str, str] = {
    "Carrier + late aircraft": OKABE_ITO["blue"],
    "Other reported causes": OKABE_ITO["orange"],
}

ACCENT = OKABE_ITO["vermillion"]   # highlights the "bad news" series
MUTED = "#9AA5B1"
INK = "#22303C"
GRID = "#D8DEE4"

# Neutral and annotation inks used by the printed figures. Named here rather than
# as literals in ``viz.py`` so a grey means the same thing in every figure and is
# auditable in one place (the same reason ``dashboard/panels/theme.py`` exists).
AXIS_INK = "#4A5568"      # axis frame and tick text
TEXT_GREY = "#5A6673"     # caption and source-stamp text
ZERO_LINE = "#8894A0"     # zero reference line on a signed axis
EQUALITY_LINE = "#B8C2CC" # 45-degree perfect-equality guide
ARROW_GREY = "#6B7684"    # annotation arrow stroke
NO_DATA = "#DCE1E7"       # empty tile where a state has no data
ANNOT_BLUE = "#3F6F8C"    # annotation label on a panel
SYNTHETIC_RED = "#B4232C" # "synthetic fixture" stamp colour

# Sequential scales must be monotonic in lightness so they survive greyscale.
SEQUENTIAL_CMAP = "viridis"
DIVERGING_CMAP = "RdBu_r"

# --------------------------------------------------------------------------
# Airport feature matrix (stage 5: clustering)
# --------------------------------------------------------------------------
AIRPORT_FEATURES: list[str] = [
    "n_dep",                # scale: completed departures in the panel
    "mean_arr_delay",       # central tendency
    "p90_arr_delay",        # tail
    "share_delayed_60",     # severe-delay risk
    "share_internal",       # legacy key: carrier + late-aircraft descriptive share
    "share_late_aircraft",  # cause mix: inherited delay
    "share_nas",            # cause mix: air-traffic imposed
    "share_weather",        # cause mix: weather imposed
    "seasonal_amplitude",   # summer/winter swing in mean delay
    "hub_stratum",          # ordinal size stratum from OurAirports type
]

AIRPORT_FEATURE_LABELS: dict[str, str] = {
    "n_dep": "Departures (log10)",
    "mean_arr_delay": "Mean arrival delay (min)",
    "p90_arr_delay": "90th pct delay (min)",
    "share_delayed_60": "Share delayed >= 60 min",
    "share_internal": "Carrier + late-aircraft share",
    "share_late_aircraft": "Late-aircraft share",
    "share_nas": "NAS cause share",
    "share_weather": "Weather cause share",
    "seasonal_amplitude": "Seasonal amplitude (min)",
    "hub_stratum": "Hub stratum",
}

# Features that are log-transformed before standardisation because departures
# span three orders of magnitude between a large hub and a regional field.
LOG_FEATURES: list[str] = ["n_dep"]

HUB_STRATUM: dict[str, int] = {
    "large_airport": 3,
    "medium_airport": 2,
    "small_airport": 1,
}

# --------------------------------------------------------------------------
# Display helpers
# --------------------------------------------------------------------------
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
