"""
Runs the Phase 3 pipeline across all 4-5 different-domain test datasets and
prints/saves a summary. This is what proves the pipeline is domain-aware
rather than hardcoded to the retail dataset -- the assignment's core
requirement for this phase.
"""

import json
import os
from orchestrator import run_pipeline

DATASETS = [
    ("Retail Sales", "../test-datasets/retail_sales.csv"),
    ("E-commerce Orders", "../test-datasets/ecommerce_orders.csv"),
    ("Inventory Stock", "../test-datasets/inventory_stock.csv"),
    ("Restaurant Sales", "../test-datasets/restaurant_sales.csv"),
    ("SaaS Metrics", "../test-datasets/saas_metrics.csv"),
]


def main():
    summary = []
    for label, path in DATASETS:
        print("\n" + "#" * 70)
        print(f"# RUNNING PIPELINE FOR: {label}  ({path})")
        print("#" * 70)

        result = run_pipeline(
            dataset_label=label,
            raw_data_path=path,
            work_dir="../test-datasets/_work",
            assets_root="../assets",
        )

        status = "SUCCESS" if result["status"] != "FAILED" else "FAILED"
        entry = {
            "dataset": label,
            "path": path,
            "status": status,
            "failed_stage": result.get("failed_stage"),
            "error": result.get("error"),
        }

        # pull the detected domain + metrics if the run succeeded
        if status == "SUCCESS":
            safe_label = "".join(c if c.isalnum() else "_" for c in label).lower()
            config_path = f"../test-datasets/_work/{safe_label}_domain_config.json"
            analysis_path = f"../test-datasets/_work/{safe_label}_analysis_results.json"
            try:
                with open(config_path) as f:
                    config = json.load(f)
                with open(analysis_path) as f:
                    analysis = json.load(f)
                entry["detected_domain"] = config.get("domain")
                entry["source_method"] = config.get("source_method")
                entry["metrics"] = analysis.get("metrics")
                entry["breakdowns"] = list(analysis.get("breakdowns", {}).keys())
            except Exception as e:
                entry["summary_read_error"] = str(e)

        summary.append(entry)

    print("\n" + "=" * 70)
    print("BATCH RUN SUMMARY")
    print("=" * 70)
    for entry in summary:
        print(f"\n{entry['dataset']}: {entry['status']}")
        if entry["status"] == "SUCCESS":
            print(f"  Detected domain: {entry['detected_domain']} ({entry['source_method']})")
            print(f"  Metrics: {list(entry['metrics'].keys())}")
            print(f"  Breakdowns: {entry['breakdowns']}")
        else:
            print(f"  Failed at: {entry['failed_stage']}  |  {entry['error']}")

    with open("../test-datasets/_work/batch_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    main()
