# Prompt / Logic Evolution Log — Project 2 Phase 3

This log tracks what broke or looked wrong while testing the pipeline, and
what was changed in response. The "prompts" here are both the literal LLM
prompt used by the Domain Configuration Agent and the equivalent
rule-based logic in its fallback path (since the fallback carries the same
responsibility whenever no API key is configured).

## Round 1 — getting the core pipeline correct on 5 domains

### v1 → v2: Junk numeric columns became fake "metrics"

**Dataset:** Retail Sales
**Problem:** The retail CSV contains a constant column (`记录数`, always `1`)
and identifier/time-part columns like `Row.ID` and `weeknum`. The first
version of the column-role detector only excluded columns with "id" in the
name, so `记录数` and `weeknum` slipped through as "numeric metrics" and the
agent proposed `Total 记录数` as a KPI — a meaningless number.
**Fix:** Added a filter that drops constant columns (`nunique <= 1`) and
columns whose name suggests an identifier or a time-part from the
numeric-metric candidate pool.

### v2 → v3: Clean Agent deleted legitimate negative-profit rows

**Dataset:** Retail Sales
**Problem:** The generic "drop rows with negative values in metric columns"
rule was applied to every configured metric, including `Profit` and
`Discount`. Profit can legitimately be negative (a sale sold at a loss) —
the filter silently deleted ~12.5k real rows (~25% of the dataset).
**Fix:** Narrowed the non-negativity check to only the single
`primary_value_column`, never the full metrics list.

### v3 → v4: High-cardinality columns produced unreadable "wall of bars" charts

**Dataset:** Retail Sales (`City`, `Country` — hundreds of distinct values)
**Problem:** The breakdown selector picked categorical columns for "value
by X" bar charts with no cardinality check. `Sales by City` rendered as
100+ overlapping bars with unreadable labels.
**Fix:** Split categorical columns into low-cardinality (≤12 — safe for a
direct bar chart) and high-cardinality (always capped to a Top-10 barh)
buckets.

### v4 → v5: "id"-named columns with medium uniqueness were treated as chart dimensions

**Dataset:** Retail Sales (`Order.ID`, ~49% unique since each order has
multiple line items)
**Problem:** The id-detection threshold (`nunique > 0.5 * len`) missed
`Order.ID`, so it was treated as a regular dimension instead of an
identifier.
**Fix:** Lowered the uniqueness threshold to 0.3 specifically for columns
whose name already contains "id".

### v5 → v6: Wrong metric picked as "primary value" when two money-like columns exist

**Dataset:** Restaurant Sales (`Order_Total` vs `Tip_Amount`)
**Problem:** The keyword-priority list checked `"amount"` before `"total"`,
so `Tip_Amount` beat `Order_Total` for the headline metric.
**Fix:** Reordered the priority list so `"total"` is checked first.

## Round 2 — from "automated" to "domain-intelligent" (feedback-driven)

Three specific pieces of feedback on the first working version drove this
round: (1) dashboards were "visually solid but somewhat generic" — every
domain got the same templated shape instead of domain-specific insight;
(2) chart/metric names still looked code-generated (raw `Product_Category`
instead of "Product Category"); (3) screenshots alone don't prove the
detection is genuine rather than five hand-built dashboards.

### v6 → v7: Generic automation isn't the same as domain intelligence

**Fix:** added a **domain playbook**
(`_apply_domain_playbook` in `domain_config_agent.py`) that runs
deterministically after either the LLM or rule-based path, on every
dataset. For each domain this pipeline knows about, it looks for the
SPECIFIC columns that domain's real KPIs depend on (a reorder-point
column, a churn flag, a tip amount, ...) among the already-detected
columns, and only adds the insight if those columns actually exist in
*this* dataset:

- **Inventory:** `% Items Below Reorder Point` + a `Warehouse Risk Ranking`
  breakdown (rate of at-risk SKUs per warehouse, not just stock totals).
- **SaaS:** `Churn Rate`, `ARPU (Avg Revenue Per Customer)`,
  `MRR Growth Rate (First → Last Year)`.
