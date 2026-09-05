"""
Dynamic Dashboard Agent (Phase 3)
------------------------------------
Builds the dashboard FROM analysis_results.json -- it has no idea in advance
whether it's looking at retail sales, SaaS MRR, or restaurant tickets. It
loops over whatever metrics/breakdowns are in the results and lays them out.

Metrics/breakdowns carry an "insight" flag set upstream by the Domain
Configuration Agent's domain playbook (churn rate, reorder risk, ARPU, ...).
Those are rendered as visually distinct "Domain Insight" cards/charts
(gold-bordered, marked with a star) separate from the generic "Key Metrics"
section -- so it's visible at a glance which parts of the dashboard are
generic automation and which are domain-specific analytical judgment.

For each dataset it produces, inside assets/<dataset_name>/:
  - one chart PNG per breakdown (bar / barh / line / pie, chosen per-breakdown)
  - a dashboard.html with dynamically generated KPI cards + chart grid
  - a single composite "result" PNG (all KPIs + charts in one image) that
    doubles as the dataset-result.png screenshot required in the submission,
    since this pipeline runs headless with no browser available for a live
    screenshot.
"""

import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["axes.unicode_minus"] = True

INSIGHT_COLOR = "#b45309"   # amber/gold, used to mark domain-specific insights
GENERIC_COLOR = "#1f77b4"   # default matplotlib blue, used for generic charts


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _draw_chart(ax, name, chart_type, data, is_insight):
    labels = list(data.keys())
    values = list(data.values())
    color = INSIGHT_COLOR if is_insight else GENERIC_COLOR
    title = f"\u2605 {name}" if is_insight else name

    if chart_type == "line":
        try:
            pairs = sorted(zip(labels, values), key=lambda p: p[0])
            labels, values = zip(*pairs)
        except Exception:
            pass
        ax.plot(labels, values, marker="o", color=color)
        ax.tick_params(axis="x", rotation=45)

    elif chart_type == "barh":
        ax.barh(labels[::-1], values[::-1], color=color)

    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.0f%%")

    else:  # default: vertical bar
        ax.bar(labels, values, color=color)
        ax.tick_params(axis="x", rotation=45)

    if chart_type != "pie":
        ax.set_ylabel("Value")
    ax.set_title(title, fontsize=11, color=(INSIGHT_COLOR if is_insight else "black"),
                 fontweight=("bold" if is_insight else "normal"))


def _make_individual_charts(breakdowns, output_folder):
    chart_files = {}
    for name, info in breakdowns.items():
        fig, ax = plt.subplots(figsize=(8, 5))
        _draw_chart(ax, name, info["chart_type"], info["data"], info.get("insight", False))
        plt.tight_layout()

        safe_name = "".join(c if c.isalnum() else "_" for c in name).lower()
        filepath = os.path.join(output_folder, f"{safe_name}.png")
        plt.savefig(filepath)
        plt.close(fig)
        chart_files[name] = os.path.basename(filepath)
        print(f"   Created chart: {filepath}")
    return chart_files


