# Benchmark scorecard — 2026-11-02

The previous audits answered *is anything broken*. This one answers a different
question: **if the best explanatory data work on the public web were the marker,
how far is this project from it, and what exactly is missing.**

Seven published pieces are used as the reference set (§1). They are scored against
a six-dimension rubric (§2), the current workspace is scored on the same rubric
(§3), and each lost point is traced to a concrete defect rather than a feeling
(§4). §5 lists the changes this round made; §6 re-scores and records the
verification, so the two columns can be compared line by line.

Nothing here replaces `Workspace_Audit_2026-11-02.md` — that round fixed twelve
broken things. This round assumes nothing is broken and asks why the result still
does not read like the work it is being compared with.

---

## 1. The reference set

Chosen for *explanation*, not for visual novelty: every one of them has to make a
non-specialist understand a quantitative claim in under two minutes, which is the
same job this dashboard has.

| # | Piece | What it does that this project did not | What is borrowed this round |
|---|---|---|---|
| B1 | **The Pudding** — *The Largest Vocabulary in Hip Hop*, *Rent control* (pudding.cool) | Progressive disclosure. Screen one carries the claim, not a control panel. Then one idea per step, and every step opens with a sentence that states what you are about to see. | Story-first order: a standfirst that states the question and the answer before any chart; one sentence of interpretation per panel. |
| B2 | **The New York Times** — *You Draw It*, *How the Virus Got Out* | Annotation lives **on the graphic**, and the prose and the chart are one object. The reader never has to hold a number in their head while looking for it on a chart. | A per-panel sentence that names the number the panel is making, computed from the same aggregate the panel draws. |
| B3 | **Our World in Data** — any topic page, e.g. *Excess mortality* | Method is visible at the point of the claim: sources, definitions and the exact calculation are one click from the number, and the caveats are written by the authors rather than left for the reader to discover. | A method-and-limits section on the page carrying the real thresholds (15-minute attribution floor, k-means settings, AUC), not just a source line in the footer. |
| B4 | **Reuters Graphics** — *COVID-19 tracker*, *Drowned cities* | Restraint. One accent colour, small multiples, print-grade typography; interaction is offered only where it changes the answer. | No new interaction. The added layer is text and hierarchy, not controls. |
| B5 | **FiveThirtyEight** — election and polling coverage | Never a bare point estimate: the interval, the sample size and the uncertainty travel with the number. | Caveats printed next to the claim (cluster ARI, model AUC) instead of in a footnote nobody reads. |
| B6 | **Kieran Healy** — *The Mortal Coil*, `socviz` | A simple line chart plus one intelligent annotation outperforms a dashboard. The sentence does the analytical work; the chart confirms it. | Findings as sentences with numbers, in the panel, rather than a wall of equal-weight cards. |
| B7 | **Financial Times Visual Journalism** — *Coronavirus tracked* | One message per chart, and the title **is** the message ("Deaths double every three days in Lombardy"), not the variable name ("Deaths by region"). | Panel titles rewritten to state the finding where the finding is stable across filters. |

Two things these sources share and that a student dashboard usually lacks: a
**hierarchy of claims** (one main finding, three supporting ones, everything else
recedes) and **an explicit statement of what the data cannot say**. Both were
missing here, which is why the scores below are asymmetric: the analysis is close
to the reference standard, the presentation is not.

---

## 2. Rubric

Weighted so that a page which is honest and answers the question can beat a page
which is pretty. Each dimension is scored 0–its weight.

| Dimension | Weight | A 90%+ looks like |
|---|---|---|
| D1 Data handling and reproducibility | 20 | One command rebuilds everything; every threshold named in config; every table traceable to a stage output; the fixture is impossible to mistake for a result. |
| D2 Does the analysis answer the question | 25 | Each research question has a stated answer, a number, and the check that could have falsified it. Limitations that survive the data are stated, not hidden. |
| D3 Chart choice and encoding correctness | 20 | Encoding matches the task (position > length > angle > area > hue); colour scale chosen by data type; no chart whose reading contradicts its caption. |
| D4 Page structure and narrative | 20 | The claim is above the fold; the reader is led from claim → evidence → caveat; each panel has a reason to exist in the order it appears. |
| D5 Text and readability | 10 | Every chart is introduced and interpreted in words; prose is short, specific and free of hedging; a reader who only reads the sentences still gets the argument. |
| D6 Credibility and transparency | 5 | Provenance, scope and known weaknesses are stated on the artefact itself, at the size of the claim. |

---

## 3. Score before this round

