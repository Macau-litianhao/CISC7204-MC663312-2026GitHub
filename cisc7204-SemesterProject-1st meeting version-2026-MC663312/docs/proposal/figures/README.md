# Proposal figures

Three images are embedded in the proposal. They are stored here, inside the
repository, and read through a path relative to `_build_proposal.py`.

| File | In the proposal | Source |
|---|---|---|
| `01_cause_waffle.png` | Fig. 1 | Ten-year panel, copied from `figures/01_cause_waffle.png` (73.3% internal split) |
| `13_dashboard_part1.png` | Fig. 2a | Top half of `figures/13_dashboard.png`, split at the grid gap between the second and third panel rows |
| `13_dashboard_part2.png` | Fig. 2b | Bottom half of `figures/13_dashboard.png`, same split point |

## Why Fig. 2 is split into two views

`figures/13_dashboard.png` is a 1440×3681 full-page capture of the eight-panel
dashboard. At any readable width its 2.56:1 aspect ratio is taller than a page,
so a single embed cannot fit on one page without either shrinking the panels
until they are illegible or cutting a chart in half. An earlier attempt
embedded only the top 55% and cut the third panel row (the cluster scatter and
the Lorenz curve) mid-chart.

The fix splits the capture at the horizontal grid gap between the second and
third panel rows (y = 1746; row 2 ends at 1739, row 3 starts at 1753), which cuts
only background, never panel content.
Fig. 2a shows the header, filters, the headline numbers and the first four panels;
Fig. 2b shows the remaining four panels, the passenger takeaway band and the
method-and-limits section. The full capture remains at
`figures/13_dashboard.png`.

## The capture must be refreshed when the page changes

Both views are screenshots of the running application, not redrawn charts, so any
change to the page invalidates them. The 3 November 11:00 capture still had the
pre-fix KPI card — `400,000 completed` next to a header stating 61,689,698 — and
that image had already been embedded in the submitted PDF. After changing
`dashboard/data_access.py` or `dashboard/layouts.py`, re-capture at 1440 px,
re-measure the row boundaries (`document.querySelectorAll('.grid > *')`), and
split at the new gap before re-running `_build_proposal.py`. `docs/video/deck/img/13_dashboard_hero.png`
is the same capture cropped to 16:9 (0–810 px) for the slide deck, and moves with it.

## Build behaviour

`FIG()` raises `FileNotFoundError` when a file is missing, and the script
asserts at the end that all three required images were actually placed in the
document. A build that loses a figure therefore fails loudly instead of
producing a proposal with a gap.
