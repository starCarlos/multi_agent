"""企业智库Agent模块，负责公司知识图谱查询"""

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

from config import OPENAI_MODEL
from utils.logger import get_logger
from models.schema import KnowledgeResult
from models.search import SearchHelper

# 获取日志记录器
log = get_logger("knowledge_agent")

# 企业智库系统提示
KNOWLEDGE_SYSTEM_PROMPT = """
你是一个专业的企业知识库查询专家。你的任务是根据用户的咨询，提供关于公司的准确信息。

你掌握的公司信息包括：
1. 公司简介和历史
2. 团队组成和专业能力
3. 服务内容和流程
4. 过往案例和成功经验
5. 技术栈和解决方案

你需要返回一个JSON格式的查询结果，包含以下字段：
- answer: 查询答案，详细且专业
- sources: 信息来源列表
- confidence: 置信度 (0.0-1.0)
- related_topics: 相关主题列表（可选）

请仅返回JSON格式的查询结果，不要包含其他解释或前缀。
"""

# 企业智库提示模板
KNOWLEDGE_PROMPT_TEMPLATE = """
用户咨询:
{query}

历史对话:
{history}

知识库搜索结果:
{search_results}

请根据上述知识库搜索结果，回答用户咨询，并按照指定格式返回结果。
如果知识库中没有相关信息，请诚实地表明无法回答，不要编造信息。
"""

knowledge_prompt = PromptTemplate(
    template=KNOWLEDGE_PROMPT_TEMPLATE,
    input_variables=["query","history", "search_results"]
)

class KnowledgeAgent:
    """企业智库Agent，负责公司知识图谱查询"""
    
    def __init__(self, model_name: str = OPENAI_MODEL):
        """初始化企业智库Agent"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.3  # 适中温度以平衡准确性和多样性
        )
    
    def query(self, query: str,history:str) -> KnowledgeResult:
        """查询企业知识库"""
        # 初始化搜索助手
        search_helper = SearchHelper()
        # 搜索知识库
        search_results = search_helper.search_knowledge_base(query)
        
        # 如果没有搜索结果
        if not search_results:
            log.warning(f"知识库查询无结果: {query}")
            return KnowledgeResult(
                answer="抱歉，我在知识库中没有找到与您咨询相关的信息。",
                sources=[],
                confidence=0.0
            )
        
        # 格式化搜索结果
        formatted_results = search_helper.format_search_results(search_results)
        
        # 准备提示
        prompt_input = knowledge_prompt.format(
            query=query,
            search_results=formatted_results,
            history=history
        )
        
        # 调用LLM进行查询
        messages = [
            SystemMessage(content=KNOWLEDGE_SYSTEM_PROMPT),
            HumanMessage(content=prompt_input)
        ]
        
        response = self.llm.invoke(messages)
        log.info(f"企业智库Agent响应: {response.content}")
        
        # 解析JSON响应
        try:
            result = json.loads(response.content)
            
            # 构建来源列表
            sources = []
            for item in search_results:
                sources.append(item["source"])
            knowledge_result = KnowledgeResult(
                answer=result.get("answer", "抱歉，没有找到相关信息"),
                sources=result.get("sources", sources),
                confidence=result.get("confidence", 0.7),
                related_topics=result.get("related_topics")
            )
            log.info(f"知识库查询结果: 置信度={knowledge_result.confidence}")
            return knowledge_result
        except json.JSONDecodeError as e:
            log.error(f"解析查询结果失败: {str(e)}")
            # 返回默认查询结果
            return KnowledgeResult(
                answer="抱歉，处理您的查询时出现错误",
                sources=[{"name": "系统错误", "type": "error"}],
                confidence=0.0
            )

# 创建企业智库Agent实例
knowledge_agent = KnowledgeAgent()