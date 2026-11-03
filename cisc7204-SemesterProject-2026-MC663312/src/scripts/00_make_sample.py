"""00 - Build the synthetic smoke fixture.

    python src/scripts/00_make_sample.py [--days 120] [--tails 200]

Writes data/sample/flights_sample.parquet in the project schema. Use it for
tests, for a quick dashboard demo, and for reviewing figures without waiting
for a seventy-million-row download. Never quote its numbers as results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team01 import config, synth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--tails", type=int, default=200)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    print(config.summarise())
    # make_panel applies the project schema, so the fixture is byte-compatible
    # with the real Parquet and every downstream stage runs unchanged.
    panel = synth.make_panel(days=args.days, tails=args.tails, seed=args.seed)

    target = config.ensure_parent(config.ROOT / str(config.get("files.flights_sample_parquet")))
    panel.to_parquet(target, index=False)

    airports = config.ensure_parent(config.airports_file())
    synth.make_airport_reference().to_csv(airports, index=False)

    print(f"rows      : {len(panel):,}")
    print(f"flights   : {target}")
    print(f"airports  : {airports}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
