"""Record a walkthrough of the running dashboard as an animated GIF.

    # with the app already listening on 127.0.0.1:8050
    python dashboard/demo.py

Why a GIF and not a video: PowerPoint plays a GIF inside the slideshow without a
media codec, and the file survives a copy onto a machine that has none. Every
frame is a real screenshot of the live app - the year menu opens, 2024 is typed
and picked, a carrier is added, the charts redraw, and the page is then walked to
the bottom - so the clip is evidence, not a mock-up. Nothing is drawn on top of
the frames after the fact; what you see is what the browser rendered.

Two capture details are deliberate:

* the dropdown is driven through its search box rather than by clicking an option
  far down the list. The list virtualises and shows roughly four rows at a time,
  so a screenshot of it open mid-list looks like a clipped menu. Typing narrows
  the list to one row, which reads cleanly and is also the interaction a reader
  actually uses on 11 years of data.
* the scroll targets are section headings, not pixel offsets, so the frames stay
  aligned when the layout grows.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures" / "13_dashboard_demo.gif"
URL = "http://127.0.0.1:8050/"

WIDTH, HEIGHT = 1280, 800
SCALE = 1.5
FRAMES: list[Image.Image] = []


def grab(page, label: str) -> None:
    shot = page.screenshot()
    FRAMES.append(Image.open(io.BytesIO(shot)).convert("RGB"))
    print(f"  frame {len(FRAMES):>2}  {label}")


def scroll_to_mark(page, prefix: str, offset: int = 90) -> str:
    """Put the section whose heading starts with ``prefix`` near the top of the viewport."""
    moved = page.evaluate(
        """([prefix, offset]) => {
            const all = [...document.querySelectorAll('*')];
            for (const n of all) {
                const t = (n.textContent || '').trim();
                if (t.startsWith(prefix) && n.children.length <= 1 && t.length < 120) {
                    const r = n.getBoundingClientRect();
                    if (r.height > 0) {
                        const y = r.top + window.scrollY - offset;
                        window.scrollTo(0, Math.max(0, y));
                        return Math.round(y);
                    }
                }
            }
            return -1;
        }""",
        [prefix, offset],
    )
    return str(moved)


def open_menu(page, dropdown_id: str) -> None:
    page.click(f"#{dropdown_id}", timeout=15000)
    page.wait_for_selector("[role='option']", timeout=15000)
    page.wait_for_timeout(500)


def type_in_menu(page, query: str) -> None:
    """The Dash 3 dropdown ships a search box; typing in it is the real interaction."""
    page.fill("input[placeholder='Search']", query)
    page.wait_for_timeout(700)


def choose(page, option: str, settle: int) -> None:
    page.locator(f"[role='option']:has-text('{option}')").first.click(timeout=15000)
    page.wait_for_timeout(settle)


def main() -> int:
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT},
                                device_scale_factor=SCALE)
        page.goto(URL, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(5000)
        grab(page, "first paint: all years, all carriers")

        # --- 1. the year filter, driven through its search box ------------------
        open_menu(page, "filter-year")
        grab(page, "year menu open, search box ready")

        type_in_menu(page, "2024")
        grab(page, "2024 typed: the eleven years narrow to one row")

        choose(page, "2024", 3200)
        grab(page, "2024 applied: headline, tile strip and charts redraw")

        # --- 2. one carrier on top, so the page is a slice, not the whole corpus -
        open_menu(page, "filter-carrier")
        grab(page, "carrier menu open: twenty reporting carriers")

        type_in_menu(page, "American")
        choose(page, "American", 4500)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1200)
        grab(page, "2024 + American: 6,162 flights, every view follows the slice")

        # --- 3. walk the product, one section per frame -------------------------
        for mark, label in (
            ("01 \u00b7", "01 arrival patterns: the distribution behind the median"),
            ("02 \u00b7", "02 time patterns: hour of day and month of year"),
            ("03 \u00b7", "03 where and carriers: the airport map and the carrier bars"),
        ):
            y = scroll_to_mark(page, mark)
            page.wait_for_timeout(1800)
            grab(page, f"{label}  (scrollY {y})")

        # the deep dive starts collapsed; open it before framing it
        opened = page.evaluate(
            """() => { let n = 0;
                document.querySelectorAll('details').forEach((d) => { if (!d.open) { d.open = true; n += 1; } });
                return n; }"""
        )
        page.wait_for_timeout(2500)
        y = scroll_to_mark(page, "04 \u00b7")
        page.wait_for_timeout(2000)
        grab(page, f"04 deep dive, {opened} panel(s) opened: model evidence  (scrollY {y})")

        page.evaluate("() => document.getElementById('method').scrollIntoView()")
        page.wait_for_timeout(1800)
        grab(page, "method: how to read the numbers, and what they cannot say")

        # close the loop where it started
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)
        grab(page, "back to the headline")

        browser.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 1200 ms a frame reads as a deliberate demonstration rather than a glitch.
    paletted = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in FRAMES]
    paletted[0].save(OUT, save_all=True, append_images=paletted[1:],
                     duration=1200, loop=0, optimize=True, disposal=2)
    print(f"\nwrote {OUT.name}: {len(FRAMES)} frames, "
          f"{OUT.stat().st_size / 1024:.0f} KB, {paletted[0].size[0]}x{paletted[0].size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
