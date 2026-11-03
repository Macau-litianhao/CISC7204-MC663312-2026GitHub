import sys, os
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# Figures are copied into the repository, next to this script, and referenced
# relatively. They used to be read from an absolute path inside the earlier
# pair-project folder: that worked on exactly one machine, and when the folder
# moved, FIG() returned False and the proposal rebuilt itself with two figures
# silently missing while still passing the page limit. Portability is now a
# build-time guarantee rather than a hope.
HERE = Path(__file__).resolve().parent
SRC_DIR = HERE / "figures"
OUT_DIR = HERE
os.makedirs(OUT_DIR, exist_ok=True)
OUT = str(OUT_DIR / "CISC7204-Team01-ProjectProposal.docx")

FONT = "Times New Roman"

doc = Document()

# ---------- page setup: match original ----------
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.left_margin = Cm(2.2)
sec.right_margin = Cm(2.2)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.2)

# ---------- base style ----------
st = doc.styles['Normal']
st.font.name = FONT
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.10


def H1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(13)
    r.font.name = FONT
    r.font.color.rgb = RGBColor(0, 0, 0)
    return p


def P(text="", size=10.5, bold=False, italic=False, align=None, space_after=4,
      space_before=0, indent=None, line=1.10):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = line
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    if align == 'center':
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == 'justify':
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if text:
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.font.name = FONT
        r.bold = bold
        r.italic = italic
    return p


def LEAD(lead, rest, size=10.5):
    """Bold lead-in paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.10
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r1 = p.add_run(lead)
    r1.bold = True
    r1.font.size = Pt(size)
    r1.font.name = FONT
    r2 = p.add_run(rest)
    r2.font.size = Pt(size)
    r2.font.name = FONT
    return p


def BUL(text, size=10.5):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.10
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = FONT
    return p


def CAP(text, keep_next=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    if keep_next:
        p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.size = Pt(9)
    r.font.name = FONT
    r.italic = True
    return p


def _repeat_as_header(row):
    """Mark a row as a header so Word repeats it after a page break.

    Without this a table that straddles two pages resumes with bare data rows
    and the reader has to scroll back to learn what the columns mean.
    """
    trPr = row._tr.get_or_add_trPr()
    flag = OxmlElement('w:tblHeader')
    flag.set(qn('w:val'), 'true')
    trPr.append(flag)


def _keep_row_whole(row):
    """Forbid Word from splitting a single row across a page boundary."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))


def _keep_row_with_next(row):
    """Bind a row to the following row so a table does not strand its header
    (or a lone row) at the bottom of a page."""
    for cell in row.cells:
        for pp in cell.paragraphs:
            pp.paragraph_format.keep_with_next = True


def _set_table_borders(table, sz=4, color='000000'):
    """Force one uniform border on the whole table.

    The 'Table Grid' style draws each cell's four edges separately, so at
    row/column intersections Word can leave a hairline gap that reads as a
    broken line. Defining the six borders once at the table level makes every
    line a single continuous stroke in the exported PDF.
    """
    tblPr = table._tbl.tblPr
    for old in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(old)
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement('w:' + edge)
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), color)
        borders.append(el)
    for anchor in ('w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook'):
        ref = tblPr.find(qn(anchor))
        if ref is not None:
            ref.addprevious(borders)
            return
    tblPr.append(borders)


def TABLE(headers, rows, widths, size=8.5, header_bold=True, keep_together=False):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ''
        pp = hdr[i].paragraphs[0]
        pp.paragraph_format.space_after = Pt(1)
        pp.paragraph_format.line_spacing = 1.0
        rr = pp.add_run(h)
        rr.bold = header_bold
        rr.font.size = Pt(size)
        rr.font.name = FONT
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ''
            pp = cells[i].paragraphs[0]
            pp.paragraph_format.space_after = Pt(1)
            pp.paragraph_format.line_spacing = 1.0
            rr = pp.add_run(val)
            rr.font.size = Pt(size)
            rr.font.name = FONT
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        _keep_row_whole(row)
    # Always bind the header row to the first data row so a table never
    # strands its header alone at the bottom of a page (which reads as a
    # truncated table).
    if len(t.rows) >= 2:
        _keep_row_with_next(t.rows[0])
    # Small tables are kept on a single page so they never split awkwardly.
    if keep_together:
        for row in list(t.rows)[:-1]:
            _keep_row_with_next(row)
    _repeat_as_header(t.rows[0])
    _set_table_borders(t)
    return t


EMBEDDED = []


def FIG(filename, width_cm=13.5):
    """Embed a figure, or stop the build.

    A missing file is fatal on purpose. The previous version returned False and
    the caller skipped both the picture and its caption, so a proposal short of
    two figures still built cleanly and still satisfied the page limit - the
    kind of omission nobody notices until a marker asks where Fig. 1 went.
    """
    path = SRC_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"proposal figure missing: {path}\n"
            f"  expected in {SRC_DIR}; see figures/README.md"
        )
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.space_after = Pt(2)
    EMBEDDED.append(filename)
    return True


def _add_hyperlink(paragraph, url, text, size=8.0):
    """Append a real, clickable hyperlink run (blue, single underline).

    python-docx has no hyperlink API, so the relationship and the ``w:hyperlink``
    element are built by hand. The run is styled as Word's default link (blue
    ``0563C1``, underlined) at *size* pt, so it reads as a link rather than a bare
    URL pasted into the register. The display text is the URL itself: a reader of
    the printed PDF still sees the exact address to re-download the dataset.
    """
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), FONT)
    fonts.set(qn("w:hAnsi"), FONT)
    rPr.append(fonts)

    colour = OxmlElement("w:color")
    colour.set(qn("w:val"), "0563C1")     # Word's default hyperlink blue
    rPr.append(colour)

    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rPr.append(underline)

    for tag in ("w:sz", "w:szCs"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), str(int(size * 2)))
        rPr.append(el)

    run.append(rPr)
    text_el = OxmlElement("w:t")
    text_el.set(qn("xml:space"), "preserve")
    text_el.text = text
    run.append(text_el)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink


