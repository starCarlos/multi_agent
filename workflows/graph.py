"""工作流图定义模块，负责构建和执行LangGraph工作流"""

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from workflows.router import (
    main_node,
    route_to_tool,
    company_node,
    requirement_node,
    estimation_node,
    State
)

# 构建工作流图
def build_enterprise_bot_graph() -> CompiledStateGraph:
    workflow = StateGraph(State)
    
    # 添加节点
    workflow.add_node("main", main_node)
    workflow.add_node("company", company_node)
    workflow.add_node("requirement", requirement_node)
    workflow.add_node("estimation", estimation_node)
    
    # 设置入口节点
    workflow.set_entry_point("main")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "main",
        route_to_tool,
        {
            "company": "company",
            "requirement": "requirement",
            "estimation": "estimation",
            END: END
        }
    )
    
    # 工具节点返回主节点
    workflow.add_edge("company", "main")
    workflow.add_edge("requirement", "main")
    workflow.add_edge("estimation", "main")
    
    return workflow.compile()
