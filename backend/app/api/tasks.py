from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import uuid
import asyncio
import os
from datetime import datetime

from ..models import Task as TaskModel, TaskCreate, TaskResponse
from ..database import async_session
from ..pipeline.orchestrator import get_orchestrator
from ..config import settings

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    """创建字幕生成任务"""
    # 校验文件存在
    if not os.path.isfile(task_data.video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    video_name = os.path.basename(task_data.video_path)
    video_size = os.path.getsize(task_data.video_path)

    task_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # 创建数据库记录
    async with async_session() as session:
        task = TaskModel(
            id=task_id,
            video_path=task_data.video_path,
            video_name=video_name,
            video_size=video_size,
            status="pending",
            target_lang=task_data.target_lang,
            translation_engine=task_data.translation_engine,
            whisper_model=task_data.whisper_model,
            progress=0.0,
            created_at=now,
            updated_at=now,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        # 转换为响应模型
        response = TaskResponse.model_validate(task)

    # 启动 pipeline（不阻塞响应）
    orchestrator = get_orchestrator()
    asyncio.create_task(orchestrator.run_pipeline(task_id))

    return response


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务状态"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.status in ("done", "failed", "cancelled"):
            raise HTTPException(status_code=400, detail=f"任务已处于终态: {task.status}")

    orchestrator = get_orchestrator()
    await orchestrator.cancel_task(task_id)
    return {"message": "任务已取消", "task_id": task_id}


@router.get("/{task_id}/srt")
async def download_srt(task_id: str):
    """下载 SRT 文件"""
    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if not task.output_file:
            raise HTTPException(status_code=400, detail="字幕文件尚未生成")
        if not os.path.isfile(task.output_file):
            raise HTTPException(status_code=404, detail="字幕文件不存在")

        return FileResponse(
            path=task.output_file,
            filename=os.path.basename(task.output_file),
            media_type="application/x-subrip",
        )