def _breakable(url):
    """Insert zero-width spaces so Word can break a long URL inside a cell.

    Word does not wrap a continuous string with no spaces, so a long URL in a
    table cell runs past the cell border. A zero-width space after every ``/``
    and ``.`` gives Word legal break points without changing what the reader
    sees, so the link wraps cleanly inside its column.
    """
    out = []
    for ch in url:
        out.append(ch)
        if ch in "/.":
            out.append("\u200b")
    return "".join(out)


def DS_TABLE(rows):
    """Dataset register as a five-column table; the last column holds links.

    Each row is ``(id, dataset, role, coverage, links)`` where ``links`` is a
    list of ``(prefix, url)`` pairs. The link cell renders one clickable
    hyperlink per pair with the URL itself as the display text, so a reader of
    the printed PDF still sees the exact address to re-download the dataset.
    """
    headers = ["ID", "Dataset (publisher)", "Role in the analysis", "Coverage", "Access"]
    t = doc.add_table(rows=1, cols=5)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ''
        pp = hdr[i].paragraphs[0]
        pp.paragraph_format.space_after = Pt(1)
        pp.paragraph_format.line_spacing = 1.0
        rr = pp.add_run(h)
        rr.bold = True
        rr.font.size = Pt(8.0)
        rr.font.name = FONT
    for rid, ds, role, cov, links in rows:
        cells = t.add_row().cells
        for i, txt in enumerate([rid, ds, role, cov]):
            cells[i].text = ''
            pp = cells[i].paragraphs[0]
            pp.paragraph_format.space_after = Pt(1)
            pp.paragraph_format.line_spacing = 1.0
            rr = pp.add_run(txt)
            rr.font.size = Pt(8.0)
            rr.font.name = FONT
            rr.bold = (i == 0)
        lc = cells[4]
        lc.text = ''
        for j, (prefix, url) in enumerate(links):
            pp = lc.paragraphs[0] if j == 0 else lc.add_paragraph()
            pp.paragraph_format.space_after = Pt(1)
            pp.paragraph_format.line_spacing = 1.0
            if prefix:
                r = pp.add_run(prefix)
                r.font.size = Pt(7.0)
                r.font.name = FONT
            _add_hyperlink(pp, url, _breakable(url), size=7.0)
    widths = [0.9, 3.4, 4.7, 2.5, 5.1]
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        _keep_row_whole(row)
    if len(t.rows) >= 2:
        _keep_row_with_next(t.rows[0])
    _repeat_as_header(t.rows[0])
    _set_table_borders(t)
    return t


# =====================================================================
# COVER PAGE
# =====================================================================
for _ in range(3):
    P("", space_after=0)

P("CISC7204 Data Science and Data Visualization", size=12, align='center', space_after=2)
P("Semester Project — Team Project Proposal", size=12, align='center', space_after=30)

P("US Domestic Flight Delay Drivers", size=22, bold=True, align='center', space_after=6)
P("Attribution, within-day cascade, airport archetypes and an interactive communication layer",
  size=11, italic=True, align='center', space_after=40)

P("Group: Class K — Team 01", size=11.5, bold=True, align='center', space_after=14)

P("AO KIT I — MC660004", size=11, align='center', space_after=1)
P("LI YING FANG — MC661599", size=11, align='center', space_after=1)
P("HO MAN HOU — MC661647", size=11, align='center', space_after=1)
P("WU PEI YE — MC661846", size=11, align='center', space_after=1)
P("LI TIAN HAO — MC663312", size=11, align='center', space_after=1)
P("SAVIDI AVRAM — MC664364", size=11, align='center', space_after=40)

P("Submission date: 5 November 2026", size=11, align='center', space_after=0)

doc.add_page_break()

# =====================================================================
# 1. OVERVIEW AND RESEARCH QUESTION
# =====================================================================
H1("1. Project Overview and Research Question")

P("This proposal documents an end-to-end, reproducible analysis of delay in U.S. domestic air travel, "
  "completed on the full ten-year panel. The region is the United States and the domain category is "
  "commercial air transportation. The analysis covers ten annual files from the Bureau of Transportation "
  "Statistics (BTS, n.d.-b) for 2015–2024 — 63,079,392 rows, of which 61,689,698 are completed flights by 20 "
  "reporting carriers — joined to airport reference metadata. The project attributes delay minutes to the "
  "five causes published by BTS (n.d.-a), measures how delay is inherited within the operating day, groups airports "
  "into delay-risk archetypes, ranks the factors that govern delay length and severe-delay risk, and "
  "communicates the result through a linked analytical dashboard and a narrative web page written for a "
  "non-specialist.", align='justify')

P("The work extends a pilot completed for Assignment 02 by LI TIAN HAO and LI YING FANG, which used "
  "the 2024 file alone. A single year "
  "cannot separate a structural pattern from a one-year operational shock, cannot support clustering with "
  "stable estimates, and cannot test whether the split between airline-controlled and system-imposed delay "
  "holds over time. The ten-year panel removes those limitations. The headline split is 73.3% "
  "airline-controlled against 26.7% system-imposed, with a bootstrap 95% interval of 73.0–73.6%, and it is "
  "stable across the decade — the per-year internal share ranges from 69.7% (2018) to 77.4% (2022), a swing "
  "of 7.7 percentage points.", align='justify')

