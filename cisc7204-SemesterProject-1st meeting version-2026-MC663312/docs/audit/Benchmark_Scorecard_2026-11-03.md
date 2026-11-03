# Benchmark scorecard — 2026-11-03 (third round)

The first two rounds answered *is anything broken* (12 defects fixed) and *why
does it not read like the work it is compared with* (narrative layer added,
69 → 88). This round is scoped by the reviewer's brief: judge the workspace on
**three levels — code, web design, workspace organisation** — against published
exemplars, then optimise the structure so a reader knows the topic, the
question, and what to take away.

The three levels were scored with the same six-dimension rubric as the last
round (so the numbers stay comparable), but the reference set is extended
beyond "what makes a chart legible" to "what makes the code and the repository
legible too".

---

## 1. Reference set, by level

The design references (B1–B7) from the previous round are unchanged and still
apply; this round adds the two levels the earlier rounds did not benchmark.

| # | Exemplar | What it does that this project did not yet do |
|---|---|---|
| B1–B7 | The Pudding, NYT, Our World in Data, Reuters, FiveThirtyEight, Kieran Healy, FT | (carried over) claim-first order, annotation on the graphic, method at the point of the claim, one message per chart. |
| B8 | **OWID's public data repositories** (`owid/etl`, `owid/covid-19-data`) | No dead code, one declarative source of truth, tests that guard the *claims* not just the syntax, and a README whose status table is the truth, not an aspiration. |
| B9 | **FiveThirtyEight's data repos** | Every chart ships with its script and its data side by side, so "which number came from where" is answered by the directory layout, not by prose. |
| B10 | **DrivenData's cookiecutter-data-science** | A repository that explains itself: `data/` is stratified raw → interim → processed, `config` is the single parameter home, `docs` carries the standards, and one command rebuilds everything. |

The working hypothesis behind adding B8–B10: a visualisation project is not only
the page. Its **code** is read by the next person who has to reproduce it, and
its **workspace** is read by anyone who has to trust a number in the report.

---

## 2. Rubric (unchanged from round two, for comparability)

| Dimension | Weight | A 90%+ looks like |
|---|---|---|
| D1 Data handling and reproducibility | 20 | One command rebuilds; thresholds in config; every table traceable; fixture impossible to mistake for a result; no dead code. |
| D2 Does the analysis answer the question | 25 | Each research question has an answer, a number, and the falsification check; limits that survive the data are stated. |
| D3 Chart choice and encoding correctness | 20 | Encoding matches the task; colour chosen by data type; no chart whose reading contradicts its caption or its title. |
| D4 Page structure and narrative | 20 | Claim above the fold; claim → evidence → caveat order; each panel earns its place; the page ends by telling the reader what to do. |
| D5 Text and readability | 10 | Every chart introduced and interpreted; prose short, specific; a reader who reads only the sentences still gets the argument. |
| D6 Credibility and transparency | 5 | Provenance, scope and known weaknesses stated on the artefact, at the size of the claim. |

---

## 3. Score before this round (the state round two left)

| Dimension | Weight | Score | The specific cost |
|---|---|---|---|
| D1 Data handling | 20 | **16** | Two dead functions still shipped (`mode_note`, `threshold_note`); `threshold_note` was flagged dead in round one and was still dead. README repo-map said "49 tests" while the status table said "51 passing" — the repository contradicted itself. |
| D2 Answers the question | 25 | **22** | Four questions answered with numbers on the page, but nothing told the reader what to *do* with them. |
| D3 Chart choice | 20 | **18** | Panel titles still named the variable, not the finding (the B7 gap round two explicitly deferred). The carrier dumbbell was sized for the ~10-carrier fixture, so the real panel's 20 carriers were squeezed to 16 px a row. |
| D4 Structure and narrative | 20 | **18** | The arc ended on the limits ("what this page cannot say"), so the page closed on a downbeat with no "so what". |
| D5 Text | 10 | **9** | Standfirst, findings and captions are strong; only the closing beat was missing. |
| D6 Transparency | 5 | **5** | Provenance, attribution floor, cluster ARI and the AUC ceiling all stated. |
| **Total** | **100** | **88** | A−. |

The shape is now reversed from round two: the writing is nearly full, but the
**structure still did not finish the sentence** — the page ended where a reader
starts looking for the payoff, and two of the eight titles still read as
metadata rather than as findings.

---

## 4. Changes made this round, mapped to the three levels

### 4.1 Code level (B8)