- **Retail:** `Profit Margin` (Profit ÷ Sales).
- **E-commerce:** `Cancellation / Return Rate`.
- **Restaurant:** `Average Tip Rate`.

These render as visually distinct gold/starred "Domain Insight" cards and
charts (sorted first in the composite preview), so it's visible at a glance
which parts came from generic column-role detection and which came from
domain-specific analytical judgment.

This required extending `analysis_agent.py` with new metric/breakdown
*types* beyond simple sum/mean: `ratio` (with an optional `as_percent`
flag), `rate_percent`, `threshold_rate` / `threshold_rate_by_group`, and
`period_growth`. All fail gracefully (skip + warn) if a domain's expected
column isn't present in a given dataset.

### v7 → v8: Chart/metric names still looked code-generated

**Problem:** labels like `Order_Value by Product_Category` and
`Top 10 Customer_ID by Order_Value` read as raw column names.
**Fix:** added a `_pretty()` display-name helper (Title Case, spaces
instead of `_`/`.`, acronyms like ID/MRR/SKU/ARPU kept uppercase) and a
`_pretty_entity_plural()` helper for "Top 10 X by Y" titles specifically —
`Customer_ID` → `Customers`, `Product.ID` → `Products`. Applied throughout
the rule-based config's name generation; the LLM prompt now explicitly
requires natural human-readable names too.

### v8 → v9: A real bug the "unseen domain" test caught

**Dataset:** a gym-memberships dataset deliberately never used while
writing the domain-detection logic (see `prove_genuine_detection.py`).
**Problem:** `Monthly_Fee` — clearly the most meaningful numeric column —
was silently excluded from candidate metrics, and `PT_Sessions_Booked`
became the "primary value column" instead. Root cause: the non-metric
filter used substring matching (`"month" in "monthly_fee"`), which matched
inside the word "Monthly".
**Fix:** replaced substring matching with real tokenization (splits on
separators and camelCase boundaries, e.g. `Monthly_Fee` →
`["monthly","fee"]`) and exact-token matching against the hint set. This
is exactly the kind of bug that only surfaces on data the logic wasn't
tuned against — the point of testing on a genuinely unseen domain instead
of only re-testing the same 5 datasets.

## Error-handling checks (deliberate tests, not bug fixes)

Ran the pipeline against:
- **A malformed CSV** (mixed types in the numeric column, unparseable
  dates, duplicate rows, missing values): did not crash. Degraded to
  `domain: general` with no metrics, cleaned what it could, and still
  produced a minimal HTML dashboard.
- **A nonexistent file path**: the orchestrator caught the exception at
  the Domain Configuration Agent stage, recorded `status: FAILED` with the
  failing stage and message, and stopped — no uncaught traceback, and (in
  the batch runner) other datasets are unaffected by one bad file.

See `qa-error-handling-test/` for the artifacts.

## Proof this is genuine detection, not five hand-built dashboards

Run `python agents/prove_genuine_detection.py`. It does two things:
1. Statically scans all five agent files for any `if dataset == "..."` /
   filename-based branching — there is none; the only domain-conditional
   logic branches on the *detected* domain string inside the playbook.
2. Runs the full pipeline live on a gym-memberships dataset never used
   while writing `DOMAIN_KEYWORDS` or the domain playbook — no
   "gym"/"membership"/"fitness" keyword appears anywhere in this codebase.
   It correctly falls through to the honest `general` domain and still
   produces a working dashboard using only automatic column-role
   detection — proof the "five domains" aren't just five if/else branches
   in a trenchcoat. (This run is also what caught the v9 bug above.)

## What's still LLM-dependent, and why the fallback matters

The Domain Configuration Agent's LLM path (Gemini via
`langchain-google-genai`) is written and ready, but all testing above ran
on the rule-based fallback since no `GOOGLE_API_KEY` was available in the
sandbox this was built in. Every fix above went into the fallback logic
directly. The domain playbook (churn rate, reorder risk, etc.) runs
identically regardless of which path produced the base config, so
domain-specific intelligence doesn't depend on the LLM call succeeding.
Set `GOOGLE_API_KEY` to also exercise the LLM-based classification path.