P("Flight delay is a public-interest problem because a single average hides very different experiences. A "
  "traveller wants to know the chance of losing an afternoon; an airline or a regulator needs to know where "
  "delay minutes originate. We therefore treat cause composition, typical delay, severe-delay risk, "
  "within-day propagation and factor ranking as separate questions rather than collapsing them into one "
  "headline number.", align='justify')

P("Research questions.", bold=True, space_after=2, space_before=2)
P("RQ1. How are reported delay minutes distributed across the five BTS causes, and how stable is that "
  "composition across 2015–2024?", indent=0.6, space_after=2, align='justify')
P("RQ2. How much of the delay observed in a given hour is inherited from earlier legs in the same day, and at "
  "which airports does that cascade concentrate?", indent=0.6, space_after=2, align='justify')
P("RQ3. Do U.S. airports fall into distinct delay-risk archetypes once size and cause mix are considered "
  "together, and what operational characteristics separate them?", indent=0.6, space_after=2, align='justify')
P("RQ4. Given route, departure hour and month, how well can delay risk be ranked, and can a linked web tool "
  "let a non-specialist act on that ranking?", indent=0.6, space_after=6, align='justify')

if FIG("01_cause_waffle.png", 8.5):
    CAP("Fig. 1  Attribution of delay minutes on the completed ten-year panel: 73.3% airline-controlled, "
        "26.7% system-imposed (each cell = 1%; the internal causes are 39% late aircraft and 35% carrier, "
        "the system causes 21% air-traffic and 5% weather).")

P("Note on the numbers. Every empirical value in this proposal is computed on the completed ten-year panel "
  "(2015–2024) and read directly from the pipeline's outputs/ artefacts — the 61.7 million completed "
  "flights, the 73.3% split, a Gini index of 0.876, R-squared 0.022 and a held-out AUC of 0.685. A 53-test "
  "suite pins the provenance of each number, and no figure here is a fixture result.",
  size=9.0, italic=True, align='justify', space_before=5)

# =====================================================================
# 2. PROJECT PURPOSE
# =====================================================================
H1("2. Project Purpose")

LEAD("Outcomes. ",
     "The project connects to three course learning outcomes: selecting visual encodings that fit different "
     "data structures and questions; moving from exploratory description to an appropriately qualified "
     "statistical comparison; and designing an interactive communication product for a non-specialist "
     "audience. It also produces a portfolio-ready example of an end-to-end data project, from public-source "
     "acquisition to reproducible delivery.")

LEAD("Skills. ",
     "We practise data engineering at scale (multi-file ingestion, partitioned storage, schema validation), "
     "exploratory analysis, panel and robust regression, quantile and logistic modelling, unsupervised "
     "clustering, gradient-boosted prediction with model explanation, dashboard and narrative web development, "
     "reproducibility testing and concise technical writing. Collaboration adds code review, issue tracking and "
     "the division of a six-person workload across analytical stages.")

LEAD("Knowledge. ",
     "The work develops applied knowledge of the BTS delay-cause taxonomy, the 15-minute reporting threshold, "
     "the difference between mean and tail behaviour, incremental explanatory power, the limits of "
     "observational models, and the conditions under which clustering is informative rather than an artefact "
     "of feature scaling.")

# =====================================================================
# 3. PROJECT TASKS AND DELIVERABLES
# =====================================================================
H1("3. Project Tasks and Deliverables")

P("Table 1 summarises the six stages of the work, the methods used and the evidence produced. All six "
  "stages are complete on the full panel; the remaining work is the communication layer, the usability "
  "check and the final submission.", align='justify')

CAP("Table 1  Workflow and delivered evidence", keep_next=True)
TABLE(
    ["Stage", "What we did", "Evidence delivered"],
    [
        ["1. Data acquisition and validation",
         "Downloaded ten annual BTS files and airport metadata; validated schema, duplicates, missingness and "
         "the 15-minute cause-field threshold; wrote partitioned Parquet.",
         "outputs/metrics/validation.json: 63.1M rows, duplicate rate 0, threshold coverage 99.9999%."],
        ["2. Attribution and exploratory analysis",
         "Partitioned attributed minutes across the five causes; compared month, carrier, hour, distance, "
         "state and airport; tested composition stability across years.",
         "73.3% internal share with a bootstrap interval; per-year range 69.7–77.4%; Figures 01–03, 07."],
        ["3. Tail and concentration",
         "Compared mean, median, percentiles and severe-delay shares; Lorenz curve; retested the "
         "mean-versus-tail hypothesis on the full panel.",
         "Gini 0.876; the worst 1% of flights carries 25% of delay minutes; Figures 04–06, 08."],
        ["4. Cascade and airport archetypes",
         "Quantified within-day inherited delay; built an airport feature matrix; k-means with silhouette "
         "selection and a Ward cross-check.",
         "k = 5 clusters over 195 airports, silhouette 0.2045 (ARI 0.69, reported unstable); Figures 09–10."],
        ["5. Prediction and explanation",
         "Logistic baseline and gradient boosting with a time-based holdout; factor ranking by incremental "
         "R-squared.",
         "R-squared 0.022; AUC 0.685 (logistic) / 0.691 (GBM) at a 6.1% base rate; departure hour the top "
         "factor; Figures 11–12."],
        ["6. Communication layer",
         "Built an eight-panel linked Dash dashboard and a narrative page; a test suite pins number "
         "provenance.",
         "Eight-panel dashboard (Fig. 2a–2b); narrative page; 53 passing tests."],
    ],
    [3.0, 7.0, 6.6], size=8.0)

