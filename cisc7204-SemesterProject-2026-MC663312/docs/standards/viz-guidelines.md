# Visualisation guidelines

This is a visualisation course, so a chart is a decision, not a default. The rules
below are the ones the library actually enforces (`src/team01/viz.py`), written
once so that a reviewer can check a figure against a standard instead of against
taste.

---

## 1. Choose the encoding for the question

Following Cleveland & McGill (1984) and Mackinlay (1986), accuracy of reading runs:

**position > length > angle/slope > area > colour hue**

Therefore:

| Question | Encoding | Figure |
|---|---|---|
| Part of a whole | unit waffle, every cell labelled | 01 cause waffle |
| Cyclical pattern | line over an ordered axis | 08 hour cascade |
| Ranked comparison | sorted bars with direct labels | 03 carrier bars |
| Distribution | percentile band, not a bar of means | 04 percentile band |
| Concentration | Lorenz curve, read by position | 05 lorenz |
| Near-null effect | flat lines with an interval, no trend claim | 06 distance bands |
| Geography | equal-area tile grid first, choropleth second | 07 state tiles |
| Volume | area with a size legend and alpha | dashboard airports |
| Two-dimensional similarity | PCA projection with labels | 10 cluster scatter |

Area and colour hue are used only where position is unavailable, and then they
are anchored: the waffle labels its own cells, the bubble map carries a size
legend.

---

## 2. Never show a mean without the distribution

The whole argument of this project is that the mean misdescribes the typical
flight. A bar of monthly means would illustrate the opposite of the finding.

Acceptable: median with an inter-percentile band, a violin, a box, a histogram.
Not acceptable: a lone bar of averages, a lone line of averages, or a "score"
that hides its spread.

If exactly one number must appear (a KPI tile), the tile shows the median beside
the mean.

---

## 3. Colour

- **One fixed colour per delay cause**, held across every figure and the
  dashboard. A cause keeps its colour the way a country keeps its colour on a map.
- The palette is Okabe–Ito (2008): distinguishable under deuteranopia,
  protanopia and tritanopia, and separable in greyscale print.
- Sequential scales use viridis — monotonic in lightness, so it survives a
  black-and-white printer. Diverging scales are centred on zero and used only for
  signed quantities (delay above/below zero).
- Never use a rainbow scale for a continuous quantity. Never use colour as the
  only channel for a category: pair it with a label, a shape or a direct value.
- Magma and similar dark-low ramps are banned for "low is good" metrics: a low
  value rendered near-black reads as "no data". Use YlOrRd or viridis instead.

---

## 4. Annotation

- A figure must be readable when it is pasted into a report **without** its
  caption. Title states what is shown; axis labels state units.
- Two-line titles: line one is the finding, line two is the measure.
  *"The average is not the typical flight / Arrival delay by month (minutes)"*.
- Direct labels beat a legend whenever there are fewer than about eight series.
- A value that a reader would otherwise estimate (the top-1% share, the k that was
  chosen) is written on the figure.
- **A solution's quality measures belong on the figure that shows the solution.**
  A scatter of coloured groups reads as a discovered typology; the silhouette
  score and the bootstrap ARI are what tell a reader whether that grouping
  survives resampling. They go in title line two - `k = 3 · silhouette = 0.17 ·
  bootstrap ARI = 0.49 · 16 airports` - not in a metrics file the audience will
  never open.
- Units are always present: "minutes", "share of flights", "statute miles".

---

## 5. Honesty

- Bar charts start at zero. Line charts may not, but then the axis is labelled and
  the zero line is drawn.
- No truncated axis, no dual axis without both axes labelled in their own colour,
  no 3-D, no drop shadow, no gradient that encodes nothing.
- A null result is drawn as a null result: Figure 06 shows flat lines because the
  distance effect is near-zero, and says so in the caption.
- The sample that produced a figure is stated (`fixed-seed sample of 600,000
  flights`) whenever it is not the full panel.
- **A figure carries its own provenance.** Every saved figure stamps its source,
  and in fixture mode it also says loudly that it is not a BTS result. A figure
  outlives the script that produced it: by the time it reaches a slide nobody
  remembers which run it came from, and a synthetic panel has the same schema as
  the real one, so nothing about the image gives it away. This is enforced in
  `viz.save`, not left to whoever remembers.

---

## 6. Dashboard rules

1. **Overview first, filter second, detail on demand** (Shneiderman, 1996). The KPI
   strip answers "how bad is it" before any control is touched.
