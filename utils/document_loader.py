import os
from typing import List, Union
import chardet
import json
import pandas as pd
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    CSVLoader,
    UnstructuredExcelLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import SUPPORTED_EXTENSIONS, CHUNK_SIZE, CHUNK_OVERLAP

from utils.excel_read import parse_excel_to_list

class DocumentLoader:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
        
        # 初始化加载器映射
        self.loader_map = {
            '.txt': self._load_text,
            '.docx': self._load_docx,
            '.md': self._load_markdown,
            '.csv': self._load_csv,
            '.xlsx': self._load_excel,
            '.xls': self._load_excel
        }

    def _detect_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'

    def _load_text(self, file_path: str) -> List[Document]:
        """加载文本文件"""
        encoding = self._detect_encoding(file_path)
        try:
            loader = TextLoader(file_path, encoding=encoding)
            return loader.load()
        except UnicodeDecodeError:
            # 如果检测到的编码不正确，尝试常用编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']:
                try:
                    loader = TextLoader(file_path, encoding=encoding)
                    return loader.load()
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"无法识别文件编码: {file_path}")

    def _load_docx(self, file_path: str) -> List[Document]:
        """加载Word文档"""
        loader = UnstructuredWordDocumentLoader(file_path)
        return loader.load()

    def _load_markdown(self, file_path: str) -> List[Document]:
        """加载Markdown文件"""
        encoding = self._detect_encoding(file_path)
        loader = UnstructuredMarkdownLoader(file_path, encoding=encoding)
        return loader.load()

    def _load_csv(self, file_path: str) -> List[Document]:
        """加载CSV文件"""
        encoding = self._detect_encoding(file_path)
        try:
            # 首先尝试使用pandas读取以处理更多格式
            df = pd.read_csv(file_path, encoding=encoding)
            # 将DataFrame转换为文档列表
            documents = []
            for index, row in df.iterrows():
                # 将每行转换为字符串
                content = "\n".join([f"{col}: {val}" for col, val in row.items()])
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": file_path,
                        "row": index,
                        "encoding": encoding
                    }
                )
                documents.append(doc)
            return documents
        except Exception as e:
            print(f"Pandas读取失败，尝试使用CSVLoader: {str(e)}")
            # 如果pandas读取失败，使用CSVLoader
            loader = CSVLoader(file_path, encoding=encoding)
            return loader.load()

    def _load_excel(self, file_path: str) -> List[Document]:
        """加载Excel文件"""
        page_content = parse_excel_to_list(file_path)
        documents = []
        documents.append(Document(page_content=page_content, metadata={"source": file_path}))
        return documents

    def load_single_document(self, file_path: str) -> List[Document]:
        """加载单个文档并分块"""
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        loader_func = self.loader_map.get(ext.lower())
        if not loader_func:
            raise ValueError(f"没有找到对应的加载器: {ext}")
        
        try:
            documents = loader_func(file_path)
            # 添加文件信息到metadata
            res_documents = []
            for doc in documents:
                doc.metadata.update({
                    "file_path": file_path,
                    "file_type": ext,
                    "file_name": os.path.basename(file_path)
                })
                # 分块处理文档
                split_docs = self.text_splitter.split_documents([doc])
                
                # 为每个分块添加块索引信息
                for i, doc in enumerate(split_docs):
                    doc.metadata.update({
                        "chunk_index": i,
                        "total_chunks": len(split_docs)
                    })
                res_documents.extend(split_docs)
            return res_documents
        except Exception as e:
            print(f"加载文件失败 {file_path}: {str(e)}")
            return []

    def load_documents(self, path: Union[str, List[str]]) -> List[Document]:
        """加载单个文件或目录下的所有支持的文档"""
        all_documents = []
        
        if isinstance(path, str):
            if os.path.isfile(path):
                return self.load_single_document(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                            file_path = os.path.join(root, file)
                            try:
                                docs = self.load_single_document(file_path)
                                all_documents.extend(docs)
                            except Exception as e:
                                print(f"Error loading {file_path}: {str(e)}")
        elif isinstance(path, list):
            for p in path:
                docs = self.load_documents(p)
                all_documents.extend(docs)
                
        return all_documents

if __name__ == "__main__":
    # 测试代码
    loader = DocumentLoader()
    
    # 测试加载文本文件
    test_file = "test.txt"
    if os.path.exists(test_file):
        docs = loader.load_single_document(test_file)
        print(f"Loaded {len(docs)} documents from {test_file}")
        for doc in docs:
            print(f"Content: {doc.page_content[:100]}...")
            print(f"Metadata: {doc.metadata}")