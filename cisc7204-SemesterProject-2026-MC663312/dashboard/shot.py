"""Capture the running dashboard as real screenshots for the report and slides.

Run with the app already listening on 127.0.0.1:8050:

    python dashboard/shot.py

Section boundaries are read from the DOM rather than guessed in pixels, so the
crops end where a section ends instead of slicing a card in half. Two extra
captures were added when the report began walking a reader through the product:
the geography band, and the deep-dive panel opened, because those two are the
parts a screenshot of the first screen cannot show.
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

from pathlib import Path

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
           s4: find('04 \\u00b7'), s5: find('Model evidence'),
           page: Math.max(doc.scrollHeight, document.body.scrollHeight) };
}"""

WIDTH = 1440


def open_details(page) -> int:
    """Expand every collapsed panel; the deep dive is a <details> and starts closed."""
    return page.evaluate(
        """() => {
            let n = 0;
            document.querySelectorAll('details').forEach((d) => {
                if (!d.open) { d.open = true; n += 1; }
            });
            window.scrollTo(0, 0);
            return n;
        }"""
    )


def set_filters(page) -> bool:
    """Drive the two filters a reader would actually touch: year, then carrier.

    Dash 3 renders dcc.Dropdown as a button plus a listbox, not react-select, so the
    interaction is click, wait for the option list, click the option.
    """
    try:
        page.click("#filter-year", timeout=10000)
        page.wait_for_selector("[role='option']", timeout=10000)
        page.click("[role='option']:has-text('2024')", timeout=10000)
        page.wait_for_timeout(2500)

        page.click("#filter-carrier", timeout=10000)
        page.wait_for_selector("[role='option']", timeout=10000)
        page.click("[role='option']:has-text('American')", timeout=10000)
        page.keyboard.press("Escape")
        # The headline note redraws a beat after the cards: at 4 s the capture still carried the
        # previous sample size, so it read 45,071 flights beside cards reporting 6,162. Six
        # seconds is past the last callback in the chain.
        page.wait_for_timeout(6000)
        return True
    except Exception as exc:                     # noqa: BLE001 - report, do not crash the run
        print("  filter step failed:", str(exc).splitlines()[0])
        return False


def stamp_captures() -> int:
    """Refresh ``figures/13_dashboard.json`` so it describes the bytes on disk.

    The other figures get their sidecar written by ``viz._stamp_source`` at draw time; a
    screenshot has no draw step, so without this the hash in the manifest still describes the
    previous capture and every capture after the first one silently disagrees with it.
    """
    import hashlib
    import json

    shots = sorted(OUT.glob("13_dashboard*.png"))
    if not shots:
        return 0
    sidecar = OUT / "13_dashboard.json"
    data = {}
    if sidecar.exists():
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    data["image_sha256"] = hashlib.sha256((OUT / "13_dashboard.png").read_bytes()).hexdigest()
    data["kind"] = "real_browser_screenshot"
    data["viewport"] = "1440x900"
    data["captures"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in shots}
    sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return len(shots)


def main() -> int:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 900},
                                device_scale_factor=2)
        page.goto(URL, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)          # plotly draws after networkidle
        marks = page.evaluate(MARKS_JS)
        print("section marks:", marks)
        if not (marks["s1"] and marks["s2"] and marks["s3"]):
            print("could not locate every section heading")
            return 1

        s1, s2, s3 = marks["s1"]["top"], marks["s2"]["top"], marks["s3"]["top"]
        shots = {
            "13_dashboard.png": (0, s1 - 18),
            "13_dashboard_charts.png": (s1 - 18, s2 - s1 - 8),
            "13_dashboard_time.png": (s2 - 18, s3 - s2 - 8),
        }
        for name, (top, height) in shots.items():
            page.screenshot(path=str(OUT / name),
                            clip={"x": 0, "y": top, "width": WIDTH, "height": height},
                            full_page=True)
            print(f"  wrote {name}  ({WIDTH}x{int(height)})")

        # --- geography band, and the deep dive opened ---------------------------
        s4 = marks.get("s4")
        if s3 and s4:
            top, bottom = s3 - 18, s4["top"] - 8
            page.screenshot(path=str(OUT / "13_dashboard_places.png"),
                            clip={"x": 0, "y": top, "width": WIDTH,
                                  "height": bottom - top},
                            full_page=True)
            print(f"  wrote 13_dashboard_places.png ({WIDTH}x{int(bottom - top)})")

        opened = open_details(page)
        page.wait_for_timeout(2500)
        print(f"  opened {opened} collapsed panel(s)")
        after = page.evaluate(MARKS_JS)
        if after.get("s4") and after["page"]:
            top = after["s4"]["top"] - 18
            page.screenshot(path=str(OUT / "13_dashboard_deepdive.png"),
                            clip={"x": 0, "y": top, "width": WIDTH,
                                  "height": after["page"] - top},
                            full_page=True)
            print(f"  wrote 13_dashboard_deepdive.png ({WIDTH}x{int(after['page'] - top)})")

        page.screenshot(path=str(OUT / "13_dashboard_full.png"), full_page=True)
        print(f"  wrote 13_dashboard_full.png (full page, {after['page']} css px tall)")

        # The model-evidence block on its own: the report ties it to the RQ4 section, so it is
        # worth one clean crop instead of asking a reader to squint into a 4,000-pixel panel.
        # The height ends the crop after the across-year table rather than mid-row.
        evidence = after.get("s5")
        if evidence:
            top = evidence["top"] - 16
            height = min(1000.0, after["page"] - top)
            page.screenshot(path=str(OUT / "13_dashboard_model.png"),
                            clip={"x": 0, "y": top, "width": WIDTH, "height": height},
                            full_page=True)
            print(f"  wrote 13_dashboard_model.png ({WIDTH}x{int(height)})")

        # --- one filter change, so the product is shown responding --------------
        page.reload(wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(3500)
        if set_filters(page):
            fresh = page.evaluate(MARKS_JS)
            page.screenshot(path=str(OUT / "13_dashboard_filtered.png"),
                            clip={"x": 0, "y": 0, "width": WIDTH,
                                  "height": fresh["s1"]["top"] - 18},
                            full_page=True)
            print("  wrote 13_dashboard_filtered.png")

        browser.close()
    print("sidecar restamped for %d capture(s)" % stamp_captures())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
