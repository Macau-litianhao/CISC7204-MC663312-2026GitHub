"""Entry point for the interactive dashboard.

    python dashboard/app.py            # http://127.0.0.1:8050
    python dashboard/app.py --debug    # auto-reload while editing callbacks

Layout, callbacks and data access are separate modules on purpose: the layout is
static, the callbacks are pure functions of the filtered frame, and the data
layer is the only part that touches the filesystem. That split is what makes
``pytest tests`` able to check the figure builders without starting a server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                 # dashboard modules
sys.path.insert(0, str(HERE.parent / "src"))  # team01 package

import dash  # noqa: E402

import callbacks  # noqa: E402
import data_access  # noqa: E402
import layouts  # noqa: E402
from team01 import config  # noqa: E402


def create_app(meta: dict | None = None):
    """Build the Dash application. Importable, so tests can call it."""
    info = meta or data_access.available()

    app = dash.Dash(
        __name__,
        title="US Domestic Flight Delay Drivers - Team 01",
        update_title=None,
        meta_tags=[{"name": "viewport",
                    "content": "width=device-width, initial-scale=1"}],
    )
    # Dash's default shell leaves <html> without a language, which makes a
    # screen reader guess (and guess American English only by luck).
    app.index_string = """<!DOCTYPE html>
<html lang="en">
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>"""
    app.layout = layouts.build(info)
    callbacks.register(app)
    return app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--port", type=int, default=int(config.get("dashboard.port", 8050)))
    parser.add_argument("--host", default=str(config.get("dashboard.host", "127.0.0.1")))
    args = parser.parse_args()

    try:
        app = create_app()
    except data_access.DataUnavailable as error:
        print("No flight table available for the dashboard.\n")
        print(error)
        print("\nBuild the smoke fixture first:")
        print("  python src/scripts/00_make_sample.py")
        print("  TEAM01_MODE=sample python src/scripts/05_clusters.py")
        return 1

    print(config.summarise())
    print(f"serving on http://{args.host}:{args.port}")
    app.run(debug=args.debug, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
