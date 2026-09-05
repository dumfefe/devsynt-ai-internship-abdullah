"""
Domain Configuration Agent
---------------------------
Runs BEFORE the orchestrator's main pipeline.

Job: look at an incoming dataset (any domain) and produce a domain_config.json
that tells the rest of the pipeline:
  - what domain the data belongs to (retail_sales, ecommerce_orders, inventory,
    restaurant_sales, saas_metrics, or "general" if nothing matches well)
  - which columns matter (id / date / numeric metric / categorical dimension)
  - what generic "success metrics" (KPIs) make sense for this domain
  - what generic breakdowns (group-by charts) make sense for this domain
  - what DOMAIN-SPECIFIC insight metrics/breakdowns apply (churn rate, ARPU,
    reorder risk, profit margin, ...) -- see _apply_domain_playbook below

Design: this tries an LLM call first (Gemini, via langchain-google-genai,
same as the rest of this project's stack) so the classification is genuinely
data-aware and reads real column semantics, not just keyword matching.

If no API key is configured, the LLM call fails, or the LLM returns something
that doesn't parse as valid JSON, the agent falls back to a deterministic
rule-based classifier so the pipeline NEVER crashes just because a key is
missing or a model call times out. This fallback is the main "error handling"
story of this agent -- see prompt-evolution-log.md for how this decision
came about.

IMPORTANT: the domain playbook (churn rate, reorder risk, ARPU, etc.) runs
AFTER either path, unconditionally, on every config -- so domain-specific
analytical intelligence doesn't depend on the LLM call succeeding. It's a
deterministic, testable, code-reviewable rule set, not a prompt hoping the
model remembers to compute a ratio correctly.
"""

import os
import re
import json
import pandas as pd


# ---------------------------------------------------------------------------
# Keyword banks used by the rule-based fallback classifier. Also used as a
# sanity check / hint injected into the LLM prompt.
# ---------------------------------------------------------------------------
DOMAIN_KEYWORDS = {
    "retail_sales": ["sales", "profit", "region", "category", "product.name", "discount"],
    "ecommerce_orders": ["order.id", "order id", "customer", "shipping", "payment", "order.date"],
    "inventory_stock": ["stock", "reorder", "warehouse", "sku", "on.hand", "on_hand", "supplier"],
    "restaurant_sales": ["menu", "dish", "table", "waiter", "server", "tip", "reservation", "cuisine"],
    "saas_metrics": ["mrr", "arr", "subscription", "plan", "churn", "signup", "trial", "seats"],
}

_NON_METRIC_NUMERIC_HINTS = {"id", "year", "week", "month", "day", "num", "number", "code", "index", "zip", "postal", "weeknum"}


def _tokenize(col):
    """Split a column name into lowercase tokens on separators AND camelCase
    boundaries, e.g. 'Monthly_Fee' -> ['monthly','fee'], 'OrderID' ->
    ['order','id']. Exact-token matching against this (rather than raw
    substring matching) is what's used for the ambiguous short hints below --
    a raw substring check on 'month' was matching inside 'Monthly_Fee' and
    wrongly excluding it from being a candidate metric (caught by testing on
    an unseen gym-memberships dataset, where it hid the actual revenue column
    behind a meaningless session-count column instead)."""
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', col)
    parts = re.split(r'[^a-zA-Z0-9]+', spaced)
    return [p.lower() for p in parts if p]

_ACRONYMS = {"id": "ID", "mrr": "MRR", "arr": "ARR", "sku": "SKU", "arpu": "ARPU", "saas": "SaaS", "ids": "IDs"}


# ---------------------------------------------------------------------------
# Display-name helpers -- turns "Order_Value" / "Customer.ID" into "Order
# Value" / "Customer ID" for chart titles and KPI labels instead of leaking
# raw column syntax into the dashboard.
# ---------------------------------------------------------------------------
def _pretty(col):
    s = col.replace(".", " ").replace("_", " ").strip()
    words = [w for w in s.split(" ") if w]
    out = []
    for w in words:
        out.append(_ACRONYMS.get(w.lower(), w[:1].upper() + w[1:]))
    return " ".join(out)


