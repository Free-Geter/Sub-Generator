import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RecognizedSegment:
    """识别出的文本片段"""
    start_time: float  # 起始时间（秒）
    end_time: float    # 结束时间（秒）
    text: str          # 识别文本
    language: str      # 检测到的语言


class SpeechRecognizer:
    """基于 faster-whisper 的语音识别器"""

    def __init__(self, model_size: str = "medium", device: str = "auto", download_root: str = None):
        """
        Args:
            model_size: Whisper 模型大小 (tiny/base/small/medium/large-v2)
            device: 计算设备 (auto/cpu/cuda)
            download_root: 模型下载/缓存目录，默认使用 faster-whisper 内置路径
        """
        import os
        from faster_whisper import WhisperModel

        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # Windows CUDA 下限制底层库线程，避免死锁
        if device == "cuda":
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            os.environ.setdefault("MKL_NUM_THREADS", "1")
            os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

        compute_type = "int8" if device == "cpu" else "float16"

        # 设置 HuggingFace 缓存目录，使模型下载到指定位置
        if download_root:
            os.makedirs(download_root, exist_ok=True)
            os.environ["HF_HOME"] = download_root
            logger.info(f"Model cache directory set to: {download_root}")

        logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=download_root if download_root else None,
            cpu_threads=1,
            num_workers=1,
        )
        logger.info("Whisper model loaded successfully")

    async def recognize_chunks(
        self,
        chunk_paths: List[str],
        chunk_duration: int = 600,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> tuple[List[RecognizedSegment], str]:
        """
        识别所有音频片段

        Args:
            chunk_paths: 音频片段文件路径列表
            chunk_duration: 每片时长（用于计算绝对时间偏移）
            progress_callback: 进度回调 (0-100)

        Returns:
            (segments列表, 检测到的语言)
        """
        all_segments: List[RecognizedSegment] = []
        detected_language = "en"
        total_chunks = len(chunk_paths)

        for idx, chunk_path in enumerate(chunk_paths):
            time_offset = idx * chunk_duration

            # 防御性检查：确保音频文件存在
            if not os.path.exists(chunk_path):
                logger.warning(f"Chunk file not found, skipping: {chunk_path}")
                continue
            file_size = os.path.getsize(chunk_path)
            if file_size == 0:
                logger.warning(f"Chunk file is empty, skipping: {chunk_path}")
                continue

            segments, language = await asyncio.to_thread(
                self._recognize_single_chunk, chunk_path, time_offset
            )

            all_segments.extend(segments)
            if language:
                detected_language = language

            if progress_callback:
                progress = (idx + 1) / total_chunks * 100
                progress_callback(progress)

        return all_segments, detected_language

    def _recognize_single_chunk(
        self,
        chunk_path: str,
        time_offset: float,
    ) -> tuple[List[RecognizedSegment], str]:
        """
        识别单个音频片段（同步方法，在线程中调用）

        Args:
            chunk_path: 音频文件路径
            time_offset: 时间偏移量（该片段在原视频中的起始时间）

        Returns:
            (segments列表, 检测语言)
        """
        logger.info(f"Recognizing chunk: {chunk_path} with offset {time_offset}s")

        segments_iter, info = self.model.transcribe(chunk_path, beam_size=5)
        detected_language = info.language

        logger.info(
            f"Detected language: {detected_language} "
            f"(probability: {info.language_probability:.2f})"
        )

        recognized_segments: List[RecognizedSegment] = []
        for segment in segments_iter:
            recognized_segments.append(
                RecognizedSegment(
                    start_time=segment.start + time_offset,
                    end_time=segment.end + time_offset,
                    text=segment.text.strip(),
                    language=detected_language,
                )
            )

        logger.info(f"Recognized {len(recognized_segments)} segments from {chunk_path}")
        return recognized_segments, detected_language
