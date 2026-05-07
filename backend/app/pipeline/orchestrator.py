import asyncio
import logging
import uuid
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from ..config import Settings
from ..models import Task as TaskModel, Segment as SegmentModel
from ..database import async_session
from ..services.progress import progress_manager
from ..services.temp_manager import TempManager
from .audio_extractor import AudioExtractor
from .speech_recognizer import SpeechRecognizer
from .translator import Translator
from .srt_generator import SRTGenerator

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """字幕生成流水线编排器"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.temp_manager = TempManager()
        self._running_tasks: dict[str, asyncio.Event] = {}  # task_id -> cancel_event

    async def run_pipeline(self, task_id: str):
        """
        执行完整的字幕生成流水线

        步骤：
        1. 文件校验（格式、大小、可读性）
        2. FFmpeg 提取音频（分片）
        3. 逐片语音识别
        4. 合并所有片段并保存到数据库
        5. 翻译
        6. 生成 SRT
        7. 清理临时文件
        """
        cancel_event = asyncio.Event()
        self._running_tasks[task_id] = cancel_event

        try:
            # 从数据库获取任务信息
            async with async_session() as session:
                task = await session.get(TaskModel, task_id)
                if not task:
                    logger.error(f"Task {task_id} not found in database")
                    return
                video_path = task.video_path
                target_lang = task.target_lang
                engine = task.translation_engine
                whisper_model = task.whisper_model

            # Step 1: 文件校验
            await self._update_task_status(task_id, "extracting", 0, "校验文件...")
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            if cancel_event.is_set():
                await self._handle_cancelled(task_id)
                return

            # Step 2: 音频提取
            await self._update_task_status(task_id, "extracting", 5, "提取音频中...")
            temp_dir = self.temp_manager.create_task_dir(task_id)
            extractor = AudioExtractor(chunk_duration=self.settings.chunk_duration)

            loop = asyncio.get_running_loop()

            # AudioExtractor 的 callback 在事件循环线程中被同步调用（未 await）
            def extract_progress(p):
                asyncio.ensure_future(
                    self._update_task_status(task_id, "extracting", 5 + p * 0.25, f"提取音频: {p:.0f}%")
                )

            chunks = await extractor.extract_audio_chunks(video_path, temp_dir, extract_progress)

            if cancel_event.is_set():
                await self._handle_cancelled(task_id)
                return

            # Step 3: 语音识别
            await self._update_task_status(task_id, "recognizing", 30, "语音识别中...")
            recognizer = SpeechRecognizer(model_size=whisper_model, device=self.settings.whisper_device)

            # SpeechRecognizer 的 callback 在子线程中调用（通过 asyncio.to_thread）
            def recognize_progress(p):
                asyncio.run_coroutine_threadsafe(
                    self._update_task_status(task_id, "recognizing", 30 + p * 0.3, f"语音识别: {p:.0f}%"),
                    loop,
                )

            segments, source_lang = await recognizer.recognize_chunks(
                chunks, self.settings.chunk_duration, recognize_progress
            )

            if cancel_event.is_set():
                await self._handle_cancelled(task_id)
                return

            # Step 4: 保存识别结果到数据库
            await self._update_task_status(task_id, "recognizing", 60, "保存识别结果...")
            async with async_session() as session:
                task = await session.get(TaskModel, task_id)
                task.source_lang = source_lang
                for seg in segments:
                    db_segment = SegmentModel(
                        id=str(uuid.uuid4()),
                        task_id=task_id,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        source_text=seg.text,
                    )
                    session.add(db_segment)
                await session.commit()

            if cancel_event.is_set():
                await self._handle_cancelled(task_id)
                return

            # Step 5: 翻译
            await self._update_task_status(task_id, "translating", 62, "翻译中...")
            translator = Translator(
                engine=engine,
                config={
                    "deepl_api_key": self.settings.deepl_api_key,
                    "openai_api_key": self.settings.openai_api_key,
                    "openai_base_url": self.settings.openai_base_url,
                    "ollama_base_url": self.settings.ollama_base_url,
                    "ollama_model": self.settings.ollama_model,
                },
            )

            seg_dicts = [
                {"start_time": s.start_time, "end_time": s.end_time, "source_text": s.text}
                for s in segments
            ]

            # Translator 的 callback 在事件循环线程中被同步调用（未 await）
            def translate_progress(p):
                asyncio.ensure_future(
                    self._update_task_status(task_id, "translating", 62 + p * 0.28, f"翻译: {p:.0f}%")
                )

            translated = await translator.translate_segments(seg_dicts, target_lang, translate_progress)

            if cancel_event.is_set():
                await self._handle_cancelled(task_id)
                return

            # 更新数据库中的翻译结果
            async with async_session() as session:
                result = await session.execute(
                    select(SegmentModel)
                    .where(SegmentModel.task_id == task_id)
                    .order_by(SegmentModel.start_time)
                )
                db_segments = result.scalars().all()
                for db_seg, trans_seg in zip(db_segments, translated):
                    db_seg.translated_text = trans_seg.translated_text
                await session.commit()

            # Step 6: 生成 SRT
            await self._update_task_status(task_id, "generating", 92, "生成字幕文件...")
            output_dir = os.path.join(self.settings.data_dir, "outputs")
            generator = SRTGenerator(output_dir=output_dir)

            srt_segments = [
                {
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "source_text": t.source_text,
                    "translated_text": t.translated_text,
                }
                for t in translated
            ]

            video_name = os.path.splitext(os.path.basename(video_path))[0]
            srt_path = generator.generate(srt_segments, f"{video_name}_{task_id[:8]}", mode="translated")

            # Step 7: 清理 & 完成
            self.temp_manager.cleanup_task(task_id)

            async with async_session() as session:
                task = await session.get(TaskModel, task_id)
                task.status = "done"
                task.progress = 100
                task.output_file = srt_path
                task.updated_at = datetime.utcnow()
                await session.commit()

            await progress_manager.broadcast(task_id, {
                "task_id": task_id,
                "step": "done",
                "progress": 100,
                "message": "完成",
            })

        except Exception as e:
            logger.exception(f"Pipeline failed for task {task_id}: {e}")
            await self._mark_failed(task_id, str(e))
        finally:
            self._running_tasks.pop(task_id, None)

    async def cancel_task(self, task_id: str):
        """取消正在运行的任务"""
        cancel_event = self._running_tasks.get(task_id)
        if cancel_event:
            cancel_event.set()
            logger.info(f"Cancel signal sent for task {task_id}")

        # 更新数据库状态
        async with async_session() as session:
            task = await session.get(TaskModel, task_id)
            if task and task.status not in ("done", "failed", "cancelled"):
                task.status = "cancelled"
                task.updated_at = datetime.utcnow()
                await session.commit()

        self.temp_manager.cleanup_task(task_id)
        await progress_manager.broadcast(task_id, {
            "task_id": task_id,
            "step": "failed",
            "progress": 0,
            "message": "任务已取消",
        })

    async def retranslate(self, task_id: str, target_lang: str, engine: str):
        """
        重新翻译（复用已识别的原文）

        1. 从数据库读取该任务的所有 Segment
        2. 仅执行翻译步骤
        3. 更新 Segment.translated_text
        4. 重新生成 SRT
        """
        try:
            # 加载现有 segments
            async with async_session() as session:
                task = await session.get(TaskModel, task_id)
                if not task:
                    raise ValueError(f"Task {task_id} not found")

                result = await session.execute(
                    select(SegmentModel)
                    .where(SegmentModel.task_id == task_id)
                    .order_by(SegmentModel.start_time)
                )
                db_segments = result.scalars().all()

                if not db_segments:
                    raise ValueError(f"No segments found for task {task_id}")

                video_path = task.video_path

            # 更新任务状态
            await self._update_task_status(task_id, "translating", 0, "重新翻译中...")

            # 创建翻译器
            translator = Translator(
                engine=engine,
                config={
                    "deepl_api_key": self.settings.deepl_api_key,
                    "openai_api_key": self.settings.openai_api_key,
                    "openai_base_url": self.settings.openai_base_url,
                    "ollama_base_url": self.settings.ollama_base_url,
                    "ollama_model": self.settings.ollama_model,
                },
            )

            seg_dicts = [
                {
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "source_text": s.source_text,
                }
                for s in db_segments
            ]

            def translate_progress(p):
                asyncio.ensure_future(
                    self._update_task_status(task_id, "translating", p, f"翻译: {p:.0f}%")
                )

            translated = await translator.translate_segments(seg_dicts, target_lang, translate_progress)

            # 更新数据库
            async with async_session() as session:
                result = await session.execute(
                    select(SegmentModel)
                    .where(SegmentModel.task_id == task_id)
                    .order_by(SegmentModel.start_time)
                )
                db_segs = result.scalars().all()
                for db_seg, trans_seg in zip(db_segs, translated):
                    db_seg.translated_text = trans_seg.translated_text
                await session.commit()

            # 重新生成 SRT
            await self._update_task_status(task_id, "generating", 90, "生成字幕文件...")
            output_dir = os.path.join(self.settings.data_dir, "outputs")
            generator = SRTGenerator(output_dir=output_dir)

            srt_segments = [
                {
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "source_text": t.source_text,
                    "translated_text": t.translated_text,
                }
                for t in translated
            ]

            video_name = os.path.splitext(os.path.basename(video_path))[0]
            srt_path = generator.generate(srt_segments, f"{video_name}_{task_id[:8]}", mode="translated")

            # 完成
            async with async_session() as session:
                task = await session.get(TaskModel, task_id)
                task.status = "done"
                task.progress = 100
                task.target_lang = target_lang
                task.translation_engine = engine
                task.output_file = srt_path
                task.updated_at = datetime.utcnow()
                await session.commit()

            await progress_manager.broadcast(task_id, {
                "task_id": task_id,
                "step": "done",
                "progress": 100,
                "message": "重新翻译完成",
            })

        except Exception as e:
            logger.exception(f"Retranslate failed for task {task_id}: {e}")
            await self._mark_failed(task_id, str(e))

    async def _update_task_status(self, task_id: str, status: str, progress: float, message: str = ""):
        """更新数据库中的任务状态并推送 WebSocket"""
        async with async_session() as session:
            task = await session.get(TaskModel, task_id)
            if task:
                task.status = status
                task.progress = progress
                task.updated_at = datetime.utcnow()
                await session.commit()

        await progress_manager.broadcast(task_id, {
            "task_id": task_id,
            "step": status,
            "progress": progress,
            "message": message,
        })

    async def _mark_failed(self, task_id: str, error: str):
        """标记任务失败"""
        async with async_session() as session:
            task = await session.get(TaskModel, task_id)
            if task:
                task.status = "failed"
                task.error_message = error
                task.updated_at = datetime.utcnow()
                await session.commit()

        await progress_manager.broadcast(task_id, {
            "task_id": task_id,
            "step": "failed",
            "progress": 0,
            "message": f"失败: {error}",
        })

        self.temp_manager.cleanup_task(task_id)

    async def _handle_cancelled(self, task_id: str):
        """处理任务取消"""
        self.temp_manager.cleanup_task(task_id)
        async with async_session() as session:
            task = await session.get(TaskModel, task_id)
            if task:
                task.status = "cancelled"
                task.updated_at = datetime.utcnow()
                await session.commit()

        await progress_manager.broadcast(task_id, {
            "task_id": task_id,
            "step": "failed",
            "progress": 0,
            "message": "任务已取消",
        })


# 全局编排器实例（需要在 main.py 启动时初始化）
orchestrator: Optional[PipelineOrchestrator] = None


def get_orchestrator() -> PipelineOrchestrator:
    """获取编排器实例"""
    global orchestrator
    if orchestrator is None:
        settings = Settings()
        orchestrator = PipelineOrchestrator(settings)
    return orchestrator
