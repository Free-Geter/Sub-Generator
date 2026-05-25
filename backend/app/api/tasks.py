from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import uuid
import asyncio
import os
from datetime import datetime, timezone

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
    now = datetime.now(timezone.utc)

    # 未指定则使用系统设置中的默认值
    engine = task_data.translation_engine or settings.translation_engine
    whisper = task_data.whisper_model or settings.whisper_model

    # 创建数据库记录
    async with async_session() as session:
        task = TaskModel(
            id=task_id,
            video_path=task_data.video_path,
            video_name=video_name,
            video_size=video_size,
            status="pending",
            target_lang=task_data.target_lang,
            translation_engine=engine,
            whisper_model=whisper,
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


@router.post("/{task_id}/rerun")
async def rerun_task(task_id: str):
    """重新执行任务（从头运行完整流水线）"""
    from sqlalchemy import delete
    from ..models import Segment as SegmentModel

    async with async_session() as session:
        task = await session.get(TaskModel, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 先取消正在运行的（如果有）
        orchestrator = get_orchestrator()
        await orchestrator.cancel_task(task_id)

        # 删除旧的 segments
        await session.execute(delete(SegmentModel).where(SegmentModel.task_id == task_id))

        # 重置任务状态
        task.status = "pending"
        task.progress = 0.0
        task.error_message = None
        task.output_file = None
        task.source_lang = None
        task.created_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        await session.commit()

    # 启动 pipeline
    asyncio.create_task(orchestrator.run_pipeline(task_id))
    return {"message": "任务已重新执行", "task_id": task_id}


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
