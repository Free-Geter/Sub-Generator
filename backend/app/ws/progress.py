from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.progress import progress_manager

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket 进度推送端点"""
    await progress_manager.connect(task_id, websocket)
    try:
        while True:
            # 保持连接，等待客户端消息（或断开）
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_manager.disconnect(task_id, websocket)
