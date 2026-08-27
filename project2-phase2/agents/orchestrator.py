from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from clean_agent import clean_data
from analysis_agent import analyze_data
from visualization_agent import create_visualizations


class AgentState(TypedDict):
    raw_data_path: str
    cleaned_data_path: str
    analysis_output_path: str
    assets_folder: str
    status: str


def clean_agent_node(state: AgentState):
    print("\n🧠 ORCHESTRATOR: Sending raw data to Clean Agent...")

    clean_data(
        input_path=state["raw_data_path"],
        output_path=state["cleaned_data_path"]
    )

    return {
        "status": "Cleaning completed"
    }


def analysis_agent_node(state: AgentState):
    print("\n🧠 ORCHESTRATOR: Sending cleaned data to Analysis Agent...")

    analyze_data(
        input_path=state["cleaned_data_path"],
        output_path=state["analysis_output_path"]
    )

    return {
        "status": "Analysis completed"
    }


def visualization_agent_node(state: AgentState):
    print("\n🧠 ORCHESTRATOR: Sending analysis results to Visualization Agent...")

    create_visualizations(
        input_path=state["analysis_output_path"],
        output_folder=state["assets_folder"]
    )

    return {
        "status": "Visualization completed"
    }


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("clean_agent", clean_agent_node)
    workflow.add_node("analysis_agent", analysis_agent_node)
    workflow.add_node("visualization_agent", visualization_agent_node)

    workflow.add_edge(START, "clean_agent")
    workflow.add_edge("clean_agent", "analysis_agent")
    workflow.add_edge("analysis_agent", "visualization_agent")
    workflow.add_edge("visualization_agent", END)

    return workflow.compile()


if __name__ == "__main__":
    print("\n==========================================")
    print("   MULTI-AGENT RETAIL DATA PIPELINE")
    print("==========================================")

    graph = build_graph()

    initial_state = {
        "raw_data_path": "data/retail_data.csv",
        "cleaned_data_path": "data/cleaned_retail_data.csv",
        "analysis_output_path": "data/analysis_results.json",
        "assets_folder": "assets",
        "status": "Pipeline started"
    }

    final_state = graph.invoke(initial_state)

    print("\n==========================================")
    print("   PIPELINE COMPLETED SUCCESSFULLY")
    print("==========================================")

    print(f"\nFinal Status: {final_state['status']}")