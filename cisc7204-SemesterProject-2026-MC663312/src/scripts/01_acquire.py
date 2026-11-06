"""01 - Acquire and prepare the flight panel.

    python src/scripts/01_acquire.py --years 2015-2024
    python src/scripts/01_acquire.py --years 2024 --reference-only
    python src/scripts/01_acquire.py --years 2024 --limit-months 2

Downloads the monthly BTS zips, coerces them to the project schema, validates
every year, writes one Parquet table and records a checksum manifest.

Progress is per file and failures are fatal: a silently missing month would
turn a decade into a nine-year panel and every trend line in the report would be
wrong without anyone noticing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from team01 import clean, config, io  # noqa: E402


def parse_years(spec: str) -> list[int]:
    """Accept ``2024``, ``2015-2024`` or ``2019,2023,2024``."""
    if "-" in spec:
        start, end = spec.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(part) for part in spec.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2015-2024")
    parser.add_argument("--limit-months", type=int, default=12,
                        help="download only the first N months of each year (testing)")
    parser.add_argument("--reference-only", action="store_true",
                        help="only refresh airports.csv")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    print(config.summarise())

    airports = io.acquire_airports(force=args.force)
    print(f"[01] airports -> {airports} ({airports.stat().st_size/1e6:.1f} MB)")
    if args.reference_only:
        return 0

    years = parse_years(args.years)
    checks: list[dict] = []
    downloaded: list[Path] = [airports]

    # One year is concatenated at a time (~1 GB) and written to a staging file,
    # then the staging files are merged into the single panel file. The previous
    # version kept all 120 months in ``frames`` and concatenated once, which held
    # the ~70M-row panel twice over during the sort and died with an OOM on this
    # 16 GB machine *after* the expensive download had already finished.
    staging = config.INTERIM_DIR / "flights_year"
    staging.mkdir(parents=True, exist_ok=True)

    for year in years:
        year_frames: list[pd.DataFrame] = []
        for month in range(1, args.limit_months + 1):
            path = io.acquire_month(year, month, force=args.force)
            downloaded.append(path)
            raw = io.read_bts_month(path)
            prepared = clean.apply_schema(raw)
            prepared = clean.drop_duplicates(prepared)
            checks.append(clean.validate(prepared, f"raw_{year}-{month:02d}"))
            year_frames.append(prepared)
            print(f"[01] {year}-{month:02d}: {len(prepared):,} rows")
        year_df = pd.concat(year_frames, ignore_index=True)
        year_df = year_df.sort_values(["flight_date", "origin", "crs_dep_time"])
        year_path = staging / f"flights_{year}.parquet"
        year_df.to_parquet(year_path, index=False, compression="zstd")
        print(f"[io] wrote {len(year_df):,} rows -> {year_path.name}")
        del year_frames, year_df

    # Merge the year files into one panel file without loading the whole panel:
    # each file is read and appended one at a time, cast to the first file's
    # schema so a year with a slightly different category value set cannot break
    # the dictionary encoding.
    target = config.flights_file()
    parts = sorted(staging.glob("flights_*.parquet"))
    schema = pq.read_schema(parts[0])
    with pq.ParquetWriter(target, schema, compression="zstd") as writer:
        for part in parts:
            writer.write_table(pq.read_table(part).cast(schema))
    print(f"[io] merged {len(parts)} year files -> {target}")

    # Panel-level validation reads one year at a time, so the full panel is
    # never held in memory. Per-year rows keep the complete field set; the
    # "panel" row reports the totals and the year span.
    panel_total = 0
    for part in parts:
        ydf = pd.read_parquet(part)
        checks.append(clean.validate(ydf, f"panel_{part.stem}"))
        panel_total += int(checks[-1]["rows"])
        del ydf
    checks.append({"stage": "panel", "rows": panel_total,
                   "years": f"{years[0]}-{years[-1]}", "year_files": len(parts)})

    report = pd.DataFrame(checks)
    report_path = config.ensure_parent(config.TABLE_DIR / "validation_by_file.csv")
    report.to_csv(report_path, index=False)

    io.write_manifest(downloaded)

    print("\n" + "=" * 62)
    print(f"panel rows        : {panel_total:,}")
    print(f"years             : {years[0]}-{years[-1]}")
    print(f"parquet           : {target}")
    print(f"validation report : {report_path}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
