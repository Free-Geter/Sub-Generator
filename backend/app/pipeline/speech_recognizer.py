import asyncio
import logging
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

    def __init__(self, model_size: str = "medium", device: str = "auto"):
        """
        Args:
            model_size: Whisper 模型大小 (tiny/base/small/medium/large-v2)
            device: 计算设备 (auto/cpu/cuda)
        """
        from faster_whisper import WhisperModel

        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        compute_type = "int8" if device == "cpu" else "float16"

        logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
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
