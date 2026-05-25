# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 将后端 + 前端打包为单个 .exe"""

import os
from pathlib import Path

# PyInstaller 提供 SPECPATH 变量指向 spec 文件所在目录
BACKEND_DIR = Path(SPECPATH).resolve()                    # Sub-Generator/backend/
PROJECT_DIR = BACKEND_DIR.parent                          # Sub-Generator/
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

# 前端静态文件
frontend_datas = []
if FRONTEND_DIST.is_dir():
    for root, dirs, files in os.walk(str(FRONTEND_DIST)):
        for f in files:
            src = os.path.join(root, f)
            # 目标路径：frontend/ 下的相对路径
            rel = os.path.relpath(src, str(FRONTEND_DIST))
            dst_dir = os.path.join("frontend", os.path.dirname(rel))
            frontend_datas.append((src, dst_dir))

a = Analysis(
    ["run.py"],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=[
        *frontend_datas,
        # .env 配置文件（可选）
        (str(BACKEND_DIR / ".env"), "."),
    ],
    hiddenimports=[
        # FastAPI / uvicorn
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # faster-whisper 依赖
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        # SQLAlchemy
        "sqlalchemy",
        "aiosqlite",
        # WebSocket
        "websockets",
        # HTTP
        "httpx",
        "httpcore",
        # Pydantic
        "pydantic",
        "pydantic_settings",
        # ffmpeg-python
        "ffmpeg",
        # Others
        "deepl",
        "openai",
        "python_dotenv",
        # App modules
        "app",
        "app.main",
        "app.config",
        "app.database",
        "app.models",
        "app.api",
        "app.api.videos",
        "app.api.tasks",
        "app.api.history",
        "app.api.settings",
        "app.pipeline",
        "app.pipeline.audio_extractor",
        "app.pipeline.speech_recognizer",
        "app.pipeline.translator",
        "app.pipeline.srt_generator",
        "app.pipeline.orchestrator",
        "app.services",
        "app.services.ollama_client",
        "app.services.progress",
        "app.services.temp_manager",
        "app.ws",
        "app.ws.progress",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "cv2",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SubGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # 显示控制台（可看到日志）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
