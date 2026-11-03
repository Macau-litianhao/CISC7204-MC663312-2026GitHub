# Forum post — Project Proposal

**Where:** the team's own PROJECT FORUM (not a personal or pair forum)
**Subject line, exactly:** `Our Team Project Proposal`
**Body:** paste the text below in full. The brief requires the proposal text in the
post itself, in addition to the uploaded PDF — a link alone does not satisfy it.

Formatting note: the text below avoids tables because the Moodle editor collapses
pasted tables into unreadable rows. Bullet lists survive a paste.

---

## Our Team Project Proposal

**Course:** CISC7204 Data Science and Data Visualization
**Team:** Class K — Team 01
**Title:** US Domestic Flight Delay Drivers — attribution, within-day cascade, airport archetypes and an interactive communication layer
**Submission date:** 5 November 2026

### 1. Project title and research question

The project analyses delay in U.S. domestic air travel. The region is the United
States and the domain category is commercial air transportation. The data are ten
annual files from the Bureau of Transportation Statistics covering 2015–2024, on
the order of seventy million reported domestic flights, joined to airport-level
weather observations and airport reference metadata.

Flight delay suits a data-science investigation because a single average hides
very different experiences: a traveller wants to know the chance of losing an
afternoon, while an airline or a regulator needs to know where the minutes
originate. We therefore treat composition, typical delay, severe-delay risk,
within-day propagation and factor ranking as separate questions rather than
collapsing them into one headline number.

Four research questions:

- **RQ1** — How are reported delay minutes distributed across the five BTS causes, and how stable is that composition across 2015–2024?
- **RQ2** — How much of the delay observed in a given hour is inherited from earlier legs of the same aircraft, and at which airports does that cascade concentrate?
- **RQ3** — Do U.S. airports fall into distinct delay-risk archetypes once size and cause mix are considered together, and what operational characteristics separate them?
- **RQ4** — Given route, departure hour and month, how well can delay risk be ranked, and can a linked web tool let a non-specialist act on that ranking?

### 2. Project purpose

**Outcomes.** The project connects to three course learning outcomes: selecting
visual encodings that fit different data structures and questions; moving from
exploratory description to an appropriately qualified statistical comparison; and
designing an interactive communication product for a non-specialist audience.

**Skills.** Multi-file ingestion and partitioned storage, schema validation,
exploratory analysis, panel and robust regression, quantile and logistic modelling,
unsupervised clustering, gradient-boosted prediction with model explanation,
dashboard development, reproducibility testing and concise technical writing.

**Knowledge.** The BTS delay-cause taxonomy and the 15-minute reporting threshold;
the difference between mean and tail behaviour; incremental explanatory power; the
limits of observational models; and the conditions under which clustering is
informative rather than an artefact of feature scaling.

### 3. Data context and sources

- **BTS Reporting Carrier On-Time Performance, 2015–2024** — primary flight-level records, 110 fields, 63,079,392 rows (61.7 million completed flights). `transtats.bts.gov`
- **BTS Airline On-Time Performance: Delay Cause** — national cause-share cross-check. `transtats.bts.gov/OT_Delay`
- **NOAA NCEI Integrated Surface Database** — hourly wind, visibility, precipitation and temperature at the busiest airports. `ncei.noaa.gov/isd`
- **OurAirports `airports.csv`** — coordinates, state and airport type for maps and hub stratum. `davidmegginson.github.io/ourairports-data`
- **FAA hub classification** — airport size stratum used in clustering.

**Reporting-threshold note.** BTS publishes the five cause-minute fields only for
flights delayed by at least 15 minutes. The pilot verified the rule directly:
1,449,964 of 1,449,966 flights at or above the threshold carry a complete cause
breakdown, a coverage of 99.9999%. All cause-share statements are scoped to that
attribution universe, while counts, means and percentiles use every completed
flight.

**Governance.** All sources are public. BTS and NOAA are U.S. federal data and are
redistributable; OurAirports is a public-domain dedication. No personal data is
processed and no ethics approval is required. Raw files are excluded from version
control and are re-downloadable from documented URLs.

### 4. Project tasks and deliverables

