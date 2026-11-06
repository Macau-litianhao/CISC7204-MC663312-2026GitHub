"""Acquisition and storage: BTS downloads, airport reference, Parquet I/O.

The rule this module enforces: nothing downstream knows where data came from.
Notebooks and the dashboard call ``load_flights`` / ``load_airports``; only the
acquisition stage touches HTTP. If the public URL changes, one constant here
changes and no other file needs editing.

Storage decision
----------------
Twelve monthly CSVs per year, ten years, is roughly 63 million rows (measured on
the 2015–2024 panel: 63,079,392). Parquet
partitioned by year keeps a single-year re-read at a few seconds instead of a
full-panel load, which is what makes the notebooks usable during development.
"""

from __future__ import annotations

import hashlib
import time
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import requests

from . import config, schema

# BTS publishes one zip per month under a stable name pattern.
BTS_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)
BTS_LANDING = "https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ"

AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

USER_AGENT = "CISC7204-Team01/0.2 (academic coursework; contact via Moodle)"
CHUNK = 1 << 20            # 1 MiB


# --------------------------------------------------------------------------
# Generic download helper
# --------------------------------------------------------------------------
def download(url: str, dest: Path, force: bool = False, retries: int = 3,
             timeout: int = 180) -> Path:
    """Stream ``url`` to ``dest``. Skips the transfer if the file already exists.

    BTS occasionally returns a 200 with a short HTML error page instead of a
    zip, so the caller is expected to validate the artefact; this function only
    guarantees a complete transfer.
    """
    dest = config.ensure_parent(Path(dest))
    if dest.exists() and not force and dest.stat().st_size > 0:
        return dest

    headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers=headers, stream=True,
                              timeout=timeout) as response:
                response.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                written = 0
                with tmp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=CHUNK):
                        if chunk:
                            handle.write(chunk)
                            written += len(chunk)
                if written == 0:
                    raise ValueError(f"empty response body for {url}")
                tmp.replace(dest)
                return dest
        except Exception as error:              # noqa: BLE001 - retried below
            last_error = error
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"download failed after {retries} attempts: {url}") from last_error


# --------------------------------------------------------------------------
# BTS flight files
# --------------------------------------------------------------------------
def bts_month_file(year: int, month: int) -> Path:
    return config.RAW_FLIGHTS_DIR / f"On_Time_{year}_{month:02d}.zip"


def acquire_month(year: int, month: int, force: bool = False) -> Path:
    """Download one monthly BTS zip and check that it is a readable archive."""
    target = bts_month_file(year, month)
    download(BTS_URL.format(year=year, month=month), target, force=force)
    if not zipfile.is_zipfile(target):
        target.unlink(missing_ok=True)
        raise ValueError(
            f"{target.name} is not a valid zip - BTS may have returned an error "
            f"page. Check {BTS_LANDING} for the current file list."
        )
    return target


def acquire_year(year: int, force: bool = False) -> list[Path]:
    """Download all twelve months of one year, reporting progress."""
    paths = []
    for month in range(1, 13):
        path = acquire_month(year, month, force=force)
        paths.append(path)
        print(f"[io] {year}-{month:02d} -> {path.name} ({path.stat().st_size/1e6:.1f} MB)")
    return paths


def read_bts_month(path: Path) -> pd.DataFrame:
    """Read one monthly file (zip or csv) with only the needed columns.

    The BTS archive holds two members - the data CSV and a ``readme.html`` - so
    the CSV has to be located inside the archive rather than letting pandas guess.
    Passing the archive directly raises "Multiple files found in ZIP file".
    """
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist()
                       if name.lower().endswith(".csv")]
            if not members:
                raise ValueError(f"no CSV inside {path.name}: {archive.namelist()}")
            with archive.open(members[0]) as handle:
                return pd.read_csv(handle, usecols=schema.USECOLS,
                                   low_memory=False)
    return pd.read_csv(path, usecols=schema.USECOLS, low_memory=False)


def acquire_airports(force: bool = False) -> Path:
    """OurAirports reference file: coordinates, type and region."""
    return download(AIRPORTS_URL, config.airports_file(), force=force)


# --------------------------------------------------------------------------
# Parquet
# --------------------------------------------------------------------------
def write_flights(df: pd.DataFrame, path: Path | None = None,
                  partition_cols: list[str] | None = None) -> Path:
    """Write the flight table, partitioned by year by default."""
    target = Path(path) if path else config.flights_file()
    config.ensure_parent(target)
    if partition_cols:
        df.to_parquet(target.parent, partition_cols=partition_cols, index=False,
                      compression="zstd")
        return target.parent
    df.to_parquet(target, index=False, compression="zstd")
    print(f"[io] wrote {len(df):,} rows -> {target}")
    return target


# Columns that must come back as ``category`` after the Parquet round-trip.
# ``apply_schema`` sets these dtypes, but writing and re-reading the panel loses
# them: on a 63M-row table the string columns alone cost ~7 GB (``month_name``
# stores 12 values as a full string once per row). Restoring the category dtype
# is what keeps a full-panel load under the memory a 16 GB machine can hold.
_DERIVED_CATEGORIES = ("month_name", "dow_name")