P("", space_after=4)
if FIG("13_dashboard_part1.png", 12.0):
    CAP("Fig. 2a  The dashboard at 1440 px, upper half — header, filters, headline numbers and the "
        "first four of eight panels. The header states the panel (61,689,698 completed flights); the "
        "headline numbers and every chart below it are drawn from a 400,000-flight random sample "
        "(0.6%), which the page states in the line under those numbers, because a filter change has to "
        "answer immediately. On that sample the airline share reads 74% where the full panel gives "
        "73.3% (Fig. 1); no conclusion turns on the gap. Year, carrier and month recompute every panel "
        "live rather than swapping pre-rendered images.")

if FIG("13_dashboard_part2.png", 12.0):
    CAP("Fig. 2b  Lower half of the same view — the remaining four panels, the passenger takeaway band "
        "and the method-and-limits section, which states what the page cannot say and why. The view is "
        "split across two figures so that no panel is cut mid-way at print width.")

# =====================================================================
# 4. DATA CONTEXT, REGION AND SOURCES
# =====================================================================
H1("4. Data Context, Region and Sources")

LEAD("Region. ",
     "The United States of America — all 50 states together with the District of Columbia, including Alaska "
     "and Hawaii and therefore four time zones. The observation window is 2007–2024 for the descriptive "
     "context and 2015–2024 for the analysis panel. U.S. territories (Puerto Rico, Guam, the U.S. Virgin "
     "Islands) and all international legs are excluded, so every row describes a scheduled domestic "
     "passenger flight that both departs from and arrives at a U.S. airport. Findings are reported at three "
     "nested spatial levels: national (all flights), state (origin state) and airport (origin airport).")

LEAD("Domain category. ",
     "Transportation — commercial aviation, specifically airline operations and air-traffic performance. "
     "In data-science terms the problem is operational performance analytics on a scheduled transport "
     "network: the unit of observation is one flight leg, the outcome of interest is arrival delay in "
     "minutes (and its heavy tail), and the candidate drivers are the operating carrier, the airports at "
     "each end, the position of the leg within the aircraft's day, the calendar, and surface weather. "
     "Stated in the template's short form: United States and transportation / commercial aviation.")

P("Five public datasets are used, listed in Table 2 as D1–D5 with their publisher, role, coverage and a "
  "clickable access link. Every link was re-checked on 2 November 2026 and returned HTTP 200; none requires "
  "a login or an API key.", align='justify', space_before=4)

CAP("Table 2  The five datasets", keep_next=True)
DS_TABLE([
    ("D1",
     "Reporting Carrier On-Time Performance (1987–present) — U.S. Bureau of Transportation Statistics",
     "Primary flight-level records: carrier, tail number, origin and destination, scheduled and actual "
     "times, delay minutes, and the five BTS cause-minute fields (37 of 110 published fields retained).",
     "12 monthly files per year, 2015–2024; 63.1M rows. Archive pattern: On_Time_..._{year}_{month}.zip",
     [("Download page: ", "https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ"),
      ("Archive directory: ", "https://transtats.bts.gov/PREZIP/")]),
    ("D2",
     "Airline On-Time Performance: Delay Cause — BTS",
     "National monthly aggregates of delay minutes by cause and carrier; an independent cross-check on our "
     "per-flight attribution.",
     "Monthly, 2003–present",
     [("Query page: ", "https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp")]),
    ("D3",
     "Integrated Surface Database (hourly surface observations) — NOAA NCEI",
     "Hourly weather at origin airports (wind, visibility, precipitation, ceiling, temperature) merged on "
     "airport and scheduled departure hour; a planned covariate.",
     "40 busiest origin airports, all ten years, one record per station-hour",
     [("Landing page: ", "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database"),
      ("Direct access: ", "https://www.ncei.noaa.gov/data/global-hourly/access/")]),
    ("D4",
     "airports.csv (airport reference file) — OurAirports",
     "Coordinates, state, municipality, airport type and scheduled-service flag, for the maps and the "
     "airport size stratum in clustering.",
     "≈75,000 airports worldwide, filtered to U.S. large, medium and small airports",
     [("Direct download: ", "https://davidmegginson.github.io/ourairports-data/airports.csv")]),
    ("D5",
     "Air Traffic by the Numbers and Passenger Boarding (Enplanement) data — FAA",
     "Annual U.S. commercial-service airport activity, to validate the hub stratum derived from D4 and "
     "report the large / medium / small hub split.",
     "Annual, all U.S. commercial-service airports",
     [("By the Numbers: ", "https://www.faa.gov/air_traffic/by_the_numbers"),
      ("Passenger boarding: ", "https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger")]),
])

P("", space_after=2)
LEAD("Reporting-threshold note. ",
     "BTS publishes the five cause-minute fields only for flights delayed by at least 15 minutes. The panel "
     "verifies this rule directly: of the 11,454,282 flights at or above the threshold, 99.9999% carry a "
     "complete cause breakdown, while none below the threshold does. All cause-share statements are scoped "
     "to that attribution universe, while counts, means and percentiles use all 61,689,698 completed "
     "flights.")

LEAD("Governance. ",
     "All five sources are public and none needs a login or key. D1 and D2 are U.S. federal government data "
     "and are redistributable; D3 is U.S. federal data in the public domain; D4 is a public-domain "
     "dedication; D5 is a U.S. federal publication. No personal data is processed and no ethics approval is "
     "required. Raw files are excluded from version control and are re-downloadable from the URLs above, "
     "with a SHA-256 manifest (`data/checksums.sha256`) recording the exact file behind any reported number.")

