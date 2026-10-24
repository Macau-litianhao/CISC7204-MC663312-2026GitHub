# %% [markdown]
# # 01 · Data Preparation — Building the 2024 Flight Table
#
# **CISC7204 Assignment 02 · Pair Project · Class K Pair 14**
# LI Tianhao (mc663312) · LI Yingfang (mc661599)
#
# ## What this notebook does
#
# 1. Shows where the data comes from and what one raw file looks like.
# 2. Documents every cleaning and type decision we made.
# 3. Verifies the delay-attribution identity that the whole project rests on.
# 4. Produces `data/processed/flights_2024.parquet` and the pre-aggregated
#    tables that the EDA notebooks and the Dash dashboard read.
#
# ## Why the data source changed from Module 04
#
# Module 04 Lab 01 used IBM's `airline_data.csv`: **27,000 rows randomly drawn
# from 1993-2017**, i.e. roughly 1,000 rows per year. That sample is fine for
# practising Plotly calls, but it cannot support any statement of the form
# "X% of delay minutes in 2024 were caused by Y", because:
#
# * the per-year slice is too small to estimate a tail probability;
# * the draw is not stratified by carrier or route, so composition is not
#   representative.
#
# We therefore use the **complete** BTS Reporting Carrier On-Time Performance
# file set for calendar year 2024 — 12 monthly files, ~7 million flights.

# %% [markdown]
# ## 1 · Environment and paths
#
# All shared constants live in `src/common.py` so that the notebooks and the
# dashboard cannot drift apart (same colour codes, same cause order).

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make src/ importable no matter which directory the kernel starts in.
SRC = Path.cwd().parent / "src" if Path.cwd().name == "notebooks" else Path.cwd() / "src"
sys.path.insert(0, str(SRC.resolve()))

import common
from common import (
    CAUSE_COLS, CAUSE_COLORS, CAUSE_LABELS, FAMILY_COLORS,
    FLIGHTS_PARQUET, PROCESSED_DIR, RAW_DIR, load_flights,
)

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 40)
print("pandas", pd.__version__, "| numpy", np.__version__)
print("project root:", common.BASE_DIR)

# %% [markdown]
# ## 2 · Source files
#
# | Item | Value |
# |---|---|
# | Publisher | U.S. Bureau of Transportation Statistics (BTS) |
# | Product | Reporting Carrier On-Time Performance (1987–present) |
# | Access | `https://transtats.bts.gov/PREZIP/` — one zip per month |
# | Period used | 2024-01 to 2024-12 |
# | Coverage | Domestic US scheduled passenger flights of reporting carriers |
# | Licence | U.S. federal government open data (public domain) |
#
# Each zip holds exactly one CSV with 110 fields. `src/01_ingest.py` downloads
# them and keeps 35.

# %%
zips = sorted(RAW_DIR.glob("On_Time_2024_*.zip"))
print(f"{len(zips)} monthly zips found")
for z in zips:
    print(f"  {z.name:24s} {z.stat().st_size / 1e6:6.1f} MB")

# %% [markdown]
# ### 2.1 What one raw file looks like
#
# We open January only, for schema inspection. Reading 3 rows keeps this
# notebook fast — the full build happens in `src/01_ingest.py`.

# %%
import zipfile

with zipfile.ZipFile(zips[0]) as zf:
    member = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    print("member inside zip:", member)
    raw_head = pd.read_csv(zf.open(member), nrows=3, low_memory=False)

print(f"raw file: {raw_head.shape[1]} columns")
print(raw_head.iloc[0, :12].to_string())

# %% [markdown]
# 110 fields is far more than we need. The dropped ones fall into two groups:
# diversion detail (`Div1..Div5*`, 46 columns) and identifiers we never plot
# (`Tail_Number`, `DOT_ID_*`, `*SeqID`, ...).
#
# Column count we keep:

# %%
print(f"{len(common.USECOLS)} of {raw_head.shape[1]} fields retained "
      f"({len(common.USECOLS) / raw_head.shape[1]:.0%})")

# %% [markdown]
# ## 3 · Load the cleaned table
#
# `src/01_ingest.py` has already:
#
# * downloaded the 12 zips and read the CSV inside each one;
# * kept 35 fields and cast them (float32 for measures, `category` for
#   identifiers) — this roughly halves memory versus the pandas defaults;
# * derived `dep_hour`, `cause_total`, `internal_min`, `system_min`,
#   `is_tail60`, `dist_band` and friends.