def _pretty_entity_plural(col):
    """For 'Top 10 X by Y' chart titles: 'Customer_ID' -> 'Customers', not
    'Top 10 Customer ID by ...'."""
    pretty = _pretty(col)
    for suffix in (" ID", " Id"):
        if pretty.endswith(suffix):
            pretty = pretty[: -len(suffix)].strip()
            break
    base = pretty
    lower = base.lower()
    if lower.endswith("y") and not lower.endswith(("ay", "ey", "oy", "uy")):
        return base[:-1] + "ies"
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return base + "es"
    return base + "s"


def _read_sample(input_path, n_rows=5):
    df = pd.read_csv(input_path)
    columns = df.columns.tolist()
    dtypes = {c: str(df[c].dtype) for c in columns}
    sample = df.head(n_rows).astype(str).to_dict(orient="records")
    return df, columns, dtypes, sample


def _score_domain_by_keywords(columns):
    cols_lower = [c.lower() for c in columns]
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in keywords:
            for c in cols_lower:
                if kw in c:
                    score += 1
        scores[domain] = score
    best_domain = max(scores, key=scores.get)
    if scores[best_domain] == 0:
        return "general"
    return best_domain


def _detect_column_roles(df):
    """Generic column-role detector used by the rule-based fallback (and as
    a cross-check against whatever the LLM returns)."""
    id_columns, date_columns, numeric_columns, categorical_columns = [], [], [], []

    for col in df.columns:
        lower = col.lower()
        series = df[col]

        if "id" in lower and series.nunique() > 0.3 * len(series):
            id_columns.append(col)
            continue

        if "date" in lower or "time" in lower:
            date_columns.append(col)
            continue

        if pd.api.types.is_numeric_dtype(series):
            is_constant = series.nunique(dropna=True) <= 1
            tokens = set(_tokenize(col))
            looks_like_id_or_time_part = bool(tokens & _NON_METRIC_NUMERIC_HINTS)
            if is_constant or looks_like_id_or_time_part:
                categorical_columns.append(col)
                continue
            numeric_columns.append(col)
            continue

        try:
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().mean() > 0.8:
                date_columns.append(col)
                continue
        except Exception:
            pass

        categorical_columns.append(col)

    return id_columns, date_columns, numeric_columns, categorical_columns


def _find_col(candidates, *keywords, numeric_only=False, df=None):
    for c in candidates:
        lc = c.lower()
        if any(k in lc for k in keywords):
            if numeric_only and (df is None or not pd.api.types.is_numeric_dtype(df[c])):
                continue
            return c
    return None