# =====================================================================
# 5. METHOD SUMMARY
# =====================================================================
H1("5. Method Summary")

LEAD("Data acquisition and validation. ",
     "Twelve monthly files per year are concatenated, types are coerced, and the analysis columns are retained. "
     "Each year is checked for row counts, duplicate keys, missingness and threshold coverage before being "
     "written to partitioned Parquet so that a single year can be re-read without loading the panel. The full "
     "panel passes with 63,079,392 rows, zero duplicate rows and 99.9999% cause coverage above the threshold.")

LEAD("Attribution and stability. ",
     "Reported delay minutes are grouped into airline-controlled causes (carrier and late aircraft) and "
     "system-imposed causes (air traffic, weather and security). The composition is recomputed per year, and a "
     "bootstrap interval is attached to the headline split so that a one-year deviation can be separated from "
     "sampling noise. The result — 73.3% internal, 95% CI 73.0–73.6% — is stable across the decade.")

LEAD("Tail and concentration. ",
     "Mean, median and percentiles are reported alongside severe-delay shares; a Lorenz curve and a Gini-style "
     "concentration statistic quantify how much of the delay burden sits in the worst flights. The mean "
     "(+4.5 minutes) sits far above the median (−6.0 minutes), and the Gini index is 0.876, so the "
     "mean-versus-tail hypothesis from the pilot is confirmed on the panel rather than on a single year.")

LEAD("Cascade measurement. ",
     "Inherited delay is measured with the BTS late-aircraft cause minutes and with a turnaround-buffer "
     "calculation on consecutive legs of the same aircraft. The result is expressed as the share of delay "
     "attributable to earlier legs, which converts the 38.8% late-aircraft share into a within-day mechanism: "
     "6.0% of flights are in an aircraft rotation with positive delay, and 17.1% of those delay minutes are "
     "inherited.")

LEAD("Airport archetypes. ",
     "Airports are described by a feature matrix covering mean delay, ninetieth-percentile delay, severe-delay "
     "share, the five cause shares, seasonal amplitude, departures and hub stratum (OurAirports, n.d.; Federal "
     "Aviation Administration, n.d.). Features are standardised; "
     "k-means is run over a range of k and selected by silhouette score (Rousseeuw, 1987); Ward linkage provides a dendrogram as "
     "a stability cross-check; PCA gives a two-dimensional projection for display. The chosen solution has "
     "k = 5 over 195 airports at silhouette 0.2045, and it is reported as unstable (mean ARI 0.69 against a "
     "0.70 threshold) rather than as a fixed taxonomy.")

LEAD("Prediction and explanation. ",
     "A logistic baseline and a gradient-boosted classifier predict arrival delay of at least 60 minutes, "
     "with a time-based split so that later months are never used to train earlier ones. SHAP-style "
     "importance (Lundberg & Lee, 2017) ranks the factors, and dependence plots expose the departure-hour curve. The held-out AUC is "
     "0.685 (logistic) and 0.691 (gradient boosting) at a 6.1% base rate; the full model explains R-squared "
     "0.022. Departure hour is the strongest factor, carrying 49.9% of the ranked importance.")

LEAD("Regime controls. ",
     "A ten-year window holds two operating regimes, so the calendar enters every model as a control rather "
     "than as a finding: year fixed effects absorb the long trend, and a COVID-era dummy covers March 2020 to "
     "December 2021. The two years stay in the panel because they are the only observations of an extreme "
     "operating condition, and every headline statistic is recomputed with them excluded, so the report shows "
     "the size of the shift rather than presenting one version of the average.")

LEAD("Visual design and interaction. ",
     "Charts are selected by the question they answer, following the encoding-effectiveness ordering described "
     "in Section 6. The communication layer separates an analytical dashboard from a narrative page: the "
     "dashboard supports exploration, while the narrative page guides a non-specialist through four findings "
     "in a fixed order.")

# =====================================================================
# 6. VISUAL DESIGN RATIONALE
# =====================================================================
H1("6. Visual Design Rationale")

P("Because this is a visualisation course, each chart is treated as a decision to be justified rather than a "
  "default. We adopt the encoding-effectiveness ordering of Cleveland and McGill (1984) and Mackinlay (1986): "
  "position along a common scale is read most accurately, followed by length, angle and slope, while area and "
  "colour hue are read least accurately. Each figure is therefore chosen by the question it answers, and "
  "where a weaker encoding is unavoidable it is supported by direct labels and a legend that states the scale. This question-first ordering follows the task-oriented design framework of Munzner (2014), and the refusal to overstate a chart's evidence reflects Cairo's (2016) guidance.",
  align='justify')

BUL("Part-to-whole: a unit waffle, where area encodes the share of delay minutes and every cell is labelled, "
    "so that the 73.3 / 26.7 split reads without a legend.")
BUL("Ordered and cyclical: a line cascade for departure hour, because a ranked bar chart would destroy the "
    "within-day shape that is the point of the figure.")
BUL("Distribution: percentile bands and a violin plot instead of a bar of means, because the mean sits at the "
    "seventy-third percentile and misrepresents the typical flight.")
BUL("Concentration: a Lorenz curve, read by position, to show that the worst one percent of flights carries "
    "25% of delay minutes.")
BUL("Geography: a state tile grid is retained for national comparison because it keeps every state visible at "
    "equal weight, and a choropleth is added alongside it for magnitude reading.")
BUL("Volume: airport bubbles sized by departures, with an explicit size legend, because area is a weak "
    "channel and must be anchored.")

