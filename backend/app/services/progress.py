import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ProgressManager:
    """WebSocket 进度推送管理"""

    def __init__(self):
        # task_id -> set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """注册 WebSocket 连接"""
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task {task_id}, total: {len(self._connections[task_id])}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        """移除连接"""
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]
            logger.info(f"WebSocket disconnected for task {task_id}")

    async def broadcast(self, task_id: str, data: dict):
        """广播进度消息给所有订阅该任务的客户端

        消息格式：
        {
            "task_id": str,
            "step": str,  # "extracting"/"recognizing"/"translating"/"generating"/"done"/"failed"
            "progress": float,  # 0-100
            "message": str  # 人类可读的状态描述
        }
        """
        if task_id not in self._connections:
            return

        dead_connections: Set[WebSocket] = set()
        message = json.dumps(data, ensure_ascii=False)

        for ws in self._connections[task_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.add(ws)

        # 清理已断开的连接
        for ws in dead_connections:
            self._connections[task_id].discard(ws)

        if task_id in self._connections and not self._connections[task_id]:
            del self._connections[task_id]


# 全局单例
progress_manager = ProgressManager()
