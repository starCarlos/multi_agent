from typing import Dict, List, Any, TypedDict, Optional
from langgraph.graph import END
from agents.entry_point import EntryPointAgent
from config import OPENAI_MODEL
from agents import (
    analyzer,
    estimator,
    knowledge,
)
from utils.logger import get_logger
from models.search import SearchHelper

# 获取日志记录器
log = get_logger("router")
# 定义状态类型
class State(TypedDict):
    message: str                 # 用户消息
    conversation_id: str        # 对话ID
    history: List[Dict[str, Any]] # 对话历史
    current_tool: Optional[str] # 当前使用的工具s
    last_input: str           # 上一个节点的输入
    tools_response: List[Dict] # 工具响应
    response: Optional[str]      # 系统响应
    is_final: bool              # 是否为最终响应
    data: Optional[Dict[str, Any]]  # 附加数据

# 工具列表
tools = []
# 主节点逻辑
def main_node(state: State) -> State:
    entry_pinot_agent = EntryPointAgent(OPENAI_MODEL)
    result = entry_pinot_agent.classify(state["message"],state["history"],state["tools_response"])
    if result["is_final"] in [True, "True", 1, "true", "TRUE", "1"]:
        state["response"] = result["output"]
        state["current_tool"] = END  # 明确设置为 NONE
        state["is_final"] = True
    else:
        state["last_input"] = result["inputs"]
        state["current_tool"] = result["next_node"]
    log.info(f"主路由Agent返回结果: {result}")
    return state

# 路由函数
def route_to_tool(state: State) -> str:
    # 确保总是返回一个有效的 ToolType 值
    return state.get("current_tool") or END

def requirement_node(state: State) -> State:

    search_helper = SearchHelper()
    # 搜索知识库
    search_results = search_helper.search_knowledge_base(state["last_input"])
    
    formatted_results = ""
    # 如果没有搜索结果
    if not search_results:
        log.warning(f"知识库查询无结果: {state["last_input"]}")
    else:
        # 格式化搜索结果
        formatted_results = search_helper.format_search_results(search_results)
        # 更新状态
        state["data"] = state.get("data", {})
        # 确保data字段存在且是字典类型
        if "data" not in state or not isinstance(state["data"], dict):
            state["data"] = {}
        #尝试解析JSON响应
        state["data"]["knowledge_result"] = formatted_results

    # 调用需求分析Agent进行需求拆解
    analysis = analyzer.analyzer_agent.analyze(state["message"], state["history"],formatted_results)

    # markdown_response = analysis.format_to_markdown()
    
    state["tools_response"].append({"node":"requirement","result": analysis})

    return state

def estimation_node(state: State) -> State:
    """处理报价测算意图"""
    # 更新状态
    formatted_results = ""
    state["data"] = state.get("data", {})
    # 确保data字段存在且是字典类型
    if "data" not in state or not isinstance(state["data"], dict):
        state["data"] = {}
        state["data"]["knowledge_result"] = state["data"].get("knowledge_result", {})
        #尝试解析JSON响应
        if "knowledge_result" not in state["data"] or not isinstance(state["data"]["knowledge_result"], str):
            search_helper = SearchHelper()
            # 搜索知识库
            search_results = search_helper.search_knowledge_base(state["last_input"])
            
            # 如果没有搜索结果
            if not search_results:
                log.warning(f"知识库查询无结果: {state["last_input"]}")
            else:
                # 格式化搜索结果
                formatted_results = search_helper.format_search_results(search_results)
        else:
            formatted_results = state["data"]["knowledge_result"]
    else:
        search_helper = SearchHelper()
        # 搜索知识库
        search_results = search_helper.search_knowledge_base(state["last_input"])
        
        # 如果没有搜索结果
        if not search_results:
            log.warning(f"知识库查询无结果: {state["last_input"]}")
        else:
            # 格式化搜索结果
            formatted_results = search_helper.format_search_results(search_results)

    message = state["message"]
    tools_response = state["tools_response"]
    for tool in tools_response:
        if tool["node"] == "requirement":
            message = tool["result"]
            break

    # 调用成本测算Agent进行报价计算
    estimation = estimator.estimator_agent.estimate(message, state["history"],formatted_results)
    
    state["tools_response"].append({"node":"estimation","result": estimation})

    return state

def company_node(state: State) -> State:
     # 调用企业智库Agent进行知识检索
    response = ""
    knowledge_result = knowledge.knowledge_agent.query(state["message"], state["history"])
    # 更新状态
    state["data"] = state.get("data", {})
    if "data" not in state or not isinstance(state["data"], dict):
        state["data"] = {}
    state["data"]["knowledge_result"] = knowledge_result.dict()

    # 如果有信息来源，添加到响应中
    if knowledge_result.sources and len(knowledge_result.sources) > 0:
        response += "\n\n信息来源:"
        for source in knowledge_result.sources[:3]:  # 最多显示3个来源
            response += f"\n- {source}"
    
    # 如果有相关主题，添加到响应中
    if knowledge_result.related_topics and len(knowledge_result.related_topics) > 0:
        response += "\n\n您可能还想了解:"
        for topic in knowledge_result.related_topics[:3]:  # 最多显示3个相关主题
            response += f"\n- {topic}"
    
    state["tools_response"].append({"node":"company","result": response})

    return state