P("One comparison is built deliberately rather than described. A single figure places the same twelve "
  "monthly profiles side by side: on the left as a bar of means, on the right with the median, the mean and "
  "the p90 retained. The bar chart is not a straw man - it uses a zero baseline, labelled values and an "
  "ordered axis, and it still cannot support the sentence a traveller needs, because no bar can show that "
  "the median never crosses zero. Publishing both turns the encoding argument into evidence rather than an "
  "assertion, and it is the figure we would point to first if asked why the report does not lead with "
  "monthly averages.", align='justify', space_before=3)

P("Table 3 lists the delivered figure set, each tied to the question it answers and the encoding it uses.",
  align='justify', space_before=2)

CAP("Table 3  Delivered figure set", keep_next=True)
TABLE(
    ["Figure", "Question it answers", "Encoding"],
    [
        ["01 cause waffle", "Where do delay minutes come from", "Area, labelled"],
        ["02 monthly composition", "Is the cause mix stable", "Stacked area"],
        ["03 carrier bars", "Which carrier delays most", "Ordered bars"],
        ["04 percentile band", "What is the delay spread", "Band, position"],
        ["05 Lorenz curve", "How concentrated is delay", "Line, position"],
        ["06 distance bands", "Does distance matter", "Band and line"],
        ["07 state tile grid", "Where is delay worst", "Colour, sequential"],
        ["08 cascade hour", "When is delay inherited", "Line"],
        ["09 silhouette", "How many clusters", "Line, position"],
        ["10 cluster scatter", "What separates archetypes", "Position, colour"],
        ["11 importance", "Which factor ranks highest", "Length"],
        ["12 hour response", "How does hour shape risk", "Line"],
        ["13 dashboard", "Interactive communication", "Linked panels"],
        ["14 mean bar vs band", "Mean vs typical flight", "Side-by-side"],
    ],
    [4.6, 7.2, 4.8], size=8.0)

P("", space_after=2)
LEAD("Colour. ",
     "One colour scale per cause, held fixed across every figure so that a cause keeps its colour. The palette "
     "follows Okabe and Ito (2008) so that the five causes stay distinguishable under the common forms of "
     "colour-vision deficiency; sequential scales use viridis, which is monotonic in lightness and therefore "
     "survives greyscale printing.")

LEAD("Interaction. ",
     "The communication layer follows Shneiderman's (1996) task taxonomy: overview first, zoom and filter, then "
     "details on demand. The dashboard opens on a national overview, exposes three filters, and reveals "
     "flight-level detail only on selection; charts are linked so that a filter applied in one panel updates "
     "all others.")

LEAD("Evaluation. ",
     "Usability is measured rather than asserted. Three tasks are given to a non-specialist — locate the worst "
     "month for a named carrier, compare two airports, estimate the risk of a 19:00 departure — and completion "
     "time and errors are recorded alongside a short satisfaction questionnaire. The result is reported as a "
     "small usability note rather than a claim that the interface is intuitive.")

# =====================================================================
# 7. REPOSITORY AND REPRODUCIBILITY
# =====================================================================
H1("7. Repository and Reproducibility")

P("The project is organised as a runnable repository. Every figure and table in the final report is "
  "regenerated from source data by one command, and a 53-test suite pins number provenance.",
  align='justify')

tree_lines = [
    "Team01-FlightDelay-Project/",
    "  README.md                  purpose, setup, run commands, data dictionary link",
    "  requirements.txt           pinned Python dependencies",
    "  Makefile                   setup / data / pipeline / figures / dashboard / test",
    "  docs/                      proposal, meeting minutes, video script, forum posts",
    "  src/                       config, io, cleaning, features, attribution, modelling, viz",
    "  dashboard/                 app.py, layouts, callbacks, panels/, assets/",
    "  figures/                   01-14, one figure per question, regenerated by the stages",
    "  outputs/                   tables/ and metrics/ consumed by the report",
    "  data/                      raw/, interim/, processed/ (excluded from Git)",
    "  tests/                     53 tests over data, analysis, figure and caption layers",
    "  reports/                   final report (report.md) and exported submission PDF",
]
for line in tree_lines:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.left_indent = Cm(0.4)
    r = p.add_run(line)
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn('w:eastAsia'), "Consolas")
    r.font.size = Pt(8)

P("", space_after=2)
LEAD("Run commands. ",
     "python -m pip install -r requirements.txt for environment setup; make data to download and validate the "
     "panel; make pipeline to run every analysis stage; make dashboard to launch the application locally; "
     "make test to run the suite. Every number on screen and in the report comes from the same outputs/ "
     "computation, so no reported number depends on stale notebook state.")

LEAD("Version control. ",
     "One shared GitHub repository with a branch per task, descriptive commit messages and review before "
     "merge. Raw and processed data are excluded because they are large and reproducible from documented URLs; "
     "a checksum manifest records the exact files used in the reported results.")

# =====================================================================
# 8. CRITERIA FOR SUCCESS
# =====================================================================
H1("8. Criteria for Success")

P("Table 4 states the completion standard and the evidence that has been produced for each criterion.",
  align='justify')