# Raw BTS fields the analysis never reads. Dropping them at load keeps the
# 63M-row panel inside a 16 GB machine: each ``float32``/``int32`` column is
# ~250 MB, so these eleven cost ~2.7 GB that no stage uses. They stay in the
# Parquet file, so nothing is lost if a later question needs one of them.
_DROP_COLUMNS = (
    "dep_delay", "dep_time", "arr_time", "taxi_out", "taxi_in",
    "crs_arr_time", "dep_delay_min", "dep_del15", "arr_del15",
    "crs_elapsed", "actual_elapsed",
)


def load_flights(columns: list[str] | None = None) -> pd.DataFrame:
    """Load the prepared flight table for the active mode.

    ``columns`` selects an explicit subset. When omitted, the unused raw fields
    (``_DROP_COLUMNS``) are projected away before any rows are materialised, so
    a full-panel load stays small enough for a 16 GB machine.
    """
    target = config.flights_file()
    if columns is None and not target.is_dir():
        # Read the Parquet schema (no row scan) and drop the unused raw fields.
        columns = [
            name for name in pq.read_schema(target).names
            if name not in _DROP_COLUMNS
        ]
    if target.is_dir():                       # partitioned layout
        frame = pd.read_parquet(target, columns=columns)
    elif not target.exists():
        raise FileNotFoundError(
            f"{target} not found.\n"
            "  full panel : python src/scripts/01_acquire.py --years 2015-2024\n"
            "  smoke test : python src/scripts/00_make_sample.py"
        )
    else:
        frame = pd.read_parquet(target, columns=columns)
    return _restore_categories(frame)


def _restore_categories(frame: pd.DataFrame) -> pd.DataFrame:
    """Re-apply the category dtype that the Parquet round-trip dropped.

    PyArrow reads dictionary-encoded strings back as ``str`` (``StringDtype``),
    not as ``category``. Casting only the declared columns — never the raw
    ``float32``/``datetime`` fields — is a no-op for any computation and can
    shrink the in-memory panel by several gigabytes.
    """
    category_columns = [
        column for column, dtype in schema.DTYPES.items() if dtype == "category"
    ] + list(_DERIVED_CATEGORIES)
    for column in category_columns:
        # ``StringDtype`` reports its ``name`` as ``"str"`` (not ``"string"``),
        # so test the type rather than its string form.
        if column in frame.columns and isinstance(
            frame[column].dtype, pd.StringDtype
        ):
            frame[column] = frame[column].astype("category")
    return frame


def load_airports(us_only: bool = True) -> pd.DataFrame:
    """Airport reference restricted to operational US airports with coordinates."""
    path = config.airports_file()
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run python src/scripts/01_acquire.py --reference-only"
        )
    airports = pd.read_csv(path, usecols=[
        "ident", "name", "type", "latitude_deg", "longitude_deg",
        "iso_country", "iso_region", "municipality", "scheduled_service", "iata_code", "local_code",
    ])
    if us_only:
        airports = airports[airports["iso_country"].isin(["US", "PR", "VI", "GU", "AS", "MP"])]
    keep = {"large_airport", "medium_airport", "small_airport"}
    return airports[airports["type"].isin(keep)].reset_index(drop=True)


def sample_completed(columns: list[str], limit: int = 400_000) -> pd.DataFrame:
    """Uniform completed-flight sample, streaming the panel with bounded memory."""
    import json
    import numpy as np
    target = config.flights_file()
    if config.mode() == 'sample':
        frame = load_flights(columns=columns)
        frame = frame.loc[frame.cancelled.eq(0) & frame.diverted.eq(0) & frame.arr_delay.notna()]
        return frame.sample(min(len(frame),limit),random_state=config.seed()).reset_index(drop=True)
    validation = json.loads((config.METRIC_DIR/'validation.json').read_text(encoding='utf-8'))
    total = int(validation['completed_flights'])
    picks = np.sort(np.random.default_rng(config.seed()).choice(total,min(total,limit),replace=False))
    chunks, offset = [], 0
    for batch in pq.ParquetFile(target).iter_batches(batch_size=500_000,columns=columns):
        frame = batch.to_pandas()
        good = frame.loc[frame.cancelled.eq(0) & frame.diverted.eq(0) & frame.arr_delay.notna()]
        low,high=np.searchsorted(picks,[offset,offset+len(good)])
        if high>low:
            chunks.append(good.iloc[picks[low:high]-offset])
        offset+=len(good)
    if offset != total:
        raise ValueError(f'Validation count stale: observed {offset}, expected {total}')
    return pd.concat(chunks,ignore_index=True)


def load_weather() -> pd.DataFrame:
    """Hourly weather keyed by (station, hour). Empty frame when not acquired."""
    path = config.weather_file()
    if not path.exists():
        return pd.DataFrame(columns=["origin", "obs_hour", "wind_speed_kt",
                                     "visibility_mi", "precip_mm", "temp_c"])
    return pd.read_parquet(path)


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(paths: list[Path], target: Path | None = None) -> Path:
    """Checksum manifest of the raw files behind the reported results.

    A number in the report is only reproducible if the exact input file is
    known, so the manifest records name, size and SHA-256 for every raw file.
    """
    out = Path(target) if target else Path(str(config.get("files.checksum_manifest")))
    out = config.ensure_parent(out if out.is_absolute() else config.ROOT / out)
    lines = []
    for path in sorted(paths):
        path = Path(path)
        if path.exists():
            lines.append(f"{sha256(path)}  {path.stat().st_size:>12}  {path.name}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[io] manifest with {len(lines)} entries -> {out}")
    return out
