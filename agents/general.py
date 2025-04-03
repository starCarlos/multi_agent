"""通用对话Agent模块，负责处理一般性对话请求"""

from typing import Dict, List, Any
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from config import OPENAI_MODEL
from utils.logger import get_logger

# 获取日志记录器
log = get_logger("general_agent")

# 通用对话系统提示
GENERAL_SYSTEM_PROMPT = """
你是一个专业的企业智能助手，代表智能科技有限公司与用户进行对话。

你应该：
1. 保持专业、友好的语气
2. 提供有帮助的回答
3. 在不确定的情况下，引导用户提供更多信息
4. 避免过度承诺或提供虚假信息

你可以讨论公司的服务、项目流程、技术能力等话题，但应避免讨论具体的价格（除非是一般性的价格范围）或承诺具体的交付日期。

如果用户询问的内容超出你的知识范围，请礼貌地表示你需要转接给相关专家，并建议用户提供联系方式以便后续跟进。
"""

# 通用对话提示模板
GENERAL_PROMPT_TEMPLATE = """
用户消息: {message}

历史对话上下文:
{history}

请根据上述信息，生成一个专业、有帮助的回复。
"""

general_prompt = PromptTemplate(
    template=GENERAL_PROMPT_TEMPLATE,
    input_variables=["message", "history"]
)

class GeneralAgent:
    """通用对话Agent，负责处理一般性对话请求"""
    
    def __init__(self, model_name: str = OPENAI_MODEL):
        """初始化通用对话Agent"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.7  # 较高温度以获得更自然的对话
        )
        log.info(f"通用对话Agent初始化完成，使用模型: {model_name}")
    
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
    
    def respond(self, message: str, history: List[Dict[str, Any]]) -> str:
        """生成对话响应"""
        if history is None:
            history = []
        
        # 格式化历史对话
        formatted_history = self.format_history(history)
        
        # 准备提示
        prompt_input = general_prompt.format(
            message=message,
            history=formatted_history
        )
        
        # 调用LLM生成响应
        messages = [
            SystemMessage(content=GENERAL_SYSTEM_PROMPT),
            HumanMessage(content=prompt_input)
        ]
        
        response = self.llm.invoke(messages)
        log.debug(f"通用对话Agent响应: {response.content[:100]}...")
        
        # 确保返回字符串类型
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # 如果是列表，将所有内容连接成字符串
            return ' '.join(str(item) for item in response.content)
        else:
            # 其他情况转换为字符串
            return str(response.content)

# 创建通用对话Agent实例
general_agent = GeneralAgent()