CAP("Table 4  Completion checklist and evidence", keep_next=True)
TABLE(
    ["Success criterion", "Evidence produced"],
    [
        ["Scope and data validity",
         "Counts reconcile across all ten annual files (63.1M rows, 61.7M completed); duplicate rate is zero; "
         "the attribution universe and the 15-minute threshold are stated wherever cause shares appear."],
        ["Analytical answer",
         "All four research questions are answered; the headline split carries a bootstrap interval and the "
         "cluster verdict carries a stability score, with no finding presented as causal without support."],
        ["Modelling discipline",
         "Every model reports a baseline, a held-out metric and an explicit statement of what the model ranks "
         "rather than predicts (AUC 0.685 / 0.691 at a 6.1% base rate)."],
        ["Visual encoding justification",
         "Each figure names the question it answers and the encoding it uses (Table 3); the delivered set "
         "covers part-to-whole, distribution, concentration, geography and interaction."],
        ["Reproducibility",
         "One command regenerates every figure; a 53-test suite passes on a clean checkout; outputs are "
         "reproducible from public data."],
        ["Communication and integrity",
         "Every chart carries a title, readable labels and a one-line interpretation; the narrative page states "
         "the core story and the limits of observational data."],
    ],
    [4.2, 12.4], size=8.5, keep_together=True)

# =====================================================================
# 9. TEAM AND COLLABORATION
# =====================================================================
H1("9. Team and Collaboration")

P("Ownership is divided by analytical stage, while interpretation, review and sign-off remain shared. Roles "
  "rotate at the mid-point of the project so that no member owns a single stage for the whole duration.",
  align='justify')

CAP("Table 5  Division of work and group roles", keep_next=True)
TABLE(
    ["Member", "Roles", "Primary responsibilities"],
    [
        ["AO KIT I\nMC660004", "Team Coordinator\nProject Tracker",
         "Meeting agendas and chairing; task board, milestones, dependency map and risk log; progress "
         "summaries; drives both submission dates."],
        ["LI YING FANG\nMC661599", "Project Developer\n(lead)",
         "Data pipeline (acquisition, cleaning, validation), notebook and repository structure, "
         "reproducibility script and dashboard engineering; leads code review."],
        ["HO MAN HOU\nMC661647", "Team Scribe",
         "Minutes of every meeting, the decision log and the scope-change log; repository folder "
         "conventions and file naming."],
        ["WU PEI YE\nMC661846", "Team Reporter\nTeam Liaison",
         "The project proposal as one continuous narrative; the introductory video from script through "
         "edit; instructor communication; rehearsal and final submission package."],
        ["LI TIAN HAO\nMC663312", "Project Analyst\nQuality Reviewer",
         "Research question and data sources; data preparation and the analysis (attribution, cascade, "
         "clustering, modelling); interpretation and limitations. Separately the quality gate: "
         "reproducibility, calculation checks, visual clarity, citations, requirement compliance."],
        ["SAVIDI AVRAM\nMC664364", "Project Developer",
         "Figures, visualisations and interactive outputs (map, archetypes); ten-year panel scaling and "
         "the weather join; stands in for the lead developer."],
    ],
    [3.4, 3.4, 9.8], size=8.2, keep_together=True)

P("", space_after=2)
P("Ground rules.", bold=True, space_after=2, space_before=2)
BUL("One shared repository, a branch per task, descriptive commits, and review before any merge. Code or "
    "figures that cannot be reproduced from the notebooks are never merged.")
BUL("One source of truth for numbers: a quoted result must match a notebook output or a file in outputs/. "
    "The same rule applies to the proposal, the README and the dashboard.")
BUL("A weekly checkpoint on progress, blockers and next actions, with a target response time of 48 hours and "
    "decisions recorded in the project log.")
BUL("Scope is frozen by consensus. A change affecting the research question, the dashboard or the submission "
    "date is discussed before it is implemented.")
BUL("Before submission, every member completes an independent read-through of the report and a functional "
    "check of the dashboard.")

# =====================================================================
# 10. TIMELINE
# =====================================================================
H1("10. Timeline")

P("The analysis stages are complete ahead of the schedule below; the remaining work is the communication "
  "layer, the usability check, the project presentation and the final submission. Project presentations are "
  "held in class on 11, 18 and 25 November, with each team's slot drawn by lot, so the deck and rehearsal "
  "are planned to finish by 11 November, leaving the team ready whichever of the three dates it draws. The "
  "plan completes all activity within four weeks, leaving a two-day buffer before the final close, which "
  "satisfies the four-week requirement in the brief and stays inside the five-week allowance stated in the "
  "course announcements.", align='justify')

CAP("Table 6  Four-week schedule and status", keep_next=True)
TABLE(
    ["Week", "Dates", "Milestone", "Output", "Status"],
    [
        ["0", "3–5 Nov", "Proposal, first meeting minutes and introductory video submitted",
         "Proposal PDF; minutes PDF; 5-minute video; two forum threads", "In progress"],
        ["Present", "11 / 18 / 25 Nov", "Project presentation to the class; Team 01 slot drawn by lot; deck "
         "and rehearsal complete before the earliest 11 Nov slot",
         "Presentation deck; delivery and Q&A", "Scheduled"],
        ["1", "6–12 Nov", "Environment reproduced by all six members; panel acquired and validated",
         "Notebooks 01–02; validation report; repository set up", "Complete"],
        ["2", "13–19 Nov", "Attribution and tail analysis complete; figure audit closed",
         "Notebooks 03–04; Figures 01–13", "Complete"],
        ["3", "20–26 Nov", "Clustering and predictive models complete; explanations written",
         "Notebooks 05–06; Figures 14–20; model table", "Complete"],
        ["4", "27 Nov–3 Dec", "Dashboard and narrative page frozen; usability tasks run",
         "Dashboard; narrative site; usability note", "Analysis done"],
        ["Close", "4–5 Dec", "Final report and submission package",
         "Report PDF; repository tag; submission", "Pending"],
    ],
    [1.5, 2.6, 5.4, 5.0, 2.1], size=8.0, keep_together=True)

# =====================================================================
# 11. LIMITATIONS
# =====================================================================
H1("11. Limitations")

