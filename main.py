"""企业智能机器人主程序入口"""

import uvicorn
from loguru import logger
from config import validate_config, APP_HOST, APP_PORT

# 导入API服务器
from api.server import app

# 验证配置
validate_config()

def main():
    """主程序入口"""
    logger.info("启动企业智能机器人服务...")
    logger.info(f"服务将在 {APP_HOST}:{APP_PORT} 上运行")
    
    # 启动FastAPI服务器
    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT,reload=True)

if __name__ == "__main__":
    main()