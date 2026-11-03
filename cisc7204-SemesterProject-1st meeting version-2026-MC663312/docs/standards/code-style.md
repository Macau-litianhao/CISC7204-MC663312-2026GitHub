# Code style

The rule that matters more than any formatting preference: **a reader should be
able to answer "why is this line here?" without running the code.** Where the
answer is not obvious from the code, it is written as a comment that explains the
reason, not the mechanics.

---

## 1. Module layout

Every module in `src/team01/` follows the same order:

1. Module docstring — what it does, why it exists, and the decision a reader
   might otherwise second-guess.
2. `from __future__ import annotations`.
3. Standard library, third party, then local imports (`from . import config`).
4. Constants in `UPPER_SNAKE_CASE`.
5. Public functions, most important first.
6. Private helpers prefixed `_`.

`schema.py` and `config.py` are the only modules with no dependencies inside the
package; that keeps import order trivial and the test suite fast.

---

## 2. Types and signatures

- Type hints on every public function, including the return type.
- `df: pd.DataFrame` is not enough when the contract matters: say which columns
  in the docstring (`Input frame must already be through apply_schema`).
- Optional arguments default to `None` and are resolved inside the function, so
  the default comes from `config/project.yaml` rather than from a literal in the
  signature.
- A function that mutates its input says so, or does not mutate. The pipeline
  prefers returning a new frame.

```python
def percentile_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Arrival-delay percentiles with the mean and its own percentile rank."""
```

---

## 3. Comments

Three rules:

1. **Explain the decision, not the syntax.** `# sort by date` is noise. `# sort by
   date so the shift() below reads the previous leg of the same aircraft` is the
   reason the line exists.
2. **Reference the data quirk.** BTS-specific traps (2400 as midnight, cause
   minutes only above 15 minutes, tail numbers reused across days) are documented
   at the point where the code handles them.
3. **Say what was rejected.** "Sequential R-squared rather than Shapley because
   the order is defensible and the numbers add up" is worth more than a formula
   restated in prose.

Comments are in English, because the deliverable is submitted in English. For
personal study a Chinese gloss may be added on its own line, prefixed with
`# 【中】`, and deleted before submission:

```python
# BTS encodes midnight as 2400, so the hour must be taken modulo 24.
# 【中】BTS 用 2400 表示午夜，所以小时数要取 24 的模。
```

Chinese never goes inside a string literal: outputs stay ASCII so that a figure
or a log line cannot break in a different locale.

---

## 4. Data handling

- **Do not mutate a shared frame.** Either `.copy()` or work on a new object.
  pandas 3 copy-on-write makes this cheap.
- **Cast deliberately.** Identifiers are `category`, minutes are `float32`,
  calendar fields are `int8`/`int16`. A `float64` column of minutes in a
  seventy-million-row table is 500 MB of avoidable memory.
- **Never silently drop rows.** A filter either returns a frame and logs the count,
  or raises. `dropna()` without a reason is banned.
- **Name the denominator.** Any function that computes a share takes its base from
  `clean.completed` or `clean.attribution_universe`, never from "whatever was
  passed in".

---

## 5. Numeric output

- Round at the boundary, not in the middle: keep full precision while computing,
  round when writing a table or a label.
- A reported number is a rounded string, a table cell, or a JSON value — not a
  `print` with three different formats.
- Percentages in text are one decimal (`75.0%`); shares in tables are rounded to
  four decimals (`0.7501`); minutes are one decimal.
- Every metric that a reader might quote is written to `outputs/` so the report
  can be checked without re-running anything.

---

## 6. Figures

- One function per figure, named `fig_<topic>`, returning the saved path.
- No `plt.show()` inside library code; the notebook decides when to display.
- `matplotlib.use("Agg")` is set once in `viz.py` so a headless run never fails.
- Colours come from `schema`, never from a literal in the plotting call.

---

## 7. Everything else

| Rule | Reason |
|---|---|
| Line length ≤ 100 | Diff-friendly, and the figure code stays readable |
| No bare `except:` | It hides a data error as if it were a network error |
| `print` only for stage progress | Results go to files; a printed result cannot be checked |
| No notebook-only code | If a notebook computes something new, it belongs in `src/` |
| Tests are not optional | `pytest tests` is the gate before every merge |

**Line-length exemption — document builders.** The `≤ 100` limit applies to
analysis and figure code, where a long line is a reader's burden. It does not
apply to document *builders* such as `docs/proposal/_build_proposal.py`, whose
"lines" are mostly natural-language prose held in one string per paragraph.
Splitting those strings at column 100 would wrap sentences mid-word in the source
without changing the rendered document, and would make the prose harder to review
than the long line it removes. A builder may therefore hold a paragraph of prose
in a single string regardless of width; code in the same file (imports, helper
functions, control flow) still keeps to the limit.
