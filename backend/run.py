"""PyInstaller 入口点 — 启动 FastAPI + uvicorn"""
import sys
import os
import asyncio
import multiprocessing

# Windows 多进程支持
if sys.platform == "win32":
    multiprocessing.freeze_support()
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from app.config import settings


def main():
    print(f"数据目录: {settings.data_dir}")
    print(f"视频目录: {settings.video_source_dir}")
    print(f"启动服务: http://{settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
