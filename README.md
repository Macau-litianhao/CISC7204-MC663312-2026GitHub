# CISC7204 Data Visualization – Coursework Portfolio

Coursework by Li Tianhao (MC663312), University of Macau, 2026.

| Folder | Contents |
|---|---|
| [cisc7204-Assgn01-2026-MC663312](cisc7204-Assgn01-2026-MC663312/) | Assignment 1 materials; preserved unchanged. |
| [cisc7204-Assgn02-2026-MC663312](cisc7204-Assgn02-2026-MC663312/) | Assignment 2 materials; preserved unchanged. |
| [cisc7204-SemesterProject-2026-MC663312](cisc7204-SemesterProject-2026-MC663312/) | Current Team 01 flight-delay analysis and visualisation product. |

## Semester project

The semester project directory contains Python analysis code, seven notebooks,
configuration, data provenance, generated figures and result tables, the linked
Dash dashboard, technical standards and automated tests. See its README for
research questions, source datasets, methods and limitations.

Course proposals, meeting records, forum drafts, videos, presentation decks,
submission checklists, review documents and final-report deliverables are managed
in the separate local Semester Project workspace. They are outside this project
directory. Earlier committed versions remain available in Git history.

```bash
cd cisc7204-SemesterProject-2026-MC663312
python -m pip install -r requirements.txt
python run_all.py --stage smoke
python dashboard/app.py
python -m pytest tests -q
```

The smoke command writes synthetic outputs to isolated sample subdirectories
without replacing empirical figures or result files. These demonstrate the workflow and are not empirical findings.
To analyse the real panel, run `python run_all.py --stage data`, then
`python run_all.py --stage pipeline`. Raw and processed datasets are excluded from
Git; source URLs and checksums are retained. The dashboard is a sample-based
prototype; see the project README before interpreting any statistics.

The repository name and remote URL remain unchanged. Only the semester project
subdirectory was renamed; assignments are unaffected.
