# Final report and submission package

The report is drafted in `report.md` — four research questions plus a limitations
section, every number read from `outputs/` after the full-panel run. What remains
is packaging: build the PDF and archive the six individual uploads.

---

## What goes here

| File | What it is | Owner |
|---|---|---|
| `CISC7204-Team01-FinalReport.pdf` | The written report, built from `reports/report.md` | Reporter |
| `report.md` | Editable source, one section per research question | Reporter |
| `figures/` | The figures the report actually uses, copied from `../figures/` | Reporter |
| `uploads/` | Screenshots of the six individual Moodle uploads | Coordinator |

---

## The report has to answer four questions, not describe eight panels

Each section below is one research question from the proposal, the artifact that
answers it, and the sentence the answer has to support. The numbers are left
blank on purpose; they are read from `outputs/` after the final pipeline run so
that the text and the tables cannot disagree.

| Section | Question | Evidence file | The claim it must support |
|---|---|---|---|
| 1 | RQ1 — where do delay minutes come from, and is the mix stable? | `outputs/metrics/attribution.json`, `outputs/tables/cause_totals.csv`, `figures/01`, `figures/02` | An airline-controlled share with a bootstrap interval, and the per-year range that says whether one year can speak for ten |
| 2 | RQ2 — how much delay is inherited within the day? | `outputs/tables/cascade_by_hour.csv`, `cascade_by_airport.csv`, `figures/08` | The inherited share at the worst hour, and the airports where it concentrates |
| 3 | RQ3 — do airports fall into distinct archetypes? | `outputs/metrics/clusters.json`, `outputs/tables/airport_archetypes.csv`, `figures/09`, `figures/10` | The chosen k, the silhouette that supports it, and the stability verdict that limits it |
| 4 | RQ4 — how well can risk be ranked, and can a reader act on it? | `outputs/metrics/models.json`, `outputs/tables/ols_hc1_coefficients.csv`, `figures/11`, `figures/12`, `figures/13` | A held-out AUC with its base rate, the factors that carry it, and the dashboard that exposes it |

---

## Rules that apply to every number in the report

1. **A quoted number has a file.** If it is not in `outputs/`, it does not go in
   the text. The auditor checks this by searching the report for digits and
   resolving each one.
2. **A sample-mode run is labelled.** Anything produced with `TEAM01_MODE=sample`
   is a layout demonstration. The report may describe the figure, never quote the
   value.
3. **Every figure names the question it answers.** A figure that survives only
   because it looks good does not go in; `figures/` has fourteen of them and the
   report will use about nine.
4. **Limitations get a section, not a footnote.** Observational data, reported
   (not measured) cause minutes, clustering that is unstable at ARI < 0.7, and a
   model whose R² is low are four separate limitations and each one changes how
   a result should be read.
