"""Run the analysis stages without make.

    python run_all.py --stage smoke      # fixture: seconds, no download
    python run_all.py --stage data       # download and prepare the real panel
    python run_all.py --stage pipeline   # every analysis stage, real panel
    python run_all.py --list

Exists because ``make`` is not installed on a default Windows machine and the
project should not require a build tool to be reproduced. The stage names match
the Makefile targets exactly, so the two entry points cannot drift.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGES: dict[str, list[tuple[str, str]]] = {
    "sample": [("00_make_sample", "sample")],
    "data": [("01_acquire", "full")],
    "validate": [("02_validate", None)],
    "attribution": [("03_attribution", None)],
    "tail": [("04_tail", None)],
    "clusters": [("05_clusters", None)],
    "models": [("06_models", None)],
    "figures": [("07_figures", None)],
    "review": [("08_review_rebuild", None)],
    "temporal": [("09_temporal_validation", None)],
    "reference-audit": [("10_reference_audit", None)],
}

PIPELINE = ["validate", "attribution", "tail", "clusters", "models", "figures"]


def run(script: str, mode: str | None, extra: list[str]) -> None:
    env = dict(os.environ)
    if mode:
        env["TEAM01_MODE"] = mode
    command = [sys.executable, str(ROOT / "src" / "scripts" / f"{script}.py"), *extra]
    print(f"\n$ {' '.join(command)}   [{env.get('TEAM01_MODE', 'default')}]", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", default="pipeline",
                        choices=[*STAGES, "pipeline", "smoke", "dashboard"])
    parser.add_argument("--list", action="store_true")
    # Anything unrecognised is forwarded to the stage script, so
    # `python run_all.py --stage data --years 2024 --force` works unchanged.
    args, extra = parser.parse_known_args()

    if args.list:
        for name in STAGES:
            print(f"  {name:12s} {'(fixture)' if name == 'sample' else ''}")
        print("  pipeline     validate -> figures on the active mode")
        print("  smoke        sample + pipeline in TEAM01_MODE=sample")
        print("  dashboard    launch dashboard/app.py")
        return 0

    started = time.time()

    if args.stage == "smoke":
        os.environ["TEAM01_MODE"] = "sample"
        run("00_make_sample", "sample", [])
        for name in PIPELINE:
            script, _ = STAGES[name][0]
            run(script, None, [])
    elif args.stage == "dashboard":
        subprocess.run([sys.executable, str(ROOT / "dashboard" / "app.py")], cwd=ROOT, check=True)
    elif args.stage == "pipeline":
        for name in PIPELINE:
            script, _ = STAGES[name][0]
            run(script, None, extra)
    else:
        script, mode = STAGES[args.stage][0]
        run(script, mode, extra)

    print(f"\ndone in {time.time() - started:,.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
