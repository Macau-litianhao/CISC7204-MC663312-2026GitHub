# Introductory video — shooting script (5:00)

Course: **CISC7204 Data Science and Data Visualization** (Class K)
Team: **Class K — Team 01**
Deliverable: one `mp4`, five minutes, based on the proposal and Minutes 01.
The deck that stages this video is **`deck/index.html`** (16 slides, 16:9, consulting-navy);
`deck/deck.pptx` / `deck/deck.pdf` are the editable / shareable exports.

Four elements are **mandatory** and are laid out on slides 1, 2 and 16 so they are
on screen no matter which narration route is used: the **group photo**, every
member's **student ID and full name**, the **project title**, and the **course
code with the academic year and semester**.

The deck has **16 slides**. The narration below totals about 550 words, which at
roughly 130 words per minute lands at five minutes with the slide pauses included.

---

## Compliance slide (must appear, first 20 s and again at the end)

```text
CISC7204  Data Science and Data Visualization
Semester Project — Class K, Team 01
2026/2027  Semester 1

AO KIT I          MC660004
LI YING FANG      MC661599
HO MAN HOU        MC661647
WU PEI YE         MC661846
LI TIAN HAO       MC663312
SAVIDI AVRAM      MC664364
```

---

## Storyboard

| # | Slide | On screen | Voice-over (summary) |
|---|---|---|---|
| 1 | Cover | Title, course, team, semester | Introduce the project. |
| 2 | Team | Group photo (numbered badges) + six names &amp; IDs | Introduce class, team and members in general. |
| 3 | Abstract | One-line conclusion + three pillars | State the conclusion up front. |
| 4 | Problem | Median −6 min vs mean +7 min | The average hides the tail. |
| 5 | Four questions | RQ1–RQ4 | State the four questions. |
| 6 | Data | Five sources, 63M rows | Name the five public datasets. |
| 7 | Method | Six-stage pipeline, 53 tests | One command regenerates everything. |
| 8 | Finding 1 | Cause waffle | 73.3% airline-controlled, stable. |
| 9 | Finding 2 | Lorenz curve | Gini 0.876, heavy tail. |
| 10 | Finding 3 | Cascade | Late aircraft 38.8%, inherited delay. |
| 11 | Findings 4+5 | Archetypes + risk | Five profiles (unstable); risk ranked. |
| 12 | Dashboard | Live filters | Change a filter, every panel recomputes. |
| 13 | Teamwork | Eight roles, governance | Roles, consensus, independent review. |
| 14 | Schedule | Timeline | Backward-built schedule to 5 Nov and beyond. |
| 15 | Success & honesty | Quality gates + limits | What "good" means; what it cannot say. |
| 16 | Close | Title + compliance | Brief thanks and close. |

---

## Voice-over script (read this, slide by slide)

**Slide 1 — Cover.** "Hi everyone, welcome to our project. We looked at why
flights get delayed in the United States — where the delays come from, how they
build up through the day, and what a traveller can actually do about it."

**Slide 2 — The team.** "We are Class K, Team 01. The slide shows our six team
members, and together we cover the different roles this project needs. We'll take
you through what we found."

**Slide 3 — Abstract.** "Let me start with our main conclusion, because it shapes
everything that follows. After studying ten years of flights, we found delay is
predictable in its structure, even though individual flights aren't. About three
quarters comes from the airline itself, and a few flights carry most of the pain.
I'll walk you through the problem, the data, and the five findings behind it."

**Slide 4 — Problem.** "Here's the problem that got us interested. Every year the
United States publishes one average delay, and that single number hides two
different stories. The typical flight lands about six minutes early, while the
average says seven minutes late, because a handful of really bad flights drag it
up. So the question is: which story should we believe?"

**Slide 5 — Four questions.** "That led us to four questions. Where do delay
minutes actually come from, and is that split stable over ten years? How much
delay passes from one flight to the next? Do airports group into their own delay
patterns? And can we turn all this into a tool a traveller can act on? These four
questions map directly onto the rest of the talk."

