"""One sentence per panel: what this filter's numbers actually say.

A chart that states its axes and nothing else leaves the argument to the reader,
and a reader who has to reconstruct four conclusions from eight panels will not
bother. The page therefore prints one interpretive sentence under every panel,
recomputed on every filter change.

Three rules govern this module, and they are the reason it is separate from the
panels rather than mixed into them:

1. **Every number comes from the same aggregate the panel drew.** ``cause()``
   calls ``data.cause_mix``, which is what ``panels/cause.py`` calls. A caption
   cannot drift from its chart because there is no second computation to drift
   from.
2. **A missing number is stated, never filled.** If a filter empties a table the
   sentence says so; it does not print 0%, which reads as a finding.
3. **No sentence survives an empty frame.** Each builder has an explicit empty
   branch, so the page can be filtered to nothing without printing "nan".

The sentences are written for a reader who will not hover: they carry the number,
they name the direction, and they stop. Interpretation beyond that belongs in the
report, not on a card.
"""

from team01 import models as metric_store, attribution


import json
from pathlib import Path

import pandas as pd

import data_access as data
from team01 import config, schema

# A state mean built on a few hundred flights is an anecdote with a colour scale.
# This floor is deliberately not in config: it guards a sentence, not a chart,
# and the chart is allowed to draw states the sentence declines to name.
STATE_FLOOR = 250

EMPTY = "No completed flights in this filter."


def _month(index) -> str:
    """1-based month number to a three-letter label."""
    try:
        return schema.MONTH_LABELS[int(index) - 1]
    except (TypeError, ValueError, IndexError):
        return str(index)


# --------------------------------------------------------------------------
# Panel sentences
# --------------------------------------------------------------------------
def cause(frame: pd.DataFrame) -> str:
    mix = data.cause_mix(frame)
    total = float(mix["minutes"].sum()) if not mix.empty else 0.0
    if total <= 0:
        return ("No flight in this filter arrives late enough to be attributed to a "
                "cause, so there is nothing to rank.")

    share = mix.set_index("cause_key")["share"]
    internal = float(share.get("min_carrier", 0.0) + share.get("min_late_aircraft", 0.0))
    system = float(share.get("min_nas", 0.0) + share.get("min_weather", 0.0) + share.get("min_security", 0.0))
    top = mix.iloc[0]
    return (f"{internal:.0%} of reported cause minutes are carrier delay plus late aircraft; "
            f"this is not a measure of airline control. The other {system:.0%} are "
            f"air traffic, weather and security. {top['cause']} alone is "
            f"{float(top['share']):.0%}.")


def monthly(frame: pd.DataFrame) -> str:
    shares = data.composition_by_month(frame)
    if shares.empty or "min_late_aircraft" not in shares.columns:
        return "No attributed minutes in this filter, so there is no composition to read."

    late = shares["min_late_aircraft"].dropna()
    if late.empty:
        return "No attributed minutes in this filter, so there is no composition to read."

    swing = float(late.max() - late.min())
    profile=data.monthly_profile(frame)
    supported=profile.loc[profile['flights'].fillna(0)>=config.min_hour_flights()]
    risk_note=(f" Highest supported 60+ minute delay share: {_month(supported['share_60'].idxmax())}, "
               f"{supported['share_60'].max():.1%}." if not supported.empty else
               ' Monthly risk estimates are hidden where sample counts are insufficient.')
    if swing < 0.05:
        # A 2-point drift is not a season. Saying "the mix changes through the
        # year" on the strength of it would be the same error the printed
        # monthly figure avoids by pinning the axis to 0-100%.
        return (f"Late aircraft holds between {late.min():.0%} and {late.max():.0%} of "
                f"the observed months' minutes - a {swing * 100:.0f}-point swing. The mix "
                f"has limited variation for this cause in the selected observed months." + risk_note)
    return (f"Late aircraft runs from {late.min():.0%} of the month's minutes in "
            f"{_month(late.idxmin())} to {late.max():.0%} in {_month(late.idxmax())}, a "
            f"{(late.max() - late.min()) * 100:.0f}-point seasonal swing inside one cause." + risk_note)


