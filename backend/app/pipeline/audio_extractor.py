import asyncio
import logging
import math
import os
import subprocess
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class AudioExtractor:
    """FFmpeg 音频提取器，支持流式提取和时间分片

    使用 subprocess.run + asyncio.to_thread 方案，兼容所有平台的 asyncio 事件循环。
    """

    def __init__(self, chunk_duration: int = 600):
        """
        Args:
            chunk_duration: 分片时长（秒），默认600秒（10分钟）
        """
        self.chunk_duration = chunk_duration

    async def get_video_duration(self, video_path: str) -> float:
        """获取视频总时长（秒），使用 ffprobe 命令获取"""
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe 获取视频时长失败 (code={result.returncode}): {result.stderr.strip()}"
            )

        duration_str = result.stdout.strip()
        if not duration_str:
            raise RuntimeError("ffprobe 返回空的时长信息")

        return float(duration_str)

    async def extract_audio_chunks(
        self,
        video_path: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> List[str]:
        """
        从视频提取音频并分片

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            progress_callback: 进度回调 (0-100)

        Returns:
            音频片段文件路径列表
        """
        os.makedirs(output_dir, exist_ok=True)

        duration = await self.get_video_duration(video_path)
        total_chunks = math.ceil(duration / self.chunk_duration)

        chunk_paths: List[str] = []

        for i in range(total_chunks):
            start_time = i * self.chunk_duration
            # 最后一片可能不足 chunk_duration
            chunk_len = min(self.chunk_duration, duration - start_time)

            output_path = os.path.join(output_dir, f"chunk_{i + 1:03d}.wav")

            result_path = await self._extract_chunk(video_path, output_path, start_time, chunk_len)
            if result_path:
                chunk_paths.append(result_path)
            else:
                logger.warning(f"Chunk {i + 1}/{total_chunks} was empty, skipping")

            if progress_callback:
                progress = (i + 1) / total_chunks * 100
                progress_callback(progress)

        return chunk_paths

    async def _extract_chunk(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float,
    ) -> str:
        """提取单个音频片段

        使用 ffmpeg 命令行提取指定时间段的音频，输出为 16kHz 单声道 WAV。
        提取后验证文件存在且非空。
        """
        # 跳过时长为 0 或极短的片段（可能出现在视频末尾边界）
        if duration < 0.5:
            logger.warning(f"Skipping chunk at {start_time}s: duration too short ({duration:.1f}s)")
            return ""

        result = await asyncio.to_thread(
            subprocess.run,
            [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-ss", str(start_time),
                "-t", str(duration),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                output_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg 提取音频片段失败 (code={result.returncode}): {result.stderr.strip()}"
            )

        # 验证输出文件存在且非空
        if not os.path.exists(output_path):
            raise RuntimeError(
                f"ffmpeg 返回成功但输出文件不存在: {output_path}"
            )
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            logger.warning(f"Chunk at {start_time}s is empty (0 bytes), skipping")
            os.remove(output_path)
            return ""

        logger.debug(f"Extracted chunk: {output_path} ({file_size} bytes, {duration:.1f}s)")
        return output_path
