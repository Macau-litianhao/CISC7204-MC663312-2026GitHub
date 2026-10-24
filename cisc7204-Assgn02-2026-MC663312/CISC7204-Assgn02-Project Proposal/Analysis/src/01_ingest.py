"""
01_ingest.py - Download the twelve 2024 BTS monthly files and build one
clean analysis table.

Run:  python src/01_ingest.py            (downloads whatever is missing)
      python src/01_ingest.py --skip-download

Outputs
-------
data/processed/flights_2024.parquet   cleaned flight-level table
data/processed/aggregates.pkl         pre-aggregated tables used by the EDA
outputs/ingest_summary.csv            row counts and quality checks
"""

from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    AIRPORTS_CSV, AIRPORTS_URL, ATTRIBUTION_THRESHOLD_MIN, BTS_URL_TEMPLATE,
    CAUSE_COLS, DTYPES, FLIGHTS_PARQUET, MINS, OUT_DIR, PROCESSED_DIR,
    RAW_DIR, USECOLS, YEAR,
)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CISC7204-A02"}


# --------------------------------------------------------------------------
# Download layer
# --------------------------------------------------------------------------
def _looks_complete(dest) -> bool:
    """A previous download only counts as done if the zip actually opens.

    Interrupted downloads leave multi-megabyte fragments behind, so file size
    alone is not a safe test.
    """
    if not dest.exists() or dest.stat().st_size < 1_000_000:
        return False
    if dest.suffix.lower() != ".zip":
        return True
    try:
        with zipfile.ZipFile(dest) as zf:
            return zf.testzip() is None
    except zipfile.BadZipFile:
        return False


def download(url: str, dest, retries: int = 3, timeout: int = 300):
    """Download `url` to `dest` unless a valid copy already exists."""
    if _looks_complete(dest):
        return dest
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                dest.write_bytes(resp.read())
            print(f"  downloaded {dest.name} "
                  f"({dest.stat().st_size / 1e6:.1f} MB)")
            return dest
        except Exception as exc:                      # noqa: BLE001
            print(f"  attempt {attempt} failed for {dest.name}: {exc}")
            if attempt == retries:
                raise
            time.sleep(3 * attempt)
    return dest


def get_month_zip(month: int, skip_download: bool):
    dest = RAW_DIR / f"On_Time_{YEAR}_{month}.zip"
    if not skip_download:
        download(BTS_URL_TEMPLATE.format(month=month), dest)
    if not dest.exists():
        raise FileNotFoundError(f"missing {dest}; run without --skip-download")
    return dest


def get_airports(skip_download: bool):
    if not skip_download:
        download(AIRPORTS_URL, AIRPORTS_CSV, timeout=120)
    return AIRPORTS_CSV


# --------------------------------------------------------------------------
# Cleaning layer
# --------------------------------------------------------------------------
def read_month(zip_path) -> pd.DataFrame:
    """Read the single CSV inside a BTS monthly zip, keeping only USECOLS."""
    with zipfile.ZipFile(zip_path) as zf:
        member = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(member) as fh:
            raw = pd.read_csv(io.BytesIO(fh.read()), usecols=USECOLS,
                              dtype=DTYPES, low_memory=False)
    return enhance(raw)


