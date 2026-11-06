"""02 - Validation and data-quality report.

    python src/scripts/02_validate.py

Answers the question the report has to answer before any finding: is the data
complete and internally consistent? Writes a per-year summary, the cause-field
coverage table, and a machine-readable metrics file the dashboard reads.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import attribution, clean, config, io, models  # noqa: E402


def main() -> int:
    print(config.summarise())
    raw = io.load_flights()
    checks = clean.validate(raw, f"panel_{config.mode()}")

    # ``summarise_panel`` needs the raw frame (its cancelled-flight count comes
    # from the unfiltered rows) and ``threshold_audit`` needs the completed one.
    # They are ordered so that only one extra copy exists at a time: on the full
    # panel the raw frame plus one completed copy already sit near the memory
    # ceiling, and a third copy would OOM.
    summary = clean.summarise_panel(raw)
    completed = clean.completed(raw)
    coverage = attribution.threshold_audit(completed)
    years = [int(y) for y in sorted(raw["year"].unique())]
    del raw

    tables = config.ensure_dir("paths.tables")
    summary.to_csv(tables / "panel_summary_by_year.csv", index=False)
    coverage.to_csv(tables / "cause_field_coverage.csv", index=False)

    print("\nPanel summary")
    print(summary.to_string(index=False))
    print("\nCause-field coverage")
    print(coverage.to_string(index=False))

    models.save_metrics({
        "mode": config.mode(),
        "checks": checks,
        "completed_flights": int(len(completed)),
        "years": years,
        "share_delayed_60": round(float((completed["arr_delay"] >= 60).mean()), 5),
    }, "validation")

    print(f"\n[02] tables -> {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