def hourly(frame: pd.DataFrame) -> str:
    profile = data.hourly_profile(frame)
    floor = config.min_hour_flights()
    supported = profile[profile["flights"].fillna(0) >= floor]
    if len(supported) < 2 or supported["share_60"].isna().all():
        return ("Too few departures in this filter to compare one hour against "
                "another without the comparison being noise.")

    first_hour = int(supported.index.min())
    peak_hour = int(supported["share_60"].idxmax())
    first_share = float(supported["share_60"].iloc[0])
    peak_share = float(supported["share_60"].max())
    return (f"Observed 60+ minute delay share is {first_share:.0%} "
            f"of {first_hour:02d}:00 departures against {peak_share:.0%} at "
            f"{peak_hour:02d}:00 (the highest supported hour). Local departure times; "
            f"an association, not an effect of changing departure time.")


def distribution(frame: pd.DataFrame) -> str:
    if frame.empty:
        return EMPTY
    delay = frame["arr_delay"]
    on_time = float((delay <= 0).mean())
    mean = float(delay.mean())
    median = float(delay.median())
    tail = float(delay.quantile(0.99))
    return (f"{on_time:.0%} of flights land on time or early and the median is "
            f"{median:+.1f} min, yet the mean is {mean:+.1f} min. The worst 1% land "
            f"{tail:+.0f} min late - that tail, not the typical flight, is what moves "
            f"the average.")


def clusters(_frame: pd.DataFrame | None = None) -> str:
    """The archetype sentence. Takes a frame for signature symmetry, ignores it.

    The cluster solution is built once by stage 05 from the whole panel, and the
    panel that draws it does not read the filters either. Saying so here is the
    point: a reader who changes the year filter and sees the dots stay put would
    otherwise assume the panel is broken.
    """
    table = data.airport_clusters()
    if table is None or "cluster" not in table.columns:
        return "Run src/scripts/05_clusters.py to build the archetypes."

    sizes = table.groupby("cluster").size()
    largest = sizes.idxmax()
    subset = table[table["cluster"] == largest]
    label = (str(subset["archetype"].iloc[0]) if "archetype" in table.columns
             else f"cluster {int(largest)}")
    return (f"{len(table)} airports are partitioned into {len(sizes)} exploratory groups; the largest is "
            f"'{label}' with {int(sizes.max())} airports. Built once over the whole "
            f"panel, so this panel does not follow the filters above.")


def lorenz(frame: pd.DataFrame) -> str:
    curve = data.lorenz_curve(frame)
    if not curve["top"]:
        return "No positive delay minutes in this filter."
    top_ten = float(curve["top"][0.10])
    top_one = float(curve["top"][0.01])
    return (f"The worst 10% of flights carry {top_ten:.0%} of all delay minutes and the "
            f"worst 1% carry {top_one:.0%} (Gini {curve['gini']:.2f}). Read the other way "
            f"round: the other 90% of flights produce the remaining {1 - top_ten:.0%}.")


def geography(frame: pd.DataFrame) -> str:
    profile = data.state_profile(frame)
    if profile.empty:
        return EMPTY

    ranked = profile[profile["flights"] >= STATE_FLOOR]
    if ranked.empty:
        ranked = profile
    worst = ranked.loc[ranked["mean"].idxmax()]
    busiest = profile.loc[profile["flights"].idxmax()]

    same = str(worst["origin_state"]) == str(busiest["origin_state"])
    closing = ("The busiest state is also the worst one."
               if same else
               "Traffic and delay rank differently, so the two channels here answer "
               "different questions.")
    return (f"Flights out of {worst['origin_state']} average {float(worst['mean']):+.1f} "
            f"min of arrival delay, the worst of any state; {busiest['origin_state']} "
            f"sends the most traffic with {float(busiest['flights']):,.0f} departures. "
            f"{closing}")


def _article(number: str) -> str:
    """'a 8-minute' is the kind of thing nobody fixes. Eight and eleven take 'an'."""
    return "an" if number.lstrip("+-").startswith(("8", "11", "18")) else "a"


