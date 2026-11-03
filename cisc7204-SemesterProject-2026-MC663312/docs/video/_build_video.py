"""
Build the Team 01 introductory-video slide deck (and, on demand, the mp4).

Run from the repository root:

    D:/Anaconda/python.exe docs/video/_build_video.py            # deck only
    D:/Anaconda/python.exe docs/video/_build_video.py --video    # deck + mp4

Deck-only mode (the default) does:

  1. builds ``docs/video/Team01_Slides.pptx``  (19 slides, 16:9)
  2. exports the slides to 1920x1080 PNGs through PowerPoint COM
  3. saves ``docs/video/Team01_Slides.pdf`` for quick review

``--video`` additionally runs:

  4. makes one narration track per slide
        - if ``docs/video/assets/narration/NN.wav|mp3`` exists it is used as-is
          (the human-voice route)
        - otherwise edge-tts synthesises it (the AI-voice route), and the rate is
          calibrated so the whole deck lands inside 4:45-5:00
  5. writes ``docs/video/Team01_IntroVideo.srt``
  6. muxes image + audio per slide and concatenates to
     ``docs/video/Team01_IntroVideo.mp4`` (1920x1080, H.264 + AAC)

The four course-mandated elements - group photo, six student IDs and full names,
project title, course code with year and semester - are laid out on slides 1, 2
and 19 and are therefore on screen no matter which route the audio takes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_DIR = os.path.join(ROOT, "docs", "video")
ASSETS = os.path.join(VIDEO_DIR, "assets")
NARRATION = os.path.join(ASSETS, "narration")
SLIDE_PNG = os.path.join(VIDEO_DIR, "_slides_png")
# scratch space: a fresh directory per run, so nothing has to be deleted
WORK = tempfile.mkdtemp(prefix="team01_video_")

PPTX = os.path.join(VIDEO_DIR, "Team01_Slides.pptx")
PDF = os.path.join(VIDEO_DIR, "Team01_Slides.pdf")
MP4 = os.path.join(VIDEO_DIR, "Team01_IntroVideo.mp4")
SRT = os.path.join(VIDEO_DIR, "Team01_IntroVideo.srt")

GROUP_PHOTO_CANDIDATES = [
    os.path.join(ASSETS, "group_photo.jpg"),
    os.path.join(ASSETS, "group_photo.png"),
    os.path.join(ASSETS, "group_photo.jpeg"),
]

# --------------------------------------------------------------------------
# house style
# --------------------------------------------------------------------------

NAVY = RGBColor(0x17, 0x32, 0x4D)
NAVY_LIGHT = RGBColor(0x2A, 0x4C, 0x71)
ACCENT = RGBColor(0xE7, 0x6F, 0x51)
INK = RGBColor(0x1B, 0x1B, 0x1B)
MUTED = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAPER = RGBColor(0xF6, 0xF8, 0xFA)
HAIR = RGBColor(0xD5, 0xDC, 0xE3)

FONT = "Arial"
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

TITLE = "US Domestic Flight Delay Drivers"
SUBTITLE = ("Attribution, within-day cascade, airport archetypes "
            "and an interactive communication layer")
COURSE = "CISC7204  Data Science and Data Visualization"
TEAM = "Class K — Team 01"
YEAR = "2026/2027  Semester 1"

MEMBERS = [
    ("AO KIT I", "MC660004", "Team Coordinator · Project Tracker"),
    ("LI YING FANG", "MC661599", "Project Developer (lead)"),
    ("HO MAN HOU", "MC661647", "Team Scribe"),
    ("WU PEI YE", "MC661846", "Team Reporter · Team Liaison"),
    ("LI TIAN HAO", "MC663312", "Project Analyst · Quality Reviewer"),
    ("SAVIDI AVRAM", "MC664364", "Project Developer"),
]

# Individual headshots extracted from "CISC7204 Class K-Team 01 Project Work Plan.pptx",
# matched to names by the slide's own grid position (slide 2 names <-> slide 9 photos).
MEMBER_PHOTOS = {
    "AO KIT I": os.path.join(ASSETS, "members", "AO_KIT_I.png"),
    "LI YING FANG": os.path.join(ASSETS, "members", "LI_YING_FANG.png"),
    "HO MAN HOU": os.path.join(ASSETS, "members", "HO_MAN_HOU.png"),
    "WU PEI YE": os.path.join(ASSETS, "members", "WU_PEI_YE.png"),
    "LI TIAN HAO": os.path.join(ASSETS, "members", "LI_TIAN_HAO.png"),
    "SAVIDI AVRAM": os.path.join(ASSETS, "members", "SAVIDI_AVRAM.png"),
}

# --------------------------------------------------------------------------
# the deck: one entry per slide
# --------------------------------------------------------------------------
# kind: 'title' | 'team' | 'bullets' | 'figure' | 'fullfigure' | 'table' | 'close'

SLIDES: list[dict] = [
    {
        "kind": "title",
        "narration": (
            "CISC7204, Data Science and Data Visualization, semester project, "
            "Class K, Team 01. Our project is US Domestic Flight Delay Drivers: "
            "attribution, within-day cascade, airport archetypes, and an "
            "interactive communication layer."
        ),
    },
    {
        "kind": "team",
        "narration": (
            "We are six members. AO KIT I, M C six six zero zero zero four. "
            "LI YING FANG, M C six six one five nine nine. HO MAN HOU, M C six "
            "six one six four seven. WU PEI YE, M C six six one eight four six. "
            "LI TIAN HAO, M C six six three three one two. SAVIDI AVRAM, M C six "
            "six four three six four."
        ),
    },
    {
        "kind": "bullets",
        "title": "Why a single average is not an answer",
        "kicker": "The problem",
        "bullets": [
            "63,079,392 reported rows, 2015-2024; 61,689,698 completed flights, 20 carriers.",
            "The median flight arrives about six minutes early; the mean is about seven minutes late.",
            "A traveller wants the chance of losing an afternoon; an airline needs to know where delay minutes originate.",
        ],
        "note": "So we report cause mix, typical delay, the tail, within-day propagation and factor ranking separately.",
        "narration": (
            "Every year the United States publishes one average delay. A single "
            "number hides very different experiences. On our panel the median "
            "flight arrives about six minutes early while the mean is about seven "
            "minutes late, because a heavy tail pulls the average upward. So a "
            "traveller asking about the chance of losing an afternoon, and an "
            "airline asking where delay minutes originate, need two different "
            "answers. We keep them separate."
        ),
    },
    {
        "kind": "bullets",
        "title": "Four research questions",
        "kicker": "What we ask",
        "bullets": [
            "RQ1  How are delay minutes distributed across the five BTS causes, and is that split stable across ten years?",
            "RQ2  How much of the delay seen in an hour is inherited from earlier legs of the same aircraft?",
            "RQ3  Do airports fall into delay-risk archetypes, and is that grouping stable?",
            "RQ4  Can a web tool let a non-specialist act on the answer?",
        ],
        "narration": (
            "We ask four questions. One: how are reported delay minutes "
            "distributed across the five causes published by the Bureau of "
            "Transportation Statistics, and is that split stable across ten "
            "years? Two: how much of the delay observed in a given hour is "
            "inherited from earlier legs? Three: do airports fall into "
            "delay-risk archetypes? Four: can a web tool let a traveller act on "
            "the answer?"
        ),
    },
    {
        "kind": "table",
        "title": "Data context and sources",
        "kicker": "United States · commercial aviation",
        "headers": ["ID", "Source", "Role in the analysis"],
        "rows": [
            ["D1", "BTS Reporting Carrier On-Time Performance", "Flight-level records, 63.1M rows, 2015-2024"],
            ["D2", "BTS Delay Cause (national monthly)", "Independent cross-check on our attribution"],
            ["D3", "NOAA Integrated Surface Database", "Hourly weather at the 40 busiest origin airports"],
            ["D4", "OurAirports airports.csv", "Coordinates, state, airport type for the maps"],
            ["D5", "BTS carrier decode table", "Carrier codes to full carrier names"],
        ],
        "note": "Region: the United States - 50 states plus the District of Columbia. Every source is public and needs no key.",
        "narration": (
            "The region is the United States and the domain is commercial "
            "aviation. Five public datasets feed the work: the flight-level "
            "on-time records, the national delay-cause aggregates used as an "
            "independent cross-check, hourly surface weather from NOAA, the "
            "airport reference file, and the carrier decode table. Every link is "
            "public and none needs an API key."
        ),
    },
    {
        "kind": "bullets",
        "title": "One pipeline, six stages, one command",
        "kicker": "How the work is built",
        "bullets": [
            "1  Acquire and validate  -  ten annual files, schema, duplicates, missingness.",
            "2  Attribute  -  split delay minutes across the five BTS causes.",
            "3  Analyse the tail  -  percentiles, concentration, typical versus mean.",
            "4  Cascade  -  trace inherited delay through the operating day.",
            "5  Cluster and model  -  airport archetypes, severe-delay risk, factor ranking.",
            "6  Communicate  -  linked dashboard and a narrative page for a non-specialist.",
        ],
        "note": "Every stage is a script, not a notebook cell. A 53-test suite pins each number to its source file.",
        "narration": (
            "The work runs as six stages. Acquire and validate; attribute the "
            "delay minutes; analyse the tail; trace the within-day cascade; "
            "cluster airports and model severe-delay risk; then communicate. "
            "Each stage is a script rather than a notebook cell, so one command "
            "regenerates every figure, and a fifty-three test suite pins each "
            "number to the file it came from."
        ),
    },
    {
        "kind": "figure",
        "title": "Finding 1  Three quarters of delay is airline-controlled",
        "kicker": "RQ1 · cause attribution",
        "image": os.path.join("figures", "01_cause_waffle.png"),
        "bullets": [
            "73.3% airline-controlled against 26.7% system-imposed.",
            "Bootstrap 95% interval: 73.0% to 73.6%.",
            "Stable across the decade: the yearly internal share moves only between 69.7% (2018) and 77.4% (2022).",
        ],
        "narration": (
            "Finding one. Seventy-three point three percent of delay minutes are "
            "attributed to causes the airline controls, against twenty-six point "
            "seven percent imposed by the system. The bootstrap ninety-five "
            "percent interval is seventy-three point zero to seventy-three point "
            "six. The split is stable: across ten years the internal share moves "
            "only between sixty-nine point seven and seventy-seven point four "
            "percent."
        ),
    },
    {
        "kind": "figure",
        "title": "Finding 2  A few flights carry most of the delay",
        "kicker": "The tail, not the mean",
        "image": os.path.join("figures", "05_lorenz.png"),
        "bullets": [
            "Gini index of delay minutes: 0.876.",
            "The mean is seven minutes late; the median flight is early.",
            "Every headline is recomputed with the pandemic years excluded, so the shift is reported, not hidden.",
        ],
        "narration": (
            "Finding two. Delay is extremely concentrated. The Gini index of "
            "delay minutes is nought point eight seven six, which means a small "
            "share of flights carries most of the total. That is why we report "
            "percentiles and the tail rather than an average, and why every "
            "headline statistic is recomputed with the pandemic years excluded, "
            "so the size of the shift is reported rather than hidden."
        ),
    },
    {
        "kind": "figure",
        "title": "Finding 3  Delay is inherited within the operating day",
        "kicker": "RQ2 · the cascade",
        "image": os.path.join("figures", "08_cascade_hour.png"),
        "bullets": [
            "Late aircraft is the largest single cause, at 38.8% of delay minutes.",
            "6.0% of flights sit in a rotation that already carries positive delay.",
            "17.1% of those minutes are inherited from an earlier leg.",
        ],
        "narration": (
            "Finding three. Late aircraft is the largest single cause at "
            "thirty-eight point eight percent. We turn that share into a "
            "mechanism: six percent of flights sit in an aircraft rotation that "
            "already carries positive delay, and seventeen point one percent of "
            "those minutes are inherited from an earlier leg. Delay propagates "
            "through the operating day, and it accumulates toward the evening."
        ),
    },
    {
        "kind": "figure",
        "title": "Finding 4  Five airport profiles - reported as unstable",
        "kicker": "RQ3 · archetypes",
        "image": os.path.join("figures", "10_cluster_scatter.png"),
        "bullets": [
            "k = 5 over 195 airports, silhouette 0.2045.",
            "Ward linkage and a PCA projection are shown as cross-checks.",
            "Mean adjusted Rand index 0.69 against a 0.70 threshold: the solution is reported as unstable.",
        ],
        "narration": (
            "Finding four. Airports sort into five delay profiles at a "
            "silhouette of nought point two zero four five, over one hundred and "
            "ninety-five airports. We show the silhouette curve, a Ward linkage "
            "cross-check and a stability score, and we report the solution as "
            "unstable - mean adjusted Rand index nought point six nine against "
            "our nought point seven zero threshold - because an unstable "
            "clustering describes a sample, not airports."
        ),
    },
    {
        "kind": "figure",
        "title": "Finding 5  Risk can be ranked, not promised",
        "kicker": "RQ4 · modelling",
        "image": os.path.join("figures", "11_importance.png"),
        "bullets": [
            "Severe delay defined as 60 minutes or more; base rate 6.1%.",
            "Held-out AUC 0.685 (logistic) and 0.691 (gradient boosting).",
            "Departure hour carries 49.9% of the ranked importance; the full model explains R-squared 0.022.",
        ],
        "narration": (
            "Finding five. Predicting an arrival delay of sixty minutes or more, "
            "the held-out AUC is nought point six eight five for logistic "
            "regression and nought point six nine one for gradient boosting, at "
            "a six point one percent base rate. Departure hour carries forty-"
            "nine point nine percent of the ranked importance. The model ranks "
            "risk; it does not promise an arrival time."
        ),
    },
    {
        "kind": "fullfigure",
        "title": "The dashboard: one linked view, upper half",
        "kicker": "Interactive communication layer",
        "image": os.path.join("docs", "proposal", "figures", "13_dashboard_part1.png"),
        "note": "Overview first, then zoom and filter, then details on demand. Year, carrier and month filters recompute every metric live.",
        "narration": (
            "All of this is delivered through one linked dashboard. It opens on "
            "the national overview, exposes three filters, and reveals "
            "flight-level detail only on selection. Change the year, the carrier "
            "or the month and every panel recomputes live rather than showing a "
            "pre-rendered picture."
        ),
    },
    {
        "kind": "fullfigure",
        "title": "The dashboard: lower half",
        "kicker": "Geography, carriers, takeaway and limits",
        "image": os.path.join("docs", "proposal", "figures", "13_dashboard_part2.png"),
        "note": "The lower half carries the map, the carrier comparison, the passenger takeaway, and a method section that states what the page cannot say.",
        "narration": (
            "The lower half carries the geography, the carrier comparison and "
            "the passenger takeaway, followed by a method section that states "
            "plainly what the page cannot say. Five findings, one pipeline, one "
            "view - and a usability check run with a non-specialist on three "
            "timed tasks."
        ),
    },
    {
        "kind": "bullets",
        "title": "How we judge whether it is good",
        "kicker": "Success criteria",
        "bullets": [
            "Counts reconcile across all ten annual files; zero duplicate rate; the 15-minute threshold stated wherever cause shares appear.",
            "All four questions answered, with intervals and stability scores; nothing presented as causal without support.",
            "Every model reports a baseline, a held-out metric, and what it ranks rather than predicts.",
            "Every figure names the question it answers and the encoding it uses.",
            "Usability is measured on three timed tasks with a non-specialist - not asserted.",
        ],
        "narration": (
            "Quality is checked against written criteria rather than asserted. "
            "Counts reconcile across all ten annual files. All four questions "
            "are answered with intervals and stability scores. Every model "
            "reports a baseline, a held-out metric and an explicit statement of "
            "what it ranks rather than predicts. Every figure names the question "
            "it answers and the encoding it uses. And usability is measured on "
            "three timed tasks with a non-specialist."
        ),
    },
    {
        "kind": "roles",
        "title": "Eight course roles across six members",
        "kicker": "Teamwork · Work Plan 1",
        "note": "Roles rotate at the mid-point, so no member owns one stage alone.",
        "narration": (
            "The eight course roles are distributed across the six of us. "
            "AO KIT I coordinates and tracks the work. LI YING FANG leads "
            "development and SAVIDI AVRAM supports it. HO MAN HOU is the team "
            "scribe. WU PEI YE reports and liaises with the instructor. And "
            "LI TIAN HAO is the project analyst and quality reviewer. Roles "
            "rotate at the mid-point, so no member owns one stage alone."
        ),
    },
    {
        "kind": "bullets",
        "title": "How we decide and review",
        "kicker": "Governance · independent peer review",
        "bullets": [
            "Consensus is the default; a quorum of five is needed, and any scope change requires all six.",
            "If consensus fails after two rounds, a simple majority resolves it.",
            "Technical disputes are settled by data and evidence, not by seniority.",
            "Every deliverable has one owner and one independent reviewer - nobody approves their own work.",
        ],
        "note": "The scribe keeps a single source of truth; the reporter builds one consistent narrative from it.",
        "narration": (
            "How we work. Consensus is the default for decisions: a quorum of "
            "five is needed, and any change to the scope requires all six. If "
            "consensus fails after two rounds, a simple majority resolves it. "
            "Technical disputes are settled by data and evidence, not by "
            "seniority. And every deliverable has one owner and one independent "
            "reviewer, so nobody approves their own work."
        ),
    },
    {
        "kind": "bullets",
        "title": "The schedule, and what comes after",
        "kicker": "Phasing · meetings · ownership",
        "bullets": [
            "28-29 Oct - team formed, roles agreed, photo set and Work Plan 1 submitted.",
            "30 Oct - 2 Nov - topic confirmed, scope fixed, data sources identified.",
            "3-4 Nov - proposal and video produced in parallel, reviewed and rehearsed.",
            "5 Nov - all three artefacts submitted by 23:00.",
            "Then - five weekly meetings; class presentation 11, 18 or 25 November; project closes 5 December.",
        ],
        "note": "The schedule is built backward from the deadline, and every November 5 deliverable has an assigned owner and reviewer.",
        "narration": (
            "The schedule is built backward from the deadline. The team formed "
            "on the twenty-eighth and twenty-ninth of October. From the "
            "thirtieth we confirmed the topic, fixed the scope and identified "
            "the data. On the third and fourth of November the proposal and "
            "this video were produced in parallel, reviewed and rehearsed. On "
            "the fifth, all three artefacts are submitted by eleven pm. After "
            "that we hold five weekly meetings, present to the class on the "
            "eleventh, eighteenth or twenty-fifth of November, and close the "
            "project on the fifth of December."
        ),
    },
    {
        "kind": "bullets",
        "title": "What this project cannot say",
        "kicker": "Limitations, stated rather than hidden",
        "bullets": [
            "R-squared 0.022: five observable factors rank risk, but most variation lies outside the data we hold.",
            "Cause minutes are reported only for flights delayed 15 minutes or more, so the split is not a share of all flights.",
            "Observational data supports ranking, not causation; the causal story is a mechanism we describe, not one we prove.",
            "Two operating regimes sit inside the ten-year window, so the calendar enters every model as a control.",
        ],
        "narration": (
            "What we cannot say. Five observable factors can rank risk, but they "
            "cannot promise an arrival time - an R-squared of nought point zero "
            "two two means most of the variation lies outside the data we hold. "
            "Cause minutes are reported only for flights delayed fifteen minutes "
            "or more, so the split is not a share of all flights. And "
            "observational data supports ranking, not causation."
        ),
    },
    {
        "kind": "close",
        "narration": (
            "We are Team 01 of Class K. CISC7204, Data Science and Data "
            "Visualization, 2026/2027, Semester 1. US Domestic Flight Delay "
            "Drivers. Thank you."
        ),
    },
]

# --------------------------------------------------------------------------
# small drawing helpers
# --------------------------------------------------------------------------


def _no_line(shape):
    shape.line.fill.background()


def _rect(slide, x, y, w, h, fill=None, line=None):
    from pptx.enum.shapes import MSO_SHAPE

    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        _no_line(sh)
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    return sh


def _textbox(slide, x, y, w, h, text, size=16, bold=False, color=INK,
             align=PP_ALIGN.LEFT, italic=False, anchor=MSO_ANCHOR.TOP,
             line_spacing=1.15, space_after=4):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split("\n") if isinstance(text, str) else list(text)
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = line
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
    return tb


def _bulleted(slide, x, y, w, h, items, size=15, color=INK, gap=10):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.12
        p.space_after = Pt(gap)
        r = p.add_run()
        r.text = "▪  " + item
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.color.rgb = color
    return tb


def _header(slide, title, kicker=None):
    """Navy band with the slide title; returns the y of the content area."""
    _rect(slide, 0, 0, SLIDE_W, Inches(1.02), fill=NAVY)
    _rect(slide, 0, Inches(1.02), SLIDE_W, Inches(0.05), fill=ACCENT)
    _textbox(slide, Inches(0.62), Inches(0.16), Inches(11.6), Inches(0.5),
             title, size=25, bold=True, color=WHITE)
    if kicker:
        _textbox(slide, Inches(0.62), Inches(0.66), Inches(11.6), Inches(0.3),
                 kicker, size=12.5, color=RGBColor(0xC7, 0xD6, 0xE4))
    return Inches(1.32)


def _footer(slide, index):
    _textbox(slide, Inches(0.62), Inches(6.98), Inches(9.0), Inches(0.28),
             f"{COURSE}   ·   {TEAM}   ·   {YEAR}",
             size=10, color=MUTED)
    _textbox(slide, Inches(11.4), Inches(6.98), Inches(1.4), Inches(0.28),
             f"{index + 1} / {len(SLIDES)}", size=10, color=MUTED,
             align=PP_ALIGN.RIGHT)


def _fit_image(slide, path, x, y, w, h):
    if not os.path.exists(path):
        _rect(slide, x, y, w, h, fill=PAPER, line=HAIR)
        _textbox(slide, x, y + h / 2 - Inches(0.2), w, Inches(0.4),
                 "figure not found", size=12, color=MUTED, align=PP_ALIGN.CENTER)
        return
    with Image.open(path) as im:
        iw, ih = im.size
    ar = iw / ih
    bw, bh = w, h
    if bw / bh > ar:
        bw = Emu(int(bh * ar))
    else:
        bh = Emu(int(bw / ar))
    px = x + int((w - bw) / 2)
    py = y + int((h - bh) / 2)
    slide.shapes.add_picture(path, px, py, bw, bh)


# --------------------------------------------------------------------------
# slide builders
# --------------------------------------------------------------------------


def _slide_title(slide, index):
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=NAVY)
    _rect(slide, 0, Inches(4.42), SLIDE_W, Inches(0.06), fill=ACCENT)
    _textbox(slide, Inches(0.9), Inches(0.8), Inches(11.5), Inches(0.4),
             COURSE, size=17, color=RGBColor(0xC7, 0xD6, 0xE4))
    _textbox(slide, Inches(0.9), Inches(1.25), Inches(11.5), Inches(0.4),
             "Semester Project  ·  Introductory Video", size=17, color=WHITE, bold=True)
    _textbox(slide, Inches(0.9), Inches(2.05), Inches(11.5), Inches(1.1),
             TITLE, size=52, bold=True, color=WHITE, line_spacing=1.0)
    _textbox(slide, Inches(0.9), Inches(3.35), Inches(11.0), Inches(0.9),
             SUBTITLE, size=19, color=RGBColor(0xC7, 0xD6, 0xE4), line_spacing=1.15)
    _textbox(slide, Inches(0.9), Inches(4.75), Inches(11.5), Inches(1.6),
             [TEAM, YEAR, "Submission date: 5 November 2026"],
             size=16, color=WHITE, line_spacing=1.35)
    _footer(slide, index)


def _slide_team(slide, index):
    _header(slide, "The team", "All six members, with student numbers")
    photo = next((p for p in GROUP_PHOTO_CANDIDATES if os.path.exists(p)), None)
    px, py = Inches(0.62), Inches(1.42)
    pw, ph = Inches(5.55), Inches(3.55)
    if photo:
        _fit_image(slide, photo, px, py, pw, ph)
    else:
        _rect(slide, px, py, pw, ph, fill=PAPER, line=HAIR)
        _rect(slide, px, py, pw, ph, fill=None, line=RGBColor(0xB8, 0xC4, 0xD0))
        _textbox(slide, px, py + Inches(1.45), pw, Inches(0.9),
                 ["GROUP PHOTO", "drop docs/video/assets/group_photo.jpg here, then re-run"],
                 size=14, color=MUTED, align=PP_ALIGN.CENTER, line_spacing=1.3)

    tx = Inches(6.55)
    ty = Inches(1.40)
    _textbox(slide, tx, ty, Inches(6.2), Inches(0.3),
             "NAME", size=10.5, bold=True, color=MUTED)
    _textbox(slide, tx + Inches(3.35), ty, Inches(2.9), Inches(0.3),
             "STUDENT ID", size=10.5, bold=True, color=MUTED)
    row = ty + Inches(0.34)
    for name, sid, role in MEMBERS:
        _textbox(slide, tx, row, Inches(3.3), Inches(0.3), name, size=15, bold=True, color=INK)
        _textbox(slide, tx + Inches(3.35), row, Inches(2.9), Inches(0.3), sid, size=15, color=NAVY)
        _textbox(slide, tx, row + Inches(0.27), Inches(6.2), Inches(0.24),
                 role, size=11, color=MUTED)
        row += Inches(0.58)

    _rect(slide, Inches(0.62), Inches(5.28), Inches(12.1), Inches(1.42), fill=PAPER)
    _textbox(slide, Inches(0.9), Inches(5.46), Inches(11.6), Inches(1.1),
             [TITLE, f"{COURSE}   ·   {TEAM}   ·   {YEAR}"],
             size=14.5, color=INK, bold=False, line_spacing=1.35)
    _footer(slide, index)


def _slide_bullets(slide, index, cfg):
    top = _header(slide, cfg["title"], cfg.get("kicker"))
    _bulleted(slide, Inches(0.72), top + Inches(0.12), Inches(11.9), Inches(4.6),
              cfg["bullets"], size=15.5 if len(cfg["bullets"]) <= 4 else 14.5,
              gap=12)
    if cfg.get("note"):
        _rect(slide, Inches(0.62), Inches(5.62), Inches(12.1), Inches(1.05), fill=PAPER)
        _textbox(slide, Inches(0.9), Inches(5.82), Inches(11.6), Inches(0.8),
                 cfg["note"], size=13.5, color=NAVY, italic=True, line_spacing=1.2)
    _footer(slide, index)


def _slide_figure(slide, index, cfg):
    top = _header(slide, cfg["title"], cfg.get("kicker"))
    _fit_image(slide, os.path.join(ROOT, cfg["image"]),
               Inches(6.5), top + Inches(0.05), Inches(6.2), Inches(4.5))
    _bulleted(slide, Inches(0.72), top + Inches(0.15), Inches(5.55), Inches(4.3),
              cfg["bullets"], size=14, gap=13)
    if cfg.get("note"):
        _textbox(slide, Inches(0.72), Inches(5.75), Inches(5.6), Inches(0.8),
                 cfg["note"], size=12, color=MUTED, italic=True)
    _footer(slide, index)


def _slide_fullfigure(slide, index, cfg):
    top = _header(slide, cfg["title"], cfg.get("kicker"))
    _rect(slide, Inches(3.05), top, Inches(7.25), Inches(5.25), fill=PAPER, line=HAIR)
    _fit_image(slide, os.path.join(ROOT, cfg["image"]),
               Inches(3.15), top + Inches(0.1), Inches(7.05), Inches(5.05))
    _textbox(slide, Inches(0.72), top + Inches(0.15), Inches(2.1), Inches(4.8),
             cfg.get("note", ""), size=12.5, color=NAVY, line_spacing=1.3)
    _footer(slide, index)


def _slide_table(slide, index, cfg):
    top = _header(slide, cfg["title"], cfg.get("kicker"))
    rows = cfg["rows"]
    n_rows = len(rows) + 1
    avail = Inches(4.65)
    rh = int(avail / n_rows)
    shape = slide.shapes.add_table(n_rows, len(cfg["headers"]),
                                   Inches(0.72), top + Inches(0.08),
                                   Inches(11.9), rh * n_rows)
    tbl = shape.table
    tbl.first_row = True
    col_w = int(Inches(11.9) / len(cfg["headers"]))
    for c in range(len(cfg["headers"])):
        tbl.columns[c].width = col_w
    tbl.columns[0].width = int(Inches(11.9) * 0.10)
    tbl.columns[1].width = int(Inches(11.9) * 0.32)
    tbl.columns[2].width = int(Inches(11.9) * 0.58)

    def _cell(r, c, text, bold=False, color=INK, size=13, fill=None):
        cell = tbl.cell(r, c)
        cell.text = ""
        cell.margin_left = Inches(0.1)
        cell.margin_right = Inches(0.1)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        if fill is not None:
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill

    for c, h in enumerate(cfg["headers"]):
        _cell(0, c, h, bold=True, color=WHITE, size=12.5, fill=NAVY)
    for r, row in enumerate(rows, start=1):
        band = WHITE if r % 2 else PAPER
        for c, val in enumerate(row):
            _cell(r, c, val, bold=(c == 0), color=NAVY if c == 0 else INK,
                  size=12.5, fill=band)

    if cfg.get("note"):
        _rect(slide, Inches(0.62), Inches(5.72), Inches(12.1), Inches(1.0), fill=PAPER)
        _textbox(slide, Inches(0.9), Inches(5.9), Inches(11.6), Inches(0.75),
                 cfg["note"], size=13, color=NAVY, italic=True, line_spacing=1.2)
    _footer(slide, index)


def _slide_roles(slide, index, cfg):
    top = _header(slide, cfg["title"], cfg.get("kicker"))
    left = Inches(0.62)
    card_w = Inches(3.9)
    gap_x = Inches(0.2)
    card_h = Inches(2.5)
    gap_y = Inches(0.18)
    for i, (name, sid, role) in enumerate(MEMBERS):
        col, row = i % 3, i // 3
        x = left + col * (card_w + gap_x)
        y = top + Inches(0.05) + row * (card_h + gap_y)
        _rect(slide, x, y, card_w, card_h, fill=PAPER, line=HAIR)
        photo = MEMBER_PHOTOS.get(name)
        if photo and os.path.exists(photo):
            _fit_image(slide, photo, x + Inches(0.16), y + Inches(0.2),
                       Inches(1.05), Inches(1.05))
        tx = x + Inches(1.38)
        _textbox(slide, tx, y + Inches(0.2), card_w - Inches(1.5), Inches(0.45),
                 name, size=14, bold=True, color=INK)
        _textbox(slide, tx, y + Inches(0.6), card_w - Inches(1.5), Inches(0.28),
                 sid, size=10.5, color=NAVY)
        _textbox(slide, tx, y + Inches(0.92), card_w - Inches(1.5), Inches(1.3),
                 role, size=11, color=MUTED, line_spacing=1.15)
    if cfg.get("note"):
        _textbox(slide, Inches(0.72), Inches(5.95), Inches(11.6), Inches(0.6),
                 cfg["note"], size=12.5, color=NAVY, italic=True)
    _footer(slide, index)


def _slide_close(slide, index):
    _rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=NAVY)
    _rect(slide, 0, Inches(1.72), SLIDE_W, Inches(0.06), fill=ACCENT)
    _textbox(slide, Inches(0.9), Inches(0.85), Inches(11.5), Inches(0.75),
             TITLE, size=42, bold=True, color=WHITE, line_spacing=1.0)
    _textbox(slide, Inches(0.9), Inches(2.05), Inches(11.5), Inches(0.5),
             COURSE, size=19, color=RGBColor(0xC7, 0xD6, 0xE4))
    _textbox(slide, Inches(0.9), Inches(2.55), Inches(11.5), Inches(0.4),
             f"{TEAM}   ·   {YEAR}", size=17, color=WHITE)

    left = Inches(0.9)
    top = Inches(3.3)
    for i, (name, sid, _role) in enumerate(MEMBERS):
        col = left + Inches(5.9) * (i % 2)
        row = top + Inches(0.62) * (i // 2)
        _textbox(slide, col, row, Inches(2.6), Inches(0.32), name, size=16,
                 bold=True, color=WHITE)
        _textbox(slide, col + Inches(2.45), row, Inches(2.0), Inches(0.32),
                 sid, size=16, color=RGBColor(0xC7, 0xD6, 0xE4))

    _textbox(slide, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.6),
             ["Semester project submission: 5 November 2026   ·   Project close: 5 December 2026",
              "github.com/Team01-FlightDelay-Project"],
             size=13.5, color=RGBColor(0xC7, 0xD6, 0xE4), line_spacing=1.35)
    _footer(slide, index)


BUILDERS = {
    "title": _slide_title,
    "team": _slide_team,
    "bullets": _slide_bullets,
    "figure": _slide_figure,
    "fullfigure": _slide_fullfigure,
    "table": _slide_table,
    "roles": _slide_roles,
    "close": _slide_close,
}


# --------------------------------------------------------------------------
# step 1 - the deck
# --------------------------------------------------------------------------


def build_pptx() -> str:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]
    for i, cfg in enumerate(SLIDES):
        slide = prs.slides.add_slide(blank)
        builder = BUILDERS[cfg["kind"]]
        if cfg["kind"] in ("title", "team", "close"):
            builder(slide, i)
        else:
            builder(slide, i, cfg)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    prs.save(PPTX)
    print(f"[1/5] deck written  -> {PPTX} ({len(SLIDES)} slides)")
    return PPTX


# --------------------------------------------------------------------------
# step 2 - export to PNG (and a PDF of the deck) through PowerPoint
# --------------------------------------------------------------------------


def export_pngs(pptx_path: str) -> list[str]:
    import win32com.client  # noqa: PLC0415

    if os.path.isdir(SLIDE_PNG):
        shutil.rmtree(SLIDE_PNG)
    os.makedirs(SLIDE_PNG)

    app = win32com.client.Dispatch("PowerPoint.Application")
    app.Visible = True
    app.DisplayAlerts = 1  # ppAlertsNone
    try:
        pres = app.Presentations.Open(pptx_path, ReadOnly=True, WithWindow=False)
        pres.Export(SLIDE_PNG, "PNG", 1920, 1080)
        pres.SaveAs(PDF, 32)  # ppSaveAsPDF
        pres.Close()
    finally:
        app.Quit()

    files = sorted(
        (f for f in os.listdir(SLIDE_PNG) if f.lower().endswith(".png")),
        key=lambda f: int(re.search(r"(\d+)", os.path.splitext(f)[0]).group(1)),
    )
    paths = [os.path.join(SLIDE_PNG, f) for f in files]
    if len(paths) != len(SLIDES):
        raise RuntimeError(f"expected {len(SLIDES)} slide PNGs, got {len(paths)}")
    print(f"[2/5] {len(paths)} slides exported at 1920x1080 -> {SLIDE_PNG}")
    print(f"      deck PDF -> {PDF}")
    return paths


# --------------------------------------------------------------------------
# step 3 - narration
# --------------------------------------------------------------------------

FFMPEG = None


def ffmpeg() -> str:
    global FFMPEG
    if FFMPEG is None:
        import imageio_ffmpeg  # noqa: PLC0415

        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    return FFMPEG


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, text=True)


def media_duration(path: str) -> float:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"cannot read duration of {path}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _existing_narration(i: int) -> str | None:
    for ext in (".wav", ".mp3", ".m4a"):
        p = os.path.join(NARRATION, f"{i + 1:02d}{ext}")
        if os.path.exists(p):
            return p
    return None


VOICE = os.environ.get("TEAM01_TTS_VOICE", "en-US-AndrewMultilingualNeural")
TARGET_AUDIO = 288.0   # seconds of decoded speech; slide pauses take it to ~4:56
PAUSE = 0.45           # seconds of silence after each slide


def synth_all(out_dir: str, rate: str) -> list[str]:
    import asyncio  # noqa: PLC0415

    import edge_tts  # noqa: PLC0415

    async def one(text: str, dest: str) -> None:
        c = edge_tts.Communicate(text, VOICE, rate=rate)
        await c.save(dest)

    async def main(texts: list[str]) -> None:
        # sequential: the endpoint is happier that way and 17 clips is quick
        for i, t in enumerate(texts):
            await one(t, os.path.join(out_dir, f"{i + 1:02d}.mp3"))

    asyncio.run(main([s["narration"] for s in SLIDES]))
    return [os.path.join(out_dir, f"{i + 1:02d}.mp3") for i in range(len(SLIDES))]


def to_wav(paths: list[str], out_dir: str) -> list[str]:
    """Decode to 44.1 kHz stereo PCM. An mp3 header duration is only an estimate,
    so every measurement in this script is taken on the decoded wav."""
    wavs = []
    for i, p in enumerate(paths):
        w = os.path.join(out_dir, f"{i + 1:02d}.wav")
        run(["-i", p, "-ar", "44100", "-ac", "2", w])
        wavs.append(w)
    return wavs


def build_narration() -> tuple[list[str], str]:
    """Returns (paths to one decoded wav per slide, provenance label)."""
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(NARRATION, exist_ok=True)

    human = [_existing_narration(i) for i in range(len(SLIDES))]
    if all(human):
        print("[3/5] using recorded human narration from assets/narration/")
        wavs = []
        for i, p in enumerate(human):
            w = os.path.join(WORK, f"{i + 1:02d}.wav")
            run(["-i", p, "-ar", "44100", "-ac", "2", w])
            wavs.append(w)
        return wavs, "human"

    tts_dir = os.path.join(WORK, "tts")

    rate = "+0%"
    wavs: list[str] = []
    total = 0.0
    for attempt in range(3):
        # one subdirectory per attempt: nothing is ever deleted
        attempt_dir = os.path.join(tts_dir, f"attempt{attempt + 1}")
        os.makedirs(attempt_dir, exist_ok=True)
        paths = synth_all(attempt_dir, rate)
        wavs = to_wav(paths, attempt_dir)
        total = sum(media_duration(w) for w in wavs)
        print(f"      attempt {attempt + 1}: rate {rate} -> speech {total:.1f}s")
        if 0.98 * TARGET_AUDIO <= total <= 1.01 * TARGET_AUDIO:
            break
        # slower voice when too short, faster when too long
        delta = int(round((total / TARGET_AUDIO - 1.0) * 100))
        delta = max(-40, min(40, delta))
        if delta == 0 or attempt == 2:
            break
        rate = f"{delta:+d}%"

    print(f"      projected runtime {total + PAUSE * len(SLIDES):.1f}s "
          f"({(total + PAUSE * len(SLIDES)) / 60:.2f} min)")
    print(f"[3/5] narration synthesised ({VOICE})")
    return wavs, f"edge-tts:{VOICE}"


# --------------------------------------------------------------------------
# step 4 - subtitles
# --------------------------------------------------------------------------


def _wrap(text: str, width: int = 42) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def write_srt(per_slide: list[tuple[float, float]], path: str) -> None:
    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    out, n = [], 0
    for i, (start, end) in enumerate(per_slide):
        for line in _wrap(SLIDES[i]["narration"]):
            n += 1
            out.append(f"{n}\n{ts(start)} --> {ts(end)}\n{line}\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print(f"[4/5] subtitles -> {path}")


# --------------------------------------------------------------------------
# step 5 - mux
# --------------------------------------------------------------------------


def build_video(pngs: list[str], audios: list[str]) -> str:
    seg_dir = os.path.join(WORK, "segs")
    os.makedirs(seg_dir, exist_ok=True)

    silence = os.path.join(WORK, "silence.wav")
    run(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", f"{PAUSE}", silence])

    segs = []
    timeline = []
    clock = 0.0
    for i, (png, audio) in enumerate(zip(pngs, audios)):
        dur = media_duration(audio)
        padded = os.path.join(WORK, f"pad_{i + 1:02d}.wav")
        lst = os.path.join(WORK, f"list_{i + 1:02d}.txt")
        with open(lst, "w", encoding="utf-8") as fh:
            for p in (audio, silence):
                fh.write(f"file '{p.replace(chr(92), '/')}'\n")
        run(["-f", "concat", "-safe", "0", "-i", lst, "-ar", "44100", "-ac", "2", padded])

        seg = os.path.join(seg_dir, f"seg_{i + 1:02d}.mp4")
        seg_dur = dur + PAUSE
        run(["-loop", "1", "-framerate", "25", "-t", f"{seg_dur:.3f}", "-i", png,
             "-i", padded,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-tune", "stillimage",
             "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
             "-shortest", "-movflags", "+faststart", seg])
        segs.append(seg)
        timeline.append((clock, clock + dur))
        clock += dur + PAUSE

    total = sum(media_duration(s) for s in segs)
    print(f"[5/5] {len(segs)} segments, {total / 60:.2f} min")

    write_srt(timeline, SRT)

    lst = os.path.join(WORK, "concat.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for s in segs:
            fh.write(f"file '{s.replace(chr(92), '/')}'\n")
    raw = os.path.join(WORK, "raw.mp4")
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])

    # try to burn the captions in; keep the clean cut if that is not possible.
    # A Windows drive letter must be escaped inside a filtergraph, or ffmpeg
    # reads "C:" as an option separator.
    srt_arg = SRT.replace("\\", "/").replace(":", r"\:")
    style = ("FontName=Arial,Fontsize=20,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H90000000,Outline=2,Shadow=0,MarginV=44")
    r = run(["-i", raw,
             "-vf", f"subtitles='{srt_arg}':force_style='{style}'",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", MP4])
    if r.returncode != 0 or not os.path.exists(MP4):
        print("      (subtitle burn unavailable - writing the clean cut instead)")
        run(["-i", raw, "-c", "copy", "-movflags", "+faststart", MP4])

    size = os.path.getsize(MP4) / (1024 * 1024)
    print(f"      video -> {MP4}  ({size:.1f} MB, {media_duration(MP4) / 60:.2f} min)")
    return MP4


def cleanup() -> None:
    """Best effort: the scratch directory lives in the OS temp area, so leaving it
    behind costs nothing and the next run gets a fresh one."""
    try:
        shutil.rmtree(WORK, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(NARRATION, exist_ok=True)
    build_pptx()
    export_pngs(PPTX)

    # The video is produced only when explicitly requested (``--video``).
    # The deck + PDF + PNGs are the day-to-day deliverables.
    if "--video" in sys.argv:
        audios, provenance = build_narration()
        pngs = sorted(
            (os.path.join(SLIDE_PNG, f) for f in os.listdir(SLIDE_PNG)
             if f.lower().endswith(".png")),
            key=lambda p: int(re.search(r"(\d+)", os.path.splitext(p)[0]).group(1)),
        )
        build_video(pngs, audios)
        cleanup()
        print(f"\nnarration source: {provenance}")
    else:
        print("\n[deck only] video not built - re-run with --video when ready.")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