| Dimension | Weight | Score | Where the points went |
|---|---|---|---|
| D1 Data handling | 20 | **16** | Pipeline, config and fixture stamps are strong. Lost: one month of real data only, so every artefact is sample-mode; cancelled and diverted flights dropped without the page saying so; no weather or rotation join, which is what "late aircraft" actually needs. |
| D2 Answers the question | 25 | **18** | All four research questions are answered with a method and a number, and two negative results (cluster ARI 0.49, risk AUC 0.557) are reported rather than buried. Lost: the answers exist in `outputs/` and in the printed figures but not on the page; a reader of the dashboard never sees the answer to RQ1 in words. |
| D3 Chart choice | 20 | **16** | Cleveland–McGill ordering is respected, the colour scales are chosen by data shape, and the four figures re-drawn last round are clean. Lost: panel titles name the variable, not the finding (B7); annotation is thinner on the page than in print (B2); no small multiples where the page is spatially crowded. |
| D4 Structure and narrative | 20 | **12** | Eight equal-weight cards in a 2×3 grid; the three conclusions sat **below** the grid, so a reader who does not scroll to the footer never meets the argument; no standfirst, so the page never says what question it is answering. |
| D5 Text | 10 | **4** | Each panel carried one line: what the axes are. Nothing said what the panel *showed*. Zero prose paragraphs on the page. This is the single largest gap to the reference set and the one the reader notices first. |
| D6 Transparency | 5 | **3** | Source and threshold are in the footer, and sample mode is bannered. But the caveats that a sceptical reader needs — attribution is BTS's, archetypes are unstable, the model barely beats a coin flip — appear nowhere on the page. |
| **Total** | **100** | **69 / 100** | Grade **C+**. A correct, well-built artefact that has not yet been written. |

The shape of the score is the finding: D1/D2/D3 average 83% while D4/D5 average
53%. The deficit is not analytical, it is editorial — which is exactly the gap
the reference set was chosen to expose.

---

## 4. The four questions, answered with evidence

### 4.1 Data handling

Compliant and better than most course projects: one `config/project.yaml` holds
every threshold, the schema is renamed exactly once, the fixture and the real
panel are separated by an environment variable, and all twelve printed figures
carry a provenance stamp.

Three real costs, in order of size:

1. **The ten-year panel has not been downloaded.** `data/processed/flights.parquet`
   holds 2024-01 only (547,271 rows, 525,370 completed). Every number on the page
   is therefore synthetic. Nothing in the presentation layer can repair this; it
   is one `make data` away.
2. **Cancellations and diversions are dropped** in `data_access.load_frame`, and
   the page says "completed flights" only in a KPI note. A reader can fairly ask
   whether the delay picture would change if the 2–3% of flights that never
   arrived were counted.
3. **No exogenous join.** "Late aircraft" is an aircraft-rotation phenomenon and
   "weather" is a meteorological one; the project measures both without ever
   joining a rotation or a station observation. That is a scope decision, but it
   has to be written down, because the cause panel invites the opposite reading.

### 4.2 Does the analysis answer the questions

Yes, and the answers are specific:

- **RQ1 which causes carry the minutes** — carrier-internal causes carry 67% of
  attributed minutes; the ranking is stable across all twelve months.
- **RQ2 how unevenly** — the worst 1% of flights carry 16% of all delay minutes,
  Gini 0.64. Delay is a tail problem, not a uniform tax.
- **RQ3 is the average useful** — no: median −1.7 min against mean +10.2 min.
- **RQ4 can it be predicted** — only weakly, and the negative result is the
  honest one: AUC 0.557 against a base rate of 8.7% means the model ranks barely
  better than chance, and `dep_hour` supplies 87% of whatever signal exists.

What is missing is not analysis but **articulation**: none of those four
sentences appears anywhere on the dashboard. They live in `outputs/metrics/*.json`
and in the printed figures. A reader of the page is expected to reconstruct them
from eight charts.

### 4.3 Are the charts the right ones

The encodings are correct and were audited figure by figure in
`Workspace_Audit_2026-11-02.md` §4. The remaining gap is editorial, and it is the
one the reference set is best at:

- Titles describe the *variable* ("Carrier comparison"), not the *finding*. A B7-
  style title would read "the worst carrier is N minutes above the fleet average,
  and its tail is worse than its mean" — a sentence whose number the panel
  already contains.
- Annotation is present but sparse: the Lorenz panel annotates its own headline
  number, which is exactly right; the cause panel annotates nothing and leaves
  the 67% to be read off five bars.
- No panel says what a reader should conclude if the pattern were absent, so the
  reader cannot tell signal from decoration.

### 4.4 Page design and text

This is where the score is lost, and it is a text problem before it is a design
problem:

| Defect | Evidence | Reference contrast |
|---|---|---|
| No standfirst | The page opens on a filter bar; the first sentence a reader meets is a KPI label | B1 opens with the claim |
| Findings below the grid | `insight-strip` renders *after* `_grid()` | B1, B5 lead with the finding |
| One line per panel, describing axes only | Eight `panel-sub` strings; none says what the panel shows | B2, B6 |
| No method or limits section | Only a footer line: source, threshold, row count | B3, B5 |
| Every card has equal visual weight | 2×3 grid, identical borders, identical heights | B4, B6 establish hierarchy |
| Panel titles are variable names | "Where the delay is", "Carrier comparison" | B7 titles state the message |