**Slide 6 — Data.** "To answer these, we brought together five public datasets:
flight-level records, the delay-cause cross-check, hourly weather from NOAA,
airport details, and airline codes. Everything is public, so anyone can check our
work. In total, that's over sixty-three million rows, and that scale is what
makes our results believable."

**Slide 7 — Method.** "Our whole analysis runs as one pipeline with six stages:
acquire, attribute, analyse the heavy tail, trace the cascade, model, and
communicate. Each stage is a script, so one command regenerates every figure, and
fifty-three tests pin every number back to its source. We built it this way so
nothing is a black box, and anyone can reproduce our results."

**Slide 8 — Finding 1.** "Our first finding answers where delay comes from. 73.3
percent traces back to the airline itself, and only 26.7 percent to the system
around it. What surprised us is how stable this is: it barely moved across the
whole decade, which tells us where airlines can actually make a difference."

**Slide 9 — Finding 2.** "Our second finding is about concentration. The Gini
index is 0.876, meaning a tiny share of flights creates most of the delay. In
plain terms, a few bad flights cause most of the misery. So we report percentiles
and the heavy tail, and we re-run every headline with the pandemic years removed."

**Slide 10 — Finding 3.** "Our third finding is about how delay spreads through
the day. Late aircraft is the biggest single cause, at 38.8 percent. About six
percent of flights start already behind, and some of that delay is inherited from
an earlier leg. So one delayed flight can quietly push the next one late too."

**Slide 11 — Findings 4 and 5.** "Findings four and five are where we're careful.
Airports do sort into five delay profiles, but that grouping isn't very stable, so
we report it with caution. And our model can rank risky flights, but it can't
promise an exact arrival time. Being honest about what we can't claim is part of
the result."

**Slide 12 — Dashboard.** "All of this comes together in one interactive
dashboard. Change the year, the airline, or the month, and every panel recomputes
live. We also ran a usability check, with three timed tasks, using someone who
isn't a data specialist. So the insight isn't locked in a report; it's something
you can actually play with."

**Slide 13 — Teamwork.** "On how we work together: we split the eight course roles
among the six of us and rotate them halfway through. We decide things as a group,
and every piece of work gets checked by someone else."

**Slide 14 — Schedule.** "For our timeline, we planned backwards from the
deadline. We've already finished the proposal and this video, we'll present in
class later this month, and we'll wrap up the project by early December."

**Slide 15 — Success and honesty.** "Finally, we set clear quality checks for
ourselves, and we're upfront about what the model can and can't do — it's good at
ranking risk, but it won't promise exact arrival times."

**Slide 16 — Close.** "Thank you for watching. That's our project."

---

## Production notes

- **Format** — 1920×1080, H.264, 25 fps, one `mp4`. Screen recordings at 1080p so
  text stays readable after compression.
- **Audio** — one narrator for continuity; record in a quiet room with a headset
  mic, normalise to about −16 LUFS. No background music, or music at −30 dB.
- **Pace** — about 130 words per minute. The script above is ≈640 words, which
  lands at five minutes with the slide pauses included.
- **Text safety** — never rely on a spoken student ID alone: the compliance block
  stays on screen for at least 6 seconds, twice (slides 1 and 16).
- **Captions** — burn in subtitles for the four research questions and the closing
  limitation; a viewer watching muted must still get the argument.
- **Slides** — the 16 frames are pre-exported at 1280×720 in `deck/png/`; use them
  directly as the video's visual track, or export 1920×1080 from PowerPoint.

---

## Pre-upload checklist

| Check | Detail |
|---|---|
| ☐ Duration | Between 4:45 and 5:00 |
| ☐ File | Single `mp4`, plays in a browser without extra codecs |
| ☐ Group photo | Present, with every member visible |
| ☐ Names and IDs | All six, spelled as on the class register |
| ☐ Project title | On the opening and closing cards |
| ☐ Course code and name | `CISC7204 Data Science and Data Visualization` |
| ☐ Academic year and semester | `2026/2027 Semester 1` |
| ☐ Presentation file | `deck/deck.pptx` or `deck/index.html` submitted alongside |
| ☐ Upload | Posted in the team forum **and** uploaded as the video assignment, by every member |
