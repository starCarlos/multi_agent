import os
import hashlib
from typing import List
from langchain_community.vectorstores import Chroma, chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from config import (
    CHROMADB_PATH, EMBEDDING_MODEL, EMBEDDING_BASE_URL,
    SEARCH_MODES, DEFAULT_SEARCH_MODE, DEFAULT_SEARCH_K,
    MMR_DIVERSITY, SIMILARITY_THRESHOLD
)

from utils.document_loader import DocumentLoader
from models.database import get_doc_fingerprints, add_doc_fingerprints, clear_doc_fingerprints

class VectorStoreManager:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=EMBEDDING_BASE_URL,
        )
        self.vector_store = None
        self._load_or_create_store()
        # 初始化向量存储
        
        documents = DocumentLoader().load_documents("docs")
        if documents:
            if self.vector_store is None:
                self.vector_store = Chroma.from_documents(
                    documents,
                    self.embeddings,
                    persist_directory=CHROMADB_PATH
                )
            else:
                self.vector_store.add_documents(documents)

    def _load_or_create_store(self):
        """加载现有的向量存储或创建新的"""
        if os.path.exists(CHROMADB_PATH):
            self.vector_store = Chroma(
                persist_directory = CHROMADB_PATH,
                embedding_function=self.embeddings,
            )
        else:
            self.vector_store = None

    def _calculate_doc_fingerprint(self, doc: Document) -> str:
        """计算文档指纹"""
        # 使用文档内容和元数据计算指纹
        content = doc.page_content
        metadata_str = str(sorted(doc.metadata.items()))
        fingerprint_str = f"{content}{metadata_str}"
        return hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()

    def _filter_new_documents(self, documents: List[Document]) -> List[Document]:
        """过滤出新文档"""
        # 获取现有指纹
        existing_fingerprints = get_doc_fingerprints()
        
        # 过滤并收集新文档
        new_docs = []
        new_fingerprints = []
        new_metadata = []
        
        for doc in documents:
            fingerprint = self._calculate_doc_fingerprint(doc)
            if fingerprint not in existing_fingerprints:
                new_docs.append(doc)
                new_fingerprints.append(fingerprint)
                new_metadata.append(doc.metadata)
        
        # 批量添加新指纹
        if new_fingerprints:
            add_doc_fingerprints(new_fingerprints, new_metadata)
        
        return new_docs

    def add_documents(self, documents: List[Document]):
        """添加文档到向量存储"""
        if not documents:
            return

        # 过滤出新文档
        new_documents = self._filter_new_documents(documents)
        
        if not new_documents:
            print("没有新的文档需要添加")
            return

        print(f"添加 {len(new_documents)} 个新文档（共 {len(documents)} 个文档）")
        
        if self.vector_store is None:
            self.vector_store = Chroma().from_documents(
                new_documents,
                self.embeddings,
                persist_directory=CHROMADB_PATH
            )
        else:
            self.vector_store.add_documents(new_documents)
        
    def search(self, 
               query: str, 
               mode: str = DEFAULT_SEARCH_MODE, 
               k: int = DEFAULT_SEARCH_K, 
               **kwargs) -> List[Document]:
        """执行搜索，支持多种搜索模式
        
        参数:
            query: 查询文本
            mode: 搜索模式，可选值: similarity, mmr, similarity_score_threshold
            k: 返回的文档数量
            **kwargs: 其他搜索参数
                - diversity: MMR多样性参数 (0-1)，仅在mode='mmr'时有效
                - score_threshold: 相似度阈值，仅在mode='similarity_score_threshold'时有效
        
        返回:
            List[Document]: 搜索结果文档列表
        """
        if self.vector_store is None:
            return []
        
        if mode not in SEARCH_MODES:
            print(f"未知的搜索模式: {mode}，使用默认模式: {DEFAULT_SEARCH_MODE}")
            mode = DEFAULT_SEARCH_MODE
        
        try:
            if mode == "similarity":
                # 标准相似度搜索
                return self.vector_store.similarity_search(query, k=k)
            
            elif mode == "mmr":
                # 最大边际相关性搜索 (多样性搜索)
                diversity = kwargs.get("diversity", MMR_DIVERSITY)
                return self.vector_store.max_marginal_relevance_search(
                    query, k=k, fetch_k=k*2, lambda_mult=diversity
                )
            
            elif mode == "similarity_score_threshold":
                # 相似度阈值搜索
                score_threshold = kwargs.get("score_threshold", SIMILARITY_THRESHOLD)
                docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k*2)
                
                # 过滤低于阈值的文档
                filtered_results = [
                    doc for doc, score in docs_and_scores 
                    if score >= score_threshold
                ]
                
                # 限制返回数量
                return filtered_results[:k]
            
            else:
                # 默认使用标准相似度搜索
                return self.vector_store.similarity_search(query, k=k)
                
        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            return []
    
    def similarity_search(self, query: str, k: int = DEFAULT_SEARCH_K) -> List[Document]:
        """执行相似性搜索 (兼容旧接口)"""
        return self.search(query, mode="similarity", k=k)
    
    def mmr_search(self, query: str, k: int = DEFAULT_SEARCH_K, diversity: float = MMR_DIVERSITY) -> List[Document]:
        """执行MMR搜索 (最大边际相关性)"""
        return self.search(query, mode="mmr", k=k, diversity=diversity)
    
    def threshold_search(self, query: str, k: int = DEFAULT_SEARCH_K, score_threshold: float = SIMILARITY_THRESHOLD) -> List[Document]:
        """执行相似度阈值搜索"""
        return self.search(query, mode="similarity_score_threshold", k=k, score_threshold=score_threshold)

    def clear(self):
        """清除向量存储和文档指纹"""
        if os.path.exists(CHROMADB_PATH):
            import shutil
            shutil.rmtree(os.path.dirname(CHROMADB_PATH))
        self.vector_store = None
        clear_doc_fingerprints()

if __name__ == "__main__":
    # 测试向量化后存储
    vector_store = VectorStoreManager()
    documents = DocumentLoader().load_documents("docs")
    vector_store.add_documents(documents)
    
    # 测试不同的搜索模式
    query = "你们是哪个公司"
    
    print("\n=== 标准相似度搜索 ===")
    results1 = vector_store.search(query, mode="similarity", k=2)
    for doc in results1:
        print(f"- {doc.page_content[:100]}...")
    
    print("\n=== MMR多样性搜索 ===")
    results2 = vector_store.search(query, mode="mmr", k=2, diversity=0.7)
    for doc in results2:
        print(f"- {doc.page_content[:100]}...")
    
    print("\n=== 相似度阈值搜索 ===")
    results3 = vector_store.search(query, mode="similarity_score_threshold", k=2, score_threshold=0.6)
    for doc in results3:
        print(f"- {doc.page_content[:100]}...")

