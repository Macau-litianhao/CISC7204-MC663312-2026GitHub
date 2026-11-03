# Minutes 01 — Team 01 First Meeting

> Complete, review, and circulate this record within 24 hours of each meeting.

Course: CISC7204 Data Science and Data Visualization · Team: Class K — Team 01

*Status: aligned with Work Plan 1 (29 October 2026); reviewed and approved by the
Coordinator on 4 November 2026 and circulated to all six members within 24 hours
of the meeting.*

---

## 1. Meeting Details

| Item | Details |
|---|---|
| Project title | US Domestic Flight Delay Drivers — attribution, cascade, airport archetypes, communication layer |
| Meeting no. | 01 (project kick-off) |
| Date | Tuesday 3 November 2026 |
| Start / end time | 20:00 – 21:15 (HKT) |
| Location / platform | Online — Tencent Meeting (link circulated on the team chat) |
| Meeting chair / facilitator | AO KIT I |
| Minute taker | HO MAN HOU |

## 2. Attendance

| Team member | Present / absent / apology | Role or responsibility |
|---|---|---|
| AO KIT I (MC660004) | Present | Team Coordinator, Project Tracker |
| LI YING FANG (MC661599) | Present | Project Developer (lead) |
| HO MAN HOU (MC661647) | Present | Team Scribe |
| WU PEI YE (MC661846) | Present | Team Reporter, Team Liaison |
| LI TIAN HAO (MC663312) | Present | Project Analyst, Quality Reviewer |
| SAVIDI AVRAM (MC664364) | Present | Project Developer |

All six members attended; the meeting was quorate for every decision below.

## 3. Agenda

| No. | Agenda item | Lead / presenter | Planned time |
|---|---|---|---|
| 1 | Team structure and role assignment | AO KIT I | 20:00 – 20:10 |
| 2 | Selection of the team proposal | LI TIAN HAO, LI YING FANG | 20:10 – 20:30 |
| 3 | Meeting schedule | AO KIT I | 20:30 – 20:40 |
| 4 | Division of work | AO KIT I | 20:40 – 20:50 |
| 5 | Data scope | LI YING FANG | 20:50 – 21:00 |
| 6 | Tooling and repository | LI YING FANG | 21:00 – 21:08 |
| 7 | Submission logistics | AO KIT I | 21:08 – 21:15 |

## 4. Follow-up from Previous Meeting

*Minutes 01 is the first formal team meeting, so there are no carry-over actions
from an earlier meeting. The rows below record the pre-meeting actions and
decisions (from Work Plan 1 and the 2 Nov group chat) that this meeting reviewed
and closed.*

| Previous action or decision | Owner | Progress / evidence | Status | Further action required |
|---|---|---|---|---|
| Work Plan 1 role map (submitted 29 Oct) fixed the eight course roles | AO KIT I | Submitted 29 Oct; pre-circulated in the 2 Nov group chat | Done | Re-confirm the map unchanged in this meeting |
| Topic shortlist discussed informally in the 2 Nov group chat | LI TIAN HAO, LI YING FANG | Preliminary consensus reached before the meeting | Done | Formal selection by vote in this meeting |
| Assignment 02 pilot — US domestic flight delay drivers (2024 file) | LI TIAN HAO, LI YING FANG | Complete: four notebooks, sixteen figures, linked dashboard | Done | Extend to the 2015–2024 panel |
| Draft division of work floated in the 2 Nov chat | AO KIT I | Draft prepared and circulated | Done | Confirm the six-way split in this meeting |

## 5. Discussion Notes

*Record key ideas, evidence, alternatives considered, concerns raised, and
agreed reasoning.*

