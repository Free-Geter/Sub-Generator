@echo off
title Sub-Generator Server
cd /d "%~dp0backend"

REM ========================================
REM Environment
REM ========================================

REM FFmpeg
set "FFMPEG_BIN=C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
if exist "%FFMPEG_BIN%\ffmpeg.exe" (
    set "PATH=%FFMPEG_BIN%;%PATH%"
) else (
    echo [WARN] FFmpeg not found at %FFMPEG_BIN%
)

REM Proxy for Ollama model downloads
set "HTTP_PROXY=http://127.0.0.1:7890"
set "HTTPS_PROXY=http://127.0.0.1:7890"

REM Use venv Python to avoid Windows App Store stub
set "VENV_PYTHON=%~dp0backend\venv\Scripts\python.exe"

REM ========================================
REM Check Ollama
REM ========================================
echo [CHECK] Ollama service ...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Ollama is not running. Translation will fail.
    echo        Start Ollama first: ollama serve
) else (
    echo [ OK ] Ollama is ready
)
echo.

REM ========================================
REM Start server
REM ========================================
echo [START] http://localhost:8000
echo [INFO ] Press Ctrl+C to stop
echo.

REM Open browser
start "" http://localhost:8000

REM Run uvicorn
"%VENV_PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
