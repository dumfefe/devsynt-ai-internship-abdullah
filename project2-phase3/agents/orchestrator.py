"""
Orchestrator (Phase 3)
------------------------
New flow vs Phase 2:

  Raw dataset
      -> Domain Configuration Agent   (NEW: detects domain, builds config)
      -> Clean Agent                  (now domain-agnostic)
      -> Analysis Agent                (now driven by domain config)
      -> Dynamic Dashboard Agent      (NEW: builds charts + HTML per domain)

Error handling: every node is wrapped so a failure in one dataset's run
records the failure in state["status"]/state["error"] and stops that run
cleanly, instead of an uncaught traceback killing the whole batch. This
matters because run_all_datasets.py loops this graph over 5 different
datasets -- one bad file should not stop the other four.
"""

import os
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from domain_config_agent import configure_domain
from clean_agent import clean_data
from analysis_agent import analyze_data
from dashboard_agent import build_dashboard


class AgentState(TypedDict):
    dataset_label: str
    raw_data_path: str
    cleaned_data_path: str
    config_path: str
    analysis_output_path: str
    assets_root: str
    result_image_path: str
    status: str
    error: Optional[str]
    failed_stage: Optional[str]


def _safe_node(stage_name, fn):
    def node(state: AgentState):
        if state.get("status") == "FAILED":
            return {}  # earlier stage already failed, skip remaining work
        try:
            fn(state)
            return {"status": f"{stage_name} completed"}
        except Exception as e:
            print(f"\n[ORCHESTRATOR] {stage_name} FAILED: {e}")
            return {"status": "FAILED", "error": str(e), "failed_stage": stage_name}
    return node


def domain_config_node_fn(state):
    configure_domain(input_path=state["raw_data_path"], output_path=state["config_path"])


def clean_node_fn(state):
    clean_data(
        input_path=state["raw_data_path"],
        output_path=state["cleaned_data_path"],
        config_path=state["config_path"],
    )


def analysis_node_fn(state):
    analyze_data(
        input_path=state["cleaned_data_path"],
        config_path=state["config_path"],
        output_path=state["analysis_output_path"],
    )


def dashboard_node_fn(state):
    build_dashboard(
        analysis_path=state["analysis_output_path"],
        dataset_label=state["dataset_label"],
        assets_root=state["assets_root"],
        result_image_path=state["result_image_path"],
    )


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("domain_config_agent", _safe_node("Domain Configuration Agent", domain_config_node_fn))
    workflow.add_node("clean_agent", _safe_node("Clean Agent", clean_node_fn))
    workflow.add_node("analysis_agent", _safe_node("Analysis Agent", analysis_node_fn))
    workflow.add_node("dashboard_agent", _safe_node("Dashboard Agent", dashboard_node_fn))

    workflow.add_edge(START, "domain_config_agent")
    workflow.add_edge("domain_config_agent", "clean_agent")
    workflow.add_edge("clean_agent", "analysis_agent")
    workflow.add_edge("analysis_agent", "dashboard_agent")
    workflow.add_edge("dashboard_agent", END)

    return workflow.compile()


def run_pipeline(dataset_label, raw_data_path, work_dir, assets_root):
    """Runs the full Phase 3 pipeline for a single dataset."""
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(assets_root, exist_ok=True)

    safe_label = "".join(c if c.isalnum() else "_" for c in dataset_label).lower()

    graph = build_graph()
    initial_state = {
        "dataset_label": dataset_label,
        "raw_data_path": raw_data_path,
        "cleaned_data_path": os.path.join(work_dir, f"{safe_label}_cleaned.csv"),
        "config_path": os.path.join(work_dir, f"{safe_label}_domain_config.json"),
        "analysis_output_path": os.path.join(work_dir, f"{safe_label}_analysis_results.json"),
        "assets_root": assets_root,
        "result_image_path": os.path.join(assets_root, f"{safe_label}-result.png"),
        "status": "Pipeline started",
        "error": None,
        "failed_stage": None,
    }

    final_state = graph.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    print("==========================================")
    print("   MULTI-AGENT PIPELINE (Phase 3)")
    print("==========================================")

    result = run_pipeline(
        dataset_label="Retail Sales",
        raw_data_path="../test-datasets/retail_sales.csv",
        work_dir="../test-datasets/_work",
        assets_root="../assets",
    )

    print("\n==========================================")
    if result["status"] == "FAILED":
        print(f"   PIPELINE FAILED at {result['failed_stage']}: {result['error']}")
    else:
        print("   PIPELINE COMPLETED SUCCESSFULLY")
    print("==========================================")