| # | Change | Where | What it fixes |
|---|---|---|---|
| C1 | Delete `mode_note()` — its result was computed in `app.py` and never rendered | `dashboard/data_access.py`, `dashboard/app.py` | Dead code flagged in round one and still present |
| C2 | Delete `threshold_note()` and its import/`__all__` entry | `dashboard/data_access.py`, `dashboard/callbacks.py` | The second dead function; the threshold sentence already lives in the method section |
| C3 | Two new tests pin `takeaways()` (structure + no `nan` + empty-frame behaviour) | `tests/test_captions.py` | The new closing band is now guarded the same way the captions are |

### 4.2 Web design level (B7, B1, B4)

| # | Change | Where | What it fixes |
|---|---|---|---|
| C4 | All eight panel titles rewritten from variable names to findings, e.g. "Carrier comparison" → **"Which carrier you fly changes the delay"**, "Where the minutes come from" → **"The airline controls most of the delay"**. A reader who scans only the eight titles now reads the whole argument. | `dashboard/layouts.py` `_grid()` | The B7 gap round two deferred; a title that states the message instead of the variable |
| C5 | A new closing band, **"What a passenger can keep in mind"**, with three actions — *fly earlier in the day*, *do not plan around the average*, *pick the carrier but know the ceiling* — each computed from the same `data_access` aggregates as the panels, so the advice cannot drift from the charts. | `dashboard/captions.py` `takeaways()`, `dashboard/layouts.py` `_takeaway()` | The page now ends on "so what" (reader benefit) before the limits, instead of on the caveats |
| C6 | Carrier and geo panels raised from 320 px to 560 px; the carrier figure height matched. | `dashboard/layouts.py`, `dashboard/panels/carrier.py`, `dashboard/panels/geo.py` | The full panel's 20 carriers were at 16 px a row (overlapping dots); the US map was squashed. 560 px gives ~25 px a row and a sane map aspect |

### 4.3 Workspace level (B9, B10)

| # | Change | Where | What it fixes |
|---|---|---|---|
| C7 | README repo-map test count corrected 49 → 51, matching the status table; dashboard description updated to name the new finding-title and takeaway features | `README.md` | The repository no longer contradicts itself about its own test count |
| — | Note (not fixed, out of scope for a code edit): the project has a `.gitignore` but no `.git` repository — `git status` walks up to the user's home directory. If the team intends to version-control it, `git init` + a first commit is a one-command fix; if Moodle is the only channel, the README's "excluded from version control" phrasing is the thing to soften. | — | Flagged for the team, not silently rewritten |

---

## 5. Re-score

| Dimension | Weight | Before | After | What moved it |
|---|---|---|---|---|
| D1 Data handling | 20 | 16 | **17** | Dead code gone (C1, C2), new-guard tests added (C3), README consistent (C7). Not 18: the weather/rotation join is still absent and the repo is still not under git. |
| D2 Answers the question | 25 | 22 | **22** | Analysis unchanged; the takeaway (C5) restates the answers as action but adds no new result. |
| D3 Chart choice | 20 | 18 | **19** | Titles now state the finding (C4); the 20-carrier dumbbell is legible (C6). Not 20: annotation is still sparser on the page than in the printed figures. |
| D4 Structure and narrative | 20 | 18 | **20** | The arc is complete — claim → evidence → takeaway → limits (C5), and the page is scannable by title (C4). |
| D5 Text | 10 | 9 | **9** | The closing beat is filled (C5); D5 was already near the ceiling. |
| D6 Transparency | 5 | 5 | **5** | Unchanged; every takeaway sentence points at the limits rather than outrunning them. |
| **Total** | **100** | **88** | **92** | **A− → A**. |

### What is still holding it below ~95, and why that is honest to say

These are properties of the data and the method, not of the editing:

1. **Weather and rotation are not joined.** "Late aircraft" and "weather" are
   measured through BTS's own cause minutes; no station observation or
   tail-number rotation feed is merged. The page discloses this (method card
   "What the page leaves out"), but disclosure is not measurement.
2. **The cluster partition is unstable** (bootstrap ARI 0.69 against a 0.70
   bar), and the page correctly refuses to call it a typology.
3. **The predictive ceiling is low** (risk AUC 0.69 against a 6.1% base rate),
   and the takeaway band says so rather than promising an arrival time.

These three are the difference between a strong explanatory artefact and a
forecasting product — and this project is, deliberately, the former.

---

## 6. Verification (all against the real ten-year panel)

- `pytest -q` → **53 passed** (51 previous + 2 new takeaway tests), 17 s.
- Dashboard launched in `full` mode: header reads **61,689,698 flights · 10
  years · 20 carriers**; all eight finding-titles and the three takeaway cards
  render; takeaway text contains no `nan`.
- Browser console: **0 errors, 0 warnings**.
- 820 px single-column breakpoint: **0 px** horizontal overflow.
- `figures/13_dashboard.png` re-shot at 1440 px, full page.
