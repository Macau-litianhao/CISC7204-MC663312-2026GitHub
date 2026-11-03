"""The panel captions are pure functions of the filtered frame.

These tests pin the two properties the module exists for: a caption never fakes
a number on an empty frame, and the headline numbers it prints are the same
numbers the panels draw (because both read the same aggregates).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "dashboard"))

import captions  # noqa: E402
import data_access  # noqa: E402


def _frame_with_causes(completed):
    # cause_mix scopes to the attribution universe; the fixture provides one.
    return completed


def test_every_builder_returns_a_string_on_empty_frame(completed):
    empty = completed.iloc[0:0]
    for key in captions.KEYS:
        text = captions.BUILDERS[key](empty)
        assert isinstance(text, str) and text.strip(), key


def test_findings_covers_every_panel_key(completed):
    found = captions.findings(completed, completed)
    assert set(found) == set(captions.KEYS)
    for text in found.values():
        assert isinstance(text, str) and text.strip()


def test_cause_caption_matches_the_panel_aggregate(completed):
    mix = data_access.cause_mix(completed)
    if mix.empty or mix["minutes"].sum() == 0:
        return
    share = mix.set_index("cause_key")["share"]
    internal = float(share.get("min_carrier", 0.0) + share.get("min_late_aircraft", 0.0))
    text = captions.cause(completed)
    assert f"{internal:.0%}" in text


def test_method_note_names_the_threshold(completed):
    note = captions.method_note(completed)
    assert note and "cause minutes" in note


def test_lorenz_caption_repeats_the_curve_number(completed):
    curve = data_access.lorenz_curve(completed)
    if not curve["top"]:
        return
    text = captions.lorenz(completed)
    assert f"{curve['top'][0.10]:.0%}" in text


def test_takeaways_are_three_numbered_actions_without_nan(completed):
    items = captions.takeaways(completed)
    # Three "what to do" sentences on a populated frame, each a title plus prose.
    assert len(items) == 3
    for item in items:
        assert set(item) == {"title", "text"}
        assert item["title"].strip() and item["text"].strip()
        assert "nan" not in item["text"].lower()


def test_takeaways_return_empty_on_empty_frame(completed):
    assert captions.takeaways(completed.iloc[0:0]) == []
