"""需求分析Agent模块，负责文档解析与需求拆解"""

from re import search
from typing import Dict, List, Any, Optional
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

from config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL
from models.schema import RequirementAnalysis
from utils.logger import get_logger
from models.search import SearchHelper

# 获取日志记录器
log = get_logger("analyzer_agent")

# 需求分析提示模板 (合并了系统提示和用户提示)
ANALYZER_PROMPT_TEMPLATE = """
请根据以下要求进行项目需求分析，并严格按照指定JSON格式输出：

你需要输出markdown格式，示例如下：
# 社区信息公示平台项目需求文档

## 系统模块概览
### 移动端功能架构
| 项目模块 | 功能模块         | 功能细分                  | 功能描述                                                                 |
|----------|------------------|---------------------------|--------------------------------------------------------------------------|
| **首页** | 社区公共收益     | 多维统计                  | 总金额+今日/本月/本年收支，支持时间筛选                                  |
|          |                  | 账单详情                  | 含发票查看、点赞评论、时空搜索功能                                       |
|          | 维修基金         | 动态报表                  | 管理端录入+自动计算，支持穿透查询                                        |
|          | 社区公告         | 多媒体展示                | 支持图文/视频滚动，点击查看详情                                          |
| **邻里** | 信息交互         | 分类筛选+发布             | 支持位置/热度/评论筛选，用户可发布带价格的社区服务                       |
| **我的** | 个人中心         | 资料管理+账号安全         | 含注销账号、隐私设置、多平台绑定                                         |

### PC管理端功能架构
| 模块       | 功能要点                     | 描述                                   |
|------------|------------------------------|----------------------------------------|
| 用户管理   | 多账号体系                   | 支持角色权限分配                       |
| 数据管理   | 收支/基金自动化计算           | 实时统计前端展示数据                   |
| 内容运营   | 轮播图/公告/活动管理          | 支持多媒体内容编辑                     |
| 公共服务   | 15类机构信息维护              | 含物业/派出所/医院等联系方式           |

---

## 项目综合分析
### 技术栈规划
| 层级       | 技术选型                                                                 |
|------------|--------------------------------------------------------------------------|
| **前端**   | 小程序(Uniapp)+PC管理端(Vue3+Element Plus)                               |
| **后端**   | Spring Boot+MyBatis Plus                                                 |
| **数据库** | MySQL(业务数据)+Redis(缓存)+MinIO(文件存储)                              |
| **运维**   | Nginx+Docker+K8s                                                         |

### 复杂度评估
- **高交互场景**：社区账单的时空搜索、多维度统计图表
- **安全要求**：微信授权+手机号绑定双重验证
- **数据一致性**：公共收益与维修基金的实时计算
- **扩展性设计**：便民服务模块支持动态配置

用户需求描述:
{requirement}

历史对话记录:
{history}

知识库参考信息:
{search_results}

请分析上述需求，并按照指定markdown格式返回拆解结果。
"""

analyzer_prompt = PromptTemplate(
    template=ANALYZER_PROMPT_TEMPLATE,
    input_variables=["requirement","history", "search_results"]
)

class AnalyzerAgent:
    """需求分析Agent，负责文档解析与需求拆解"""
    
    def __init__(self, model_name: str = OPENAI_MODEL):
        """初始化需求分析Agent"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.2  # 低温度以获得更确定的分析结果
        )
        log.info(f"需求分析Agent初始化完成，使用模型: {model_name}")
    
    def analyze(self, requirement: str, history: str,formatted_results:str) -> str:
        """分析需求"""
        
        # 准备提示
        prompt_input = analyzer_prompt.format(requirement=requirement, history=history, search_results=formatted_results)
        
        
        # 调用LLM进行分析 (使用单一消息而不是系统消息+用户消息)
        messages = [
            HumanMessage(content=prompt_input)
        ]
        # log.info(f"发送到需求分析Agent的消息: {prompt_input[:100]}...")
        # llm绑定输出结构
        response = self.llm.invoke(messages)
        log.debug(f"需求分析Agent响应: {response}")
        
        return response.content
    
    
# 创建需求分析Agent实例
analyzer_agent = AnalyzerAgent()