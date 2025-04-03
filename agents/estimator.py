"""成本测算Agent模块，负责工时模型和报价矩阵计算"""

from typing import List
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

from config import OPENAI_MODEL
from utils.logger import get_logger
from models.vector_store import VectorStoreManager

# 获取日志记录器
log = get_logger("estimator_agent")
# todo 可以加一个根据需求提取对应功能点，然后查询对应功能点的报价矩阵，然后根据需求计算成本,还有其他问题，比如去掉某某功能多少钱，商城一般多少钱
# 成本测算系统提示
ESTIMATOR_SYSTEM_PROMPT = """
你是一个专业的项目成本测算专家。你的任务是根据项目需求分析结果，计算项目的成本和报价。

你需要：
1. 计算项目总成本
2. 提供工作日明细（设计/开发/测试/部署等）
3. 建议资源分配方案
4. 提供合理的报价区间（最低/建议/最高）

"""

# 成本测算提示模板
ESTIMATOR_PROMPT_TEMPLATE = """
用户消息:
{message}

消息历史:
{history}

知识库查询结果:
{knowledge_results}

请根据上述信息，计算项目成本和报价，并按照指定格式返回测算结果。
"""

estimator_prompt = PromptTemplate(
    template=ESTIMATOR_PROMPT_TEMPLATE,
    input_variables=["message", "history", "knowledge_results"]
)

class EstimatorAgent:
    """成本测算Agent，负责工时模型和报价矩阵计算"""
    
    def __init__(self, model_name: str = OPENAI_MODEL):
        """初始化成本测算Agent"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.2,  # 低温度以获得更确定的测算结果
            streaming=True
        )
        log.info(f"成本测算Agent初始化完成，使用模型: {model_name}")
    
    def estimate(self, requirement: str, history: str,formatted_results:str) -> str:
        """计算项目成本和报价"""

        # 准备提示
        prompt_input = estimator_prompt.format(
            message=requirement,
            history=history,
            knowledge_results=formatted_results
        )
        
        # 调用LLM进行测算
        messages = [
            SystemMessage(content=ESTIMATOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt_input)
        ]
        
        response = self.llm.invoke(messages)
        log.debug(f"成本测算Agent响应: {response}")
        
        return response.content

# 创建成本测算Agent实例
estimator_agent = EstimatorAgent()