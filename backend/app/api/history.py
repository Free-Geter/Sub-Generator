from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from sqlalchemy import select

from ..models import Task as TaskModel, TaskResponse
from ..database import async_session
from ..pipeline.orchestrator import get_orchestrator

router = APIRouter(prefix="/api/history", tags=["history"])


class RetranslateRequest(BaseModel):
    target_lang: str = "zh"
    engine: str = "deepl"


@router.get("")
async def get_history():
    """获取任务历史列表（按创建时间倒序）"""
    async with async_session() as session:
        result = await session.execute(
            select(TaskModel).order_by(TaskModel.created_at.desc())
        )
        tasks = result.scalars().all()
        return [TaskResponse.model_validate(t) for t in tasks]


@router.post("/{task_id}/retranslate")
async def retranslate(task_id: str, request: RetranslateRequest):
    """重新翻译"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.status not in ("done", "failed"):
            raise HTTPException(status_code=400, detail="只有已完成或失败的任务可以重新翻译")

    orchestrator = get_orchestrator()
    asyncio.create_task(
        orchestrator.retranslate(task_id, request.target_lang, request.engine)
    )
    return {"message": "重新翻译已启动", "task_id": task_id}