BUL("Observational, not causal. BTS cause minutes are a reported partition in which overlapping causes are "
    "assigned by the reporting carrier; the split is not an independent causal decomposition.")
BUL("Weather enters as a planned covariate, not a delivered one. The hour-matching join is implemented and "
    "exercised on the fixture, but the ten-year Integrated Surface Database (ISD; National Centers for "
    "Environmental Information, n.d.) extraction is not yet part of "
    "the pipeline, so until it lands the weather signal is only the carrier-reported weather cause share. "
    "If the extraction does not land before the report, the covariate is dropped from the claim rather than "
    "reported at partial coverage.")
BUL("Clustering is unstable. The chosen k = 5 solution has silhouette 0.2045 but a mean ARI of 0.69 across "
    "resampled years, below the 0.70 stability threshold; the archetypes are therefore reported with a "
    "stability verdict rather than as fixed airport categories.")
BUL("Prediction is ranking, not forecasting. The held-out AUC is 0.685 (logistic) and 0.691 (gradient "
    "boosting) at a 6.1% base rate, and the full model explains R-squared 0.022 — enough to rank flights, "
    "not to promise a specific arrival time.")
BUL("The 2020-2021 pandemic period is retained but controlled: year fixed effects and a COVID-era dummy enter "
    "every model, and every headline statistic is recomputed with those two years excluded. The report "
    "compares the two versions rather than choosing one silently.")

# =====================================================================
# 12. REFERENCES
# =====================================================================
H1("12. References")

refs = [
    "Bureau of Transportation Statistics. (n.d.-a). Airline on-time performance: Delay cause [Data set]. "
    "U.S. Department of Transportation. Retrieved October 21, 2026, from "
    "https://www.transtats.bts.gov/ot_delay/ot_delaycause1.asp",

    "Bureau of Transportation Statistics. (n.d.-b). Reporting carrier on-time performance (1987–present) "
    "[Data set]. U.S. Department of Transportation. Retrieved October 21, 2026, from "
    "https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EFI",

    "Cairo, A. (2016). The truthful art: Data, charts, and maps for communication. New Riders.",

    "Cleveland, W. S., & McGill, R. (1984). Graphical perception: Theory, experimentation, and application to "
    "the development of graphical methods. Journal of the American Statistical Association, 79(387), 531–554. "
    "https://doi.org/10.1080/01621459.1984.10478080",

    "Federal Aviation Administration. (n.d.). Air traffic by the numbers and passenger boarding (enplanement) "
    "data [Data set]. U.S. Department of Transportation. Retrieved October 21, 2026, from "
    "https://www.faa.gov/air_traffic/by_the_numbers",

    "Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. In Advances "
    "in Neural Information Processing Systems (Vol. 30, pp. 4765–4774).",

    "Mackinlay, J. (1986). Automating the design of graphical presentations of relational information. ACM "
    "Transactions on Graphics, 5(2), 110–141. https://doi.org/10.1145/22949.22950",

    "Munzner, T. (2014). Visualization analysis and design. CRC Press.",

    "National Centers for Environmental Information. (n.d.). Integrated Surface Database (ISD) [Data set]. "
    "National Oceanic and Atmospheric Administration. Retrieved October 21, 2026, from "
    "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",

    "Okabe, M., & Ito, K. (2008). Color universal design (CUD): How to make figures and presentations that "
    "are friendly to colorblind people. J*Fly. https://jfly.uni-koeln.de/color/",

    "OurAirports. (n.d.). Airports [Data set]. Retrieved October 21, 2026, from "
    "https://davidmegginson.github.io/ourairports-data/airports.csv",

    "Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster "
    "analysis. Journal of Computational and Applied Mathematics, 20, 53–65. "
    "https://doi.org/10.1016/0377-0427(87)90125-7",

    "Shneiderman, B. (1996). The eyes have it: A task by data type taxonomy for information visualizations. "
    "In Proceedings of the 1996 IEEE Symposium on Visual Languages (pp. 336–343). "
    "https://doi.org/10.1109/VL.1996.545307",
]

doc.paragraphs[-1].paragraph_format.space_before = Pt(6)
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.0
    if i < len(refs):
        p.paragraph_format.keep_with_next = True
    r = p.add_run(ref)
    r.font.size = Pt(8.6)
    r.font.name = FONT

REQUIRED_FIGURES = {"01_cause_waffle.png", "13_dashboard_part1.png", "13_dashboard_part2.png"}
_missing = REQUIRED_FIGURES - set(EMBEDDED)
assert not _missing, f"figures never reached the document: {sorted(_missing)}"

# =====================================================================
# PAGE NUMBERS
# =====================================================================
# The submitted PDF had no folio on any of its ten pages, so a reader could not
# say "see p. 6" and a marker could not record where a comment applied. A PAGE
# field is used rather than a typed number: if the text is edited later and the
# document re-paginates, the folio follows automatically instead of lying.


def _add_page_number(section):
    para = section.footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(0)
    run = para.add_run()
    run.font.name = FONT
    run.font.size = Pt(9)
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' PAGE '
    fld_sep = OxmlElement('w:fldChar')
    fld_sep.set(qn('w:fldCharType'), 'separate')
    placeholder = OxmlElement('w:t')
    placeholder.text = '1'
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    for el in (fld_begin, instr, fld_sep, placeholder, fld_end):
        run._r.append(el)


for _section in doc.sections:
    _add_page_number(_section)

doc.save(OUT)
print("SAVED:", OUT)
print("figures embedded:", sorted(EMBEDDED))
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables), "images:", len(doc.inline_shapes))
