"""数据模型定义"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# 用户输入模型
class UserInput(BaseModel):
    """用户输入的消息模型"""
    message: str = Field(..., description="用户消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")
    
# 意图分类结果模型
class IntentClassification(BaseModel):
    """意图分类结果模型"""
    next_node:str = Field(..., description="下一个节点名称")
    inputs:str = Field(..., description="节点输入 (根据节点类型而定)")
    outputs:str = Field(default="", description="节点输出 (根据节点类型而定)")
    is_final:str = Field(default="", description="是否为最终响应 (True/False)")

# 需求分析结果模型
class RequirementAnalysis(BaseModel):
    """需求分析结果模型"""
    mobile_modules: List[Dict[str, str]] = Field(..., description="移动端功能架构，每个元素包含项目模块、功能模块、功能细分、功能描述")
    pc_modules: List[Dict[str, str]] = Field(..., description="PC管理端功能架构，每个元素包含模块、功能要点、描述")
    tech_stack: Dict[str, List[str]] = Field(..., description="技术栈规划，包含前端、后端等分类，每个分类是一个技术选型数组")
    complexity_assessment: List[str] = Field(..., description="复杂度评估，列出关键难点")
    
    def format_to_markdown(self) -> str:
        """将需求分析结果格式化为Markdown格式"""
        markdown = "## 系统模块概览\n\n"
        
        # 移动端功能架构
        markdown += "### 移动端功能架构\n\n"
        markdown += "| 项目模块 | 功能模块 | 功能细分 | 功能描述 |\n"
        markdown += "| -------- | -------- | -------- | -------- |\n"
        
        for module in self.mobile_modules:
            markdown += f"| {module.get('project_module', '')} | {module.get('function_module', '')} | {module.get('function_detail', '')} | {module.get('description', '')} |\n"
        
        markdown += "\n"
        
        # PC管理端功能架构
        markdown += "### PC管理端功能架构\n\n"
        markdown += "| 模块 | 功能要点 | 描述 |\n"
        markdown += "| ---- | -------- | ---- |\n"
        
        for module in self.pc_modules:
            markdown += f"| {module.get('module', '')} | {module.get('features', '')} | {module.get('description', '')} |\n"
        
        markdown += "\n"
        
        # 项目综合分析
        markdown += "## 项目综合分析\n\n"
        
        # 技术栈规划
        markdown += "### 技术栈规划\n\n"
        for stack_type, technologies in self.tech_stack.items():
            markdown += f"**{stack_type}**:\n"
            for tech in technologies:
                markdown += f"- {tech}\n"
            markdown += "\n"
        
        # 复杂度评估
        markdown += "### 复杂度评估\n\n"
        for point in self.complexity_assessment:
            markdown += f"- {point}\n"
        
        return markdown
    
# 成本测算结果模型
class CostEstimation(BaseModel):
    """成本测算结果模型"""
    total_cost: float = Field(..., description="总成本估算（人民币）")
    workday_breakdown: Dict[str, float] = Field(..., description="工作日明细，包含各角色/阶段的工作日分配")
    resource_allocation: Dict[str, Any] = Field(..., description="资源分配建议，包含团队组成和人员分配")
    price_range: Dict[str, float] = Field(..., description="报价区间：最低/建议/最高")
    estimated_duration: Optional[int] = Field(default=None, description="预估项目周期（天）")
    risk_assessment: Optional[str] = Field(default=None, description="风险评估")
    
    def format_to_markdown(self) -> str:
        """将成本测算结果格式化为Markdown格式"""
        markdown = "## 项目成本测算\n\n"
        
        # 基本信息
        markdown += f"**总成本**: ¥{self.total_cost}\n"
        markdown += f"**建议报价**: ¥{self.price_range.get('recommended', 0.0)}\n"
        markdown += f"**报价区间**: ¥{self.price_range.get('min', 0.0)} - ¥{self.price_range.get('max', 0.0)}\n"
        
        if self.estimated_duration:
            markdown += f"**预估周期**: {self.estimated_duration} 天\n"
        
        # 工作日明细
        markdown += "\n### 工作日明细\n\n"
        markdown += "| 角色/阶段 | 工作日 |\n"
        markdown += "| -------- | ------ |\n"
        
        for role, days in self.workday_breakdown.items():
            markdown += f"| {role} | {days} |\n"
        
        # 资源分配建议
        markdown += "\n### 资源分配建议\n\n"
        
        for team, members in self.resource_allocation.items():
            if isinstance(members, dict):
                markdown += f"**{team}**:\n"
                for role, count in members.items():
                    markdown += f"- {role}: {count} 人\n"
            else:
                markdown += f"**{team}**: {members}\n"
        
        # 风险评估
        if self.risk_assessment:
            markdown += "\n### 风险评估\n\n"
            markdown += self.risk_assessment
        
        return markdown

# 知识库查询结果模型
class KnowledgeResult(BaseModel):
    """知识库查询结果模型"""
    answer: str = Field(..., description="查询答案")
    sources: List[str] = Field(..., description="信息来源")
    confidence: float = Field(..., description="置信度")
    related_topics: Optional[List[str]] = Field(default=None, description="相关主题")
    
# 系统响应模型
class SystemResponse(BaseModel):
    """系统响应模型"""
    response_id: str = Field(..., description="响应ID")
    message: str = Field(..., description="响应消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    data: Optional[Dict[str, Any]] = Field(default=None, description="附加数据")
    
# 对话历史记录模型
class ConversationHistory(BaseModel):
    """对话历史记录模型"""
    conversation_id: str = Field(..., description="对话ID")
    messages: List[Dict[str, Any]] = Field(..., description="消息列表")
    start_time: datetime = Field(..., description="对话开始时间")
    end_time: Optional[datetime] = Field(default=None, description="对话结束时间")
    talk: Optional[Dict[str, Any]] = Field(default=None, description="元数据")

# 项目记录模型
class Project(BaseModel):
    """项目记录模型"""
    project_id: str = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    requirements: List[Dict[str, Any]] = Field(..., description="项目需求")
    estimated_cost: float = Field(..., description="预估成本")
    actual_cost: Optional[float] = Field(default=None, description="实际成本")
    start_date: datetime = Field(..., description="开始日期")
    end_date: Optional[datetime] = Field(default=None, description="结束日期")
    status: str = Field(..., description="项目状态")
    team_members: List[str] = Field(..., description="团队成员")
    notes: Optional[str] = Field(default=None, description="备注")