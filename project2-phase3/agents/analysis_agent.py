"""
Analysis / EDA Agent (domain-agnostic, Phase 3)
-------------------------------------------------
Computes whatever the domain_config.json says matters for THIS dataset:
  - "metrics"    -> single-number KPIs
  - "breakdowns" -> group-by aggregations that become charts downstream

Two kinds of metrics/breakdowns are supported:

1. GENERIC (type "simple" / default) -- Total X, Average X, X by category,
   Top 10 Y by X. These come from the Domain Configuration Agent's automatic
   column-role detection and work on ANY dataset, which is what proves the
   pipeline generalizes rather than being hand-built per dataset.

2. DOMAIN-SPECIFIC (type "ratio", "rate_percent", "threshold_rate",
   "period_growth", "category_match_rate", or breakdown type
   "threshold_rate_by_group") -- these come from the Domain Configuration
   Agent's domain playbook (see domain_config_agent._apply_domain_playbook)
   and represent actual analytical judgment for a detected domain: churn
   rate and ARPU for SaaS, reorder risk for inventory, profit margin for
   retail, etc. -- not just "another bar chart".

If a configured column doesn't actually exist in the cleaned data, that
metric/breakdown is skipped with a warning instead of crashing the run.
"""

import json
import pandas as pd


def _load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _agg_value(series, agg):
    if agg == "mean":
        return series.mean()
    if agg == "nunique":
        return series.nunique()
    if agg == "count":
        return series.count()
    return series.sum()


def _compute_metric(df, metric):
    """Returns (value, unit) or None if the metric can't be computed."""
    name = metric.get("name")
    mtype = metric.get("type", "simple")

    try:
        if mtype == "simple":
            column = metric.get("column")
            agg = metric.get("agg", "sum")
            if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
                print(f"   [analysis-agent] warning: metric '{name}' column '{column}' missing/non-numeric, skipping")
                return None
            return float(_agg_value(df[column], agg)), ""

        elif mtype == "rate_percent":
            # e.g. Churn Rate from a 0/1 flag column
            column = metric.get("column")
            if column not in df.columns:
                print(f"   [analysis-agent] warning: metric '{name}' column '{column}' missing, skipping")
                return None
            numeric_series = pd.to_numeric(df[column], errors="coerce")
            return float(numeric_series.mean() * 100), "%"

        elif mtype == "threshold_rate":
            # e.g. % of items below their reorder point
            value_col = metric.get("value_column")
            threshold_col = metric.get("threshold_column")
            comparison = metric.get("comparison", "below")
            if value_col not in df.columns or threshold_col not in df.columns:
                print(f"   [analysis-agent] warning: metric '{name}' references missing column(s), skipping")
                return None
            if comparison == "below":
                mask = df[value_col] < df[threshold_col]
            else:
                mask = df[value_col] > df[threshold_col]
            return float(mask.mean() * 100), "%"

        elif mtype == "ratio":
            num_col = metric.get("numerator_column")
            den_col = metric.get("denominator_column")
            num_agg = metric.get("numerator_agg", "sum")
            den_agg = metric.get("denominator_agg", "sum")
            if num_col not in df.columns or den_col not in df.columns:
                print(f"   [analysis-agent] warning: metric '{name}' references missing column(s), skipping")
                return None
            numerator = _agg_value(df[num_col], num_agg)
            denominator = _agg_value(df[den_col], den_agg)
            if not denominator:
                print(f"   [analysis-agent] warning: metric '{name}' has a zero denominator, skipping")
                return None
            value = numerator / denominator
            as_percent = metric.get("as_percent", False)
            if as_percent:
                value *= 100
            return float(value), ("%" if as_percent else "")

        elif mtype == "period_growth":
            value_col = metric.get("value_column")
            time_col = metric.get("time_column")
            grain = metric.get("time_grain", "year")
            if value_col not in df.columns or time_col not in df.columns:
                print(f"   [analysis-agent] warning: metric '{name}' references missing column(s), skipping")
                return None
            if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
                print(f"   [analysis-agent] warning: metric '{name}' time column '{time_col}' isn't a parsed date, skipping")
                return None
            bucket = df[time_col].dt.year if grain == "year" else df[time_col].dt.to_period("M").astype(str)
            grouped = df.groupby(bucket)[value_col].sum().sort_index()
            if len(grouped) < 2 or grouped.iloc[0] == 0:
                print(f"   [analysis-agent] warning: metric '{name}' doesn't have enough periods to compute growth, skipping")
                return None
            growth = (grouped.iloc[-1] - grouped.iloc[0]) / grouped.iloc[0] * 100
            return float(growth), "%"

        elif mtype == "category_match_rate":
            column = metric.get("column")
            keywords = metric.get("match_keywords", [])
            if column not in df.columns:
                print(f"   [analysis-agent] warning: metric '{name}' column '{column}' missing, skipping")
                return None
            series = df[column].astype(str).str.lower()
            mask = series.apply(lambda v: any(k in v for k in keywords))
            return float(mask.mean() * 100), "%"

        else:
            print(f"   [analysis-agent] warning: unknown metric type '{mtype}' for '{name}', skipping")
            return None

    except Exception as e:
        print(f"   [analysis-agent] warning: metric '{name}' failed to compute ({e}), skipping")
        return None