| Agenda item / topic | Discussion notes |
|---|---|
| Team structure and role assignment | The plan's role map, already shared in the 2 Nov WeChat discussion, was reviewed line by line and confirmed unchanged, so every later document uses the same names. |
| Selection of the team proposal | LI TIAN HAO and LI YING FANG presented their Assignment 02 pilot — *US domestic flight delay drivers* (the 2024 file: four notebooks, sixteen figures, a linked dashboard). Two further pair proposals were also on the table. The group had reached a preliminary consensus in the 2 Nov chat. Criteria agreed before the vote: public data at sufficient scale, an existing validated analysis to build on, and room to extend to six people. |
| Meeting schedule | Weekly meetings plus the two in-class working sessions, as set out in Work Plan 1. The 4 Nov in-class session is reserved for a proposal and video review. |
| Division of work | The pair project was already substantial at two people; a six-person team needs separable work, not the same work split six ways. The division floated on 2 Nov was confirmed here. |
| Data scope | One year cannot separate a structural pattern from a one-year shock, cannot support stable clustering, and cannot test whether the airline/system split holds over time. |
| Tooling and repository | Reuse the validated pipeline rather than restart; convert it into a team repository with tests, a configuration file and documented conventions. |
| Submission logistics | Three artefacts are due 5 November 23:00, and every member submits individually. Implementation began on 2 November, so most analytical work is already complete; the 4 Nov in-class session reviews the video, and 5 November is reserved for final checks and upload. |

## 6. Decisions Made

| No. | Decision | Reason / supporting evidence | Decision owner | Date agreed |
|---|---|---|---|---|
| 1 | Roles confirmed exactly as in Work Plan 1 (see §2); rotation at the mid-point of the project, recorded in Minutes 03 | Role map pre-circulated and reviewed line by line, unchanged | AO KIT I | 3 Nov 2026 |
| 2 | Assignment 02 by LI TIAN HAO and LI YING FANG selected unanimously; analytical and engineering development led by those two, the other four members take on separable work | Public data at sufficient scale, an existing validated analysis to build on, room to extend to six people | Whole team (unanimous) | 3 Nov 2026 |
| 3 | Weekly online meetings with the in-class sessions used as working reviews; minutes circulated within 24 hours; the 4 Nov session doubles as the video storyboard review | Matches Work Plan 1; the in-class sessions are already reserved | AO KIT I | 3 Nov 2026 |
| 4 | Development led by LI TIAN HAO and LI YING FANG; each of the four other members owns a distinct stream and cross-reviews another's (§7); contributions recorded per stage | A six-person team needs separable work, not the same work split six ways | AO KIT I | 3 Nov 2026 |
| 5 | Extend to 2015–2024 — 63,079,392 rows, of which 61,689,698 are completed flights by 20 reporting carriers; add the within-day cascade reconstruction and airport clustering; weather covariates held as a stretch goal | One year cannot separate a structural pattern from a one-year shock, support stable clustering, or test the airline/system split | LI TIAN HAO | 3 Nov 2026 |
| 6 | One shared repository (`Team01-FlightDelay-Project`), a stage per script, a fixture-based smoke run, and `pytest` as the merge gate | Reuse the validated pipeline rather than restart | LI YING FANG | 3 Nov 2026 |
| 7 | Proposal, Minutes 01 and the introductory video are each posted in full to the correct forum **and** uploaded; no member uploads on another member's behalf; submission completed on 5 November | Course requires a forum post **and** a link upload per artefact, and every member submits individually | AO KIT I | 3 Nov 2026 |

## 7. Action Items and Task Assignments

*Each task has one accountable member and a clear due date.*

