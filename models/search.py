from typing import Dict, List, Any
from models.vector_store import VectorStoreManager

class SearchHelper:
    """搜索助手，负责与向量数据库交互"""

    def __init__(self):
        """初始化搜索助手"""
        # 初始化向量存储管理器
        self.vector_store = VectorStoreManager()


    def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        # 使用向量数据库搜索相关知识
        search_results = self.vector_store.search(
            query=query,
            mode="mmr",  # 使用MMR搜索以获得更多样化的结果
            k=limit
        )
        
        # 将搜索结果转换为标准格式
        results = []
        for i, doc in enumerate(search_results):
            # 提取文档内容和元数据
            content = doc.page_content
            metadata = doc.metadata
            
            # 创建结果项
            result_item = {
                "id": i + 1,
                "content": content,
                "source": metadata.get("source", "企业知识库"),
                "relevance": 1.0 - (i * 0.1)  # 简单的相关性评分，第一个结果最高
            }
            
            results.append(result_item)
        
        return results
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化搜索结果为文本"""
        if not results:
            return "未找到相关知识"
        
        formatted_text = ""
        for result in results:
            formatted_text += f"[{result['id']}] 来源: {result['source']}\n"
            formatted_text += f"相关度: {result['relevance']:.2f}\n"
            formatted_text += f"内容: {result['content']}\n\n"
        
        return formatted_text