2. **Every control updates every panel.** A filter that changes one chart and not
   its neighbour invites a false comparison.
3. **Recompute, do not pre-render.** Each panel aggregates the filtered frame;
   nothing on screen can diverge from the report.
4. **Name the data.** A banner states which mode is loaded; the sample fixture is
   labelled as a demonstration in the interface itself, not only in the README.
5. **Degrade to a sentence.** A missing stage produces a readable message in the
   panel, not a traceback and not an empty box.
6. **One channel, one meaning.** On a map, fill carries one variable and bubble
   size carries another. A second colour scale on top of the first invites the
   reader to compare two things that are not comparable, and it halves the number
   of distinguishable colours in the first scale.
7. **Anchor the weak channel.** Area and colour intensity are weak channels: they
   need a legend that gives the reader a value to compare against. A bubble map
   without a size legend is a picture of "some airports are bigger".
8. **No mean below a sample floor.** If an hour, a carrier or an airport holds
   fewer than `viz.min_hour_flights` observations, plot the share but drop the
   mean. A mean over 18 flights draws a cliff that is not in the data. One key,
   read by the dashboard *and* by the printed cascade figure — a floor that only
   one of the two applies makes the page and the report disagree.
9. **Text lives inside the plot.** Annotations go in `yref="paper"` coordinates
   inside the axes, not on the margin where a 26px top margin will slice them.
   Legends go below with reserved space (`LEGEND_BELOW` + `LEGEND_MARGIN`), never
   at a hard-coded `y` offset.
10. **Label the hubs, hover the rest.** Past about eight points in a small card,
    codes collide. Label the largest and let hover carry the rest; do not shrink
    the font until nothing is readable.
11. **The page has to cite itself.** Footer: source, the threshold that scopes
    the numbers, the mode, the row count and the generation time. The printed
    figures do this; the page is not exempt.
12. **State is a link.** The filter combination lives in the URL
    (`?year=&carrier=&months=`), so "what I am looking at" can be sent to a
    teammate. A drill-down is a transient view, not a filter: it does not belong
    in the URL and it must be clearable in one click.
13. **Verify the fix took effect.** A stylesheet written against the wrong
    component classes fails silently: the slider stayed purple through a "fix"
    that targeted Dash 2's `rc-slider-*` while Dash 4 renders `dash-slider-*`.
    After any styling change, read the computed style back
    (`getComputedStyle(el).backgroundColor`) instead of trusting the diff.
14. **Re-shoot after every change.** Five widths (1440/1280/1152/1024/390), every
    panel looked at. Half the defects found in the 2026-11-02 rebuild only
    appeared in the second round of screenshots.
15. **Never park a legend on a data point.** The archetype projection has no empty
    corner once sixteen airports are plotted; the key goes under the axes in two
    columns. A legend that hides data to explain data is a net loss.
16. **A caption and a legend may not share a height.** Position both explicitly —
    bottom margin, legend anchor, caption y — in three adjacent lines. The cause
    mix figure printed its legend through its own caption for two pipelines
    because the two numbers were chosen in different functions.
17. **A highlighted maximum is only a statement if the bars differ.** If the spread
    is under about 15%, draw the reference line and say in the caption that the
    order is a description, not a distinction.
18. **Pick the colour scale from the data, not from the metric's name.** Mean delay
    cannot be negative, so a diverging scale pinned at zero spends half its range
    on impossible values and compresses every real difference into one hue. Use a
    diverging scale only when the values actually straddle the midpoint.
19. **Geography: tile grid in print, choropleth on screen.** Equal-area tiles keep
    Vermont visible next to Texas and are the right default for a national
    comparison across states. The dashboard keeps a choropleth because airport
    bubbles need real coordinates; that is a difference of task, and the report has
    to say which figure it is showing and why.
20. **Every selection rule gets drawn.** A silhouette curve that peaks at k = 5
    while the chosen k is 3 contradicts itself unless the rejected peak is
    annotated with its reason ("smallest cluster = 1"). If a rule is worth
    following, it is worth showing.

---

## 7. Audit before submission

For every figure, answer these five questions. If one answer is missing, the
figure is not finished.

1. What question does it answer, in one sentence?
2. Which encoding, and why that one rather than the obvious alternative?
3. What would a reader conclude if the figure were misleading — and is that
   conclusion excluded by the axis, the labels and the caption?
4. Is the number in the text identical to the number in the figure?
5. Can it be regenerated by `python src/scripts/07_figures.py` with no manual
   edits?
