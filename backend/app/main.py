import sys
import os
import asyncio

# Windows 上必须使用 ProactorEventLoop 才能支持 asyncio subprocess
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .api import videos, tasks, history, settings as settings_api
from .ws import progress as ws_progress


def _get_frontend_dir() -> str:
    """获取前端静态文件目录，兼容 PyInstaller 打包和开发模式"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，资源在 _MEIPASS 临时目录
        return os.path.join(sys._MEIPASS, "frontend")
    else:
        # 开发模式：相对于 backend 目录
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(title="视频字幕自动生成", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(videos.router)
app.include_router(tasks.router)
app.include_router(history.router)
app.include_router(settings_api.router)
app.include_router(ws_progress.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# ── 静态文件服务（前端 SPA）──
frontend_dir = _get_frontend_dir()
if os.path.isdir(frontend_dir):
    # 挂载静态资源（js/css 等）
    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 回退：所有非 API 路由返回 index.html"""
        # 跳过 API 路由
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        # 尝试返回前端文件
        file_path = os.path.join(frontend_dir, full_path) if full_path else frontend_dir
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # SPA 回退
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        from fastapi import HTTPException
        raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