def _compute_breakdown(df, breakdown):
    name = breakdown.get("name")
    btype = breakdown.get("type", "group_agg")

    try:
        if btype == "threshold_rate_by_group":
            # e.g. Warehouse Risk Ranking (% of SKUs below reorder point)
            value_col = breakdown.get("value_column")
            threshold_col = breakdown.get("threshold_column")
            group_by = breakdown.get("group_by")
            comparison = breakdown.get("comparison", "below")
            if value_col not in df.columns or threshold_col not in df.columns or group_by not in df.columns:
                print(f"   [analysis-agent] warning: breakdown '{name}' references missing column(s), skipping")
                return None
            mask = df[value_col] < df[threshold_col] if comparison == "below" else df[value_col] > df[threshold_col]
            rate = df.assign(_risk=mask).groupby(group_by)["_risk"].mean() * 100
            rate = rate.sort_values(ascending=False)
            top_n = breakdown.get("top_n")
            if top_n:
                rate = rate.head(top_n)
            return {str(k): float(v) for k, v in rate.to_dict().items()}

        else:  # "group_agg" (default / backward compatible)
            group_by = breakdown.get("group_by")
            value = breakdown.get("value")
            agg = breakdown.get("agg", "sum")
            top_n = breakdown.get("top_n")
            time_grain = breakdown.get("time_grain")

            if group_by not in df.columns or value not in df.columns:
                print(f"   [analysis-agent] warning: breakdown '{name}' references missing column(s), skipping")
                return None

            series = df[group_by]
            if time_grain and pd.api.types.is_datetime64_any_dtype(series):
                series = series.dt.year if time_grain == "year" else series.dt.to_period("M").astype(str)

            grouped = df.groupby(series)[value]
            result = grouped.mean() if agg == "mean" else (grouped.count() if agg == "count" else grouped.sum())
            result = result.sort_values(ascending=False)
            if top_n:
                result = result.head(top_n)
            return {str(k): float(v) for k, v in result.to_dict().items()}

    except Exception as e:
        print(f"   [analysis-agent] warning: breakdown '{name}' failed to compute ({e}), skipping")
        return None


def analyze_data(input_path, config_path, output_path):
    print("\n========== ANALYSIS AGENT STARTED ==========")

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise RuntimeError(f"Analysis Agent could not read '{input_path}': {e}")

    config = _load_config(config_path)

    for col in config.get("date_columns", []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    print(f"Dataset shape: {df.shape}  |  domain: {config.get('domain')}")

    metrics_out = {}
    for metric in config.get("metrics", []):
        result = _compute_metric(df, metric)
        if result is not None:
            value, unit = result
            metrics_out[metric["name"]] = {"value": value, "unit": unit, "insight": bool(metric.get("insight"))}

    breakdowns_out = {}
    for breakdown in config.get("breakdowns", []):
        result = _compute_breakdown(df, breakdown)
        if result is not None:
            breakdowns_out[breakdown["name"]] = {
                "data": result,
                "chart_type": breakdown.get("chart_type", "bar"),
                "insight": bool(breakdown.get("insight")),
            }

    analysis_results = {
        "domain": config.get("domain"),
        "row_count": int(len(df)),
        "metrics": metrics_out,
        "breakdowns": breakdowns_out,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=4)
    except Exception as e:
        raise RuntimeError(f"Analysis Agent could not save results to '{output_path}': {e}")

    print("---------- KEY METRICS ----------")
    for name, m in metrics_out.items():
        print(f"{name}: {m['value']:,.2f}{m['unit']}")
    print(f"Breakdowns computed: {list(breakdowns_out.keys())}")
    print(f"Analysis saved to: {output_path}")
    print("========== ANALYSIS AGENT COMPLETED ==========")

    return analysis_results


if __name__ == "__main__":
    analyze_data(
        input_path="../test-datasets/cleaned_retail_sales.csv",
        config_path="../test-datasets/domain_config.json",
        output_path="../test-datasets/analysis_results.json",
    )
