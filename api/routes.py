"""API路由定义模块，提供REST API接口"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid
import json

from models.schema import UserInput, SystemResponse
from models.database import create_conversation, add_message, get_conversation_history
from workflows.graph import build_enterprise_bot_graph
from workflows.router import State
from utils.logger import get_logger
from fastapi.websockets import WebSocketState  # 新增导入

# 获取日志记录器
log = get_logger("api")

# 创建路由器
router = APIRouter(prefix="/api", tags=["enterprise-bot"])

# 存储活跃的WebSocket连接
active_connections = {}

# 健康检查端点
@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# WebSocket连接端点
@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    log.info(f"WebSocket连接已建立: {conversation_id}")
    
    # 将连接添加到活跃连接字典中
    if conversation_id not in active_connections:
        active_connections[conversation_id] = []
    active_connections[conversation_id].append(websocket)
    
    log.info(f"WebSocket连接已建立: {conversation_id}")
    
    try:
        while True:
            # 添加心跳检测
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                log.debug("收到并响应心跳检测")
    except WebSocketDisconnect:
        # 连接断开时从活跃连接中移除
        active_connections[conversation_id].remove(websocket)
        if not active_connections[conversation_id]:
            del active_connections[conversation_id]
        log.info(f"WebSocket连接已断开: {conversation_id}")

# 对话端点
@router.post("/chat", response_model=SystemResponse)
async def chat(user_input: UserInput, background_tasks: BackgroundTasks):
    """处理用户对话请求"""
    log.info(f"收到用户消息: {user_input.message[:50]}...")
    
    # 创建或获取对话
    conversation_id = user_input.context.get("conversation_id") if user_input.context else None
    if not conversation_id:
        conversation_id = create_conversation()
    
    # 添加用户消息到数据库
    add_message(conversation_id, "user", user_input.message)
    
    # 获取对话历史
    history = get_conversation_history(conversation_id)
    
    # 立即通过WebSocket发送开始处理通知
    if conversation_id in active_connections:
        start_data = {
            "conversation_id": conversation_id,
            "status": "started",
            "message": "开始处理您的请求..."
        }
        for connection in active_connections[conversation_id]:
            await send_websocket_message(connection, start_data)

    async def process_message():
        try:
            log.info(f"开始处理消息流，conversation_id: {conversation_id}")
            graph = build_enterprise_bot_graph()
            init_state = State(
                message=user_input.message,
                conversation_id=conversation_id,
                history=history,
                current_tool=None,
                tools_response=[]
            )
            json_del = False
            async for step in graph.astream_events(init_state,version="v2"):
                # log.info(f"当前event: {step}")
                if step["event"] == "on_chat_model_stream":
                    response = step["data"]["chunk"].content
                    if not json_del:
                        # 检查是否以 "```json" 开头
                        if response.startswith("```json") or response.startswith("{"):
                            json_del = True
                            continue
                    if json_del:
                        # 检查是否以 "```" 结尾
                        if response.endswith("```") or response.endswith("}"):
                            json_del = False

                        continue
                    if conversation_id in active_connections:
                        response_data = {
                            "conversation_id": conversation_id,
                            "status": "streaming",
                            "message": response,
                        }
                        for connection in active_connections[conversation_id]:
                            await send_websocket_message(connection, response_data)
                elif step["event"] == "on_chain_end":
                    output = step["data"]["output"]
                    if not isinstance(output, dict):
                        if isinstance(output, str) and output=="__end__":
                            break
                        continue
                    # 实时发送每个状态更新
                    if output.get("response"):
                        response = output.get("response")
                        add_message(conversation_id, "system", response)
                        
                        if conversation_id in active_connections:
                            response_data = {
                                "conversation_id": conversation_id,
                                "status": "completed" if output.get("is_final") else "processing",
                                "message": response,
                            }
                            for connection in active_connections[conversation_id]:
                                await send_websocket_message(connection, response_data)
                    
                    elif output.get("current_tool") and step["tags"][0].startswith("graph"):
                        # log.info(f"event:{step}")
                        tool_response = ""
                        if output.get('tools_response') not in [None,""]:
                            for tool in output.get('tools_response'):
                                log.info(f"当前工具response: {tool}")
                                if tool.get("node") == output.get('current_tool'):
                                    if tool.get("result"):
                                        tool_response += tool.get("result") + "\n"
                        
                        if conversation_id in active_connections:
                            tool_data = {
                                "conversation_id": conversation_id,
                                "status": "tool",
                                "message": tool_response,
                                "tool_name": output.get('current_tool')
                            }
                            for connection in active_connections[conversation_id]:
                                await send_websocket_message(connection, tool_data)
            
        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            log.error(error_msg)
            add_message(conversation_id, "system", f"处理请求时出现错误: {str(e)}")
            
            if conversation_id in active_connections:
                error_data = {
                    "conversation_id": conversation_id,
                    "status": "error",
                    "message": f"处理请求时出现错误: {str(e)}",
                }
                for connection in active_connections[conversation_id]:
                    await send_websocket_message(connection, error_data)
    
    background_tasks.add_task(process_message)
    
    return SystemResponse(
        response_id=f"resp_{uuid.uuid4()}",
        message="您的请求正在处理中，请稍候...",
        data={
            "conversation_id": conversation_id,
            "status": "processing"
        }
    )

# 辅助函数：发送WebSocket消息
async def send_websocket_message(websocket: WebSocket, data: dict):
    """发送WebSocket消息"""
    try:
        if websocket.application_state == WebSocketState.CONNECTED:
            log.debug(f"准备发送消息到 {websocket}: {data}")  # 新增调试日志
            await websocket.send_json(data)
            await websocket.send_text("")  # 发送空消息确保通道畅通
            log.debug(f"已发送WebSocket消息: {data}")  # 修改日志级别为info
        else:
            log.warning(f"连接状态异常: {websocket.application_state}")
    except WebSocketDisconnect:
        log.warning("客户端已主动断开连接")
    except Exception as e:
        log.error(f"发送WebSocket消息失败: {str(e)}", exc_info=True)
        # 从活跃连接中移除
        for conv_id, connections in active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del active_connections[conv_id]

# 获取对话历史端点
@router.get("/conversations/{conversation_id}/history")
async def get_history(conversation_id: str, limit: int = 10):
    """获取对话历史"""
    try:
        history = get_conversation_history(conversation_id, limit)
        return {"conversation_id": conversation_id, "messages": history}
    except Exception as e:
        log.error(f"获取对话历史时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取对话状态端点
@router.get("/conversations/{conversation_id}/status")
async def get_conversation_status(conversation_id: str):
    """获取对话处理状态"""
    try:
        # 获取最新消息
        history = get_conversation_history(conversation_id, 1)
        if not history:
            return {"status": "not_found"}
        
        latest_message = history[0]
        is_system_message = latest_message.get("role") == "system"
        
        return {
            "conversation_id": conversation_id,
            "status": "completed" if is_system_message else "processing",
            "latest_message": latest_message
        }
    except Exception as e:
        log.error(f"获取对话状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))