# %%
df = load_flights()
print(f"shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"memory: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
print(f"date range: {df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}")

# %%
df.head(3).T.iloc[:40]

# %% [markdown]
# ### 3.1 Field types after casting
#
# Note the deliberate split: **measures are float32** (delay minutes never
# need double precision) and **identifiers are categorical** (10 carriers, a
# few hundred airports, 50 states — storing them as strings 7 million times
# would cost gigabytes for nothing).

# %%
pd.DataFrame({
    "dtype": df.dtypes.astype(str),
    "non_null": df.notna().sum(),
    "null_pct": (df.isna().mean() * 100).round(2),
}).sort_values("null_pct", ascending=False).head(22)

# %% [markdown]
# ## 4 · Cleaning decisions (and why)
#
# Four decisions matter enough to state explicitly, because each one changes
# the denominator of every later percentage.
#
# **D1 — Cancelled and diverted flights stay in the table but are excluded
# from delay statistics.** A cancelled flight has no arrival delay; including
# it as 0 would understate delay. We keep a `completed` flag instead, so
# cancellation rate can be reported separately (it is a finding in itself:
# cancellation spikes are the visible face of the same storms that produce
# the delay tail).
#
# **D2 — Delays are not trimmed or winsorised.** Extreme delays (the ≥180
# minute tail) are the phenomenon we are trying to explain. Removing them
# would delete the signal.
#
# **D3 — Negative arrival delays are kept.** An early flight is real
# information; a mean arrival delay of −3 minutes is meaningful.

# %%
n_total = len(df)
n_completed = int(df["completed"].sum())
n_cancelled = int((df["Cancelled"] == 1).sum())
n_diverted = int((df["Diverted"] == 1).sum())
n_negative = int((df["ArrDelay"] < 0).sum())

summary = pd.DataFrame({
    "count": [n_total, n_completed, n_cancelled, n_diverted, n_negative],
    "share_%": [100, n_completed / n_total * 100, n_cancelled / n_total * 100,
                n_diverted / n_total * 100, n_negative / n_total * 100],
}, index=["all records", "completed flights", "cancelled",
          "diverted", "arrived early"])
summary.round(2)

# %% [markdown]
# **D4 — Duplicates.** The monthly files are official publications, so we
# expect none. We check rather than assume:

# %%
dup = int(df.duplicated(subset=["FlightDate", "Reporting_Airline", "Origin",
                               "Dest", "CRSDepTime"]).sum())
print(f"duplicate (date, carrier, origin, dest, sched departure) rows: {dup:,}")
print(f"-> {dup / n_total:.4%} of the table")

# %% [markdown]
# ## 5 · The two facts the attribution analysis depends on
#
# BTS attributes the minutes of arrival delay to exactly five causes.
#
# | Field | Meaning |
# |---|---|
# | `CarrierDelay` | airline-internal: crew, maintenance, fuelling, boarding |
# | `LateAircraftDelay` | airline-internal: the inbound aircraft arrived late |
# | `NASDelay` | system: air traffic control, non-extreme weather, runway |
# | `WeatherDelay` | system: extreme weather that closed the airport |
# | `SecurityDelay` | system: security or evacuation |
#
# `CarrierDelay + LateAircraftDelay` = **Internal** (the airline controls it).
# `NASDelay + WeatherDelay + SecurityDelay` = **System** (imposed from
# outside). That split is the analytical backbone of notebook 02.
#
# ### Fact 1 — the causes are only published for delays of 15 minutes or more
#
# This is a rule of the publication, not missing data, and it defines the
# universe of every attribution figure in this project. We measure it rather
# than assume it:

# %%
done = df[df["completed"] == 1]
coverage = []
for thr in [0, 1, 5, 10, 15, 20, 30, 60, 120]:
    subset = done[done["ArrDelayMinutes"] >= thr]
    coverage.append({
        "delay threshold (min)": thr,
        "flights": len(subset),
        "with cause recorded (%)": subset["CarrierDelay"].notna().mean() * 100,
    })
pd.DataFrame(coverage).round(2)

# %% [markdown]
# Coverage jumps from about two-thirds to exactly 100% at 15 minutes. So:
#
# > **The attribution universe is the 1.45 million flights delayed 15 minutes
# > or more.** Every "share of delay minutes" statement in this project refers
# > to the delay minutes of those flights — they account for the large
# > majority of all delay minutes, but not literally all of them.
#
# Being explicit about this matters: a reader who thinks the shares cover all
# delay minutes would be misled by a few percentage points.

# %%
att = done[done["ArrDelayMinutes"] >= 15]
print(f"attribution universe      : {len(att):,} flights "
      f"({len(att) / done['is_delayed'].sum():.1%} of delayed flights)")
print(f"their delay minutes       : {att['ArrDelayMinutes'].sum() / 1e6:.1f} M")
print(f"share of all delay minutes: "
      f"{att['ArrDelayMinutes'].sum() / done['ArrDelayMinutes'].sum():.1%}")

# %% [markdown]
# ### Fact 2 — inside that universe, the five columns add up exactly
#
# If the five columns did not sum to the recorded arrival delay, no
# decomposition would be legitimate. We test it:

# %%
gap = (att["cause_total"] - att["ArrDelayMinutes"]).abs()
print(f"|sum(causes) - ArrDelayMinutes|: median {gap.median():.4f} min, "
      f"p99 {gap.quantile(0.99):.2f} min, max {gap.max():.0f} min")
print(f"exact match rate (within 1 min): {(gap < 1).mean():.4%}")

# %% [markdown]
# The median absolute discrepancy is zero. The decomposition is exact, which
# is why notebook 02 can report cause shares as arithmetic rather than as
# model output.

# %%
cause_totals = (att[CAUSE_COLS].sum()
                .rename(lambda c: CAUSE_LABELS[c])
                .to_frame("minutes"))
cause_totals["share_%"] = (cause_totals["minutes"]
                           / cause_totals["minutes"].sum() * 100)
cause_totals["family"] = [common.CAUSE_FAMILY[c] for c in CAUSE_COLS]
cause_totals.round(1)

# %% [markdown]
# ## 6 · Pre-aggregated tables
#
# The 7-million-row table is too heavy to re-group every time a chart is
# redrawn, and the dashboard must start in under a second. So we pre-compute
# the groupings once and store them in `data/processed/aggregates.pkl`.

# %%
agg = pd.read_pickle(PROCESSED_DIR / "aggregates.pkl")
for name, table in agg.items():
    if isinstance(table, pd.DataFrame):
        print(f"  {name:16s} {table.shape}")
    else:
        print(f"  {name:16s} Series, {len(table)} values")

# %%
headline = agg["headline"]
print("=== 2024 headline figures ===")
for key in ["flights_total", "flights_completed", "cancelled", "carriers",
            "airports", "routes", "mean_arr_delay", "median_arr_delay",
            "p90_arr_delay", "pct_tail60", "pct_tail180",
            "attributed_min_total", "internal_share", "system_share"]:
    value = headline[key]
    if "pct" in key or "share" in key:
        print(f"  {key:22s} {value:10.2f} %")
    elif isinstance(value, (int, np.integer)):
        print(f"  {key:22s} {value:10,}")
    else:
        print(f"  {key:22s} {value:10.2f}")

# %% [markdown]
# ## 7 · Coverage check
#
# A quick monthly count before trusting anything downstream: if one month had
# silently failed to download, every seasonal statement would be wrong.

# %%
coverage = (df.groupby("Month", observed=True)
            .agg(flights=("date", "size"),
                 days=("date", "nunique"),
                 cancelled=("Cancelled", "sum")))
coverage["flights_per_day"] = (coverage["flights"] / coverage["days"]).round(0)
coverage

# %% [markdown]
# ## 8 · Output
#
# Three artefacts leave this notebook:
#
# | File | Used by |
# |---|---|
# | `data/processed/flights_2024.parquet` | notebooks 02–04 |
# | `data/processed/aggregates.pkl` | notebooks 02–03, Dash dashboard |
# | `outputs/ingest_summary.csv` | README / reproducibility log |

# %%
print(FLIGHTS_PARQUET)
print(f"  exists: {FLIGHTS_PARQUET.exists()}  "
      f"size: {FLIGHTS_PARQUET.stat().st_size / 1e6:.0f} MB")

# %% [markdown]
# 【中文导读】
#
# 这一格之后的三个 notebook 都直接用 `flights_2024.parquet`，所以本 notebook 只有第一次需要跑 `src/01_ingest.py`（要下 12 个 zip，约 300 MB）。
#
# 三个最该记住的点：
#
# 1. **换数据不是"升级"，是"补上可行性"**。Module 04 那份 IBM 抽样每年只有约一千条，任何"占比""尾部概率"在这种样本上都估不准。这是你们从 A01/A02 的 lab 数据走向真实研究的必经一步。
# 2. **五类延误分钟数可加总**，这是我们能做"归因"而不是只做"描述"的根本原因。99% 以上的精确匹配率就是证据。
# 3. **Internal / System 两分法**是后面所有图的主线。整份分析只回答一个问题：这两类各占多少，以及它们在不同承运人、月份、机场上怎么变。
