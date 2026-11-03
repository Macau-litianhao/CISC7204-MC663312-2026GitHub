# Forum post — First Meeting Minutes

**Where:** the team's own Collaborative Forum
**Subject line, exactly:** `Team 01 - Our First Team Meeting Minutes`
**Body:** paste the minutes below in full, then attach the same content as a PDF
for the assignment upload. Both are required; neither substitutes for the other.

Formatting note: the tables are transcribed as plain lists because the Moodle
editor turns a pasted table into a single unreadable row. The PDF attachment keeps
the tabular layout.

---

## Team 01 - Our First Team Meeting Minutes

**Course:** CISC7204 Data Science and Data Visualization
**Team:** Class K — Team 01
**Meeting:** 01, project kick-off
**Date:** Tuesday 3 November 2026, 20:00–21:15 (HKT), online
**Chair:** AO KIT I · **Minute taker:** HO MAN HOU

### 1. Attendance

All six members present, so the meeting was quorate for every decision recorded
below: AO KIT I (MC660004), LI YING FANG (MC661599), HO MAN HOU (MC661647),
WU PEI YE (MC661846), LI TIAN HAO (MC663312), SAVIDI AVRAM (MC664364).

### 2. Team structure and roles

The eight course roles are mapped onto six members exactly as in Work Plan 1, so
every later document uses the same names. Assignment:

- **AO KIT I** — Team Coordinator and Project Tracker: meeting agendas and chairing, task board, milestones, dependency map, risk log, drives both submission dates.
- **LI YING FANG** — Project Developer (lead): data pipeline, notebook and repository structure, reproducibility script, dashboard engineering, leads code review.
- **HO MAN HOU** — Team Scribe: minutes, decision log, scope-change log, repository folder conventions and file naming.
- **WU PEI YE** — Team Reporter and Team Liaison: proposal narrative, introductory video script, instructor communication, rehearsal and final submission package.
- **LI TIAN HAO** — Project Analyst and Quality Reviewer: research question and data sources, data preparation and analysis, interpretation and limitations; separately the quality gate before submission.
- **SAVIDI AVRAM** — Project Developer: figures, visualisations and interactive outputs (map, archetypes), ten-year panel scaling and the weather join, and the recording and editing of the introductory video; stands in for the lead developer.

**Decision.** Roles rotate at the midpoint of the project so that no member owns a
single stage for the whole duration. The swap will be recorded in Minutes 03.

### 3. Selection of the team proposal

Three pair proposals were presented. Criteria agreed before voting: availability
of public data at sufficient scale, an existing validated analysis to build on,
and room to extend to six people.

**Decision (unanimous).** The proposal based on the Assignment 02 completed by
**LI TIAN HAO and LI YING FANG** — *US Domestic Flight Delay Drivers* — becomes the
team project. Reasons: a complete pilot analysis already exists (four notebooks,
sixteen figures, a linked dashboard); the data are public and redistributable; and
three extensions are identifiable rather than invented — a ten-year panel, a
within-day cascade measurement and airport clustering.

Because the pilot already exists, the analytical and engineering development is led
by LI TIAN HAO and LI YING FANG, while the other four members take on genuinely
separable work.

### 4. Meeting schedule

Weekly meetings plus the two in-class working sessions, as set out in Work Plan 1.

**Decision.** Weekly online meetings with the in-class sessions used as working
reviews. Minutes are circulated within 24 hours of each meeting and kept in the
shared folder.

### 5. Division of work and individual contributions

Work is divided by deliverable with one owner and one reviewer, as in Work Plan 1.
Development (analytical and engineering) is led by LI TIAN HAO and LI YING FANG;
each of the four other members owns a distinct stream and cross-reviews another's.

- LI TIAN HAO — the analysis: within-day cascade, airport clustering, tail concentration, predictive modelling; and the quality gate.
- LI YING FANG — the pipeline: ten-year panel acquisition, validation and cause attribution; repository and reproducibility.
- SAVIDI AVRAM — the new dashboard panels (map, archetypes), the weather join, figure styling, and the video.
- WU PEI YE — the proposal narrative and video script; instructor liaison.
- HO MAN HOU — the minutes, decision log and repository naming conventions.
- AO KIT I — the task board, milestone list, risk log, and driving the submission.

Individual contributions are recorded per stage so the final report can state who
did what.

### 6. Data scope

**Decision.** Extend the pilot from 2024 to 2015–2024 — 63,079,392 rows, of which
61.7 million are completed flights by 20 reporting carriers. Add the within-day
cascade reconstruction and airport clustering as new analytical content. Weather
covariates are a stretch goal and are not promised in the proposal.

### 7. Action items

- LI YING FANG — extend the pair's pipeline to the ten-year panel. Due 4 Nov, 20:00.
- LI TIAN HAO — complete the analysis (cascade, clustering, tail, modelling). Due 4 Nov, 20:00.
- SAVIDI AVRAM — build the new dashboard panels, weather join and figure styling. Due 5 Nov, 12:00.
- WU PEI YE — integrate the proposal narrative. Due 4 Nov, 18:00.
- HO MAN HOU — draft Minutes 01, decision log and naming conventions. Due 4 Nov, 20:00.
- AO KIT I — task board, milestones, risk log; drive the 5 Nov submission. Due 5 Nov, 10:00.
- SAVIDI AVRAM — record and edit the five-minute video. Due 5 Nov, 16:00.
- LI TIAN HAO — quality gate: tests, calculation and citation checks, figure audit. Due 5 Nov, 12:00.
- WU PEI YE — confirm video format and channel with the instructor. Due 4 Nov, 18:00.
- AO KIT I — post both artefacts to their forums and confirm six individual uploads. Due 5 Nov, 21:00.

### 8. Risks and support needed

- **Ten-year panel is ≈4 GB.** Mitigation: build and validate the pipeline on a synthetic fixture first, and start the download in the background on day one.
- **The pilot was already complete at two people.** Mitigation: new analytical content is defined up front rather than invented late.
- **Fifteen-page limit includes cover and references.** Mitigation: draft to nine pages and measure the PDF page count before submission.
- **Six people editing one document.** Mitigation: one owner per section, merged by the Reporter.
- **Forum post forgotten after a file upload.** Mitigation: a submission checklist with a forum row and an upload row per artefact, verified by two members.

### 9. Next meeting

Wednesday 4 November 2026, in class (proposal and video review before the
5 November deadline). Chair: AO KIT I. Minute taker: HO MAN HOU.

Agenda: final read-through of the near-final proposal before the 5 November
upload; download status of the panel and the fallback if incomplete; the
clustering selection (chosen k, silhouette, stability); and the first draft
structure of the final report.

### 10. Any other business

The annotated group photo from the team-formation session will be reused in the
video. Every quoted number must match a file in `outputs/` or a notebook cell;
numbers are never typed from memory. No member uploads on another member's behalf,
because the brief marks individual submission.

---

Minutes prepared by HO MAN HOU on 4 November 2026, reviewed by AO KIT I, shared
in the team folder and distributed to all six members within 24 hours of the meeting.
