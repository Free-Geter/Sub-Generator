from fastapi import APIRouter, Query, HTTPException
from ..config import settings
from .settings import _load_settings
import os
import asyncio

router = APIRouter(prefix="/api/videos", tags=["videos"])

SUPPORTED_FORMATS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}


def _get_video_source_dir() -> str:
    """获取视频源目录：优先从持久化配置读取，fallback 到 settings 默认值"""
    saved = _load_settings()
    saved_dir = saved.get("video_source_dir", "")
    return saved_dir if saved_dir else settings.video_source_dir


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_duration(seconds: float) -> str:
    """格式化时长"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@router.get("")
async def list_videos():
    """列出配置目录下的所有视频文件"""
    video_dir = _get_video_source_dir()
    if not os.path.isdir(video_dir):
        return []

    videos = []
    for entry in os.scandir(video_dir):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in SUPPORTED_FORMATS:
                stat = entry.stat()
                videos.append({
                    "name": entry.name,
                    "path": entry.path,
                    "size": stat.st_size,
                    "size_formatted": _format_size(stat.st_size),
                })

    videos.sort(key=lambda v: v["name"])
    return videos


@router.get("/preview")
async def get_video_preview(path: str = Query(...)):
    """获取视频基本信息（时长、格式、大小）"""
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail="不支持的视频格式")

    size = os.path.getsize(path)
    name = os.path.basename(path)

    # 使用 ffprobe 获取时长
    duration = 0.0
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0 and stdout.strip():
            duration = float(stdout.strip())
    except Exception:
        pass

    return {
        "name": name,
        "path": path,
        "size": size,
        "size_formatted": _format_size(size),
        "duration": duration,
        "duration_formatted": _format_duration(duration),
        "format": ext.lstrip("."),
    }
