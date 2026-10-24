"""
py2ipynb.py - Turn a `# %%` cell-marked Python file into an executed notebook.

Why this exists
---------------
Writing raw .ipynb JSON by hand is unreadable in version control. We author the
analysis as ordinary readable .py files with cell markers (the jupytext
convention) and generate the graded .ipynb from them:

    # %% [markdown]      -> markdown cell
    # %%                 -> code cell

Usage
-----
    python src/py2ipynb.py notebooks/_source/02_Delay_Attribution_EDA.py \
        -o notebooks/02_Delay_Attribution_EDA.ipynb --execute

The --execute flag runs every cell through a real kernel so the delivered
notebook already contains its outputs (no "please run all" surprises).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


def parse_cell_file(path: Path):
    """Split a `# %%` marked file into (cell_type, source) pairs."""
    cells, kind, buf = [], None, []

    def flush():
        if kind is None:
            return
        text = "\n".join(buf).strip("\n")
        if not text.strip():
            return
        if kind == "markdown":
            lines = []
            for line in text.split("\n"):
                if line.startswith("# "):
                    lines.append(line[2:])
                elif line.strip() == "#":
                    lines.append("")
                else:
                    lines.append(line)
            text = "\n".join(lines)
        cells.append((kind, text.strip() + "\n"))

    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("# %%"):
            flush()
            buf = []
            kind = "markdown" if "markdown" in line else "code"
        else:
            buf.append(line)
    flush()
    return cells


def build(src: Path, out: Path) -> Path:
    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(s) if k == "markdown" else nbf.v4.new_code_cell(s)
        for k, s in parse_cell_file(src)
    ]
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, out)
    print(f"[built] {out}  ({len(nb['cells'])} cells)")
    return out


def execute(path: Path, timeout: int = 1200) -> None:
    nb = nbf.read(path, as_version=4)
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3",
                            resources={"metadata": {"path": str(path.parent)}})
    client.execute()
    nbf.write(nb, path)
    print(f"[executed] {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    out = build(args.src, args.out)
    if args.execute:
        execute(out, args.timeout)


if __name__ == "__main__":
    main()
