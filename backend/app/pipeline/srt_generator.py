import os
from typing import List
from dataclasses import dataclass


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int        # 序号，从1开始
    start_time: float  # 起始时间（秒）
    end_time: float    # 结束时间（秒）
    source_text: str   # 原文
    translated_text: str  # 译文（可为空）


class SRTGenerator:
    """SRT 字幕文件生成器"""

    def __init__(self, output_dir: str):
        """
        Args:
            output_dir: SRT 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(
        self,
        segments: List[dict],
        filename: str,
        mode: str = "translated"
    ) -> str:
        """
        生成 SRT 文件

        Args:
            segments: 字幕段落列表
            filename: 输出文件名（不含扩展名）
            mode:
                - "translated": 只输出译文
                - "source": 只输出原文
                - "bilingual": 双语（原文在上，译文在下）

        Returns:
            生成的 SRT 文件完整路径
        """
        srt_content = self._build_srt_content(segments, mode)

        if mode == "bilingual":
            output_filename = f"{filename}_bilingual.srt"
        else:
            output_filename = f"{filename}.srt"

        output_path = os.path.join(self.output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(srt_content)

        return output_path

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        将秒数转换为 SRT 时间戳格式

        例：3723.456 → "01:02:03,456"
        格式：HH:MM:SS,mmm
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _build_srt_content(
        self,
        segments: List[dict],
        mode: str
    ) -> str:
        """
        构建 SRT 文件内容字符串

        SRT 格式：
        1
        00:00:01,000 --> 00:00:04,500
        Hello world

        2
        00:00:05,000 --> 00:00:08,200
        This is subtitle

        每个条目之间用空行分隔。
        """
        lines = []

        for idx, segment in enumerate(segments, start=1):
            start_ts = self.format_timestamp(segment["start_time"])
            end_ts = self.format_timestamp(segment["end_time"])

            source_text = segment.get("source_text", "")
            translated_text = segment.get("translated_text", "")

            if mode == "source":
                text = source_text
            elif mode == "translated":
                text = translated_text if translated_text else source_text
            elif mode == "bilingual":
                text = f"{source_text}\n{translated_text}"
            else:
                text = translated_text if translated_text else source_text

            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")  # 空行分隔

        return "\n".join(lines)
