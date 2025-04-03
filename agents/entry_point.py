"""入口模块，负责实时对话"""

import re
from typing import Dict, List, Any
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

from config import OPENAI_MODEL
from utils.logger import get_logger
from models.schema import IntentClassification

# 获取日志记录器
log = get_logger("entry_point")

# 意图主路由系统提示
ENTRYPOINT_SYSTEM_PROMPT = """
你是智能客服，负责处理用户提出的各种问题。你的工作逻辑如下：
1. 当用户提出通用性问题时，请直接根据已有知识回答问题。
2. 当用户的问题不属于通用问题时，请根据用户的问题类型，调用相应的节点进行处理。
3. 在调用各个节点时，请确保传递用户问题的关键信息，并严格按照调用顺序汇总各节点返回的结果后再给出最终回答。
4. 每完成一个节点调用后，请仔细分析当前已完成的步骤和工具返回的结果，确定下一步应调用的节点，确保回答内容全面且准确。
5. 已经调用过的节点，请勿重复调用。

节点列表：
1. 需求相关 (requirement): 用户询问或描述项目需求、功能规格、技术实现等
2. 报价测算 (estimation): 用户询问项目报价、成本、工期、资源分配等
3. 公司咨询 (company): 用户询问公司信息、团队能力、过往案例、服务流程等
5. 结束 (__end__): 结束节点，当所有节点都调用完毕后，总结归纳，进入结束节点，结束对话。

你需要返回一个JSON格式的结果，包含以下字段:
- next_node: 下一个节点名称 (requirement/estimation/company/general/__end__)
- inputs: 节点输入 (提取到的关键信息字符串)
- output: 节点输出 (节点返回的结果字符串)
- is_final: 是否为最终响应 (True/False)

示例结果：
{
    "next_node": "estimation",
    "inputs": "用户的问题",
    "output": "节点返回的结果",
    "is_final": "False" 
}
通用问题示例结果：
{
    "next_node": "__end__",
    "inputs": "用户的问题",
    "output": "回答",
    "is_final": "True"
}

请仅返回JSON格式的主路由结果，不要包含其他解释或前缀。
"""

# 意图主路由提示模板
ENTRYPOINT_PROMPT_TEMPLATE = """
用户消息: {message}

历史对话上下文:
{history}

已经调用过的节点:
{used_tools}
"""

entry_point_prompt = PromptTemplate(
    template=ENTRYPOINT_PROMPT_TEMPLATE,
    input_variables=["message", "history", "used_tools"]
)

class EntryPointAgent:
    """主路由Agent，负责实时对话意图识别"""
    
    def __init__(self, model_name: str = OPENAI_MODEL):
        """初始化主路由Agent"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1  # 低温度以获得更确定的主路由结果
        )
        log.info(f"主路由Agent初始化完成，使用模型: {model_name}")
    
    def format_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "无历史对话"
        
        formatted_history = ""
        for msg in history:
            role = "用户" if msg.get("role") == "user" else "系统"
            content = msg.get("content", "")
            formatted_history += f"{role}- {content}\n"
        
        return formatted_history
    
    def classify(self, message: str, history: List[Dict[str, Any]],tools_response: List[Dict]) -> Dict[str, Any]:
        """主路由用户消息意图"""
        if history is None:
            history = []
        
        # 格式化历史对话
        formatted_history = self.format_history(history)
        log.info(f"主路由Agent开始主路由，历史对话长度: {len(history)}")
        log.info(f"主路由Agent开始主路由，用户消息: {message[:50]}...")
        # 准备提示
        prompt_input = entry_point_prompt.format(
            message=message,
            history=formatted_history,
            used_tools=json.dumps(tools_response, ensure_ascii=False)
        )
        # 调用LLM进行主路由
        messages = [
            SystemMessage(content=ENTRYPOINT_SYSTEM_PROMPT),
            HumanMessage(content=prompt_input)
        ]
        response = self.llm.invoke(messages)

        try:
            response_dict = json.loads(response.content)
            return response_dict
        except json.JSONDecodeError:
            log.error(f"主Agent响应无法解析为JSON: {response.content}")
            return {}

# 创建主路由Agent实例
entry_point_agent = EntryPointAgent()