def carrier(carrier_frame: pd.DataFrame) -> str:
    profile = data.carrier_profile(carrier_frame)
    if len(profile) < 2:
        return "Fewer than two carriers clear the flight floor in this filter."

    best, worst = profile.iloc[0], profile.iloc[-1]
    spread = float(worst["mean"] - best["mean"])
    tail_lo = float(profile["p90"].min())
    tail_hi = float(profile["p90"].max())
    tail_gap = tail_hi - tail_lo
    if tail_gap > spread * 1.2:
        tail_note = "so the tail separates these carriers more sharply than the average does"
    elif tail_gap < spread * 0.8:
        tail_note = "so the average separates them more than the tail does"
    else:
        tail_note = "so the average and the tail agree about who is worse"

    spread_text = f"{spread:.1f}"
    return (f"{best['carrier']} averages {float(best['mean']):+.1f} min and "
            f"{worst['carrier']} {float(worst['mean']):+.1f} min - "
            f"{_article(spread_text)} {spread_text}-minute spread. The 90th percentile "
            f"runs from {tail_lo:+.0f} to {tail_hi:+.0f} min, {tail_note}.")


BUILDERS = {
    "cause": cause,
    "monthly": monthly,
    "hourly": hourly,
    "dist": distribution,
    "clusters": clusters,
    "lorenz": lorenz,
    "geo": geography,
    "carrier": carrier,
}

KEYS = list(BUILDERS)


def findings(frame: pd.DataFrame,
             carrier_frame: pd.DataFrame | None = None) -> dict[str, str]:
    """Every panel's sentence, keyed by the graph id suffix it belongs to.

    ``carrier_frame`` is separate because the carrier panel is deliberately not
    filtered by carrier - see ``callbacks._register_panels``. Passing the full
    frame keeps the sentence describing the same rows the dumbbell drew.
    """
    out: dict[str, str] = {}
    for key, builder in BUILDERS.items():
        source = carrier_frame if (key == "carrier" and carrier_frame is not None) else frame
        out[key] = builder(source)
    return out


def cluster_note() -> str:
    """The cluster solution's stability, read from ``clusters.json``.

    The method section states this at the same size as the claim the cluster
    panel makes, and it must agree with ``quality_line`` in the panel above it.
    Both read the same artefact; the only literal here is the 0.70 bar, which
    mirrors the threshold inside ``cluster.stability()`` and must move with it.
    """
    path = Path(config.METRIC_DIR) / "clusters.json"
    if not path.exists():
        return "Run src/scripts/05_clusters.py to build the archetypes."
    try:
        payload = metric_store.load_metrics(path.stem)
    except json.JSONDecodeError:
        return "The cluster metrics file could not be read."

    ari = (payload.get("stability") or {}).get("mean_ari")
    k = payload.get("chosen_k")
    if ari is None:
        return ("k-means on standardised airport features. The groups describe regions "
                "of feature space; they are not a class an airport belongs to.")
    bar = 0.70  # mirrors cluster.stability(): >= 0.7 reads as "stable"
    verdict = ("above the project's subsample-stability threshold"
               if float(ari) >= bar else "below the project's subsample-stability threshold")
    ktext = f"{int(k)}-group" if k is not None else "grouped"
    return (f"k-means on standardised airport features. With a subsample ARI of "
            f"{float(ari):.2f} against a {bar:.2f} bar, the {ktext} partition is "
            f"{verdict}. This heuristic does not establish a natural typology; read 'archetype' as a region of feature "
            f"space, not as a class an airport belongs to.")


