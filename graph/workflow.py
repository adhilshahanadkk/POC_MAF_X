from typing import TypedDict
from typing import TypedDict, List
from io import BytesIO
from langgraph.graph import END, StateGraph
from agents.rag_agent_node import rag_agent_node

from agents.supervisor_agent import supervisor_node
from agents.sql_agent import sql_agent_node
from agents.mssql_agent import mssql_agent_node
from agents.report_agent import report_agent_node
from agents.charts_agent import graph_agent_node

from agents.planner_agent import planner_agent_node
from agents.multi_agent_executor import execute_agents_node
from agents.combiner_agent import combiner_node

from agents.charts_agent import graph_agent_node  


class AgentState(TypedDict, total=False):
    query: str
    route: str
    final_output: str
    chat_history: list
    last_agent: str
    rag_agent: object
    report_text: str
    plan: list
    multi_results: list
    has_uploaded_docs: bool
    uploaded_doc_names: list
    full_tasks: List[dict]
    context_data: list        # ← FIXES 'list has no attribute strip' error
    chart_buffer: BytesIO 
    should_visualize: bool      # ← matplotlib PNG buffer from graph_agent


def check_if_report_needed(state):
    query = state.get("query", "").lower()
    if "report" in query or "generate a report" in query:
        return "report_agent"
    return "end"

    
def should_generate_chart(state):
    """
    Determines if chart agent should be triggered based on:
    1. Route (report queries skip charts)
    2. should_visualize flag from planner/combiner
    """
    route = state.get("route", "")
    should_visualize = state.get("should_visualize", False)
    
    if route == "report_agent":
        return "end"  # Reports don't need chart agent before report generation
    
    if should_visualize:
        return "graph_agent"
    else:
        return "end"   



def router(state):
    return state["route"]


def build_graph():

    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("mysql_agent", sql_agent_node)
    workflow.add_node("mssql_agent", mssql_agent_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("report_agent", report_agent_node)
    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("executor", execute_agents_node)
    workflow.add_node("combiner", combiner_node)
    workflow.add_node("graph_agent", graph_agent_node)



    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "mysql_agent": "mysql_agent",
            "mssql_agent": "mssql_agent",
            "rag_agent":"rag_agent",
            "report_agent": "report_agent",
            "multi_agent": "planner",

        },
    )
    # ---------- SINGLE-AGENT PATH ----------
    # mysql and mssql route through conditional edge to check visualization flag
    workflow.add_conditional_edges(
        "mysql_agent",
        should_generate_chart,
        {
            "graph_agent": "graph_agent",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "mssql_agent",
        should_generate_chart,
        {
            "graph_agent": "graph_agent",
            "end": END
        }
    )
    workflow.add_edge("rag_agent", END)       # RAG = text only, no chart needed
    workflow.add_edge("report_agent", END)

    # ---------- MULTI-AGENT PATH ----------
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "combiner")
    workflow.add_conditional_edges(
        "combiner",
        should_generate_chart,
        {
            "graph_agent": "graph_agent",
            "end": END
        }
    )

    # ---------- GRAPH AGENT → END or REPORT ----------
    workflow.add_conditional_edges(
        "graph_agent",
        check_if_report_needed,
        {
            "report_agent": "report_agent",
            "end": END
        }
    )

    return workflow.compile()