1. **Acquisition and validation** — ten annual files, weather and airport metadata; schema, duplicate, missingness and threshold checks; partitioned Parquet. *Deliverable: notebook 01, data dictionary, validation report.*
2. **Attribution and exploratory analysis** — partition attributed minutes across the five causes; compare month, carrier, hour, distance, state and airport; test composition stability by year. *Deliverable: notebook 02, figures 01–08, composition and stability tables.*
3. **Tail and concentration** — mean, median, percentile and severe-delay shares; Lorenz curve; retest of the mean-versus-tail hypothesis on the full panel. *Deliverable: notebook 03, figures 09–13.*
4. **Cascade and airport archetypes** — quantify inherited delay from the aircraft rotation; build an airport feature matrix; k-means with silhouette selection; Ward hierarchy and PCA projection. *Deliverable: notebook 04, figures 14–17, cluster profile table.*
5. **Prediction and explanation** — logistic baseline, gradient-boosted classifier and regressor, time-based holdout, permutation importance and dependence plots. *Deliverable: notebook 05, model comparison table, explanation report.*
6. **Communication layer** — linked dashboard with eight panels, three filters and a map; narrative page; deployment smoke test. *Deliverable: dashboard, narrative site, README, final report.*

### 5. Criteria for success

- Every figure regenerated from raw data by a single command, with no manual edits.
- Every quoted number traceable to a file in `outputs/` or a notebook cell.
- Cause statements scoped to the attribution universe; the threshold check repeated for every year.
- Clustering reported with the selection evidence (silhouette, Ward cophenetic correlation, subsample stability), not as a fixed taxonomy.
- Model performance reported honestly, including the pilot ceiling of R² 0.029 and AUC 0.679.
- A dashboard usability check with three scripted tasks and recorded completion time and errors.

### 6. Team and collaboration

Roles map onto six members, and rotate at the midpoint of the project:

- **AO KIT I (MC660004)** — Team Coordinator and Project Tracker: agendas and chairing, task board, milestones, dependency map, risk log, drives submissions.
- **LI YING FANG (MC661599)** — Project Developer (lead): data pipeline, notebook and repository structure, reproducibility script, dashboard engineering, leads code review.
- **HO MAN HOU (MC661647)** — Team Scribe: minutes, decision log, scope-change log, repository folder conventions and naming.
- **WU PEI YE (MC661846)** — Team Reporter and Team Liaison: proposal narrative, introductory video script and edit, instructor liaison, final submission package.
- **LI TIAN HAO (MC663312)** — Project Analyst and Quality Reviewer: research question, data sources, preparation and analysis, interpretation and limitations; the quality gate.
- **SAVIDI AVRAM (MC664364)** — Project Developer: figures, visualisations and interactive outputs (map, archetypes), ten-year scaling, weather join.

Ground rules: one shared repository with a branch per task and review before merge;
one source of truth for numbers; a weekly checkpoint on progress and blockers with
a 48-hour response target; scope frozen by consensus; an independent read-through
by every member before submission.

### 7. Timeline

The schedule starts at the proposal submission date and completes all activity
within four weeks, leaving a two-day buffer before the final close. Project
presentations are held in class on 11, 18 and 25 November, with each team's slot
drawn by lot; the deck and rehearsal finish by 11 November so the team is ready
whichever date it draws. This satisfies the four-week requirement in the brief and
stays inside the five-week allowance stated in the course announcements.

- **3–5 Nov** — proposal, first meeting minutes, introductory video.
- **11 / 18 / 25 Nov** — project presentation to the class (Team 01 slot drawn by lot; deck and rehearsal complete by 11 Nov).
- **6–12 Nov** — environment reproduced by all six members; panel acquired and validated.
- **13–19 Nov** — attribution and tail analysis complete; figure audit closed.
- **20–26 Nov** — clustering and predictive models complete; explanations written.
- **27 Nov–3 Dec** — dashboard and narrative page frozen; usability tasks run.
- **4–5 Dec** — final report and submission package.

### 8. What we already have

The team starts from a completed pilot on the 2024 file: four executed notebooks,
sixteen publication-ready figures, a six-panel linked dashboard and a one-command
rebuild script. The team project extends that pilot with a ten-year panel, a
within-day cascade measurement, weather covariates and airport clustering — three
extensions that use the additional capacity rather than repeating the pilot.

### 9. References

Thirteen sources in APA 7, every one of them cited in the body text and listed in
full in the uploaded PDF: BTS on-time performance data (two datasets), BTS
delay-cause data, NOAA ISD, OurAirports, FAA air-traffic and enplanement figures,
Cairo (2016) *The Truthful Art*, Cleveland and McGill (1984) on graphical
perception, Mackinlay (1986) on the automated design of graphical presentations,
Munzner (2014) *Visualization Analysis and Design*, Shneiderman (1996) on the task
by data type taxonomy, Rousseeuw (1987) on silhouettes, Okabe and Ito (2008) on
colour universal design, and Lundberg and Lee (2017) on model interpretation.

---

*The full proposal, including tables, the figure audit and the complete reference
list, is attached as a PDF (10 pages, within the 15-page limit).*
