"""
run_all.py - Rebuild the whole analysis with one command.

    python run_all.py                 # ingest (if needed) + all four notebooks
    python run_all.py --skip-ingest   # notebooks only
    python run_all.py --no-execute    # build notebooks without running them

Why a single entry point: the graded artefacts are the notebooks, and a
notebook that only works because a kernel still holds an old variable is a
trap for whoever re-runs it. This script regenerates every notebook from its
`# %%` source and executes it against a fresh kernel, then reports which
figures and outputs appeared. A clean run is the reproduction claim.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NB_DIR = ROOT / "notebooks"
NB_SRC = NB_DIR / "_source"

sys.path.insert(0, str(SRC))
import py2ipynb  # noqa: E402

NOTEBOOKS = [
    "01_Data_Preparation",
    "02_Delay_Attribution_EDA",
    "03_Right_Tail_Paradox",
    "04_Statistical_Modelling",
]


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ingest", action="store_true",
                    help="use the parquet already in data/processed")
    ap.add_argument("--no-execute", action="store_true",
                    help="build the .ipynb files but do not run them")
    args = ap.parse_args()

    t0 = time.time()

    parquet = ROOT / "data" / "processed" / "flights_2024.parquet"
    if not args.skip_ingest:
        flag = "--from-parquet" if parquet.exists() else "--skip-download"
        zips = list((ROOT / "data" / "raw").glob("On_Time_2024_*.zip"))
        if not parquet.exists() and len(zips) < 12:
            flag = ""            # let the script download what is missing
        run([sys.executable, "src/01_ingest.py"] + ([flag] if flag else []))
    elif not parquet.exists():
        print(f"missing {parquet} - run without --skip-ingest first")
        return 1

    for name in NOTEBOOKS:
        src = NB_SRC / f"{name}.py"
        out = NB_DIR / f"{name}.ipynb"
        print(f"\n=== {name} ===", flush=True)
        if args.no_execute:
            py2ipynb.build(src, out)
        else:
            py2ipynb.build(src, out)
            py2ipynb.execute(out)

    # The proposal needs one figure drawn for its printed width, which is a
    # different job from the notebook figures.
    run([sys.executable, "src/05_proposal_figure.py"])

    figs = sorted((ROOT / "figures").glob("*.png"))
    outs = sorted((ROOT / "outputs").glob("*"))
    print("\n" + "=" * 62)
    print(f"done in {time.time() - t0:,.0f}s")
    print(f"notebooks : {len(list(NB_DIR.glob('*.ipynb')))}")
    print(f"figures   : {len(figs)}  ({figs[0].name} ... {figs[-1].name})"
          if figs else "figures   : none")
    print(f"outputs   : {len(outs)} files in outputs/")
    print("=" * 62)
    print("next: python dashboard/app.py      -> http://127.0.0.1:8050")
    print("      review outputs/ and figures/  -> quoted numbers and final visuals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