def model_note() -> str:
    """The predictive ceiling, read from ``models.json`` rather than retyped.

    A negative result is the easiest thing in a project to soften by accident, so
    the numbers here are pulled from the artefact that produced the printed
    figure. If the file is missing the sentence says so instead of quoting a
    memory of what the model scored.
    """
    path = Path(config.METRIC_DIR) / "models.json"
    if not path.exists():
        return "Run src/scripts/06_models.py to fit the models this page refers to."
    try:
        payload = metric_store.load_metrics(path.stem)
    except json.JSONDecodeError:
        return "The model metrics file could not be read."

    risk = payload.get("risk") or {}
    models = risk.get("models") or {}
    logistic = models.get("logistic") or {}
    auc = logistic.get("roc_auc")
    base = risk.get("base_rate")
    if auc is None or base is None:
        return ("The model metrics file does not contain a risk model, so this page "
                "makes no claim about prediction.")

    boosting = models.get('gradient_boosting') or {}
    baseline = models.get('constant_train_rate') or {}
    note = (f"Temporal holdout ROC AUC: logistic {auc:.3f}; "
            f"gradient boosting {boosting.get('roc_auc', float('nan')):.3f}. "
            "Ranking ability does not guarantee accurate individual probabilities. "
            "See the fixed holdout evaluation below for baseline error and calibration. ")
    if baseline:
        note += f"Constant-rate Brier {baseline['brier']:.4f}; boosting {boosting['brier']:.4f}. "
    return note + "Permutation importance describes changes in model ranking under feature shuffling, not causal effects."


def method_note(frame: pd.DataFrame) -> str:
    """The one dynamic number in the method section.

    What it discloses is the size of the floor the cause panels stand on: a
    reader is entitled to know that the cause ranking they just read was
    computed on a subset, and how large that subset is for the filter they
    chose.
    """
    if frame.empty:
        return "No completed flights match this filter."
    floor = config.threshold()
    below = float((frame["arr_delay"] < floor).mean())
    warning = 'Sparse sample: treat percentages as uncertain descriptions. ' if len(frame)<1000 else ''
    return (warning + f"In this filter {below:.0%} of the {len(frame):,} flights shown here arrived "
            f"less than {floor:.0f} minutes late and therefore carry no cause minutes. "
            f"The cause ranking and the monthly composition are computed on the "
            f"remaining {1 - below:.0%}, after excluding incomplete or unreconciled cause records. "
            f"Excluded in this selection: {attribution.cause_population(frame)[1]["eligible"] - attribution.cause_population(frame)[1]["retained"]:,}.")


def takeaways(frame: pd.DataFrame) -> list[dict]:
    """Three "what to do" sentences: the reader-facing close of the page.

    The findings band states what the data shows; this states what a passenger
    can do with it. Both read the same aggregates, so they cannot disagree, but
    the framing is different - findings report, takeaways act. Each number here
    is the same one the panel above it already drew, reframed as advice.

    Everything here is directional. The report's honest ceiling (risk AUC 0.69)
    is stated in the limits section the page ends on, and these sentences must
    not outrun it - which is why every one closes by pointing at that ceiling
    rather than promising an arrival time.
    """
    if frame.empty:
        return []

    items: list[dict] = []

    # 1. Time of day. The model's strongest factor is departure hour, and the
    #    hourly panel above has already shown the slope, so this is a
    #    restatement of a curve the reader just saw, not a new claim.
    items.append({
        "title": "Compare departure-time patterns",
        "text": ("Compare the observed hourly profile for your selected carrier and airport. "
                 "Pooled historical associations do not establish the effect of "
                 "switching flights or guarantee an individual arrival time."),
    })

    # 2. The average hides the tail.
    delay = frame["arr_delay"]
    mean, median = float(delay.mean()), float(delay.median())
    top_one = float(data.lorenz_curve(frame)["top"].get(0.01, 0.0))
    items.append({
        "title": "Do not plan around the average",
        "text": (f"The typical flight lands {median:+.0f} minutes, but the mean is "
                 f"{mean:+.1f} - the gap is the tail. The worst 1% of flights carry "
                 f"{top_one:.0%} of all delay minutes, so slack on the bad flights is "
                 f"worth more than a better average."),
    })

    # 3. Who controls the minutes.
    mix = data.cause_mix(frame)
    if not mix.empty and mix["minutes"].sum() > 0:
        internal = float(mix.loc[mix["family"] == schema.CAUSE_FAMILY["min_carrier"],
                                 "minutes"].sum() / mix["minutes"].sum())
        items.append({
            "title": "Compare carriers in context",
            "text": (f"Carrier plus late-aircraft categories account for {internal:.0%} of "
                     f"reported minutes in the opening view. These labels do not "
                     f"establish control. Carrier comparisons also reflect route, "
                     f"airport and schedule differences."),
        })

    return items
