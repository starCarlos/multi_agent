"""API服务器配置模块，提供FastAPI服务器配置"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from datetime import datetime

from api.routes import router
from utils.logger import get_logger
from config import validate_config

# 验证配置
validate_config()

# 获取日志记录器
log = get_logger("server")

# 创建FastAPI应用
app = FastAPI(
    title="企业智能机器人API",
    description="基于LangGraph构建的企业智能机器人系统API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求计时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# 包含API路由
app.include_router(router)

# 根路径
@app.get("/")
async def root():
    return {
        "name": "企业智能机器人API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    log.info("API服务器启动")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    log.info("API服务器关闭")