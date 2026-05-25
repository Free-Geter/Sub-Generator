from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os

from sqlalchemy import select, delete

from ..models import Task as TaskModel, Segment as SegmentModel, TaskResponse
from ..database import async_session
from ..pipeline.orchestrator import get_orchestrator
from ..services.temp_manager import TempManager

router = APIRouter(prefix="/api/history", tags=["history"])


class BatchDeleteRequest(BaseModel):
    ids: List[str]


class RetranslateRequest(BaseModel):
    target_lang: str = "zh"
    engine: str = "deepl"
    ollama_model: Optional[str] = None  # 用户可选覆盖 Ollama 模型


@router.get("")
async def get_history():
    """获取任务历史列表（按创建时间倒序）"""
    async with async_session() as session:
        result = await session.execute(
            select(TaskModel).order_by(TaskModel.created_at.desc())
        )
        tasks = result.scalars().all()
        return [TaskResponse.model_validate(t) for t in tasks]


@router.delete("/batch")
async def batch_delete_tasks(request: BatchDeleteRequest):
    """批量删除任务"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="请提供要删除的任务ID列表")

    deleted = 0
    for task_id in request.ids:
        async with async_session() as session:
            task = await session.get(TaskModel, task_id)
            if not task:
                continue
            if task.output_file and os.path.isfile(task.output_file):
                try:
                    os.remove(task.output_file)
                except OSError:
                    pass
            TempManager().cleanup_task(task_id)
            await session.execute(delete(SegmentModel).where(SegmentModel.task_id == task_id))
            await session.delete(task)
            await session.commit()
        deleted += 1

    return {"message": f"已删除 {deleted} 个任务", "deleted": deleted}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """永久删除任务及其关联数据"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 删除输出文件
        if task.output_file and os.path.isfile(task.output_file):
            try:
                os.remove(task.output_file)
            except OSError:
                pass

        # 清理临时文件
        TempManager().cleanup_task(task_id)

        # 先删 segments（级联），再删 task
        await session.execute(delete(SegmentModel).where(SegmentModel.task_id == task_id))
        await session.delete(task)
        await session.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.post("/{task_id}/retranslate")
async def retranslate(task_id: str, request: RetranslateRequest):
    """重新翻译"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.status not in ("done", "failed", "cancelled"):
            raise HTTPException(status_code=400, detail="只有已完成、失败或已取消的任务可以重新翻译")

    orchestrator = get_orchestrator()
    asyncio.create_task(
        orchestrator.retranslate(task_id, request.target_lang, request.engine, request.ollama_model)
    )
    return {"message": "重新翻译已启动", "task_id": task_id}