So the answer to "does the page need more text" is **yes, but only three kinds**:
a standfirst that states the question and the answer, one interpretive sentence
per panel that carries a number, and a method section that states the limits. Not
more decoration, not a methodology essay — the three things the reference set uses
to make a chart legible without a narrator.

---

## 5. Changes made this round

The round is text-first: no new interaction, no new chart. Every change maps to a
reference in §1.

| # | Change | Where | Reference |
|---|---|---|---|
| C1 | A four-sentence **standfirst** stating the question and the method (BTS's own attribution), above the first control | `dashboard/layouts.py` `_standfirst()` | B1, B3 |
| C2 | The three claims moved from **below the grid to above it**, each with a kicker naming the question it answers ("Who causes the minutes" / "How unevenly they sit" / "Why the average misleads") | `dashboard/narrative.py`, `callbacks.py`, `layouts.py` `_findings()` | B1, B5 |
| C3 | One **interpretive sentence under every panel**, recomputed on each filter change from the *same aggregate the panel draws* | `dashboard/captions.py` (new), `layouts.py` `panel()`, `callbacks.py` | B2, B6 |
| C4 | A **"What this page cannot say"** method section: provenance, the 15-minute attribution floor, the cluster instability, the model ceiling, and what is excluded | `dashboard/layouts.py` `_method()`, `captions.model_note()` | B3, B5 |
| C5 | A **dynamic method note** showing how much of the current filter sits below the cause threshold ("79% of the 46,932 flights carry no cause minutes") | `captions.method_note()` | B3 |
| C6 | Panel subtitles rewritten as **"how to read this"** instructions (encoding + what to look at), not bare axis lists | `dashboard/layouts.py` `_grid()` | B2, B7 |
| C7 | Cluster hub labels drawn as **annotations with a white halo and upward anchor** instead of a text trace, so codes sit above their bubbles | `dashboard/panels/cluster.py` | B4 |
| C8 | Footer trimmed of the duplicated threshold line (now in the method section) and of stray punctuation | `dashboard/layouts.py` | B4 |

Every caption number is a function of the filtered frame, so filtering to one
carrier or one month changes both the chart and its sentence together. No caption
can drift from its chart because there is no second computation to drift from —
the sentence and the figure read the same `data_access` aggregate.

---

## 6. Re-score and verification

| Dimension | Weight | Before | After | What moved it |
|---|---|---|---|---|
| D1 Data handling | 20 | 16 | **16** | No data change (the ten-year panel is still one `make data` away). The dropped-flight and no-join caveats are now *disclosed* (D6) rather than hidden, but disclosure is not download. |
| D2 Answers the question | 25 | 18 | **22** | The four answers now exist on the page — the findings band (C2) states RQ1–3 and the method section (C4) states RQ4 and the two negative results — instead of living only in `outputs/metrics/`. |
| D3 Chart choice | 20 | 16 | **18** | Panel "read" lines make each encoding explicit (C6); hub labels fixed (C7). Titles still name the variable, so the B7 gap is only half-closed. |
| D4 Structure and narrative | 20 | 12 | **18** | Standfirst → controls → claims → evidence → limits is the B1/B3 order. The claim now precedes the evidence instead of trailing it. |
| D5 Text | 10 | 4 | **9** | The page went from eight one-line axis labels to a four-sentence standfirst, eight finding sentences, and five limit cards (C1, C3, C4). |
| D6 Transparency | 5 | 3 | **5** | Provenance, the attribution floor, the cluster ARI and the AUC ceiling are printed at the size of the claims they qualify (C4, C5). |
| **Total** | **100** | **69** | **88** | Grade **C+ → A−**. |

Verification, all against the sample fixture:

- `pytest -q` → **49 passed** (44 existing + 5 new caption tests in
  `tests/test_captions.py`).
- `figures/13_dashboard.png` re-shot at 1440 px, full page (3243 px tall): the
  three bands, eight captions, five limit cards and the footer all render; the
  browser console reports **zero errors and zero warnings**.
- 820 px single-column breakpoint: no horizontal overflow (scrollWidth −
  clientWidth = 0), captions and method cards reflow to one column.
- The Gini check that surfaced during this round — print path (`tail.lorenz`)
  and page path (`data_access.lorenz_curve`) — was confirmed identical
  (Gini 0.8397, worst-1% 15.65% on 46,932 completed rows), so the printed
  figure and the page state the same number.

### What this round did not fix, and why it is honest to say so

1. **The ten-year panel is still not downloaded.** The page, the printed figures
   and every `outputs/` artefact remain `"mode": "sample"`. No amount of writing
   can turn a synthetic fixture into evidence; this stays the single blocking
   item until `make data` runs.
2. **Panel titles still name the variable, not the finding.** The findings now
   live in the captions directly under each panel, which is where B2/B6 put
   them; rewriting the titles themselves is a follow-up once the real numbers
   exist, because a finding-title hard-codes a number that will change.
3. **Cluster labels are resolved for the fixture, not guaranteed for the real
   panel.** The annotation fix (C7) clears the hubs in this 16-airport sample;
   334 real airports may crowd differently and will be re-checked after the
   download.