def _rule_based_config(input_path, df, columns, dtypes):
    domain = _score_domain_by_keywords(columns)
    id_cols, date_cols, numeric_cols, cat_cols = _detect_column_roles(df)

    value_priority = ["sales", "revenue", "total", "amount", "price", "mrr", "value"]
    value_column = None
    for kw in value_priority:
        for c in numeric_cols:
            if kw in c.lower():
                value_column = c
                break
        if value_column:
            break
    if value_column is None and numeric_cols:
        value_column = numeric_cols[0]

    metrics = []
    if value_column:
        metrics.append({"name": f"Total {_pretty(value_column)}", "column": value_column, "agg": "sum"})
        metrics.append({"name": f"Average {_pretty(value_column)}", "column": value_column, "agg": "mean"})

    for c in numeric_cols:
        if c != value_column and len(metrics) < 5:
            metrics.append({"name": f"Total {_pretty(c)}", "column": c, "agg": "sum"})

    LOW_CARDINALITY_MAX = 12
    low_card_cols = [c for c in cat_cols if 2 <= df[c].nunique() <= LOW_CARDINALITY_MAX]
    high_card_cols = [c for c in cat_cols if df[c].nunique() > LOW_CARDINALITY_MAX]

    breakdowns = []
    if value_column:
        for c in low_card_cols[:2]:
            breakdowns.append({
                "name": f"{_pretty(value_column)} by {_pretty(c)}",
                "group_by": c, "value": value_column, "agg": "sum",
                "chart_type": "bar", "top_n": None,
            })

        if date_cols:
            breakdowns.append({
                "name": f"{_pretty(value_column)} Over Time",
                "group_by": date_cols[0], "value": value_column, "agg": "sum",
                "chart_type": "line", "time_grain": "year",
            })

        if high_card_cols:
            most_specific = max(high_card_cols, key=lambda c: df[c].nunique())
            breakdowns.append({
                "name": f"Top 10 {_pretty_entity_plural(most_specific)} by {_pretty(value_column)}",
                "group_by": most_specific, "value": value_column, "agg": "sum",
                "chart_type": "barh", "top_n": 10,
            })
        elif low_card_cols[2:3]:
            c = low_card_cols[2]
            breakdowns.append({
                "name": f"Top {_pretty_entity_plural(c)} by {_pretty(value_column)}",
                "group_by": c, "value": value_column, "agg": "sum",
                "chart_type": "barh", "top_n": 10,
            })

    return {
        "domain": domain,
        "source_method": "rule_based_fallback",
        "row_count": int(len(df)),
        "columns": columns,
        "id_columns": id_cols,
        "date_columns": date_cols,
        "numeric_columns": numeric_cols,
        "categorical_columns": cat_cols,
        "key_columns": {"primary_value_column": value_column},
        "metrics": metrics,
        "breakdowns": breakdowns,
    }