| No. | Task / deliverable | Assigned to | Due date | Priority | Status / notes |
|---|---|---|---|---|---|
| 1 | Extend the pair's pipeline to the ten-year panel: acquisition, validation and cause attribution | LI YING FANG (Developer lead) | 3 Nov | High | Done |
| 2 | Complete the analysis on the full panel: within-day cascade, airport clustering, tail concentration and predictive modelling | LI TIAN HAO (Analyst) | 3 Nov | High | Done |
| 3 | Build the new dashboard panels (map, archetypes), the weather join and the figure styling | SAVIDI AVRAM (Developer) | 4 Nov | Medium | In progress |
| 4 | Integrate the proposal as one continuous narrative, drawing on the pair's analysis | WU PEI YE (Reporter) | 4 Nov | High | In progress |
| 5 | Draft Minutes 01 and the decision log; set the repository naming conventions | HO MAN HOU (Scribe) | 4 Nov | High | In progress |
| 6 | Build the task board, milestone list and risk log; drive the 5 Nov submission | AO KIT I (Coordinator, Tracker) | 4 Nov | High | In progress |
| 7 | Agree the video storyboard in the 4 Nov class, then record and edit the five-minute video (group photo, six names and IDs, project title, course code) | SAVIDI AVRAM | 5 Nov | High | Open |
| 8 | Quality gate: reproducibility tests, calculation and citation checks, figure audit, requirement compliance | LI TIAN HAO (Quality Reviewer) | 5 Nov | High | Open |
| 9 | Confirm the video format and submission channel with the instructor | WU PEI YE (Liaison) | 4 Nov | Medium | Open |
| 10 | Post the proposal and minutes to their forums; confirm all six individual uploads | AO KIT I (Coordinator) | 5 Nov | High | Open |

## 8. Risks, Issues, and Support Needed

| Issue, risk, or blocker | Impact | Owner | Resolution / support required | Target date |
|---|---|---|---|---|
| Ten-year panel is ≈4 GB and the download is slow or throttled | Blocks every analytical stage | LI YING FANG | Build the pipeline against a synthetic fixture first; download in the background from day one | 3 Nov |
| The pilot project was already complete at two people | Four members may have no substantive work, which shows in the collaboration mark | LI TIAN HAO | New analytical content is defined up front (cascade, clustering, weather, dashboard) rather than created late | 4 Nov |
| 15-page limit includes cover and references | Trimming after writing risks losing content | WU PEI YE | Draft to nine pages, then measure the PDF page count before submission (current draft: 10 pages, within the limit) | 5 Nov |
| Six people editing one document | Version conflicts and lost edits | WU PEI YE | One owner per section, merged by the Reporter; no simultaneous editing of the same file | 5 Nov |
| Forum post forgotten because a file was uploaded | Artefact not marked | AO KIT I | Submission checklist with a forum row and an upload row per artefact, verified by two members | 5 Nov |

## 9. Matters for Next Meeting

| Matter to resolve / next agenda item | Preparation required | Responsible member |
|---|---|---|
| Final read-through of the near-final proposal before the 5 November upload; record any instructor comments received so far | Bring the near-final proposal PDF and any comments already received | AO KIT I (Coordinator) |
| Discuss and agree the five-minute video: storyboard, footage, roles and narration | Draft the storyboard and shot list | SAVIDI AVRAM (Developer) |
| Walk through the clustering selection: chosen k, silhouette value and stability verdict | Prepare the clustering summary and metrics | LI TIAN HAO (Analyst) |
| Agree the first draft structure of the final report and who writes which section | Propose a section outline | WU PEI YE (Reporter) |

## 10. Next Meeting

| Item | Details |
|---|---|
| Date and time | Wednesday 4 November 2026, in class (proposal and video-storyboard review before the 5 November deadline) |
| Location / platform | In class, then online as needed |
| Proposed chair / minute taker | Chair: AO KIT I · Minute taker: HO MAN HOU |

## 11. Any Other Business (AOB)

| Item / note | Follow-up or decision |
|---|---|
| The annotated group photo from the team-formation session is available | Reuse it in the five-minute video |
| Every quoted number must match a file in `outputs/` or a notebook cell; numbers are never typed from memory | Standing rule for all reports |
| The video storyboard and script are discussed in the 4 Nov in-class session; no member uploads on another member's behalf | Review the storyboard on 4 Nov |

## 12. Review and Circulation

| Item | Details |
|---|---|
| Minutes prepared by | HO MAN HOU (Scribe) |
| Prepared on | 4 November 2026 |
| Reviewed / approved by | AO KIT I (Coordinator) |
| Distribution / shared-storage location | All six members, within 24 hours of the meeting; team shared folder `docs/meeting-minutes/`; posted in the Collaborative Forum |