def enhance(df: pd.DataFrame) -> pd.DataFrame:
    """Derive the analysis fields we need beyond the raw BTS columns."""
    # Scheduled departure hour. CRSDepTime arrives as hhmm (e.g. 1830 -> 18).
    df["dep_hour"] = (df["CRSDepTime"] // 100).astype("int8")

    # Scheduled arrival hour, same treatment.
    df["arr_hour"] = (df["CRSArrTime"] // 100).astype("int8")

    # The five delay-cause minutes sum to ArrDelayMinutes for delayed flights.
    df["cause_total"] = df[CAUSE_COLS].sum(axis=1, skipna=True)
    df["has_cause"] = df[CAUSE_COLS].notna().any(axis=1)
    df["internal_min"] = df[["CarrierDelay", "LateAircraftDelay"]].sum(
        axis=1, skipna=True)
    df["system_min"] = df[["NASDelay", "WeatherDelay", "SecurityDelay"]].sum(
        axis=1, skipna=True)

    # Flag any minute of delay as a delayed flight; also expose the two
    # tail thresholds the project argues about.
    df["is_delayed"] = (df["ArrDelayMinutes"].fillna(0) > 0).astype("int8")
    df["is_late15"] = (df["ArrDelayMinutes"].fillna(0) >= 15).astype("int8")
    df["is_tail60"] = (df["ArrDelayMinutes"].fillna(0) >= 60).astype("int8")
    df["is_tail180"] = (df["ArrDelayMinutes"].fillna(0) >= 180).astype("int8")

    # Completed flights only make sense for delay statistics.
    df["completed"] = ((df["Cancelled"].fillna(0) == 0)
                       & (df["Diverted"].fillna(0) == 0)).astype("int8")

    # Flight date as a real date so the dashboard can filter on it.
    df["date"] = pd.to_datetime(df["FlightDate"], format="%Y-%m-%d",
                                errors="coerce")

    # Distance bands used in the EDA and in the regression.
    bins = [0, 250, 500, 750, 1000, 1500, 2500, 6000]
    labels = ["<250", "250-500", "500-750", "750-1k", "1k-1.5k",
              "1.5k-2.5k", ">2.5k"]
    df["dist_band"] = pd.cut(df["Distance"], bins=bins, labels=labels,
                             right=False)

    return df


# --------------------------------------------------------------------------
# Aggregate layer (what the EDA and dashboard actually consume)
# --------------------------------------------------------------------------
def build_aggregates(df: pd.DataFrame) -> dict:
    """Pre-compute the grouped tables so notebooks stay fast to re-run.

    Two universes are used deliberately and must never be mixed up:

    * `done` - every completed flight. Used for delay *distributions*
      (mean, percentiles, tail probability).
    * `att`  - completed flights with `ArrDelayMinutes >= 15`. BTS only
      publishes the five delay-cause minutes for flights delayed 15 minutes
      or more, so this is the only universe in which the decomposition is
      defined. Coverage inside `att` is 100%, which we verify in notebook 01.
    """
    done = df[df["completed"] == 1]
    att = done[done["ArrDelayMinutes"] >= 15]
    agg = {}

    # 2024 totals: the headline numbers quoted in the proposal.
    agg["headline"] = pd.Series({
        "flights_total": len(df),
        "flights_completed": int(done.shape[0]),
        "cancelled": int((df["Cancelled"] == 1).sum()),
        "diverted": int((df["Diverted"] == 1).sum()),
        "carriers": df["Reporting_Airline"].nunique(),
        "airports": df["Origin"].nunique(),
        "routes": df.groupby(["Origin", "Dest"], observed=True).ngroups,
        "arr_delay_total_min": float(done["ArrDelayMinutes"].sum()),
        "mean_arr_delay": float(done["ArrDelay"].mean()),
        "median_arr_delay": float(done["ArrDelay"].median()),
        "p90_arr_delay": float(done["ArrDelay"].quantile(0.90)),
        "p99_arr_delay": float(done["ArrDelay"].quantile(0.99)),
        "pct_late15": float(done["is_late15"].mean() * 100),
        "pct_tail60": float(done["is_tail60"].mean() * 100),
        "pct_tail180": float(done["is_tail180"].mean() * 100),
        # --- the attribution universe ------------------------------------
        "att_flights": int(att.shape[0]),
        "att_share_of_delayed": float(att.shape[0] / done["is_delayed"].sum()
                                      * 100),
        "att_min_total": float(att["ArrDelayMinutes"].sum()),
        "att_share_of_delay_min": float(att["ArrDelayMinutes"].sum()
                                        / done["ArrDelayMinutes"].sum() * 100),
        "attributed_min_total": float(att["cause_total"].sum()),
        "attribution_coverage": float(att["CarrierDelay"].notna().mean() * 100),
        "internal_share": float(att["internal_min"].sum()
                                / att["cause_total"].sum() * 100),
        "system_share": float(att["system_min"].sum()
                              / att["cause_total"].sum() * 100),
    })
    for col in CAUSE_COLS:
        agg["headline"][f"{col}_sum"] = float(att[col].sum())
        agg["headline"][f"{col}_share"] = float(
            att[col].sum() / att["cause_total"].sum() * 100)

    # Monthly series: the right-tail paradox lives here. Delay distributions
    # come from `done`; cause minutes from `att`.
    month_dist = done.groupby("Month", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        median_delay=("ArrDelay", "median"),
        p90=("ArrDelay", lambda s: s.quantile(0.90)),
        p99=("ArrDelay", lambda s: s.quantile(0.99)),
        pct_late15=("is_late15", lambda s: s.mean() * 100),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
        pct_tail180=("is_tail180", lambda s: s.mean() * 100),
    )
    month_cause = att.groupby("Month", observed=True)[CAUSE_COLS].sum()
    month_cause.columns = [MINS[c] for c in CAUSE_COLS]
    agg["by_month"] = month_dist.join(month_cause).reset_index()
    agg["by_month"]["min_total"] = agg["by_month"][list(MINS.values())].sum(
        axis=1)

    # Carrier series: who carries the internal blame?
    car_dist = done.groupby("Reporting_Airline", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
        pct_tail180=("is_tail180", lambda s: s.mean() * 100),
        distance=("Distance", "mean"),
    )
    car_cause = att.groupby("Reporting_Airline", observed=True)[
        CAUSE_COLS].sum()
    car_cause.columns = [MINS[c] for c in CAUSE_COLS]
    agg["by_carrier"] = car_dist.join(car_cause).reset_index()
    agg["by_carrier"]["min_total"] = agg["by_carrier"][
        list(MINS.values())].sum(axis=1)
    agg["by_carrier"]["internal_share"] = (
        agg["by_carrier"][[MINS["CarrierDelay"], MINS["LateAircraftDelay"]]]
        .sum(axis=1) / agg["by_carrier"]["min_total"] * 100)
    agg["by_carrier"]["delay_min_per_flight"] = (
        agg["by_carrier"]["min_total"] / agg["by_carrier"]["flights"])

    # Origin airport series: where does the system hurt most?
    org_dist = done.groupby("Origin", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
        origin_state=("OriginState", "first"),
        city=("OriginCityName", "first"),
    )
    org_cause = att.groupby("Origin", observed=True)[CAUSE_COLS].sum()
    org_cause.columns = [MINS[c] for c in CAUSE_COLS]
    origin = org_dist.join(org_cause).reset_index()
    origin["min_total"] = origin[list(MINS.values())].sum(axis=1)
    origin["system_share"] = (
        origin[[MINS["NASDelay"], MINS["WeatherDelay"],
                MINS["SecurityDelay"]]].sum(axis=1)
        / origin["min_total"] * 100)
    agg["by_origin"] = origin

    # Destination state, for the tile-grid map and the folium choropleth.
    st_dist = done.groupby("DestState", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
    )
    st_cause = att.groupby("DestState", observed=True)[CAUSE_COLS].sum()
    st_cause.columns = [MINS[c] for c in CAUSE_COLS]
    st = st_dist.join(st_cause).reset_index()
    st["min_total"] = st[list(MINS.values())].sum(axis=1)
    st["system_share"] = (
        st[[MINS["NASDelay"], MINS["WeatherDelay"], MINS["SecurityDelay"]]]
        .sum(axis=1) / st["min_total"] * 100)
    agg["by_dest_state"] = st

    # Departure-hour profile: the "evening cascade" evidence.
    hr_dist = done.groupby("dep_hour", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
    )
    hr_cause = att.groupby("dep_hour", observed=True)[CAUSE_COLS].sum()
    hr_cause.columns = [MINS[c] for c in CAUSE_COLS]
    agg["by_dep_hour"] = hr_dist.join(hr_cause).reset_index()
    agg["by_dep_hour"]["min_total"] = agg["by_dep_hour"][
        list(MINS.values())].sum(axis=1)

    # Daily series: cancellation spikes and storm days.
    agg["by_date"] = done.groupby("date", observed=True).agg(
        flights=("ArrDelay", "size"),
        mean_delay=("ArrDelay", "mean"),
        pct_tail60=("is_tail60", lambda s: s.mean() * 100),
    ).reset_index()
    agg["cancel_by_date"] = (
        df.groupby("date", observed=True)["Cancelled"].mean()
        .mul(100).reset_index(name="pct_cancelled"))

    # ------------------------------------------------------------------
    # The cube the dashboard filters on.
    #
    # A dashboard that only swaps between pre-aggregated tables cannot show
    # "LATE flights from ORD in July on carriers X and Y". Aggregating the
    # full table once by (month x carrier x departure hour x distance band)
    # gives 30k rows from which every dashboard figure can be *recomputed*
    # under the user's filter, instead of merely redisplayed.
    #
    # Only summable measures go in: counts, delay-minute sums and tail counts.
    # Median and p90 are not summable, so the dashboard reports mean and tail
    # probabilities, which are.
    # ------------------------------------------------------------------
    keys = ["Month", "Reporting_Airline", "dep_hour", "dist_band"]
    cube = done.groupby(keys, observed=True, dropna=False).agg(
        flights=("ArrDelay", "size"),
        sum_delay=("ArrDelay", "sum"),
        sum_delay_min=("ArrDelayMinutes", "sum"),
        n60=("is_tail60", "sum"),
        n180=("is_tail180", "sum"),
        distance=("Distance", "mean"),
    ).reset_index()
    cube_cause = att.groupby(keys, observed=True, dropna=False)[
        CAUSE_COLS].sum().reset_index()
    cube = cube.merge(cube_cause, on=keys, how="left")
    cube[CAUSE_COLS] = cube[CAUSE_COLS].fillna(0.0)
    cube["min_total"] = cube[CAUSE_COLS].sum(axis=1)
    agg["cube"] = cube

    # Second cube with the state dimension instead of the distance band, so
    # the dashboard's state panel also responds to the month/carrier/hour
    # filters rather than showing a national picture under a local filter.
    skeys = ["Month", "Reporting_Airline", "dep_hour", "DestState"]
    scube = done.groupby(skeys, observed=True, dropna=False).agg(
        flights=("ArrDelay", "size"),
        sum_delay=("ArrDelay", "sum"),
        sum_delay_min=("ArrDelayMinutes", "sum"),
        n60=("is_tail60", "sum"),
        n180=("is_tail180", "sum"),
        distance=("Distance", "mean"),
    ).reset_index()
    scube_cause = att.groupby(skeys, observed=True, dropna=False)[
        CAUSE_COLS].sum().reset_index()
    scube = scube.merge(scube_cause, on=skeys, how="left")
    scube[CAUSE_COLS] = scube[CAUSE_COLS].fillna(0.0)
    scube["min_total"] = scube[CAUSE_COLS].sum(axis=1)
    agg["cube_state"] = scube

    return agg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true",
                        help="use zips already sitting in data/raw")
    parser.add_argument("--from-parquet", action="store_true",
                        help="rebuild the aggregates from an existing parquet")
    args = parser.parse_args()

    if args.from_parquet:
        if not FLIGHTS_PARQUET.exists():
            raise FileNotFoundError(FLIGHTS_PARQUET)
        print(f"=== loading {FLIGHTS_PARQUET.name} ===")
        df = pd.read_parquet(FLIGHTS_PARQUET)
        print(f"  {len(df):,} rows, {df.shape[1]} columns")
        agg = build_aggregates(df)
        pd.to_pickle(agg, PROCESSED_DIR / "aggregates.pkl")
        print(f"  wrote aggregates.pkl ({len(agg)} tables)")
        print(agg["headline"].round(2).to_string())
        return

    print(f"=== Step 1/3: fetch {YEAR} monthly files ===")
    frames = []
    for month in range(1, 13):
        zp = get_month_zip(month, args.skip_download)
        part = read_month(zp)
        part.insert(0, "month_idx", month)
        frames.append(part)
        print(f"  {YEAR}-{month:02d}  rows={len(part):>8,}  "
              f"cols={part.shape[1]}")

    print("=== Step 2/3: concatenate and validate ===")
    df = pd.concat(frames, ignore_index=True)
    del frames
    for col in ("Reporting_Airline", "Origin", "OriginCityName",
                "OriginState", "Dest", "DestCityName", "DestState",
                "CancellationCode"):
        df[col] = df[col].astype("category")

    # ---- quality checks -------------------------------------------------
    checks = []
    checks.append(("raw_rows", len(df)))
    checks.append(("duplicate_rows", int(df.duplicated().sum())))

    done_mask = df["completed"] == 1
    valid_mask = df["ArrDelay"].notna()
    checks.append(("completed_rows", int(done_mask.sum())))
    checks.append(("arrdelay_notna", int(valid_mask.sum())))

    # Delay minutes should be attributed for (nearly) every delayed flight.
    delayed = df[(df["completed"] == 1) & (df["ArrDelayMinutes"].fillna(0) > 0)]
    checks.append(("delayed_flights", len(delayed)))
    checks.append(("delayed_with_cause",
                   int(delayed["has_cause"].sum())))
    checks.append(("cause_minus_arrdelay_median_abs",
                   float((delayed["cause_total"]
                          - delayed["ArrDelayMinutes"]).abs().median())))

    # BTS publishes causes only for delays >= 15 minutes. Confirm the cut is
    # clean (100% coverage above it) so the attribution universe is exact.
    att = df[(df["completed"] == 1)
             & (df["ArrDelayMinutes"] >= ATTRIBUTION_THRESHOLD_MIN)]
    checks.append(("cause_coverage_at_15min_pct",
                   float(att["CarrierDelay"].notna().mean() * 100)))
    checks.append(("cause_coverage_below_15min_pct",
                   float(delayed[delayed["ArrDelayMinutes"]
                                 < ATTRIBUTION_THRESHOLD_MIN]
                         ["CarrierDelay"].notna().mean() * 100)))

    checks_df = pd.DataFrame(checks, columns=["check", "value"])
    checks_df.to_csv(OUT_DIR / "ingest_summary.csv", index=False)
    for k, v in checks:
        print(f"  {k:34s} {v:,.0f}" if isinstance(v, (int, np.integer))
              else f"  {k:34s} {v:,.2f}")

    print("=== Step 3/3: write parquet + aggregates ===")
    df.to_parquet(FLIGHTS_PARQUET, index=False, compression="zstd")
    print(f"  wrote {FLIGHTS_PARQUET} "
          f"({FLIGHTS_PARQUET.stat().st_size / 1e6:.0f} MB)")

    agg = build_aggregates(df)
    pd.to_pickle(agg, PROCESSED_DIR / "aggregates.pkl")
    print(f"  wrote {PROCESSED_DIR / 'aggregates.pkl'} "
          f"({len(agg)} tables)")
    print(agg["headline"].round(2).to_string())


if __name__ == "__main__":
    main()