# ---------------------------------------------------------------------------
# DOMAIN PLAYBOOK
# ---------------------------------------------------------------------------
# This is the part that answers "is this genuinely domain-aware, or just
# generic automation with a label on it?". For each domain this pipeline
# knows about, it looks for the specific columns that domain's real KPIs
# depend on (a reorder point, a churn flag, a tip amount, ...) using the
# ALREADY-DETECTED column roles, and only adds the insight if those columns
# actually exist in THIS dataset. Nothing here is hardcoded to a specific
# dataset's column names -- it's hardcoded to a domain's semantics, then
# matched against whatever columns that domain's dataset happens to have.
# Runs on every config, whether it came from the LLM or the rule-based path.
# ---------------------------------------------------------------------------
def _apply_domain_playbook(domain, df, config):
    numeric_cols = config.get("numeric_columns", [])
    cat_cols = config.get("categorical_columns", [])
    date_cols = config.get("date_columns", [])
    id_cols = config.get("id_columns", [])
    value_column = config.get("key_columns", {}).get("primary_value_column")

    new_metrics = []
    new_breakdowns = []

    if domain == "inventory_stock":
        stock_col = value_column or _find_col(numeric_cols, "stock", df=df, numeric_only=True)
        reorder_col = _find_col(numeric_cols, "reorder", df=df, numeric_only=True)
        warehouse_col = _find_col(cat_cols, "warehouse", "location", "site") or (cat_cols[0] if cat_cols else None)

        if stock_col and reorder_col:
            new_metrics.append({
                "name": "Items Below Reorder Point", "type": "threshold_rate",
                "value_column": stock_col, "threshold_column": reorder_col,
                "comparison": "below", "insight": True,
            })
            if warehouse_col:
                new_breakdowns.append({
                    "name": f"Warehouse Risk Ranking (% Below Reorder Point)", "type": "threshold_rate_by_group",
                    "value_column": stock_col, "threshold_column": reorder_col, "group_by": warehouse_col,
                    "comparison": "below", "chart_type": "barh", "top_n": 10, "insight": True,
                })

    elif domain == "saas_metrics":
        mrr_col = value_column or _find_col(numeric_cols, "mrr", "revenue", df=df, numeric_only=True)
        churn_col = _find_col(numeric_cols + cat_cols, "churn")
        customer_id_col = _find_col(id_cols, "customer") or (id_cols[0] if id_cols else None)

        if churn_col:
            new_metrics.append({
                "name": "Churn Rate", "type": "rate_percent", "column": churn_col, "insight": True,
            })
        if mrr_col and customer_id_col:
            new_metrics.append({
                "name": "ARPU (Avg Revenue Per Customer)", "type": "ratio",
                "numerator_column": mrr_col, "numerator_agg": "sum",
                "denominator_column": customer_id_col, "denominator_agg": "nunique",
                "insight": True,
            })
        if mrr_col and date_cols:
            new_metrics.append({
                "name": "MRR Growth Rate (First to Last Year)", "type": "period_growth",
                "value_column": mrr_col, "time_column": date_cols[0], "time_grain": "year",
                "insight": True,
            })

    elif domain == "retail_sales":
        sales_col = value_column
        profit_col = _find_col(numeric_cols, "profit", df=df, numeric_only=True)
        if sales_col and profit_col:
            new_metrics.append({
                "name": "Profit Margin", "type": "ratio",
                "numerator_column": profit_col, "numerator_agg": "sum",
                "denominator_column": sales_col, "denominator_agg": "sum",
                "as_percent": True, "insight": True,
            })

    elif domain == "ecommerce_orders":
        status_col = _find_col(cat_cols, "status")
        if status_col:
            new_metrics.append({
                "name": "Cancellation / Return Rate", "type": "category_match_rate",
                "column": status_col, "match_keywords": ["cancel", "return"], "insight": True,
            })

    elif domain == "restaurant_sales":
        total_col = value_column
        tip_col = _find_col(numeric_cols, "tip", df=df, numeric_only=True)
        if total_col and tip_col:
            new_metrics.append({
                "name": "Average Tip Rate", "type": "ratio",
                "numerator_column": tip_col, "numerator_agg": "sum",
                "denominator_column": total_col, "denominator_agg": "sum",
                "as_percent": True, "insight": True,
            })

    # domain == "general" (or anything unrecognized): deliberately no playbook
    # entries -- this is the honest fallback for a dataset that doesn't match
    # a known domain. See qa-error-handling-test/ and
    # test-datasets/unseen_domain_gym_memberships.csv for what that looks like.

    config["metrics"] = config.get("metrics", []) + new_metrics
    config["breakdowns"] = config.get("breakdowns", []) + new_breakdowns
    return config


