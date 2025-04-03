"""日志工具模块，提供统一的日志记录功能"""

import sys
from pathlib import Path
from loguru import logger
from config import LOG_LEVEL, LOG_PATH

# 确保日志目录存在
def ensure_log_directory():
    """确保日志目录存在"""
    log_dir = Path(LOG_PATH)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

# 配置日志格式
def configure_logger():
    """配置日志记录器"""
    # 清除默认处理程序
    logger.remove()
    
    # 添加控制台处理程序
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
    )
    
    # 添加文件处理程序
    log_dir = ensure_log_directory()
    log_file = log_dir / "enterprise_bot.log"
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="10 MB",  # 日志文件达到10MB时轮转
        retention="1 month",  # 保留1个月的日志
        compression="zip",  # 压缩旧日志
    )
    
    logger.info(f"日志配置完成，级别: {LOG_LEVEL}, 文件路径: {log_file}")
    return logger

# 初始化日志配置
configure_logger()

# 导出日志记录器
get_logger = lambda name=None: logger.bind(name=name if name else "enterprise_bot")