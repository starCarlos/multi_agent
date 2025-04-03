"""数据库操作模块，提供SQLite数据库的连接和操作"""

import os
from typing import Dict, List, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from loguru import logger
from config import SQLITE_PATH
from utils.logger import get_logger

# 获取日志记录器
log = get_logger("database")

# 创建SQLAlchemy基类
Base = declarative_base()

# 定义数据库模型
class Conversation(Base):
    """对话表"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(50), unique=True, nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    talk = Column(Text, nullable=True)  # JSON格式存储
    
    # 关系
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False)
    conversation_id = Column(String(50), ForeignKey("conversations.conversation_id"))
    role = Column(String(20), nullable=False)  # user 或 system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")

class DocumentFingerprint(Base):
    """文档指纹表，用于存储已处理文档的指纹"""
    __tablename__ = "document_fingerprints"
    
    id = Column(Integer, primary_key=True)
    fingerprint = Column(String(50), unique=True, nullable=False)
    doc_metadata = Column(Text, nullable=True)  # JSON格式存储文档元数据
    created_at = Column(DateTime, default=datetime.now)

# 数据库连接和会话
class Database:
    """数据库操作类"""
    def __init__(self, db_path: str = SQLITE_PATH):
        """初始化数据库连接"""
        self.db_path = db_path
        self.engine = None
        self.Session = None
        self.initialize()
    
    def initialize(self):
        """初始化数据库"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # 创建数据库引擎
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        
        # 创建表
        Base.metadata.create_all(self.engine)
        
        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)
        
        log.info(f"数据库初始化完成: {self.db_path}")
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            log.info("数据库连接已关闭")

# 创建全局数据库实例
db = Database()

# 数据库操作函数
def create_conversation() -> str:
    """创建新对话"""
    from utils.helpers import generate_id
    
    session = db.get_session()
    try:
        # 创建对话
        conversation_id = generate_id("conv")
        conversation = Conversation(conversation_id=conversation_id)
        session.add(conversation)
        session.commit()
        log.info(f"创建新对话: {conversation_id}")
        return conversation_id
    finally:
        session.close()

def add_message(conversation_id: str, role: str, content: str) -> Message:
    """添加消息到对话"""
    from utils.helpers import generate_id
    
    session = db.get_session()
    try:
        # 检查对话是否存在
        conversation = session.query(Conversation).filter_by(conversation_id=conversation_id).first()
        if not conversation:
            log.error(f"对话不存在: {conversation_id}")
            raise ValueError(f"对话不存在: {conversation_id}")
        
        # 添加消息
        message_id = generate_id("msg")
        message = Message(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        session.add(message)
        session.commit()
        log.debug(f"添加消息: {message_id} 到对话: {conversation_id}")
        return message
    finally:
        session.close()

def get_conversation_history(conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """获取对话历史"""
    session = db.get_session()
    try:
        messages = session.query(Message).filter_by(conversation_id=conversation_id)\
            .order_by(Message.timestamp.desc()).limit(limit).all()
        
        # 转换为字典列表
        history = [
            {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in reversed(messages)  # 反转顺序，使最早的消息在前
        ]
        
        return history
    finally:
        session.close()

def get_doc_fingerprints() -> List[str]:
    """获取所有文档指纹"""
    session = db.get_session()
    try:
        fingerprints = session.query(DocumentFingerprint.fingerprint).all()
        return [fp[0] for fp in fingerprints]
    finally:
        session.close()

def add_doc_fingerprints(fingerprints: List[str], metadata_list: List[Dict[str, Any]] = None):
    """批量添加文档指纹
    
    Args:
        fingerprints: 文档指纹列表
        metadata_list: 对应的元数据列表，可选
    """
    import json
    
    if not fingerprints:
        return
    
    if metadata_list is None:
        metadata_list = [None] * len(fingerprints)
    
    session = db.get_session()
    try:
        for i, fingerprint in enumerate(fingerprints):
            metadata_json = None
            if i < len(metadata_list) and metadata_list[i]:
                metadata_json = json.dumps(metadata_list[i])
            
            doc_fp = DocumentFingerprint(
                fingerprint=fingerprint,
                doc_metadata=metadata_json
            )
            session.add(doc_fp)
        
        session.commit()
        log.debug(f"添加了 {len(fingerprints)} 个文档指纹")
    except Exception as e:
        session.rollback()
        log.error(f"添加文档指纹失败: {str(e)}")
    finally:
        session.close()

def clear_doc_fingerprints():
    """清除所有文档指纹"""
    session = db.get_session()
    try:
        count = session.query(DocumentFingerprint).delete()
        session.commit()
        log.info(f"清除了 {count} 个文档指纹")
    finally:
        session.close()
