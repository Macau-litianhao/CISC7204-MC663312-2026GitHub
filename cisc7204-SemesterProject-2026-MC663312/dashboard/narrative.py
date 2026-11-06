"""The three sentences at the top of the page, under "What the data says".

A dashboard that leaves every conclusion to the reader is a dashboard that only
its author can read. These three lines are the entry point of the narrative:
each one is a claim the panels below already support, printed with the number
that carries it, recomputed for whatever filter is active.

They sit **above** the panels, not below them. They used to be a closing strip,
which meant the argument was only reachable by scrolling past eight charts - the
exact inversion of what the reference work in this field does. A reader who
bounces after ten seconds now leaves with the finding instead of with a filter
bar.

Nothing here is a constant. If a filter empties the frame, the strip says so
instead of showing a stale percentage.
"""

from __future__ import annotations

import pandas as pd

import data_access as data
from team01 import schema


def _internal_share(frame: pd.DataFrame) -> float | None:
    """Combined carrier and late-aircraft share; not causal responsibility."""
    mix = data.cause_mix(frame)
    if mix.empty or not mix["minutes"].sum():
        return None
    internal = mix.loc[mix["family"] == schema.CAUSE_FAMILY["min_carrier"], "minutes"].sum()
    return float(internal / mix["minutes"].sum())


def insights(frame: pd.DataFrame) -> list[dict]:
    """Three (label, value, sentence) triples. Missing evidence drops the line.

    The labels answer the three questions the standfirst asks, in the same order:
    who causes the minutes, how unevenly they sit, and why the average is the
    wrong summary. Time-of-day is deliberately not one of the three: the hourly
    panel already shows it, and a one-number summary of a curve that starts flat
    and ends steep would flatten exactly the shape that matters.
    """
    if frame.empty:
        return [{"label": "Nothing to report",
                 "value": "-",
                 "text": "No completed flights match this filter."}]

    items: list[dict] = []

    share = _internal_share(frame)
    if share is not None:
        items.append({
            "label": "Reported cause composition",
            "value": f"{share:.0%}",
            "text": ("of reported cause minutes are carrier delay plus late aircraft. "
                     "This descriptive grouping does not establish airline control."),
        })

    curve = data.lorenz_curve(frame)
    top_one = curve["top"].get(0.01)
    if top_one:
        items.append({
            "label": "How unevenly they sit",
            "value": f"{top_one:.0%}",
            "text": (f"of all delay minutes are carried by the worst 1% of flights "
                     f"(Gini {curve['gini']:.2f})."),
        })

    delay = frame["arr_delay"]
    mean, median = float(delay.mean()), float(delay.median())
    items.append({
        "label": "Why the average misleads",
        "value": f"{mean - median:+.1f} min",
        "text": (f"is the gap between the average ({mean:+.1f}) and the typical "
                 f"flight ({median:+.1f}). The tail moves the mean, not the median."),
    })

    return items
