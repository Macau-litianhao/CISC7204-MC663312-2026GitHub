"""Capture the running dashboard as real screenshots for the report and slides.

Run with the app already listening on 127.0.0.1:8050:

    python dashboard/shot.py

Section boundaries are read from the DOM rather than guessed in pixels, so the
crops end where a section ends instead of slicing a card in half.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures"
URL = "http://127.0.0.1:8050/"

MARKS_JS = """() => {
  const all = [...document.querySelectorAll('*')];
  const find = (prefix) => {
    for (const n of all) {
      const t = (n.textContent || '').trim();
      if (t.startsWith(prefix) && n.children.length <= 1 && t.length < 120) {
        const r = n.getBoundingClientRect();
        if (r.height > 0) return { top: r.top + window.scrollY, bottom: r.bottom + window.scrollY };
      }
    }
    return null;
  };
  const doc = document.documentElement;
  return { s1: find('01 \\u00b7'), s2: find('02 \\u00b7'), s3: find('03 \\u00b7'),
           page: Math.max(doc.scrollHeight, document.body.scrollHeight) };
}"""


def main() -> int:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=2)
        page.goto(URL, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)          # plotly draws after networkidle
        marks = page.evaluate(MARKS_JS)
        print("section marks:", marks)
        if not (marks["s1"] and marks["s2"] and marks["s3"]):
            print("could not locate every section heading")
            return 1

        width = 1440
        s1, s2, s3 = marks["s1"]["top"], marks["s2"]["top"], marks["s3"]["top"]
        shots = {
            "13_dashboard.png": (0, s1 - 18),
            "13_dashboard_charts.png": (s1 - 18, s2 - s1 - 8),
            "13_dashboard_time.png": (s2 - 18, s3 - s2 - 8),
        }
        for name, (top, height) in shots.items():
            page.screenshot(path=str(OUT / name),
                            clip={"x": 0, "y": top, "width": width, "height": height},
                            full_page=True)
            print(f"  wrote {name}  ({width}x{int(height)})")

        page.screenshot(path=str(OUT / "13_dashboard_full.png"), full_page=True)
        print(f"  wrote 13_dashboard_full.png (full page, {marks['page']} css px tall)")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
