import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = Path(__file__).resolve().parent
OUT_DOCX = str(HERE / "01_Team01_Meeting_Minutes.docx")
OUT_PDF = str(HERE / "01_Team01_Meeting_Minutes.pdf")

FONT = "Times New Roman"

# Template palette (sampled from the official template PDF).
DARK_BLUE = RGBColor(0x17, 0x36, 0x5D)   # title + section headings
HEADER_FILL = "B7D7EE"                     # light-blue table header row
FOOTER_GRAY = RGBColor(0x80, 0x80, 0x80)   # running footer text

doc = Document()

# ---------- page setup ----------
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
    """Section heading in the template's dark blue."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(12.5)
    r.font.name = FONT
    r.font.color.rgb = DARK_BLUE
    return p


def P(text="", size=10.5, bold=False, italic=False, align=None, space_after=4,
      space_before=0, line=1.10, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = line
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
        if color is not None:
            r.font.color.rgb = color
    return p


def _repeat_as_header(row):
    trPr = row._tr.get_or_add_trPr()
    flag = OxmlElement('w:tblHeader')
    flag.set(qn('w:val'), 'true')
    trPr.append(flag)


def _keep_row_whole(row):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))


def _keep_row_with_next(row):
    """Bind a row to the following row so a table does not strand a single row
    alone on the next page."""
    for cell in row.cells:
        for pp in cell.paragraphs:
            pp.paragraph_format.keep_with_next = True


def _shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    tcPr.append(shd)


def _set_table_borders(table, sz=4, color='000000'):
    """Force one uniform border on the whole table (no hairline gaps)."""
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


def TABLE(headers, rows, widths, size=9.0, keep_together=False):
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
        rr.bold = True
        rr.font.size = Pt(size)
        rr.font.name = FONT
        _shade_cell(hdr[i], HEADER_FILL)
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
    if keep_together:
        for row in list(t.rows)[:-1]:
            _keep_row_with_next(row)
    elif len(t.rows) >= 2:
        _keep_row_with_next(t.rows[-2])
    _repeat_as_header(t.rows[0])
    _set_table_borders(t)
    return t


def BUL(text, size=10.5, keep_next=False):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.10
    if keep_next:
        p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = FONT
    return p


# ---------- running footer ----------
# A borderless two-cell table gives reliable left/right alignment without
# relying on tab stops (Word drops direct-format tab stops on the Footer style).
footer = sec.footer
for p in list(footer.paragraphs):
    p._element.getparent().remove(p._element)

def _footer_run(par, text, align):
    par.alignment = align
    par.paragraph_format.space_after = Pt(0)
    par.paragraph_format.space_before = Pt(0)
    rr = par.add_run(text)
    rr.italic = True
    rr.font.size = Pt(9)
    rr.font.name = FONT
    rr.font.color.rgb = FOOTER_GRAY
    return rr

_tbl = footer.add_table(rows=1, cols=2, width=Cm(16.6))
_tbl.autofit = False
_tblPr = _tbl._tbl.tblPr
_layout = OxmlElement('w:tblLayout'); _layout.set(qn('w:type'), 'fixed'); _tblPr.append(_layout)

_left = _tbl.cell(0, 0)
_left.width = Cm(11.6)
_footer_run(_left.paragraphs[0], "Self-Directed Project Team Meeting Minutes",
            WD_ALIGN_PARAGRAPH.LEFT)

_right = _tbl.cell(0, 1)
_right.width = Cm(5.0)
_footer_run(_right.paragraphs[0], "Page ", WD_ALIGN_PARAGRAPH.RIGHT)
# PAGE field in the right cell
_r = _right.paragraphs[0].add_run()
_r.italic = True
_r.font.size = Pt(9)
_r.font.name = FONT
_r.font.color.rgb = FOOTER_GRAY
_f1 = OxmlElement('w:fldChar'); _f1.set(qn('w:fldCharType'), 'begin')
_instr = OxmlElement('w:instrText'); _instr.set(qn('xml:space'), 'preserve'); _instr.text = 'PAGE'
_f2 = OxmlElement('w:fldChar'); _f2.set(qn('w:fldCharType'), 'end')
_r._r.append(_f1); _r._r.append(_instr); _r._r.append(_f2)


# =====================================================================
# TITLE BLOCK (matches the official template)
# =====================================================================
P("SELF-DIRECTED PROJECT TEAM", size=18, bold=True, align='center',
  space_after=0, color=DARK_BLUE)
P("MEETING MINUTES", size=18, bold=True, align='center',
  space_after=6, color=DARK_BLUE)
P("Complete, review, and circulate this record within 24 hours of each meeting.",
  size=10.5, italic=True, align='center', space_after=10)
P("CISC7204 Data Science and Data Visualization · Class K — Team 01 · Minutes 01 (First Meeting)",
  size=11, align='center', space_after=14, color=DARK_BLUE)

# =====================================================================
# 1. MEETING DETAILS
# =====================================================================
H1("1. Meeting Details")
TABLE(
    ["Item", "Details"],
    [
        ["Project title", "US Domestic Flight Delay Drivers — attribution, cascade, airport archetypes, communication layer"],
        ["Meeting no.", "01 (project kick-off)"],
        ["Date", "Tuesday 3 November 2026"],
        ["Start / end time", "20:00 – 21:15 (HKT)"],
        ["Location / platform", "Online — Tencent Meeting (link circulated on the team chat)"],
        ["Meeting chair / facilitator", "AO KIT I"],
        ["Minute taker", "HO MAN HOU"],
    ],
    [6.5, 10.1], size=10.0, keep_together=True)

# =====================================================================
# 2. ATTENDANCE
# =====================================================================
H1("2. Attendance")
TABLE(
    ["Team member", "Present / absent / apology", "Role or responsibility"],
    [
        ["AO KIT I (MC660004)", "Present", "Team Coordinator, Project Tracker"],
        ["LI YING FANG (MC661599)", "Present", "Project Developer (lead)"],
        ["HO MAN HOU (MC661647)", "Present", "Team Scribe"],
        ["WU PEI YE (MC661846)", "Present", "Team Reporter, Team Liaison"],
        ["LI TIAN HAO (MC663312)", "Present", "Project Analyst, Quality Reviewer"],
        ["SAVIDI AVRAM (MC664364)", "Present", "Project Developer"],
    ],
    [5.0, 4.2, 7.4], size=10.0, keep_together=True)
P("All six members attended; the meeting was quorate for every decision below.",
  size=10.0, italic=True, space_before=4)

# =====================================================================
# 3. AGENDA
# =====================================================================
H1("3. Agenda")
TABLE(
    ["No.", "Agenda item", "Lead / presenter", "Planned time"],
    [
        ["1", "Team structure and role assignment", "AO KIT I", "20:00 – 20:10"],
        ["2", "Selection of the team proposal", "LI TIAN HAO, LI YING FANG", "20:10 – 20:30"],
        ["3", "Meeting schedule", "AO KIT I", "20:30 – 20:40"],
        ["4", "Division of work", "AO KIT I", "20:40 – 20:50"],
        ["5", "Data scope", "LI YING FANG", "20:50 – 21:00"],
        ["6", "Tooling and repository", "LI YING FANG", "21:00 – 21:08"],
        ["7", "Submission logistics", "AO KIT I", "21:08 – 21:15"],
    ],
    [1.0, 6.8, 5.0, 3.8], size=9.0)

# =====================================================================
# 4. FOLLOW-UP FROM PREVIOUS MEETING
# =====================================================================
H1("4. Follow-up from Previous Meeting")
P("Minutes 01 is the first formal team meeting, so there are no carry-over "
  "actions from an earlier meeting. The rows below record the pre-meeting "
  "actions and decisions (from Work Plan 1 and the 2 Nov group chat) that this "
  "meeting reviewed and closed.", size=9.5, italic=True, space_after=4)
TABLE(
    ["Previous action or decision", "Owner", "Progress / evidence", "Status", "Further action required"],
    [
        ["Work Plan 1 role map (submitted 29 Oct) fixed the eight course roles",
         "AO KIT I",
         "Submitted 29 Oct; pre-circulated in the 2 Nov group chat",
         "Done",
         "Re-confirm the map unchanged in this meeting"],
        ["Topic shortlist discussed informally in the 2 Nov group chat",
         "LI TIAN HAO, LI YING FANG",
         "Preliminary consensus reached before the meeting",
         "Done",
         "Formal selection by vote in this meeting"],
        ["Assignment 02 pilot — US domestic flight delay drivers (2024 file)",
         "LI TIAN HAO, LI YING FANG",
         "Complete: four notebooks, sixteen figures, linked dashboard",
         "Done",
         "Extend to the 2015–2024 panel"],
        ["Draft division of work floated in the 2 Nov chat",
         "AO KIT I",
         "Draft prepared and circulated",
         "Done",
         "Confirm the six-way split in this meeting"],
    ],
    [4.2, 2.8, 3.6, 1.2, 4.8], size=8.5)

# =====================================================================
# 5. DISCUSSION NOTES
# =====================================================================
H1("5. Discussion Notes")
P("Record key ideas, evidence, alternatives considered, concerns raised, and "
  "agreed reasoning.", size=9.5, italic=True, space_after=4)
TABLE(
    ["Agenda item / topic", "Discussion notes"],
    [
        ["Team structure and role assignment",
         "The plan's role map, already shared in the 2 Nov WeChat discussion, was reviewed line by line and confirmed unchanged, so every later document uses the same names."],
        ["Selection of the team proposal",
         "LI TIAN HAO and LI YING FANG presented their Assignment 02 pilot — US domestic flight delay drivers (the 2024 file: four notebooks, sixteen figures, a linked dashboard). Two further pair proposals were also on the table. The group had reached a preliminary consensus in the 2 Nov chat. Criteria agreed before the vote: public data at sufficient scale, an existing validated analysis to build on, and room to extend to six people."],
        ["Meeting schedule",
         "Weekly meetings plus the two in-class working sessions, as set out in Work Plan 1. The 4 Nov in-class session is reserved for a proposal and video review."],
        ["Division of work",
         "The pair project was already substantial at two people; a six-person team needs separable work, not the same work split six ways. The division floated on 2 Nov was confirmed here."],
        ["Data scope",
         "One year cannot separate a structural pattern from a one-year shock, cannot support stable clustering, and cannot test whether the airline/system split holds over time."],
        ["Tooling and repository",
         "Reuse the validated pipeline rather than restart; convert it into a team repository with tests, a configuration file and documented conventions."],
        ["Submission logistics",
         "Three artefacts are due 5 November 23:00, and every member submits individually. Implementation began on 2 November, so most analytical work is already complete; the 4 Nov in-class session reviews the video, and 5 November is reserved for final checks and upload."],
    ],
    [4.2, 12.4], size=9.0)

# =====================================================================
# 6. DECISIONS MADE
# =====================================================================
H1("6. Decisions Made")
TABLE(
    ["No.", "Decision", "Reason / supporting evidence", "Decision owner", "Date agreed"],
    [
        ["1", "Roles confirmed exactly as in Work Plan 1 (see §2); rotation at the mid-point of the project, recorded in Minutes 03",
         "Role map pre-circulated and reviewed line by line, unchanged",
         "AO KIT I", "3 Nov 2026"],
        ["2", "Assignment 02 by LI TIAN HAO and LI YING FANG selected unanimously; analytical and engineering development led by those two, the other four members take on separable work",
         "Public data at sufficient scale, an existing validated analysis to build on, room to extend to six people",
         "Whole team (unanimous)", "3 Nov 2026"],
        ["3", "Weekly online meetings with the in-class sessions used as working reviews; minutes circulated within 24 hours; the 4 Nov session doubles as the video storyboard review",
         "Matches Work Plan 1; the in-class sessions are already reserved",
         "AO KIT I", "3 Nov 2026"],
        ["4", "Development led by LI TIAN HAO and LI YING FANG; each of the four other members owns a distinct stream and cross-reviews another's (§7); contributions recorded per stage",
         "A six-person team needs separable work, not the same work split six ways",
         "AO KIT I", "3 Nov 2026"],
        ["5", "Extend to 2015–2024 — 63,079,392 rows, of which 61,689,698 are completed flights by 20 reporting carriers; add the within-day cascade reconstruction and airport clustering; weather covariates held as a stretch goal",
         "One year cannot separate a structural pattern from a one-year shock, support stable clustering, or test the airline/system split",
         "LI TIAN HAO", "3 Nov 2026"],
        ["6", "One shared repository (Team01-FlightDelay-Project), a stage per script, a fixture-based smoke run, and pytest as the merge gate",
         "Reuse the validated pipeline rather than restart",
         "LI YING FANG", "3 Nov 2026"],
        ["7", "Proposal, Minutes 01 and the introductory video are each posted in full to the correct forum and uploaded; no member uploads on another member's behalf; submission completed on 5 November",
         "Course requires a forum post and a link upload per artefact, and every member submits individually",
         "AO KIT I", "3 Nov 2026"],
    ],
    [0.9, 6.8, 4.6, 2.4, 1.9], size=8.0)

# =====================================================================
# 7. ACTION ITEMS AND TASK ASSIGNMENTS
# =====================================================================
H1("7. Action Items and Task Assignments")
P("Each task has one accountable member and a clear due date.",
  size=9.5, italic=True, space_after=4)
TABLE(
    ["No.", "Task / deliverable", "Assigned to", "Due date", "Priority", "Status / notes"],
    [
        ["1", "Extend the pair's pipeline to the ten-year panel: acquisition, validation and cause attribution", "LI YING FANG (Developer lead)", "3 Nov", "High", "Done"],
        ["2", "Complete the analysis on the full panel: within-day cascade, airport clustering, tail concentration and predictive modelling", "LI TIAN HAO (Analyst)", "3 Nov", "High", "Done"],
        ["3", "Build the new dashboard panels (map, archetypes), the weather join and the figure styling", "SAVIDI AVRAM (Developer)", "4 Nov", "Medium", "In progress"],
        ["4", "Integrate the proposal as one continuous narrative, drawing on the pair's analysis", "WU PEI YE (Reporter)", "4 Nov", "High", "In progress"],
        ["5", "Draft Minutes 01 and the decision log; set the repository naming conventions", "HO MAN HOU (Scribe)", "4 Nov", "High", "In progress"],
        ["6", "Build the task board, milestone list and risk log; drive the 5 Nov submission", "AO KIT I (Coordinator, Tracker)", "4 Nov", "High", "In progress"],
        ["7", "Agree the video storyboard in the 4 Nov class, then record and edit the five-minute video (group photo, six names and IDs, project title, course code)", "SAVIDI AVRAM", "5 Nov", "High", "Open"],
        ["8", "Quality gate: reproducibility tests, calculation and citation checks, figure audit, requirement compliance", "LI TIAN HAO (Quality Reviewer)", "5 Nov", "High", "Open"],
        ["9", "Confirm the video format and submission channel with the instructor", "WU PEI YE (Liaison)", "4 Nov", "Medium", "Open"],
        ["10", "Post the proposal and minutes to their forums; confirm all six individual uploads", "AO KIT I (Coordinator)", "5 Nov", "High", "Open"],
    ],
    [1.0, 5.8, 3.2, 1.6, 1.4, 2.6], size=8.0)

# =====================================================================
# 8. RISKS, ISSUES, AND SUPPORT NEEDED
# =====================================================================
H1("8. Risks, Issues, and Support Needed")
TABLE(
    ["Issue, risk, or blocker", "Impact", "Owner", "Resolution / support required", "Target date"],
    [
        ["Ten-year panel is ≈4 GB and the download is slow or throttled",
         "Blocks every analytical stage",
         "LI YING FANG",
         "Build the pipeline against a synthetic fixture first; download in the background from day one",
         "3 Nov"],
        ["The pilot project was already complete at two people",
         "Four members may have no substantive work, which shows in the collaboration mark",
         "LI TIAN HAO",
         "New analytical content is defined up front (cascade, clustering, weather, dashboard) rather than created late",
         "4 Nov"],
        ["15-page limit includes cover and references",
         "Trimming after writing risks losing content",
         "WU PEI YE",
         "Draft to nine pages, then measure the PDF page count before submission (current draft: 10 pages, within the limit)",
         "5 Nov"],
        ["Six people editing one document",
         "Version conflicts and lost edits",
         "WU PEI YE",
         "One owner per section, merged by the Reporter; no simultaneous editing of the same file",
         "5 Nov"],
        ["Forum post forgotten because a file was uploaded",
         "Artefact not marked",
         "AO KIT I",
         "Submission checklist with a forum row and an upload row per artefact, verified by two members",
         "5 Nov"],
    ],
    [4.2, 3.0, 2.2, 5.2, 1.8], size=8.0)

# =====================================================================
# 9. MATTERS FOR NEXT MEETING
# =====================================================================
H1("9. Matters for Next Meeting")
TABLE(
    ["Matter to resolve / next agenda item", "Preparation required", "Responsible member"],
    [
        ["Final read-through of the near-final proposal before the 5 November upload; record any instructor comments received so far",
         "Bring the near-final proposal PDF and any comments already received",
         "AO KIT I (Coordinator)"],
        ["Discuss and agree the five-minute video: storyboard, footage, roles and narration",
         "Draft the storyboard and shot list",
         "SAVIDI AVRAM (Developer)"],
        ["Walk through the clustering selection: chosen k, silhouette value and stability verdict",
         "Prepare the clustering summary and metrics",
         "LI TIAN HAO (Analyst)"],
        ["Agree the first draft structure of the final report and who writes which section",
         "Propose a section outline",
         "WU PEI YE (Reporter)"],
    ],
    [7.2, 4.6, 4.8], size=9.0)

# =====================================================================
# 10. NEXT MEETING
# =====================================================================
H1("10. Next Meeting")
TABLE(
    ["Item", "Details"],
    [
        ["Date and time", "Wednesday 4 November 2026, in class (proposal and video-storyboard review before the 5 November deadline)"],
        ["Location / platform", "In class, then online as needed"],
        ["Proposed chair / minute taker", "Chair: AO KIT I · Minute taker: HO MAN HOU"],
    ],
    [6.5, 10.1], size=10.0, keep_together=True)

# =====================================================================
# 11. ANY OTHER BUSINESS (AOB)
# =====================================================================
H1("11. Any Other Business (AOB)")
TABLE(
    ["Item / note", "Follow-up or decision"],
    [
        ["The annotated group photo from the team-formation session is available",
         "Reuse it in the five-minute video"],
        ["Every quoted number must match a file in outputs/ or a notebook cell; numbers are never typed from memory",
         "Standing rule for all reports"],
        ["The video storyboard and script are discussed in the 4 Nov in-class session; no member uploads on another member's behalf",
         "Review the storyboard on 4 Nov"],
    ],
    [8.2, 8.4], size=9.0)

# =====================================================================
# 12. REVIEW AND CIRCULATION
# =====================================================================
H1("12. Review and Circulation")
TABLE(
    ["Item", "Details"],
    [
        ["Minutes prepared by", "HO MAN HOU (Scribe)"],
        ["Prepared on", "4 November 2026"],
        ["Reviewed / approved by", "AO KIT I (Coordinator)"],
        ["Distribution / shared-storage location", "All six members, within 24 hours of the meeting; team shared folder docs/meeting-minutes/; posted in the Collaborative Forum"],
    ],
    [6.5, 10.1], size=10.0, keep_together=True)


doc.save(OUT_DOCX)
print("saved", OUT_DOCX)


# ---------- export PDF ----------
def export_pdf():
    import win32com.client
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        d = word.Documents.Open(OUT_DOCX, ReadOnly=True)
        # wdFormatPDF = 17
        d.SaveAs(OUT_PDF, FileFormat=17)
        d.Close(False)
    finally:
        word.Quit()
    print("saved", OUT_PDF)


if __name__ == "__main__":
    export_pdf()
