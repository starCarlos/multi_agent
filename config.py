"""配置加载模块，负责从.env文件加载配置并提供给应用使用"""

import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.absolute()

# 加载.env文件
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    logger.warning(".env文件不存在，将使用默认配置或环境变量")
    # 如果.env不存在，尝试加载.env.example作为备选
    example_env_path = ROOT_DIR / ".env.example"
    if example_env_path.exists():
        load_dotenv(example_env_path)
        logger.info("已加载.env.example作为配置")

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

# 数据库配置
CHROMADB_PATH = os.getenv("CHROMADB_PATH", str(ROOT_DIR / "data" / "chroma"))
SQLITE_PATH = os.getenv("SQLITE_PATH", str(ROOT_DIR / "data" / "enterprise.db"))

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PATH = os.getenv("LOG_PATH", str(ROOT_DIR / "logs"))

# 应用配置
APP_PORT = int(os.getenv("APP_PORT", 8000))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")

# 向量存储配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-large:latest")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "localhost:11434")
SEARCH_MODES = ["similarity", "mmr", "similarity_score_threshold"]
DEFAULT_SEARCH_MODE = os.getenv("DEFAULT_SEARCH_MODE", "similarity")
MMR_DIVERSITY = float(os.getenv("MMR_DIVERSITY", 0.5))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.6))
DEFAULT_SEARCH_K = int(os.getenv("DEFAULT_SEARCH_K", 5))

# 文档加载配置
SUPPORTED_EXTENSIONS = ['.txt', '.docx', '.md', '.csv', '.xlsx', '.xls']
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))

# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录结构存在"""
    directories = [
        ROOT_DIR / "data",
        ROOT_DIR / "data" / "chroma",
        ROOT_DIR / "logs",
        Path(CHROMADB_PATH).parent,  # 确保chroma索引目录存在
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"确保目录存在: {directory}")

# 配置验证
def validate_config():
    """验证配置是否有效"""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY未设置，某些功能可能无法正常工作")
    
    # 确保目录存在
    ensure_directories()
    
    logger.info("配置加载完成")
    return True