"""对话记忆管理模块，负责管理对话历史和上下文"""

from typing import Dict, List, Any, Optional
import time
from utils.logger import get_logger
from langchain.memory import ConversationSummaryMemory
from langchain.llms.base import BaseLLM
from langchain_openai import ChatOpenAI
from config import OPENAI_MODEL
# 获取日志记录器
log = get_logger("memory")

class ConversationMemory:
    """对话记忆管理器，负责存储和检索对话历史"""
    
    def __init__(self, max_history: int = 10, ttl: int = 3600, llm: Optional[BaseLLM] = None):
        """
        初始化对话记忆管理器
        
        参数:
            max_history: 每个对话保留的最大历史消息数量
            ttl: 记忆的生存时间（秒），超过此时间的记忆将被清理
            llm: 用于总结对话的语言模型，如果为None则使用默认模型
        """
        self.memories = {}  # 存储所有对话的记忆对象
        self.raw_histories = {}  # 存储原始对话历史
        self.timestamps = {}  # 存储每个对话的最后访问时间
        self.max_history = max_history
        self.ttl = ttl
        self.llm = llm or ChatOpenAI(model=OPENAI_MODEL,temperature=0)
        log.info(f"对话记忆管理器初始化完成，最大历史记录数: {max_history}, TTL: {ttl}秒")
    
    def _create_memory(self, conversation_id: str) -> ConversationSummaryMemory:
        """为指定对话创建一个新的记忆对象"""
        memory = ConversationSummaryMemory(llm=self.llm)
        self.memories[conversation_id] = memory
        self.raw_histories[conversation_id] = []
        return memory
    
    def get_memory(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取指定对话的记忆"""
        # 更新访问时间
        self.timestamps[conversation_id] = time.time()
        
        # 返回原始历史记录（如果存在）
        return self.raw_histories.get(conversation_id, [])
    
    def get_memory_variables(self, conversation_id: str) -> Dict[str, Any]:
        """获取指定对话的记忆变量，包括总结"""
        # 更新访问时间
        self.timestamps[conversation_id] = time.time()
        
        # 如果记忆对象不存在，创建一个新的
        if conversation_id not in self.memories:
            self._create_memory(conversation_id)
        
        # 返回记忆变量
        return self.memories[conversation_id].load_memory_variables({})
    
    def initialize_memory(self, conversation_id: str, history: List[Dict[str, Any]]) -> None:
        """使用现有历史初始化对话记忆"""
        if conversation_id not in self.memories:
            # 创建新的记忆对象
            memory = self._create_memory(conversation_id)
            
            # 限制历史记录数量
            limited_history = history[-self.max_history:] if history else []
            self.raw_histories[conversation_id] = limited_history
            
            # 将历史记录添加到记忆中
            for i in range(0, len(limited_history), 2):
                if i+1 < len(limited_history):
                    user_message = limited_history[i].get("content", "")
                    ai_message = limited_history[i+1].get("content", "")
                    memory.save_context({"input": user_message}, {"output": ai_message})
            
            self.timestamps[conversation_id] = time.time()
            log.info(f"初始化对话记忆: {conversation_id}, 历史记录数: {len(limited_history)}")
    
    def add_exchange(self, conversation_id: str, user_message: Dict[str, Any], system_message: Dict[str, Any]) -> None:
        """添加一轮对话交流到记忆中"""
        # 如果记忆对象不存在，创建一个新的
        if conversation_id not in self.memories:
            self._create_memory(conversation_id)
        
        # 添加用户消息和系统响应到原始历史记录
        if conversation_id not in self.raw_histories:
            self.raw_histories[conversation_id] = []
        
        self.raw_histories[conversation_id].append(user_message)
        self.raw_histories[conversation_id].append(system_message)
        
        # 限制原始历史记录数量
        if len(self.raw_histories[conversation_id]) > self.max_history:
            self.raw_histories[conversation_id] = self.raw_histories[conversation_id][-self.max_history:]
        
        # 添加到记忆总结中
        user_content = user_message.get("content", "")
        system_content = system_message.get("content", "")
        self.memories[conversation_id].save_context({"input": user_content}, {"output": system_content})
        
        # 更新访问时间
        self.timestamps[conversation_id] = time.time()
        log.debug(f"添加对话交流到记忆: {conversation_id}, 当前历史记录数: {len(self.raw_histories[conversation_id])}")
    
    def clear_memory(self, conversation_id: str) -> None:
        """清除指定对话的记忆"""
        if conversation_id in self.memories:
            del self.memories[conversation_id]
        if conversation_id in self.raw_histories:
            del self.raw_histories[conversation_id]
        if conversation_id in self.timestamps:
            del self.timestamps[conversation_id]
        log.info(f"清除对话记忆: {conversation_id}")
    
    def cleanup_old_memories(self) -> int:
        """清理过期的记忆，返回清理的记忆数量"""
        current_time = time.time()
        expired_ids = [
            conv_id for conv_id, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        # 清除过期记忆
        for conv_id in expired_ids:
            self.clear_memory(conv_id)
        
        if expired_ids:
            log.info(f"清理过期记忆，共清理 {len(expired_ids)} 个对话")
        
        return len(expired_ids)