def _try_llm_config(input_path, df, columns, dtypes, sample, api_key):
    """Attempt an LLM-based classification. Returns a config dict on success,
    or None on any failure (missing key, import error, bad JSON, etc.)."""
    if not api_key:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        print("   [domain-config] langchain-google-genai not installed, skipping LLM path")
        return None

    keyword_hint = _score_domain_by_keywords(columns)

    prompt = f"""You are a data analyst. Look at this dataset's columns, dtypes, and
sample rows, and return ONLY a single JSON object (no markdown fences, no prose)
describing how to analyze it.

Columns: {columns}
Dtypes: {dtypes}
Sample rows: {json.dumps(sample, indent=2)}
A simple keyword-based guess for domain (for reference only, you may override it): {keyword_hint}

Return JSON with EXACTLY this shape:
{{
  "domain": "one of: retail_sales, ecommerce_orders, inventory_stock, restaurant_sales, saas_metrics, general",
  "id_columns": [...],
  "date_columns": [...],
  "numeric_columns": [...],
  "categorical_columns": [...],
  "key_columns": {{"primary_value_column": "<the single most important numeric column for this domain, e.g. Sales, Revenue, MRR, Stock_Level>"}},
  "metrics": [{{"name": "<natural human-readable display name, e.g. 'Total Sales' not 'total_sales'>", "column": "<column name>", "agg": "sum|mean|count"}}],
  "breakdowns": [{{"name": "<natural human-readable display name, e.g. 'Sales by Region' not 'Sales_by_Region'>", "group_by": "<column name>", "value": "<numeric column>", "agg": "sum|mean|count", "chart_type": "bar|barh|line|pie", "top_n": null_or_int}}]
}}

Pick 2-5 metrics and 2-4 breakdowns that genuinely make sense for THIS domain and THESE
columns. Only use column names that actually appear in the Columns list above.
Display names must read naturally in English (spaces, not underscores/dots; no raw
column syntax) -- e.g. "Top 10 Customers by Order Value", not "Top 10 Customer_ID by Order_Value"."""

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)
        response = llm.invoke(prompt)
        text = response.content.strip()
        text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
        config = json.loads(text)

        referenced = set()
        for m in config.get("metrics", []):
            referenced.add(m.get("column"))
        for b in config.get("breakdowns", []):
            referenced.add(b.get("group_by"))
            referenced.add(b.get("value"))
        referenced.discard(None)
        if not referenced.issubset(set(columns)):
            print("   [domain-config] LLM referenced a column that doesn't exist, discarding LLM result")
            return None

        config["source_method"] = "llm_gemini"
        config["row_count"] = int(len(df))
        config["columns"] = columns
        return config

    except Exception as e:
        print(f"   [domain-config] LLM call failed ({type(e).__name__}: {e}), falling back to rules")
        return None


def _verify_config_against_dataset(config, columns):
    """Self-check logged to the console: proves the config genuinely
    references this dataset's real columns, for anyone auditing the run."""
    referenced = set()
    for m in config.get("metrics", []):
        for key in ("column", "numerator_column", "denominator_column", "value_column", "threshold_column", "time_column"):
            if m.get(key):
                referenced.add(m[key])
    for b in config.get("breakdowns", []):
        for key in ("group_by", "value", "value_column", "threshold_column"):
            if b.get(key):
                referenced.add(b[key])

    missing = referenced - set(columns)
    if missing:
        print(f"   [domain-config] WARNING: config references columns not in dataset: {missing}")
    else:
        print(f"   [domain-config] verified: all {len(referenced)} referenced columns exist in this dataset")


def configure_domain(input_path, output_path):
    print("\n========== DOMAIN CONFIGURATION AGENT STARTED ==========")

    try:
        df, columns, dtypes, sample = _read_sample(input_path)
    except Exception as e:
        raise RuntimeError(f"Domain Config Agent could not read '{input_path}': {e}")

    api_key = os.environ.get("GOOGLE_API_KEY")
    config = _try_llm_config(input_path, df, columns, dtypes, sample, api_key)

    if config is None:
        config = _rule_based_config(input_path, df, columns, dtypes)

    config = _apply_domain_playbook(config["domain"], df, config)
    _verify_config_against_dataset(config, columns)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    n_insight_metrics = sum(1 for m in config["metrics"] if m.get("insight"))
    n_insight_breakdowns = sum(1 for b in config["breakdowns"] if b.get("insight"))

    print(f"Detected domain: {config['domain']}  (method: {config['source_method']})")
    print(f"Primary value column: {config['key_columns'].get('primary_value_column')}")
    print(f"Metrics configured: {[m['name'] for m in config['metrics']]}")
    print(f"Breakdowns configured: {[b['name'] for b in config['breakdowns']]}")
    print(f"Domain-specific insights added by playbook: {n_insight_metrics} metric(s), {n_insight_breakdowns} chart(s)")
    print(f"Domain config saved to: {output_path}")
    print("========== DOMAIN CONFIGURATION AGENT COMPLETED ==========")

    return config


if __name__ == "__main__":
    configure_domain(
        input_path="../test-datasets/retail_sales.csv",
        output_path="../test-datasets/domain_config.json",
    )