def _make_composite_preview(domain, metrics, breakdowns, output_path):
    """One combined image: KPI row + a grid of charts. Acts as the
    dataset-result.png screenshot for the submission. Insight charts are
    sorted first so they're the first thing a reviewer sees."""
    items = sorted(breakdowns.items(), key=lambda kv: not kv[1].get("insight", False))

    n_charts = len(items)
    n_cols = 2
    n_rows = max(1, (n_charts + 1) // 2)

    fig = plt.figure(figsize=(13, 4 + 4 * n_rows))
    gs = fig.add_gridspec(n_rows + 1, n_cols, height_ratios=[0.6] + [1] * n_rows)

    kpi_ax = fig.add_subplot(gs[0, :])
    kpi_ax.axis("off")
    generic_text = "   |   ".join(
        f"{k}: {v['value']:,.2f}{v['unit']}" for k, v in metrics.items() if not v.get("insight")
    )
    insight_text = "   |   ".join(
        f"\u2605 {k}: {v['value']:,.2f}{v['unit']}" for k, v in metrics.items() if v.get("insight")
    )
    kpi_ax.text(0.5, 0.75, f"Domain: {domain}", ha="center", fontsize=15, fontweight="bold")
    kpi_ax.text(0.5, 0.42, generic_text, ha="center", fontsize=10, wrap=True)
    if insight_text:
        kpi_ax.text(0.5, 0.1, insight_text, ha="center", fontsize=10.5, wrap=True,
                     color=INSIGHT_COLOR, fontweight="bold")

    for i, (name, info) in enumerate(items):
        row, col = divmod(i, n_cols)
        ax = fig.add_subplot(gs[row + 1, col])
        _draw_chart(ax, name, info["chart_type"], info["data"], info.get("insight", False))

    plt.tight_layout()
    plt.savefig(output_path, dpi=110)
    plt.close(fig)
    print(f"   Created composite dashboard preview: {output_path}")


def _make_html(domain, row_count, metrics, breakdowns, chart_files, output_path, dataset_label):
    generic_metrics = {k: v for k, v in metrics.items() if not v.get("insight")}
    insight_metrics = {k: v for k, v in metrics.items() if v.get("insight")}
    generic_breakdowns = {k: v for k, v in breakdowns.items() if not v.get("insight")}
    insight_breakdowns = {k: v for k, v in breakdowns.items() if v.get("insight")}

    def kpi_card(name, m, insight=False):
        cls = "card insight" if insight else "card"
        label = f"\u2605 {name}" if insight else name
        return f'<div class="{cls}"><h3>{label}</h3><p>{m["value"]:,.2f}{m["unit"]}</p></div>'

    def chart_card(name, filename, insight=False):
        cls = "chart-card insight" if insight else "chart-card"
        label = f"\u2605 {name}" if insight else name
        return f'<div class="{cls}"><h3>{label}</h3><img src="{filename}" alt="{name}"></div>'

    generic_cards = "\n".join(kpi_card(n, m) for n, m in generic_metrics.items())
    insight_cards = "\n".join(kpi_card(n, m, True) for n, m in insight_metrics.items())
    generic_charts = "\n".join(chart_card(n, chart_files[n]) for n in generic_breakdowns if n in chart_files)
    insight_charts = "\n".join(chart_card(n, chart_files[n], True) for n in insight_breakdowns if n in chart_files)

    insight_section = ""
    if insight_cards or insight_charts:
        insight_section = f"""
  <section class="insight-banner">
    <h2>\u2605 Domain-Specific Insights</h2>
    <p>Computed because the Domain Configuration Agent detected this dataset as <b>{domain}</b> and applied that domain's analysis playbook -- not generic templating.</p>
  </section>
  <section class="summary-cards">
    {insight_cards}
  </section>
  <section class="chart-grid">
    {insight_charts}
  </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{dataset_label} Dashboard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: Arial, sans-serif; background:#f4f6f9; color:#222; line-height:1.6; }}
header {{ background:#1f2937; color:white; text-align:center; padding:30px 20px; }}
header p {{ opacity:0.85; }}
main {{ width:90%; max-width:1300px; margin:30px auto; }}
h2 {{ margin-bottom:14px; font-size:1.3rem; }}
.insight-banner {{ background:#fffbeb; border:1px solid #fcd34d; border-radius:10px; padding:16px 20px; margin:30px 0 20px; }}
.insight-banner h2 {{ color:{INSIGHT_COLOR}; margin-bottom:6px; }}
.insight-banner p {{ font-size:0.9rem; color:#555; }}
.summary-cards {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:20px; margin-bottom:40px; }}
.card {{ background:white; padding:22px; border-radius:12px; box-shadow:0 3px 10px rgba(0,0,0,0.08); }}
.card.insight {{ border:2px solid {INSIGHT_COLOR}; background:#fffdf5; }}
.card h3 {{ color:#666; font-size:0.9rem; margin-bottom:8px; }}
.card.insight h3 {{ color:{INSIGHT_COLOR}; }}
.card p {{ font-size:1.6rem; font-weight:bold; }}
.chart-grid {{ display:grid; grid-template-columns: repeat(2, 1fr); gap:25px; }}
.chart-card {{ background:white; padding:18px; border-radius:12px; box-shadow:0 3px 10px rgba(0,0,0,0.08); }}
.chart-card.insight {{ border:2px solid {INSIGHT_COLOR}; background:#fffdf5; }}
.chart-card h3 {{ margin-bottom:12px; text-align:center; font-size:1rem; }}
.chart-card.insight h3 {{ color:{INSIGHT_COLOR}; }}
.chart-card img {{ width:100%; height:auto; display:block; }}
footer {{ margin-top:50px; padding:22px; text-align:center; background:#1f2937; color:white; }}
@media (max-width:900px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>{dataset_label} Dashboard</h1>
  <p>Domain detected: {domain} &middot; {row_count:,} rows &middot; Auto-generated by Dashboard Agent</p>
</header>
<main>
  {insight_section}
  <h2>Key Metrics</h2>
  <section class="summary-cards">
    {generic_cards}
  </section>
  <section class="chart-grid">
    {generic_charts}
  </section>
</main>
<footer><p>Built by the Dynamic Dashboard Agent &middot; Project 2 Phase 3</p></footer>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   Created HTML dashboard: {output_path}")


def build_dashboard(analysis_path, dataset_label, assets_root, result_image_path):
    print("\n========== DASHBOARD AGENT STARTED ==========")

    try:
        results = _load_json(analysis_path)
    except Exception as e:
        raise RuntimeError(f"Dashboard Agent could not read '{analysis_path}': {e}")

    domain = results.get("domain", "general")
    row_count = results.get("row_count", 0)
    metrics = results.get("metrics", {})
    breakdowns = results.get("breakdowns", {})

    if not metrics and not breakdowns:
        print("   [dashboard-agent] warning: no metrics or breakdowns to render, dashboard will be minimal")

    n_insight_metrics = sum(1 for m in metrics.values() if m.get("insight"))
    n_insight_breakdowns = sum(1 for b in breakdowns.values() if b.get("insight"))
    print(f"   Domain-specific insights: {n_insight_metrics} metric(s), {n_insight_breakdowns} chart(s)")

    safe_label = "".join(c if c.isalnum() else "_" for c in dataset_label).lower()
    output_folder = os.path.join(assets_root, safe_label)
    os.makedirs(output_folder, exist_ok=True)

    chart_files = _make_individual_charts(breakdowns, output_folder)
    html_path = os.path.join(output_folder, "dashboard.html")
    _make_html(domain, row_count, metrics, breakdowns, chart_files, html_path, dataset_label)

    if breakdowns:
        _make_composite_preview(domain, metrics, breakdowns, result_image_path)
    else:
        print("   [dashboard-agent] skipping composite preview (no breakdowns)")

    print("========== DASHBOARD AGENT COMPLETED ==========")
    return {"dashboard_html": html_path, "result_image": result_image_path}


if __name__ == "__main__":
    build_dashboard(
        analysis_path="../test-datasets/analysis_results.json",
        dataset_label="Retail Sales",
        assets_root="../assets",
        result_image_path="../assets/retail_sales-result.png",
    )
